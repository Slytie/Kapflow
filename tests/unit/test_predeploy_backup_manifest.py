from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from scripts.prepare_predeploy_backup import prepare_predeploy_backup_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]
DIGEST = "sha256:" + ("3" * 64)


def test_predeploy_backup_manifest_validates_tuple_without_copying_state(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "runtime.db"
    db_path.write_bytes(b"sqlite fixture\n")
    artifact_root = tmp_path / "artifact-root"
    artifact_root.mkdir()
    (artifact_root / "blob.bin").write_bytes(b"blob")
    release_manifest = _write_release_manifest(tmp_path)
    output = tmp_path / "out" / "backup_manifest.json"

    manifest = prepare_predeploy_backup_manifest(
        environment="lab",
        db_url=f"sqlite:///{db_path}",
        artifact_root=artifact_root,
        release_manifest=release_manifest,
        output=output,
        secret_refs=("jwt-public-key-ref", "openai-api-key-ref", "jwt-public-key-ref"),
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_backup_manifest(manifest)
    assert manifest["mode"] == "validate_only"
    assert manifest["state_copy_performed"] is False
    assert manifest["restore_proof"] is False
    assert manifest["artifact_root"]["file_count"] == 1
    assert manifest["secret_refs"] == ["jwt-public-key-ref", "openai-api-key-ref"]
    assert output.exists()
    assert sorted(path.name for path in output.parent.iterdir()) == ["backup_manifest.json"]


def test_predeploy_backup_manifest_rejects_secret_values(tmp_path: Path) -> None:
    db_path = tmp_path / "runtime.db"
    db_path.write_bytes(b"sqlite fixture\n")
    artifact_root = tmp_path / "artifact-root"
    artifact_root.mkdir()
    release_manifest = _write_release_manifest(tmp_path)

    with pytest.raises(SystemExit, match="not a secret value"):
        prepare_predeploy_backup_manifest(
            environment="lab",
            db_url=f"sqlite:///{db_path}",
            artifact_root=artifact_root,
            release_manifest=release_manifest,
            output=tmp_path / "backup_manifest.json",
            secret_refs=("JWT_SECRET=do-not-store",),
            now_iso="2026-06-02T00:00:00Z",
        )


def test_predeploy_backup_manifest_rejects_missing_artifact_root(tmp_path: Path) -> None:
    db_path = tmp_path / "runtime.db"
    db_path.write_bytes(b"sqlite fixture\n")
    release_manifest = _write_release_manifest(tmp_path)

    with pytest.raises(SystemExit, match="artifact root does not exist"):
        prepare_predeploy_backup_manifest(
            environment="lab",
            db_url=f"sqlite:///{db_path}",
            artifact_root=tmp_path / "missing-artifacts",
            release_manifest=release_manifest,
            output=tmp_path / "backup_manifest.json",
            now_iso="2026-06-02T00:00:00Z",
        )


def test_predeploy_backup_manifest_rejects_non_sqlite_db_url(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifact-root"
    artifact_root.mkdir()
    release_manifest = _write_release_manifest(tmp_path)

    with pytest.raises(SystemExit, match="local sqlite"):
        prepare_predeploy_backup_manifest(
            environment="lab",
            db_url="postgresql://example.invalid/runtime",
            artifact_root=artifact_root,
            release_manifest=release_manifest,
            output=tmp_path / "backup_manifest.json",
            now_iso="2026-06-02T00:00:00Z",
        )


def _write_release_manifest(tmp_path: Path) -> Path:
    bundle_path = tmp_path / "release-source-bundle.zip"
    bundle_path.write_bytes(b"release bundle fixture\n")
    manifest = {
        "manifest_version": 1,
        "command": "release.image.build",
        "created_at": "2026-06-02T00:00:00Z",
        "git_commit": "b" * 40,
        "build_mode": "push",
        "deployment": {"performed": False, "commands": []},
        "release_source_bundle": {
            "path": str(bundle_path),
            "sha256": _sha256(bundle_path),
            "size_bytes": bundle_path.stat().st_size,
            "archive_root": "fixture-release-source-bundle",
            "bundle_kind": "release_source_bundle",
            "provenance_path": "release_provenance.json",
        },
        "dockerfile": {
            "path": "Dockerfile",
            "sha256": "1" * 64,
        },
        "image": {
            "ref": "us-docker.pkg.dev/example/release/onetruth-api:test",
            "repository": "us-docker.pkg.dev/example/release/onetruth-api",
            "tag": "test",
            "digest": DIGEST,
            "digest_ref": f"us-docker.pkg.dev/example/release/onetruth-api@{DIGEST}",
            "digest_source": "registry_push",
            "pushed": True,
        },
        "manifest_path": str(tmp_path / "release_manifest.json"),
    }
    path = tmp_path / "release_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _validate_backup_manifest(manifest: dict[str, object]) -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas/ops/backup_manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(manifest)


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
