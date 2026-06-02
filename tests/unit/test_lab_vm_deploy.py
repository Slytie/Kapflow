from __future__ import annotations

import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator
import pytest

from scripts.deploy_lab_vm import deploy_lab_vm, plan_lab_vm_deploy


REPO_ROOT = Path(__file__).resolve().parents[2]
DIGEST = "sha256:" + ("4" * 64)


def test_lab_vm_deploy_plan_validates_release_and_stays_dry_run(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)

    report = plan_lab_vm_deploy(
        **kwargs,
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_lab_vm_report(report)
    assert report["status"] == "planned"
    assert report["environment"] == "lab"
    assert report["live_deploy_evidence_recorded"] is False
    assert report["live_deploy_evidence_required_for_task_done"] is True
    assert [command["tool"] for command in report["commands"]] == [
        "gcloud_compute_ssh",
        "gcloud_compute_scp",
        "gcloud_compute_ssh",
    ]
    command_text = "\n".join(" ".join(command["argv"]) for command in report["commands"])
    assert "gcloud compute ssh" in command_text
    assert "gcloud compute scp" in command_text
    assert "gcloud run" not in command_text
    assert "kubectl" not in command_text
    assert "terraform" not in command_text
    assert "/api/v1/ops/health" in command_text
    assert "/api/v1/ops/readiness" in command_text
    assert "/api/v1/viewer" in command_text
    assert "prepare_predeploy_backup.py" in command_text
    assert "npm ci && npm run build" in command_text


def test_lab_vm_deploy_execute_requires_explicit_lab_confirmations(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)

    with pytest.raises(SystemExit, match="requires --confirm-lab-target"):
        plan_lab_vm_deploy(
            **kwargs,
            execute=True,
            confirm_lab_target=True,
            confirm_no_real_users=False,
        )


def test_lab_vm_deploy_execute_runs_gcloud_commands_in_order(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)
    runner = _GcloudRunner()
    output = tmp_path / "reports" / "lab_vm_deploy_report.json"

    report = deploy_lab_vm(
        **kwargs,
        execute=True,
        confirm_lab_target=True,
        confirm_no_real_users=True,
        output=output,
        runner=runner,
        now_iso="2026-06-02T00:00:00Z",
    )

    _validate_lab_vm_report(report)
    assert report["status"] == "executed"
    assert report["live_deploy_evidence_recorded"] is True
    assert [command[1:3] for command in runner.commands] == [
        ["compute", "ssh"],
        ["compute", "scp"],
        ["compute", "ssh"],
    ]
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "executed"


def test_lab_vm_deploy_rejects_non_lab_or_production_targets(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)

    with pytest.raises(SystemExit, match="environment lab only"):
        plan_lab_vm_deploy(**{**kwargs, "environment": "prod"})

    with pytest.raises(SystemExit, match="production target"):
        plan_lab_vm_deploy(
            **{**kwargs, "remote_artifact_root": "/srv/onetruth/prod-artifacts"}
        )


def test_lab_vm_deploy_rejects_secret_values_and_invalid_viewer_env(tmp_path: Path) -> None:
    kwargs = _base_kwargs(tmp_path)

    with pytest.raises(SystemExit, match="not a secret value"):
        plan_lab_vm_deploy(**{**kwargs, "secret_refs": ("JWT_SECRET=do-not-store",)})

    with pytest.raises(SystemExit, match="shell env var name"):
        plan_lab_vm_deploy(**{**kwargs, "remote_viewer_token_env": "lab-token"})


class _GcloudRunner:
    def __init__(self) -> None:
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
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")


def _base_kwargs(tmp_path: Path) -> dict[str, object]:
    bundle_path = tmp_path / "release-source-bundle.zip"
    bundle_path.write_bytes(b"release bundle fixture\n")
    manifest_path = _write_release_manifest(tmp_path, bundle_path)
    return {
        "environment": "lab",
        "gcp_project": "kapflow-lab-project",
        "zone": "europe-west3-a",
        "instance": "kapflow-lab-vm",
        "release_source_bundle": bundle_path,
        "release_manifest": manifest_path,
        "remote_release_root": "/srv/onetruth/lab/releases-root",
        "remote_db_url": "sqlite:////srv/onetruth/lab/runtime.db",
        "remote_artifact_root": "/srv/onetruth/lab/artifacts",
        "remote_service_name": "onetruth-api",
        "remote_viewer_token_env": "LAB_VIEWER_SMOKE_TOKEN",
        "secret_refs": ("shared-env-jwt-public-key", "shared-env-jwt-public-key"),
    }


def _write_release_manifest(tmp_path: Path, bundle_path: Path) -> Path:
    manifest = {
        "manifest_version": 1,
        "command": "release.image.build",
        "created_at": "2026-06-02T00:00:00Z",
        "git_commit": "c" * 40,
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
            "sha256": "5" * 64,
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


def _validate_lab_vm_report(report: dict[str, object]) -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas/ops/lab_vm_deploy_report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(report)


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
