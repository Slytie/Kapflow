from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import mimetypes
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from onetruth.infrastructure.db.session import sqlite_path_from_url

DEFAULT_STORAGE_DIRNAME = "artifact_store"
ArtifactIngressKind = Literal["request_bytes", "local_source_path"]


class ArtifactStorageError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactIngressDescriptor:
    ingress_kind: ArtifactIngressKind
    content_base64: str | None = None
    source_path: str | None = None

    def __post_init__(self) -> None:
        if self.ingress_kind == "request_bytes":
            if self.content_base64 is None or self.source_path is not None:
                raise ArtifactStorageError(
                    "request_bytes ingress requires content_base64 only"
                )
            return
        if self.ingress_kind == "local_source_path":
            if self.source_path is None or self.content_base64 is not None:
                raise ArtifactStorageError(
                    "local_source_path ingress requires source_path only"
                )
            return
        raise ArtifactStorageError(f"unsupported artifact ingress kind: {self.ingress_kind}")

    @classmethod
    def request_bytes(cls, *, content_base64: str) -> ArtifactIngressDescriptor:
        return cls(ingress_kind="request_bytes", content_base64=content_base64)

    @classmethod
    def local_source_path(cls, *, source_path: str) -> ArtifactIngressDescriptor:
        return cls(ingress_kind="local_source_path", source_path=source_path)


def default_storage_root_for_db_url(
    db_url: str,
    *,
    override: str | None = None,
) -> Path:
    if override is not None and override.strip():
        root = Path(override).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    db_path = sqlite_path_from_url(db_url).resolve()
    root = db_path.parent / DEFAULT_STORAGE_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def infer_media_type(filename: str | None, fallback: str = "application/octet-stream") -> str:
    if filename:
        guessed, _ = mimetypes.guess_type(filename)
        if guessed:
            return guessed
    return fallback


def read_bytes_from_file(path: str) -> bytes:
    source = Path(path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise ArtifactStorageError(f"source file not found: {source}")
    return source.read_bytes()


def decode_base64_content(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        raise ArtifactStorageError("invalid content_base64 payload") from exc


def encode_base64_content(content: bytes) -> str:
    return base64.b64encode(content).decode("ascii")


def resolve_artifact_ingress(
    descriptor: ArtifactIngressDescriptor,
) -> tuple[bytes, str]:
    if descriptor.ingress_kind == "local_source_path":
        assert descriptor.source_path is not None
        raw_content = read_bytes_from_file(descriptor.source_path)
        default_name = Path(str(descriptor.source_path)).name
        return raw_content, default_name

    assert descriptor.content_base64 is not None
    raw_content = decode_base64_content(descriptor.content_base64)
    return raw_content, "uploaded_document.bin"


def write_blob(
    *,
    storage_root: Path,
    workflow_run_id: str,
    file_name: str,
    content: bytes,
) -> tuple[str, str, int]:
    digest = hashlib.sha256(content).hexdigest()
    safe_file_name = _sanitize_file_name(file_name)
    target = (
        storage_root
        / workflow_run_id
        / digest[:2]
        / digest
        / safe_file_name
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(content)
    return target.resolve().as_uri(), f"sha256:{digest}", len(content)


def read_blob(storage_uri: str) -> bytes:
    parsed = urlparse(storage_uri)
    if parsed.scheme != "file":
        raise ArtifactStorageError(f"unsupported storage_uri scheme: {parsed.scheme}")
    path = Path(parsed.path)
    if not path.exists() or not path.is_file():
        raise ArtifactStorageError(f"artifact blob not found: {storage_uri}")
    return path.read_bytes()


def _sanitize_file_name(file_name: str) -> str:
    raw = file_name.strip().replace("\\", "/")
    candidate = Path(raw).name
    if not candidate:
        candidate = "artifact.bin"
    return "".join(char if _is_safe(char) else "_" for char in candidate)


def _is_safe(char: str) -> bool:
    return char.isalnum() or char in {".", "-", "_"}
