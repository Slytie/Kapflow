from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = REPO_ROOT / "docs/ops/runbooks/logistics_single_node_cadence.md"
OPS_README_PATH = REPO_ROOT / "docs/ops/README.md"
RUNBOOKS_README_PATH = REPO_ROOT / "docs/ops/runbooks/README.md"


def test_logistics_operational_cadence_runbook_freezes_cli_and_shared_env_recipe() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "onetruthctl cadence tick-logistics" in runbook
    assert "onetruthctl cadence tick-logistics --service-date-id SD-2026-03-06" in runbook
    assert "Python `3.11`" in runbook
    assert "Node `20`" in runbook
    assert 'python3.11 -m pip install -e ".[api]"' in runbook
    assert "cd frontend && npm ci && npm run build" in runbook
    assert "ONETRUTH_API_BOUNDARY_PROFILE=shared_env" in runbook
    assert "ONETRUTH_DB_URL" in runbook
    assert "ONETRUTH_ARTIFACT_ROOT" in runbook
    assert "cron" in runbook
    assert "systemd" in runbook
    assert "CronJob" in runbook
    assert "manual weekly publish happens through the normal workflow/task/approval path" in runbook
    assert "reporting intake task remains human-owned" in runbook


def test_logistics_operational_cadence_runbook_is_discoverable_from_ops_readmes() -> None:
    ops_readme = OPS_README_PATH.read_text(encoding="utf-8")
    runbooks_readme = RUNBOOKS_README_PATH.read_text(encoding="utf-8")

    assert "docs/ops/runbooks/logistics_single_node_cadence.md" in ops_readme
    assert "`logistics_single_node_cadence.md`" in runbooks_readme
