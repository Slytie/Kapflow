from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_makefile_exposes_lab_auth_and_vm_deploy_targets() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "lab-auth-smoke:" in makefile
    assert "scripts/run_lab_auth_smoke.py" in makefile
    assert "--bearer-token-env" in _target_body(makefile, "lab-auth-smoke")
    assert "lab-vm-deploy-plan:" in makefile
    assert "lab-vm-deploy:" in makefile
    assert "scripts/deploy_lab_vm.py" in makefile
    assert "--execute" not in _target_body(makefile, "lab-vm-deploy-plan")
    assert "--confirm-lab-target" in _target_body(makefile, "lab-vm-deploy")
    assert "--confirm-no-real-users" in _target_body(makefile, "lab-vm-deploy")


def test_lab_ops_docs_record_no_production_or_real_user_boundary() -> None:
    runbook = (
        REPO_ROOT / "docs/ops/runbooks/lab_auth_and_vm_deploy.md"
    ).read_text(encoding="utf-8")

    assert "existing `shared_env` RS256 JWT resolver" in runbook
    assert "does not add JWKS lookup" in runbook
    assert "must not print or persist bearer token values" in runbook
    assert "lab-only VM lane" in runbook
    assert "no real users" in runbook
    assert "actual operator-supplied lab VM execute-and-smoke evidence" in runbook
    assert "not CAPEX activation" in runbook
    assert "gcloud compute scp" in runbook
    assert "gcloud compute ssh" in runbook
    assert "Cloud Run" in runbook
    assert "Kubernetes" in runbook
    assert "Terraform" in runbook


def test_lab_auth_and_vm_deploy_schemas_are_registered_contracts() -> None:
    auth_schema = json.loads(
        (REPO_ROOT / "schemas/ops/lab_auth_smoke_report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    deploy_schema = json.loads(
        (REPO_ROOT / "schemas/ops/lab_vm_deploy_report.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(auth_schema)
    Draft202012Validator.check_schema(deploy_schema)
    assert auth_schema["properties"]["command"]["const"] == "lab.auth.smoke"
    assert deploy_schema["properties"]["command"]["const"] == "lab.vm.deploy"
    assert deploy_schema["properties"]["environment"]["const"] == "lab"


def _target_body(makefile: str, target_name: str) -> str:
    start = makefile.index(f"{target_name}:")
    remainder = makefile[start + len(target_name) + 1 :]
    lines: list[str] = []
    for line in remainder.splitlines():
        if line and not line.startswith("\t") and not line.startswith(" "):
            break
        lines.append(line)
    return "\n".join(lines)
