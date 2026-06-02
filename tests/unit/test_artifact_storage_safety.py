from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pytest

from onetruth.infrastructure.artifacts.storage import (
    ArtifactStorageError,
    ArtifactStorageRootError,
    read_blob,
    write_blob,
)


def _uri_path(storage_uri: str) -> Path:
    return Path(urlparse(storage_uri).path).resolve()


def test_write_blob_confines_sanitized_segments_to_storage_root(tmp_path: Path) -> None:
    storage_root = tmp_path / "artifact-root"
    storage_uri, digest, byte_size = write_blob(
        storage_root=storage_root,
        workflow_run_id="../tenant-a/workflow:../../escape",
        file_name="../../unsafe report?.xlsx",
        content=b"artifact-bytes",
    )

    blob_path = _uri_path(storage_uri)
    blob_path.relative_to(storage_root.resolve())
    assert ".." not in blob_path.relative_to(storage_root.resolve()).parts
    assert blob_path.name == "unsafe_report_.xlsx"
    assert blob_path.read_bytes() == b"artifact-bytes"
    assert digest.startswith("sha256:")
    assert byte_size == len(b"artifact-bytes")
    assert not (tmp_path / "escape").exists()


def test_read_blob_accepts_file_inside_configured_storage_root(tmp_path: Path) -> None:
    storage_root = tmp_path / "artifact-root"
    storage_uri, _, _ = write_blob(
        storage_root=storage_root,
        workflow_run_id="wr-safe",
        file_name="packet.json",
        content=b'{"ok":true}',
    )

    assert read_blob(storage_uri, storage_root=storage_root) == b'{"ok":true}'


def test_read_blob_rejects_file_uri_outside_configured_storage_root(tmp_path: Path) -> None:
    storage_root = tmp_path / "artifact-root"
    storage_root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")

    with pytest.raises(ArtifactStorageRootError, match="escapes storage root"):
        read_blob(outside.resolve().as_uri(), storage_root=storage_root)

    with pytest.raises(ArtifactStorageError):
        read_blob(outside.resolve().as_uri(), storage_root=storage_root)
