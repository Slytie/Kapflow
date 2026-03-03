from __future__ import annotations

from tests.helpers.reference_model import reduce_events
from tests.helpers.trace_loader import load_trace


def test_workflow_run_pins_service_interval_and_timezone() -> None:
    state = reduce_events(load_trace("schedule_happy_path_publish_and_replan.jsonl"))
    run = state["workflow_runs"]["run-sd-2026-03-04"]
    assert run["partition_key"] == "SD-2026-03-04"
    assert run["logical_date"] == "2026-03-04"
    assert run["service_timezone"] == "Europe/Berlin"
    assert run["service_interval_start"] == "2026-03-03T23:00:00Z"
    assert run["service_interval_end"] == "2026-03-04T23:00:00Z"


def test_stage07_activation_keys_are_issue_scoped() -> None:
    state = reduce_events(load_trace("schedule_happy_path_publish_and_replan.jsonl"))
    stage07 = [task for task in state["task_runs"].values() if task["stage_id"] == "Stage07"]
    assert len(stage07) == 1
    assert stage07[0]["activation_key"] == "run-sd-2026-03-04|flag-noshow-001|exception_triage|0"


def test_drift_trace_marks_review_task_stale_and_records_drift() -> None:
    state = reduce_events(load_trace("schedule_drift_after_review.jsonl"))
    task = state["task_runs"]["tr-stage06-drift-001"]
    assert task["state"] == "STALE"
    pointer = state["pointers"]["ptr/schedule.published_schedule.workbook/SD-2026-03-04"]
    assert pointer["drift_detected"] is True
    assert pointer["reviewed_artifact_version_id"] == "av-published-candidate-001"
    assert pointer["promoted_artifact_version_id"] == "av-published-candidate-002"


def test_lease_expiry_trace_reopens_work_without_new_task_run() -> None:
    state = reduce_events(load_trace("schedule_lease_expiry_recovery.jsonl"))
    assert list(state["task_runs"]) == ["tr-stage07-lease-001"]
    first_human_task = state["human_tasks"]["ht-stage07-lease-001"]
    second_human_task = state["human_tasks"]["ht-stage07-lease-002"]
    assert first_human_task["state"] == "EXPIRED"
    assert first_human_task["reopened"] is True
    assert second_human_task["state"] == "COMPLETED"
    assert state["task_runs"]["tr-stage07-lease-001"]["state"] == "SUCCEEDED"
