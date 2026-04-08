from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from .runtime_cli import REPO_ROOT, SRC_ROOT


def run_logistics_workpage_demo_prep_script(
    *,
    db_url: str,
    planning_week_id: str = "PW-2026-W10",
    service_date_id: str = "SD-2026-03-06",
    output_json_path: Path | None = None,
    include_driver_preferences: bool = True,
) -> dict[str, Any]:
    args = [
        "scripts/run_logistics_workpage_demo_prep.py",
        "--db-url",
        db_url,
        "--planning-week-id",
        planning_week_id,
        "--service-date-id",
        service_date_id,
    ]
    if output_json_path is not None:
        args.extend(["--output-json", str(output_json_path)])
    if not include_driver_preferences:
        args.append("--no-driver-preferences")
    return _run_script(args=args)


def run_logistics_demo_frontend_launcher_script(
    *,
    demo_json_path: Path | None = None,
    api_base_url: str = "http://127.0.0.1:8080/api/v1",
    host: str = "127.0.0.1",
) -> dict[str, Any]:
    args = [
        "scripts/run_logistics_demo_frontend.py",
        "--api-base-url",
        api_base_url,
        "--host",
        host,
        "--print-launch-config",
    ]
    if demo_json_path is not None:
        args.extend(["--demo-json", str(demo_json_path)])
    return _run_script(args=args)


def _run_script(*, args: list[str]) -> dict[str, Any]:
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
