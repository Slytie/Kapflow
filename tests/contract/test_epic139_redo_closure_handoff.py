from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "frontend/src/data/capexEpicProgressData.json"
HANDOFF_PATH = ROOT / "docs/planning/EPIC139_REDO_CLOSURE_HANDOFF.md"
MATRIX_PATH = ROOT / "docs/planning/EPIC139_REDO_RECLOSE_MATRIX.md"


def _load_data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _matrix_task_ids() -> set[str]:
    text = MATRIX_PATH.read_text(encoding="utf-8")
    task_ids: set[str] = set()
    for line in text.splitlines():
        if line.startswith("| TASK-"):
            task_ids.add(line.split("|", maxsplit=2)[1].strip())
    return task_ids


def _task_text(task_id: str) -> str:
    matches = sorted((ROOT / "codex/tasks").glob(f"{task_id}-*.md"))
    assert len(matches) == 1
    return matches[0].read_text(encoding="utf-8")


def test_epic139_redo_closure_handoff_progress_stays_done() -> None:
    data = _load_data()
    epics = {epic["id"]: epic for epic in data["epics"]}
    epic139 = epics["EPIC-139"]

    assert epic139["displayStatus"] == "done"
    assert epic139["counts"]["needs_review"] == 0
    assert epic139["counts"]["blocked"] == 0
    assert "State C / repaired" in epic139["reviewPosture"]
    assert "TASK-0647" in epic139["reviewPosture"]
    assert "RED/active" not in epic139["reviewPosture"]
    assert "Gated while EPIC-139 remains RED" not in epic139["reviewPosture"]

    task_statuses = {task["id"]: task["displayStatus"] for task in epic139["tasks"]}
    assert task_statuses["TASK-0576"] == "done"
    for task_id in ("TASK-0643", "TASK-0644", "TASK-0645", "TASK-0646", "TASK-0647"):
        assert task_statuses[task_id] == "done"

    assert epics["EPIC-140"]["displayStatus"] == "done"
    assert "EPIC-140 project/access work is closed" in epics["EPIC-140"]["reviewPosture"]
    assert "CAPEX activation remains blocked" in epics["EPIC-140"]["reviewPosture"]


def test_epic139_red_interlocks_remain_lifted_after_closure_handoff() -> None:
    epics = {epic["id"]: epic for epic in _load_data()["epics"]}

    assert epics["EPIC-143"]["displayStatus"] == "in_progress"
    assert epics["EPIC-150"]["displayStatus"] == "not_started"
    assert epics["EPIC-151"]["displayStatus"] == "not_started"
    for epic_id in ("EPIC-143", "EPIC-150", "EPIC-151"):
        assert "Gated while EPIC-139 remains RED" not in epics[epic_id]["reviewPosture"]


def test_epic139_redo_closure_handoff_note_defines_boundary() -> None:
    text = HANDOFF_PATH.read_text(encoding="utf-8")

    assert "`TASK-0643` through `TASK-0646` close the EPIC-139 redo package requirements" in text
    assert "`TASK-0647` is post-package handoff evidence, not a new package source row" in text
    assert "EPIC-140 is the next gated CAPEX tranche" in text
    assert "CAPEX runtime activation remains blocked" in text
    assert "should not be marked blocked merely because of EPIC-139" in text


def test_epic139_reclose_matrix_remains_package_bounded() -> None:
    matrix_task_ids = _matrix_task_ids()

    assert {"TASK-0643", "TASK-0644", "TASK-0645", "TASK-0646"} <= matrix_task_ids
    assert "TASK-0647" not in matrix_task_ids

    task0647_text = _task_text("TASK-0647")
    assert "depends_on: [\"TASK-0646\"]" in task0647_text
    assert "Source task ID: `E139-REDO-HANDOFF`" in task0647_text
    assert "Adding TASK-0647 to the TASK-0643 through TASK-0646 package reclose matrix" in task0647_text


def test_epic139_and_epic150_docs_preserve_corrected_handoff_language() -> None:
    epic139_text = (ROOT / "docs/planning/epics/EPIC-139.md").read_text(
        encoding="utf-8"
    )
    epic150_text = (ROOT / "docs/planning/epics/EPIC-150.md").read_text(
        encoding="utf-8"
    )
    epic150_context = (ROOT / "codex/context/EPIC-150.md").read_text(
        encoding="utf-8"
    )

    assert "`TASK-0647` (`EPIC-139-REDO`) - Closure handoff and next-tranche guard" in epic139_text
    assert re.search(r"TASK-0647.*EPIC-140 gated project/access work", epic139_text, re.S)
    assert "EPIC-139 - artifact/blob custody and auth-before-read" not in epic150_text
    assert (
        "EPIC-139 - domain-boundary cleanup and approval/workpage neutrality"
        in epic150_text
    )
    assert "EPIC-139 approval/workpage domain neutrality is accepted" in epic150_context
