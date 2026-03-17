from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ADR_003_PATH = REPO_ROOT / "docs/adr/ADR-003-stage4-runtime-architecture.md"
ADR_004_PATH = REPO_ROOT / "docs/adr/ADR-004-first-user-production-lab-topology.md"
TOPOLOGY_PATH = REPO_ROOT / "docs/ops/production_lab_topology.md"
RUNBOOK_PATH = REPO_ROOT / "docs/ops/runbooks/rollback_and_deploy.md"
README_PATH = REPO_ROOT / "README.md"


def test_adrs_freeze_first_user_production_lab_topology_contract() -> None:
    adr_003 = ADR_003_PATH.read_text(encoding="utf-8")
    adr_004 = ADR_004_PATH.read_text(encoding="utf-8")

    assert "Superseded in part by ADR-004" in adr_003
    assert "separate single-node environments" in adr_004
    assert "`release_source_bundle`" in adr_004
    assert "`handoff_source_bundle`" in adr_004
    assert "`runtime_workspace_bundle`" in adr_004
    assert "reviewed release process" in adr_004
    assert "not through direct runtime mutation" in adr_004


def test_ops_docs_freeze_deploy_inputs_and_state_separation() -> None:
    topology = TOPOLOGY_PATH.read_text(encoding="utf-8")
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")

    assert "ONETRUTH_DB_URL" in topology
    assert "ONETRUTH_ARTIFACT_ROOT" in topology
    assert "ONETRUTH_API_BOUNDARY_PROFILE=shared_env" in topology
    assert 'python3.11 -m pip install -e ".[api]"' in topology
    assert "Prod and lab do not share live DBs, artifact roots, or secrets." in topology

    assert "`release_source_bundle`" in runbook
    assert "`bundle_manifest.json`" in runbook
    assert "`release_provenance.json`" in runbook
    assert "do not rewrite or delete historical runs" in runbook

    assert "docs/ops/production_lab_topology.md" in readme
    assert "docs/ops/runbooks/rollback_and_deploy.md" in readme
