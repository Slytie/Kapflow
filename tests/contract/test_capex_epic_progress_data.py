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
    assert meta["lastUpdated"] == "2026-06-23"
    assert (
        meta["codexRule"]
        == "When a CAPEX task is completed, set status: DONE, add completed_at in ISO 8601 timezone form, add completion/closeout evidence, and regenerate this progress data in the same change."
    )


def test_capex_epic_progress_data_uses_v2_estimates() -> None:
    data = _load_data()

    assert data["schemaVersion"] == "capex.epic_progress.v2"
    assert data["summary"]["taskCount"] == 432
    assert data["summary"]["estimate"]["completedTasks"] == 138
    assert data["summary"]["estimate"]["remainingTasks"] == 294
    assert data["summary"]["estimate"]["etaDate"] == "2026-08-17"
    assert data["summary"]["estimate"]["label"] == "ETA 2026-08-17"
    assert all("estimate" in epic for epic in data["epics"])

    epic139 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-139")
    assert epic139["displayStatus"] == "done"
    assert epic139["counts"]["done"] == 22
    assert epic139["counts"]["needs_review"] == 0
    assert epic139["estimate"]["label"] == "Complete"

    epic150 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-150")
    assert epic150["displayStatus"] == "in_progress"
    assert epic150["taskCount"] == 66
    assert epic150["counts"]["done"] == 3
    assert epic150["counts"]["not_started"] == 63
    task_ids = {task["id"] for task in epic150["tasks"]}
    assert {"TASK-0607", "TASK-0642"} <= task_ids

    epic141 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-141")
    epic142 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-142")
    epic143 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-143")
    task_statuses = {
        task["id"]: task["displayStatus"]
        for epic in (epic141, epic142, epic143)
        for task in epic["tasks"]
    }
    assert task_statuses["TASK-0266"] == "done"
    assert task_statuses["TASK-0267"] == "done"
    assert task_statuses["TASK-0268"] == "done"
    assert task_statuses["TASK-0269"] == "done"
    assert task_statuses["TASK-0270"] == "done"
    assert task_statuses["TASK-0271"] == "done"
    assert task_statuses["TASK-0272"] == "done"
    assert task_statuses["TASK-0273"] == "done"
    assert task_statuses["TASK-0274"] == "done"
    assert task_statuses["TASK-0372"] == "done"
    assert task_statuses["TASK-0373"] == "done"
    assert task_statuses["TASK-0374"] == "done"
    assert task_statuses["TASK-0391"] == "done"
    assert task_statuses["TASK-0392"] == "done"
    assert task_statuses["TASK-0393"] == "done"
    assert task_statuses["TASK-0394"] == "done"
    assert task_statuses["TASK-0395"] == "done"
    assert task_statuses["TASK-0396"] == "done"
    assert task_statuses["TASK-0397"] == "done"
    assert task_statuses["TASK-0398"] == "done"
    assert task_statuses["TASK-0399"] == "done"
    assert task_statuses["TASK-0276"] == "done"
    assert task_statuses["TASK-0278"] == "done"
    assert task_statuses["TASK-0283"] == "done"
    assert task_statuses["TASK-0284"] == "done"
    assert task_statuses["TASK-0285"] == "done"
    assert task_statuses["TASK-0286"] == "done"
    assert task_statuses["TASK-0287"] == "done"
    assert task_statuses["TASK-0288"] == "done"
    assert task_statuses["TASK-0289"] == "done"

    epic151 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-151")
    epic151_task_statuses = {
        task["id"]: task["displayStatus"] for task in epic151["tasks"]
    }
    assert epic151_task_statuses["TASK-0277"] == "done"
    assert epic151_task_statuses["TASK-0290"] == "done"
    assert epic151_task_statuses["TASK-0539"] == "done"
    assert epic151_task_statuses["TASK-0540"] == "done"
    assert epic151_task_statuses["TASK-0659"] == "done"

    epic144 = next(epic for epic in data["epics"] if epic["id"] == "EPIC-144")
    epic144_task_statuses = {
        task["id"]: task["displayStatus"] for task in epic144["tasks"]
    }
    assert epic144_task_statuses["TASK-0299"] == "done"


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
    assert epics["EPIC-150"]["displayStatus"] == "in_progress"
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
