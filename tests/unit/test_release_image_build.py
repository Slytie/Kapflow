from __future__ import annotations

import json
from pathlib import Path
import subprocess
import zipfile

from jsonschema import Draft202012Validator
import pytest

from scripts import build_release_image


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_DIGEST = "sha256:" + ("1" * 64)
PUSH_DIGEST = "sha256:" + ("2" * 64)


def test_release_image_manifest_records_bundle_digest_and_local_image_id(
    tmp_path: Path,
) -> None:
    bundle_path = _write_release_bundle(tmp_path / "release-source-bundle.zip")
    runner = _DockerRunner(local_digest=LOCAL_DIGEST)

    manifest = build_release_image.build_release_image(
        repo_root=REPO_ROOT,
        output_root=tmp_path / "out",
        image_ref="us-docker.pkg.dev/example/release/onetruth-api:test",
        release_source_bundle=bundle_path,
        runner=runner,
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_release_manifest(manifest)
    assert manifest["build_mode"] == "local"
    assert manifest["deployment"] == {"performed": False, "commands": []}
    assert manifest["release_source_bundle"]["sha256"] == _sha256(bundle_path)
    assert manifest["image"] == {
        "ref": "us-docker.pkg.dev/example/release/onetruth-api:test",
        "repository": "us-docker.pkg.dev/example/release/onetruth-api",
        "tag": "test",
        "digest": LOCAL_DIGEST,
        "digest_ref": f"us-docker.pkg.dev/example/release/onetruth-api@{LOCAL_DIGEST}",
        "digest_source": "local_image_id",
        "pushed": False,
    }
    assert (tmp_path / "out" / "release_manifest.json").exists()
    assert runner.commands[0][0:2] == ["docker", "build"]
    assert all("kubectl" not in " ".join(command) for command in runner.commands)


def test_release_image_push_records_registry_digest(tmp_path: Path) -> None:
    bundle_path = _write_release_bundle(tmp_path / "release-source-bundle.zip")
    runner = _DockerRunner(local_digest=LOCAL_DIGEST, push_digest=PUSH_DIGEST)

    manifest = build_release_image.build_release_image(
        repo_root=REPO_ROOT,
        output_root=tmp_path / "out",
        image_ref="us-docker.pkg.dev/example/release/onetruth-api:test",
        release_source_bundle=bundle_path,
        push=True,
        runner=runner,
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_release_manifest(manifest)
    assert manifest["build_mode"] == "push"
    assert manifest["image"]["digest"] == PUSH_DIGEST
    assert manifest["image"]["digest_source"] == "registry_push"
    assert manifest["image"]["digest_ref"] == (
        f"us-docker.pkg.dev/example/release/onetruth-api@{PUSH_DIGEST}"
    )
    assert [command[0:2] for command in runner.commands] == [
        ["docker", "build"],
        ["docker", "push"],
    ]


def test_release_image_push_requires_registry_digest(tmp_path: Path) -> None:
    bundle_path = _write_release_bundle(tmp_path / "release-source-bundle.zip")
    runner = _DockerRunner(local_digest=LOCAL_DIGEST, push_digest=None)

    with pytest.raises(SystemExit, match="docker push did not report"):
        build_release_image.build_release_image(
            repo_root=REPO_ROOT,
            output_root=tmp_path / "out",
            image_ref="us-docker.pkg.dev/example/release/onetruth-api:test",
            release_source_bundle=bundle_path,
            push=True,
            runner=runner,
            now_iso="2026-06-02T00:00:00Z",
        )


def test_release_image_rejects_digest_ref_input(tmp_path: Path) -> None:
    bundle_path = _write_release_bundle(tmp_path / "release-source-bundle.zip")

    with pytest.raises(SystemExit, match="not an @sha256 digest ref"):
        build_release_image.build_release_image(
            repo_root=REPO_ROOT,
            output_root=tmp_path / "out",
            image_ref=f"us-docker.pkg.dev/example/release/onetruth-api@{LOCAL_DIGEST}",
            release_source_bundle=bundle_path,
            runner=_DockerRunner(local_digest=LOCAL_DIGEST),
            now_iso="2026-06-02T00:00:00Z",
        )


class _DockerRunner:
    def __init__(self, *, local_digest: str, push_digest: str | None = None) -> None:
        self.local_digest = local_digest
        self.push_digest = push_digest
        self.commands: list[list[str]] = []

    def __call__(
        self,
        command: list[str],
        *,
        text: bool,
        capture_output: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[1] == "build":
            iid_path = Path(command[command.index("--iidfile") + 1])
            iid_path.write_text(self.local_digest, encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        if command[1] == "push":
            stdout = (
                f"latest: digest: {self.push_digest} size: 123\n"
                if self.push_digest
                else "pushed without digest\n"
            )
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")
        raise AssertionError(f"unexpected command: {command}")


def _write_release_bundle(path: Path) -> Path:
    archive_root = "fixture-release-source-bundle"
    dockerfile_text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    manifest = {
        "manifest_version": 1,
        "bundle_kind": "release_source_bundle",
        "archive_root": archive_root,
        "distribution_class": "operator_release",
        "tracked_only": True,
        "git_commit": "a" * 40,
        "tracked_worktree_clean": True,
        "provenance_path": "release_provenance.json",
    }
    provenance = {
        "provenance_version": 1,
        "bundle_kind": "release_source_bundle",
        "archive_root": archive_root,
        "git_commit": "a" * 40,
        "tracked_only": True,
        "source_manifests": [],
        "files": [],
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{archive_root}/bundle_manifest.json", json.dumps(manifest))
        archive.writestr(f"{archive_root}/release_provenance.json", json.dumps(provenance))
        archive.writestr(f"{archive_root}/Dockerfile", dockerfile_text)
        archive.writestr(f"{archive_root}/pyproject.toml", "[project]\nname='fixture'\n")
    return path


def _validate_release_manifest(manifest: dict[str, object]) -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas/release/release_manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(manifest)


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
