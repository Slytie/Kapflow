from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from tests.runtime.helpers.runtime_cli import REPO_ROOT, SRC_ROOT


def _run_script(*, args: list[str]) -> dict[str, object]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(SRC_ROOT)
    )
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
    return json.loads(result.stdout)


def test_logistics_workpage_demo_prep_script_emits_stable_canonical_urls_and_ids(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'workpage-demo.db'}"
    output_json_path = tmp_path / "workpage-demo.json"
    args = [
        "scripts/run_logistics_workpage_demo_prep.py",
        "--db-url",
        db_url,
        "--planning-week-id",
        "PW-2026-W10",
        "--service-date-id",
        "SD-2026-03-06",
        "--output-json",
        str(output_json_path),
    ]

    first = _run_script(args=args)
    second = _run_script(args=args)

    assert output_json_path.exists()
    written = json.loads(output_json_path.read_text(encoding="utf-8"))
    assert first == second == written
    assert written["status"] == "ok"
    assert written["command"] == "logistics-workpage-demo.prepare"
    assert written["output_json_path"] == str(output_json_path)
    assert written["recommended_story_url"] == (
        "/demo/logistics?planning_week_id=PW-2026-W10&service_date_id=SD-2026-03-06"
    )
    assert written["weekly_workspace_url"] == f"/runs/{written['weekly_run_id']}/workspace"
    assert written["reporting_workspace_url"] == f"/runs/{written['reporting_run_id']}/workspace"
    assert written["schedule_workpage_url"] == (
        f"/runs/{written['weekly_run_id']}/workpages/schedule-v0"
    )
    assert written["schedule_artifact_url"] == (
        f"/runs/{written['weekly_run_id']}/workpages/schedule-v0/artifacts/"
        f"{written['schedule_artifact_version_id']}"
    )
    assert written["route_demand_workpage_url"] == (
        f"/runs/{written['weekly_run_id']}/workpages/route-demand-v0"
    )
    assert written["route_demand_artifact_url"] == (
        f"/runs/{written['weekly_run_id']}/workpages/route-demand-v0/artifacts/"
        f"{written['route_demand_artifact_version_id']}"
    )
    assert written["driver_preferences_workpage_url"] == (
        f"/runs/{written['weekly_run_id']}/workpages/driver-preferences-v0"
    )
    assert written["driver_preferences_artifact_version_id"] is not None
    assert written["driver_preferences_artifact_url"] == (
        f"/runs/{written['weekly_run_id']}/workpages/driver-preferences-v0/artifacts/"
        f"{written['driver_preferences_artifact_version_id']}"
    )
    assert written["eod_workpage_url"] == (
        f"/runs/{written['reporting_run_id']}/workpages/eod-v0"
    )


def test_logistics_workpage_demo_prep_script_skips_driver_preferences_when_requested(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'workpage-demo-no-driver-preferences.db'}"
    payload = _run_script(
        args=[
            "scripts/run_logistics_workpage_demo_prep.py",
            "--db-url",
            db_url,
            "--planning-week-id",
            "PW-2026-W10",
            "--service-date-id",
            "SD-2026-03-06",
            "--no-driver-preferences",
        ]
    )

    assert payload["status"] == "ok"
    assert payload["command"] == "logistics-workpage-demo.prepare"
    assert payload["driver_preferences_workpage_url"] == (
        f"/runs/{payload['weekly_run_id']}/workpages/driver-preferences-v0"
    )
    assert payload["driver_preferences_artifact_version_id"] is None
    assert payload["driver_preferences_artifact_url"] is None
