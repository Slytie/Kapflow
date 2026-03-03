from __future__ import annotations

from tests.helpers.reference_model import reduce_events
from tests.helpers.trace_loader import load_trace


def test_conditional_task_spawn_trace_records_child_task_lineage() -> None:
    events = load_trace("schedule_conditional_task_spawn_review_loop.jsonl")
    parent_completion_idx = next(i for i, event in enumerate(events) if event["event_id"] == "evt-spawn-0005")
    child_creation_idx = next(i for i, event in enumerate(events) if event["event_id"] == "evt-spawn-0006")
    assert child_creation_idx > parent_completion_idx

    state = reduce_events(events)
    child = state["task_runs"]["tr-stage06-info-001"]
    assert child["stage_id"] == "Stage06"
    assert child["task_kind"] == "information_request"
    assert child["spawned_from_task_run_id"] == "tr-stage06-review-001"
    assert child["spawn_rule_id"] == "stage06_request_missing_information"
    assert child["spawn_cause_kind"] == "task_completion"
    assert child["spawn_depth"] == 1
