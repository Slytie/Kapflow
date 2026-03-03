from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness
from tests.runtime.helpers.runtime_cli import REPO_ROOT

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)


def _first_event(
    events: list[dict[str, Any]],
    event_type: str,
    predicate: Any,
) -> dict[str, Any]:
    for event in events:
        if event["event_type"] != event_type:
            continue
        if predicate(event):
            return event
    raise AssertionError(f"event not found: {event_type}")


def _event_index(
    events: list[dict[str, Any]],
    event_type: str,
    predicate: Any,
) -> int:
    for index, event in enumerate(events):
        if event["event_type"] != event_type:
            continue
        if predicate(event):
            return index
    raise AssertionError(f"event index not found: {event_type}")


def test_stage06_publish_happy_path_step_run(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    scenario = harness.scenario
    parent_complete = harness.output("complete_stage06_review")
    spawned_children = parent_complete["result"]["spawned_children"]
    assert len(spawned_children) == 1
    child = spawned_children[0]
    expected_child = scenario["expected_spawned_children"][0]
    assert child["stage_id"] == expected_child["stage_id"]
    assert child["task_kind"] == expected_child["task_kind"]
    assert child["spawn_rule_id"] == expected_child["spawn_rule_id"]

    events = harness.list_events()
    ordered_contains = scenario["expected_events"]["ordered_contains"]
    cursor = 0
    for expected_event_type in ordered_contains:
        while cursor < len(events) and events[cursor]["event_type"] != expected_event_type:
            cursor += 1
        assert cursor < len(events), f"missing expected event type in order: {expected_event_type}"
        cursor += 1

    parent_human_task_id = harness.output("create_stage06_review")["result"]["human_task"]["human_task_id"]
    parent_task_run_id = harness.output("create_stage06_review")["result"]["task_run"]["task_run_id"]
    parent_completed_event = _first_event(
        events,
        "task.completed",
        lambda event: event["payload"]["human_task_id"] == parent_human_task_id
        and event["payload"]["completion_code"] == "draft_is_publish_ready",
    )
    child_task_run_rows = harness.query_rows(
        """
        SELECT
            task_run_id,
            workflow_run_id,
            stage_id,
            task_kind,
            state,
            spawned_from_task_run_id,
            spawn_rule_id,
            spawn_cause_kind,
            spawn_cause_event_id,
            spawn_depth,
            spawn_budget_key
        FROM task_runs
        WHERE task_run_id = ?
        """,
        (child["task_run_id"],),
    )
    assert len(child_task_run_rows) == 1
    child_task_run = child_task_run_rows[0]
    assert child_task_run["workflow_run_id"] == harness.workflow_run_id
    assert child_task_run["stage_id"] == "Stage06"
    assert child_task_run["task_kind"] == "final_review"
    assert child_task_run["state"] == "COMPLETED"
    assert child_task_run["spawned_from_task_run_id"] == parent_task_run_id
    assert child_task_run["spawn_rule_id"] == "stage06_final_publish_review"
    assert child_task_run["spawn_cause_kind"] == "task_completion"
    assert child_task_run["spawn_cause_event_id"] == parent_completed_event["event_id"]
    assert int(child_task_run["spawn_depth"]) == 1
    assert str(child_task_run["spawn_budget_key"]).startswith("stage06:")

    created_artifact_version_id = harness.output("create_published_artifact")["artifact_version"]["artifact_version_id"]
    promoted_pointer = harness.output("promote_official_pointer")["pointer"]
    assert promoted_pointer["artifact_version_id"] == created_artifact_version_id
    assert promoted_pointer["pointer_key"] == "official:schedule.published_schedule.workbook"
    assert promoted_pointer["promotion_reason"] == "official_publish"

    parent_complete_index = _event_index(
        events,
        "task.completed",
        lambda event: event["payload"]["human_task_id"] == parent_human_task_id
        and event["payload"]["completion_code"] == "draft_is_publish_ready",
    )
    child_task_run_created_index = _event_index(
        events,
        "task.run.created",
        lambda event: event["payload"]["task_run_id"] == child["task_run_id"],
    )
    approval_requested_index = _event_index(
        events,
        "approval.requested",
        lambda event: event["payload"]["approval_id"]
        == harness.output("request_publish_approval")["approval"]["approval_id"],
    )
    approval_responded_index = _event_index(
        events,
        "approval.responded",
        lambda event: event["payload"]["approval_id"]
        == harness.output("respond_publish_approval")["approval"]["approval_id"],
    )
    artifact_created_index = _event_index(
        events,
        "artifact.version.created",
        lambda event: event["payload"]["artifact_version_id"] == created_artifact_version_id,
    )
    pointer_promoted_index = _event_index(
        events,
        "artifact.pointer.promoted",
        lambda event: event["payload"]["promoted_artifact_version_id"] == created_artifact_version_id,
    )

    assert parent_complete_index < child_task_run_created_index
    assert child_task_run_created_index < approval_requested_index
    assert approval_requested_index < approval_responded_index
    assert approval_responded_index < artifact_created_index
    assert artifact_created_index < pointer_promoted_index

    tasks_payload = harness.list_tasks()
    assert tasks_payload["status"] == "ok"
    tasks = tasks_payload["tasks"]
    assert len(tasks) == int(scenario["expected_query_rows"]["task_rows"])
    assert {task["task_kind"] for task in tasks} == {"review_packet", "final_review"}
    assert all(task["state"] == "COMPLETED" for task in tasks)

    approvals_payload = harness.list_approvals()
    assert approvals_payload["status"] == "ok"
    approvals = approvals_payload["approvals"]
    assert len(approvals) == int(scenario["expected_query_rows"]["approval_rows"])
    assert approvals[0]["state"] == "RESPONDED"
    assert approvals[0]["response_kind"] == "approve"

    pointers_payload = harness.list_pointers()
    assert pointers_payload["status"] == "ok"
    pointers = pointers_payload["pointers"]
    assert len(pointers) == int(scenario["expected_query_rows"]["pointer_rows"])
    assert pointers[0]["artifact_version_id"] == created_artifact_version_id


def test_stage06_negative_cannot_promote_official_pointer_without_approval(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    for step_id in [
        "create_stage06_review",
        "claim_stage06_review",
        "complete_stage06_review",
        "claim_final_review",
        "complete_final_review",
        "create_published_artifact",
    ]:
        harness.run_named_step(step_id)

    pointer_error = harness.run_action(
        action="pointers.promote",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": "Stage06",
            "pointer_key": "official:schedule.published_schedule.workbook",
            "artifact_kind": "schedule.published_schedule.workbook",
            "artifact_version_id": harness.output("create_published_artifact")["artifact_version"]["artifact_version_id"],
            "promotion_reason": "official_publish",
            "promoted_by_task_run_id": harness.output("complete_final_review")["result"]["task_run"]["task_run_id"],
            "idempotency_key": f"scenario:{harness.scenario_id}:negative:pointer-without-approval",
        },
        expect_error_code="approval_required_for_promotion",
    )
    assert pointer_error["status"] == "error"
    assert pointer_error["error"]["error_code"] == "approval_required_for_promotion"

    events = harness.list_events()
    assert not any(event["event_type"] == "artifact.pointer.promoted" for event in events)
