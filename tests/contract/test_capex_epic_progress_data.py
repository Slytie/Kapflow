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


def test_capex_epic_progress_data_matches_regenerated_output() -> None:
    validator = _load_validator_module()

    assert _load_data() == validator.build_data()


def test_capex_epic_progress_data_records_repo_owned_local_rule() -> None:
    meta = _load_data()["meta"]

    assert meta["localOnly"] is True
    assert meta["lastUpdated"] == "2026-06-17"
    assert (
        meta["codexRule"]
        == "When a CAPEX task is completed, set status: DONE, add completed_at in ISO 8601 timezone form, add completion/closeout evidence, and regenerate this progress data in the same change."
    )


def test_capex_epic_progress_data_uses_v2_estimates() -> None:
    data = _load_data()

    assert data["schemaVersion"] == "capex.epic_progress.v2"
    assert data["summary"]["estimate"]["remainingTasks"] == 312
    assert data["summary"]["estimate"]["etaDate"] == "2026-09-09"
    assert data["summary"]["estimate"]["label"] == "ETA 2026-09-09"
    assert all("estimate" in epic for epic in data["epics"])

    epic139 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-139")
    assert epic139["displayStatus"] == "done"
    assert epic139["counts"]["done"] == 22
    assert epic139["counts"]["needs_review"] == 0
    assert epic139["estimate"]["label"] == "Complete"


def test_epic139_redo_final_acceptance_releases_red_interlocks() -> None:
    data = _load_data()
    epics = {epic["id"]: epic for epic in data["epics"]}

    epic139 = epics["EPIC-139"]
    assert epic139["displayStatus"] == "done"
    assert "State C / repaired" in epic139["reviewPosture"]
    task_statuses = {task["id"]: task["displayStatus"] for task in epic139["tasks"]}
    assert task_statuses["TASK-0576"] == "done"
    assert task_statuses["TASK-0643"] == "done"
    assert task_statuses["TASK-0644"] == "done"
    assert task_statuses["TASK-0645"] == "done"
    assert task_statuses["TASK-0646"] == "done"
    assert task_statuses["TASK-0647"] == "done"

    assert epics["EPIC-143"]["displayStatus"] == "in_progress"
    assert epics["EPIC-150"]["displayStatus"] == "not_started"
    assert epics["EPIC-151"]["displayStatus"] == "in_progress"
    for epic_id in ("EPIC-143", "EPIC-150", "EPIC-151"):
        assert "Gated while EPIC-139 remains RED" not in epics[epic_id]["reviewPosture"]

    epic150_text = (ROOT / "docs/planning/epics/EPIC-150.md").read_text(
        encoding="utf-8"
    )
    epic150_context = (ROOT / "codex/context/EPIC-150.md").read_text(
        encoding="utf-8"
    )
    assert "EPIC-139 - artifact/blob custody and auth-before-read" not in epic150_text
    assert (
        "EPIC-139 - domain-boundary cleanup and approval/workpage neutrality"
        in epic150_text
    )
    assert "EPIC-139 approval/workpage domain neutrality is accepted" in epic150_context
    assert "platform artifact/blob auth-before-read is resolved" in epic150_context
    assert "EPIC-141 SourceRefs are meaningful and resolved" in epic150_context


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
