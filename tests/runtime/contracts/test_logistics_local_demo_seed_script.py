from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from tests.runtime.helpers.runtime_cli import REPO_ROOT, SRC_ROOT


def _run_script(
    *,
    args: list[str],
    openai_api_key: str | None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(SRC_ROOT)
    )
    if openai_api_key is None:
        env.pop("OPENAI_API_KEY", None)
    else:
        env["OPENAI_API_KEY"] = openai_api_key
    result = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"script failed ({result.returncode})\nCMD: {' '.join(args)}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
    return result


def test_logistics_local_demo_seed_script_emits_stable_urls_and_ids_and_truthful_openai_flag(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'local-demo.db'}"
    output_json_path = tmp_path / "local-demo.json"
    args = [
        "scripts/run_logistics_local_demo.py",
        "--db-url",
        db_url,
        "--planning-week-id",
        "PW-2026-W10",
        "--service-date-id",
        "SD-2026-03-06",
        "--output-json",
        str(output_json_path),
    ]

    first = json.loads(_run_script(args=args, openai_api_key=None).stdout)
    second = json.loads(_run_script(args=args, openai_api_key=None).stdout)

    assert output_json_path.exists()
    written = json.loads(output_json_path.read_text(encoding="utf-8"))
    assert written["command"] == "logistics-local-demo.seed"
    assert written["recommended_story_url"] == (
        "/demo/logistics?planning_week_id=PW-2026-W10&service_date_id=SD-2026-03-06"
    )
    assert written["weekly_workspace_url"] == f"/runs/{written['weekly_run_id']}/workspace"
    assert written["reporting_workspace_url"] == f"/runs/{written['reporting_run_id']}/workspace"
    assert written["live_workspace_url"] is None
    assert written["prepare_live_dispatch_path"] == (
        f"/api/v1/workflow-runs/{written['weekly_run_id']}/prepare-live-dispatch-day"
    )
    assert written["review_ready_weekly_workspace_url"] == (
        f"/runs/{written['review_ready_weekly_run_id']}/workspace"
    )
    assert written["review_ready_reporting_workspace_url"] == (
        f"/runs/{written['review_ready_reporting_run_id']}/workspace"
    )
    assert written["review_ready_schedule_workpage_url"] == (
        f"/runs/{written['review_ready_weekly_run_id']}/workpages/schedule-v0"
    )
    assert written["review_ready_route_demand_workpage_url"] == (
        f"/runs/{written['review_ready_weekly_run_id']}/workpages/route-demand-v0"
    )
    assert written["review_ready_driver_preferences_workpage_url"] == (
        f"/runs/{written['review_ready_weekly_run_id']}/workpages/driver-preferences-v0"
    )
    assert written["review_ready_eod_workpage_url"] == (
        f"/runs/{written['review_ready_reporting_run_id']}/workpages/eod-v0"
    )
    assert written["upload_pack_root"].endswith("fixtures/logistics/local_demo_upload_pack")
    assert written["openai_api_key_present"] is False

    assert first["weekly_run_id"] == second["weekly_run_id"] == written["weekly_run_id"]
    assert first["reporting_run_id"] == second["reporting_run_id"] == written["reporting_run_id"]
    assert first["prior_reporting_run_id"] == second["prior_reporting_run_id"]
    assert (
        first["review_ready_weekly_run_id"]
        == second["review_ready_weekly_run_id"]
        == written["review_ready_weekly_run_id"]
    )
    assert (
        first["review_ready_reporting_run_id"]
        == second["review_ready_reporting_run_id"]
        == written["review_ready_reporting_run_id"]
    )

    with_key = json.loads(_run_script(args=args, openai_api_key="sk-demo-local").stdout)
    assert with_key["openai_api_key_present"] is True
