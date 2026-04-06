from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_INDEX_PATH = REPO_ROOT / "docs/planning/TASK_INDEX.md"
CURRENT_FOCUS_PATH = REPO_ROOT / "docs/status/CURRENT_FOCUS.md"
EPIC_125_PATH = REPO_ROOT / "docs/planning/epics/EPIC-125.md"
EPIC_125_CONTEXT_PATH = REPO_ROOT / "codex/context/EPIC-125.md"
TASK_0154_PATH = REPO_ROOT / "codex/tasks/TASK-0154-minimal-manual-daily-replan-lane-via-live-dispatch.md"
TASK_0157_PATH = REPO_ROOT / "codex/tasks/TASK-0157-close-epic-125-capture-first-demo-feedback-and-sync-doc-truth.md"
TASK_0158_PATH = REPO_ROOT / "codex/tasks/TASK-0158-triage-first-demo-feedback-and-land-high-value-ux-corrections.md"
TASK_0159_PATH = REPO_ROOT / "codex/tasks/TASK-0159-harden-regression-observability-and-failure-state-truth-for-weekly-daily-operator-loops.md"
TASK_0160_PATH = REPO_ROOT / "codex/tasks/TASK-0160-freeze-workpages-v1-boundary-clean-up-route-posture-and-close-doc-truth.md"
FEEDBACK_NOTE_PATH = (
    REPO_ROOT / "docs/planning/LOGISTICS_WORKPAGES_EPIC125_CLOSEOUT_AND_FEEDBACK_NOTE.md"
)


def test_epic_125_closeout_docs_freeze_completed_status_and_no_open_backlog() -> None:
    task_index = TASK_INDEX_PATH.read_text(encoding="utf-8")
    current_focus = CURRENT_FOCUS_PATH.read_text(encoding="utf-8")
    epic_125 = EPIC_125_PATH.read_text(encoding="utf-8")
    epic_125_context = EPIC_125_CONTEXT_PATH.read_text(encoding="utf-8")
    task_0154 = TASK_0154_PATH.read_text(encoding="utf-8")
    task_0157 = TASK_0157_PATH.read_text(encoding="utf-8")
    task_0158 = TASK_0158_PATH.read_text(encoding="utf-8")
    task_0159 = TASK_0159_PATH.read_text(encoding="utf-8")
    task_0160 = TASK_0160_PATH.read_text(encoding="utf-8")

    assert "| TASK-0154 | EPIC-125 | DONE |" in task_index
    assert "| TASK-0157 | EPIC-125 | DONE |" in task_index

    assert "Completed on 2026-04-06." in epic_125
    assert "- TASK-0154 - DONE" in epic_125
    assert "- TASK-0157 - DONE" in epic_125

    assert "EPIC-125 is closed as completed history." in epic_125_context
    assert "TASK-0154` and `TASK-0157` are now complete" in epic_125_context

    assert "status: DONE" in task_0154
    assert "status: DONE" in task_0157
    assert "status: DONE" in task_0158
    assert "status: DONE" in task_0159
    assert "status: DONE" in task_0160
    assert "planned under EPIC-126" not in task_0158
    assert "planned under EPIC-126" not in task_0159
    assert "planned under EPIC-126" not in task_0160

    assert "EPIC-125 is now completed history:" in current_focus
    assert "No EPIC-125 carry-forward backlog item remains open." in current_focus
    assert "`TASK-0154` - Finish the remaining bounded live-dispatch closure" not in current_focus
    assert "`TASK-0157` - Capture post-demo feedback against the canonical Workpages v1 posture." not in current_focus


def test_epic_125_feedback_note_freezes_bounded_themes_and_downstream_epics() -> None:
    note = FEEDBACK_NOTE_PATH.read_text(encoding="utf-8")

    assert "EPIC-125 is complete as of `2026-04-06`." in note
    assert "demo-shell and route discoverability needed simplification and canonical-route clarity" in note
    assert (
        "weekly schedule editing, route-demand truth, driver preferences, and live day-of control needed a clearer boundary split"
        in note
    )
    assert "workpage lineage, latest-draft, and action semantics needed to move server-side" in note
    assert (
        "supported-environment and deterministic demo-prep truth needed to replace ad hoc local-demo assumptions"
        in note
    )
    assert "Still deferred for future selection" in note
    for epic_id in ("EPIC-126", "EPIC-131", "EPIC-132", "EPIC-133", "EPIC-134"):
        assert epic_id in note
