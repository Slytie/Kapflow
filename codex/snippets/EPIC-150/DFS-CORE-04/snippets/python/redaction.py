"""Illustrative CAPEX path redaction boundary.

Not a production patch. Replace key management, path normalization, and model names
with actual CAPEX implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import hashlib
import hmac
import uuid


@dataclass(frozen=True)
class RedactedPathRef:
    source_root_id: str
    occurrence_id: str
    relative_path_hash: str
    parent_path_hash: str
    extension_hint: str
    filename_display: str
    filename_policy: str
    salt_version: str


def _stable_relpath(root: Path, path: Path) -> str:
    root_resolved = root.resolve(strict=True)
    path_resolved = path.resolve(strict=True)
    rel = path_resolved.relative_to(root_resolved)
    return PurePosixPath(*rel.parts).as_posix()


def _hmac_hex(key: bytes, value: str) -> str:
    return "hmac-sha256:" + hmac.new(
        key,
        value.encode("utf-8", errors="surrogateescape"),
        hashlib.sha256,
    ).hexdigest()


def _extension_hint(path: Path) -> str:
    suffixes = path.suffixes[-2:]
    return "".join(suffixes).lower()[:32]


def _policy_display_name(*, occurrence_counter: int, extension_hint: str, raw_name: str, filename_policy: str) -> str:
    if filename_policy == "raw_allowed":
        return raw_name[:256]
    if filename_policy == "extension_only":
        return f"Document candidate {occurrence_counter:04d}{extension_hint or ''}"
    if filename_policy == "generated_label":
        return f"Document candidate {occurrence_counter:04d}"
    raise ValueError(f"unknown filename policy: {filename_policy}")


def redact_path_for_boundary(
    *,
    source_root_id: str,
    root: Path,
    path: Path,
    project_path_hmac_key: bytes,
    salt_version: str,
    occurrence_counter: int,
    filename_policy: str = "extension_only",
) -> RedactedPathRef:
    rel = _stable_relpath(root, path)
    parent = str(PurePosixPath(rel).parent)
    if parent == ".":
        parent = ""

    ext = _extension_hint(path)
    return RedactedPathRef(
        source_root_id=source_root_id,
        occurrence_id=str(uuid.uuid4()),
        relative_path_hash=_hmac_hex(project_path_hmac_key, rel),
        parent_path_hash=_hmac_hex(project_path_hmac_key, parent),
        extension_hint=ext,
        filename_display=_policy_display_name(
            occurrence_counter=occurrence_counter,
            extension_hint=ext,
            raw_name=path.name,
            filename_policy=filename_policy,
        ),
        filename_policy=filename_policy,
        salt_version=salt_version,
    )
