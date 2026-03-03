from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_major_replan_happy.yaml"
)


def _event_index(events: list[dict[str, Any]], event_type: str, predicate: Any) -> int:
    for index, event in enumerate(events):
        if event["event_type"] != event_type:
            continue
        if predicate(event):
            return index
    raise AssertionError(f"event index not found: {event_type}")


def test_stage07_major_replan_happy_path(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    flag_id = harness.output("create_flag")["flag"]["flag_id"]
    complete_triage = harness.output("complete_triage")["result"]
    spawned_children = complete_triage["spawned_children"]
    assert len(spawned_children) == 1
    child = spawned_children[0]
    assert child["stage_id"] == "Stage07"
    assert child["task_kind"] == "final_review"
    assert child["spawn_rule_id"] == "stage07_final_replan_review"
    assert child["spawned_from_flag_id"] == flag_id

    child_rows = harness.query_rows(
        """
        SELECT
            task_run_id,
            stage_id,
            task_kind,
            state,
            generation,
            spawned_from_flag_id,
            spawned_from_task_run_id,
            spawn_rule_id,
            spawn_cause_kind,
            spawn_depth,
            spawn_budget_key
        FROM task_runs
        WHERE task_run_id = ?
        """,
        (child["task_run_id"],),
    )
    assert len(child_rows) == 1
    child_row = child_rows[0]
    assert child_row["stage_id"] == "Stage07"
    assert child_row["task_kind"] == "final_review"
    assert child_row["state"] == "COMPLETED"
    assert child_row["spawned_from_flag_id"] == flag_id
    assert child_row["spawn_rule_id"] == "stage07_final_replan_review"
    assert child_row["spawn_cause_kind"] == "task_completion"
    assert int(child_row["spawn_depth"]) == 1
    assert str(child_row["spawn_budget_key"]).startswith("stage07:")

    flags = harness.list_flags()["flags"]
    assert len(flags) == 1
    assert flags[0]["state"] == "resolved"
    assert flags[0]["flag_id"] == flag_id

    pointers = harness.list_pointers()["pointers"]
    pointer_by_key = {row["pointer_key"]: row for row in pointers}
    base_pointer = pointer_by_key["official:schedule.published_schedule.workbook"]
    delta_pointer = pointer_by_key["official:schedule.replan_delta.workbook"]
    assert base_pointer["artifact_version_id"] == harness.output("create_base_artifact")["artifact_version"]["artifact_version_id"]
    assert delta_pointer["artifact_version_id"] == harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"]
    assert delta_pointer["promotion_reason"] == "official_major_replan"
    assert delta_pointer["approved_by_approval_id"] == harness.output("respond_major_replan_approval")["approval"]["approval_id"]

    approvals = harness.list_approvals()["approvals"]
    assert len(approvals) == 1
    assert approvals[0]["state"] == "RESPONDED"
    assert approvals[0]["response_kind"] == "approve"

    events = harness.list_events()
    assert any(event["event_type"] == "artifact.pointer.promoted" for event in events)
    assert not any(event["event_type"] == "artifact.pointer.drift_detected" for event in events)

    complete_triage_idx = _event_index(
        events,
        "task.completed",
        lambda event: event["payload"]["human_task_id"]
        == harness.output("activate_issue")["result"]["human_task"]["human_task_id"],
    )
    child_created_idx = _event_index(
        events,
        "task.run.created",
        lambda event: event["payload"]["task_run_id"] == child["task_run_id"],
    )
    approval_requested_idx = _event_index(
        events,
        "approval.requested",
        lambda event: event["payload"]["approval_id"]
        == harness.output("request_major_replan_approval")["approval"]["approval_id"],
    )
    pointer_promoted_idx = _event_index(
        events,
        "artifact.pointer.promoted",
        lambda event: event["payload"]["promoted_artifact_version_id"]
        == harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"],
    )
    assert complete_triage_idx < child_created_idx < approval_requested_idx < pointer_promoted_idx


def test_stage07_negative_cannot_promote_major_replan_without_approval(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    for step_id in [
        "create_base_artifact",
        "promote_base_pointer",
        "create_flag",
        "activate_issue",
        "claim_triage",
        "complete_triage",
        "claim_final_review",
        "complete_final_review",
        "create_replan_delta",
    ]:
        harness.run_named_step(step_id)

    error = harness.run_action(
        action="pointers.promote",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": "Stage07",
            "pointer_key": "official:schedule.replan_delta.workbook",
            "artifact_kind": "schedule.replan_delta.workbook",
            "artifact_version_id": harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"],
            "promotion_reason": "official_major_replan",
            "promoted_by_task_run_id": harness.output("complete_final_review")["result"]["task_run"]["task_run_id"],
            "reviewed_base_artifact_version_id": harness.output("create_base_artifact")["artifact_version"]["artifact_version_id"],
            "base_pointer_key": "official:schedule.published_schedule.workbook",
            "idempotency_key": f"scenario:{harness.scenario_id}:negative:major-without-approval",
        },
        expect_error_code="approval_required_for_promotion",
    )
    assert error["status"] == "error"
    assert error["error"]["error_code"] == "approval_required_for_promotion"

    events = harness.list_events()
    assert not any(
        event["event_type"] == "artifact.pointer.promoted"
        and event["payload"]["promoted_artifact_version_id"]
        == harness.output("create_replan_delta")["artifact_version"]["artifact_version_id"]
        for event in events
    )
