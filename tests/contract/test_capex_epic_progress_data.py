from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "frontend/src/data/capexEpicProgressData.json"


def _load_validator_module():
    spec = importlib.util.spec_from_file_location(
        "validate_capex_epic_progress_data",
        ROOT / "scripts/validate_capex_epic_progress_data.py",
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_capex_epic_progress_data_is_current() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_capex_epic_progress_data.py",
            "frontend/src/data/capexEpicProgressData.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_capex_epic_progress_data_uses_v2_estimates() -> None:
    data = _load_data()

    assert data["schemaVersion"] == "capex.epic_progress.v2"
    assert data["summary"]["estimate"]["remainingTasks"] == 337
    assert data["summary"]["estimate"]["etaDate"] == "2026-08-09"
    assert data["summary"]["estimate"]["label"] == "ETA 2026-08-09"
    assert all("estimate" in epic for epic in data["epics"])

    epic139 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-139")
    assert epic139["displayStatus"] == "done"
    assert epic139["counts"]["done"] == 17
    assert epic139["estimate"]["label"] == "Complete"


def test_historical_done_tasks_report_missing_completion_timestamps() -> None:
    data = _load_data()
    tasks = [task for epic in data["epics"] for task in epic["tasks"]]
    historical_missing = [
        task
        for task in tasks
        if task["sourceStatus"] == "DONE"
        and task["completionTimestampStatus"] == "missing_historical"
    ]

    assert {task["id"] for task in historical_missing} >= {"TASK-0233", "TASK-0249"}


def test_done_task_missing_completed_at_without_exception_fails_validation() -> None:
    validator = _load_validator_module()
    data = copy.deepcopy(_load_data())
    task = data["epics"][0]["tasks"][0]
    task["completionTimestampStatus"] = "missing_required"
    task["completionTimestampSource"] = "not_recorded"

    errors = validator.validate(data)

    assert any("must include completed_at" in error for error in errors)


def test_invalid_completed_at_fails_validation() -> None:
    validator = _load_validator_module()
    data = copy.deepcopy(_load_data())
    task = data["epics"][0]["tasks"][0]
    task["completedAt"] = "2026-06-03"
    task["completionTimestampStatus"] = "recorded"
    task["completionTimestampSource"] = "task_frontmatter"

    errors = validator.validate(data)

    assert any("completedAt must be ISO 8601 with timezone" in error for error in errors)
