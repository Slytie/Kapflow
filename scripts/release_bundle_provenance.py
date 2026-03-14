from __future__ import annotations

import hashlib
from pathlib import Path


RELEASE_PROVENANCE_VERSION = 1
RELEASE_PROVENANCE_PATH = "release_provenance.json"
SOURCE_MANIFEST_CANDIDATES = (
    "pyproject.toml",
    "requirements.txt",
    "package-lock.json",
    "frontend/package.json",
    "frontend/package-lock.json",
    ".nvmrc",
)


def build_release_provenance(
    *,
    repo_root: Path,
    archive_root: str,
    bundle_kind: str,
    git_commit: str,
    tracked_only: bool,
    files_to_write: list[Path],
) -> dict[str, object]:
    file_records = [
        _build_file_record(repo_root=repo_root, absolute_path=absolute_path)
        for absolute_path in sorted(
            files_to_write, key=lambda path: path.relative_to(repo_root).as_posix()
        )
    ]
    source_manifests = [
        file_record
        for file_record in file_records
        if str(file_record["path"]) in SOURCE_MANIFEST_CANDIDATES
    ]
    return {
        "provenance_version": RELEASE_PROVENANCE_VERSION,
        "bundle_kind": bundle_kind,
        "archive_root": archive_root,
        "git_commit": git_commit,
        "tracked_only": tracked_only,
        "source_manifests": source_manifests,
        "files": file_records,
    }


def _build_file_record(*, repo_root: Path, absolute_path: Path) -> dict[str, object]:
    content = absolute_path.read_bytes()
    return {
        "path": absolute_path.relative_to(repo_root).as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }
