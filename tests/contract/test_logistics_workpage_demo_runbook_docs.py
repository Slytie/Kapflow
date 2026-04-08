from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNBOOK_PATH = REPO_ROOT / "docs/ops/runbooks/logistics_canonical_workpage_demo.md"
LEGACY_RUNBOOK_PATH = REPO_ROOT / "docs/ops/runbooks/logistics_local_demo_weekly_first.md"
OPS_README_PATH = REPO_ROOT / "docs/ops/README.md"
RUNBOOKS_README_PATH = REPO_ROOT / "docs/ops/runbooks/README.md"


def test_canonical_workpage_demo_runbook_freezes_startup_and_url_contract() -> None:
    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert 'python3.11 -m pip install -e ".[api,dev]"' in runbook
    assert "Node `20`" in runbook
    assert "cd frontend && npm ci" in runbook
    assert "PYTHONPATH=src onetruth-api \\" in runbook
    assert "scripts/run_logistics_demo_frontend.py" in runbook
    assert "--demo-json .tmp/logistics-canonical-workpage-demo.json" in runbook
    assert "scripts/run_logistics_local_demo.py" in runbook
    assert "scripts/run_logistics_workpage_demo_prep.py" in runbook
    assert "No OpenAI required." in runbook
    assert "frontend_request_context" in runbook
    assert "schedule_workpage_url" in runbook
    assert "schedule_artifact_url" in runbook
    assert "route_demand_workpage_url" in runbook
    assert "route_demand_artifact_url" in runbook
    assert "driver_preferences_workpage_url" in runbook
    assert "driver_preferences_artifact_url" in runbook
    assert "eod_workpage_url" in runbook
    assert "multi-week accepted history" in runbook
    assert "route-demand auto-drift seed" in runbook
    assert "live-dispatch completion lane" in runbook
    assert "pre-created EOD draft artifact" in runbook


def test_canonical_workpage_demo_runbook_is_discoverable_and_legacy_runbook_points_to_it() -> None:
    ops_readme = OPS_README_PATH.read_text(encoding="utf-8")
    runbooks_readme = RUNBOOKS_README_PATH.read_text(encoding="utf-8")
    legacy_runbook = LEGACY_RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "docs/ops/runbooks/logistics_canonical_workpage_demo.md" in ops_readme
    assert "`logistics_canonical_workpage_demo.md`" in runbooks_readme
    assert "deterministic canonical-workpage validation path" in legacy_runbook
    assert "logistics_canonical_workpage_demo.md" in legacy_runbook
    assert "scripts/run_logistics_demo_frontend.py" in legacy_runbook
    assert "--demo-json .tmp/logistics-local-demo.json" in legacy_runbook
