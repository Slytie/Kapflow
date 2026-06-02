from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_api_runtime_dockerfile_is_secretless_and_non_deploying() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.11-slim" in dockerfile
    assert 'ONETRUTH_API_BOUNDARY_PROFILE=shared_env' in dockerfile
    assert 'python -m pip install --no-cache-dir -e ".[api]"' in dockerfile
    assert "EXPOSE 8080" in dockerfile
    assert 'CMD ["onetruth-api"' in dockerfile
    assert "OPENAI_API_KEY" not in dockerfile
    assert "PRODUCTION_DB_URL" not in dockerfile
    assert "ONETRUTH_ARTIFACT_ROOT" not in dockerfile
    assert "gcloud run" not in dockerfile
    assert "kubectl" not in dockerfile
    assert "terraform" not in dockerfile


def test_makefile_exposes_non_push_release_and_validate_only_backup_targets() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "release-image:" in makefile
    assert "scripts/build_release_image.py" in makefile
    assert "--image-ref" in makefile
    assert "--push" not in _target_body(makefile, "release-image")
    assert "predeploy-backup-manifest:" in makefile
    assert "scripts/prepare_predeploy_backup.py" in makefile
    assert "--environment" in makefile
    assert "--release-manifest" in makefile


def test_release_and_backup_docs_preserve_non_activation_boundary() -> None:
    deploy_runbook = (REPO_ROOT / "docs/ops/runbooks/rollback_and_deploy.md").read_text(
        encoding="utf-8"
    )
    backup_runbook = (REPO_ROOT / "docs/ops/runbooks/backup_and_restore.md").read_text(
        encoding="utf-8"
    )

    assert "release_source_bundle remains the only deploy input" in deploy_runbook
    assert "API image is release evidence/build output" in deploy_runbook
    assert "not deployment approval" in deploy_runbook
    assert "validation-only predeploy backup skeleton" in backup_runbook
    assert "does not copy live state" in backup_runbook
    assert "not restore proof" in backup_runbook


def _target_body(makefile: str, target_name: str) -> str:
    start = makefile.index(f"{target_name}:")
    remainder = makefile[start + len(target_name) + 1 :]
    lines: list[str] = []
    for line in remainder.splitlines():
        if line and not line.startswith("\t") and not line.startswith(" "):
            break
        lines.append(line)
    return "\n".join(lines)
