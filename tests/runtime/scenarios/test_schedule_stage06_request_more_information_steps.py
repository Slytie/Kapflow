from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness
from tests.runtime.helpers.runtime_cli import REPO_ROOT

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_review_requires_more_information.yaml"
)


def test_stage06_review_requires_more_information_spawns_child_and_no_publish_pointer(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    scenario = harness.scenario
    complete_output = harness.output("complete_stage06_review")
    spawned_children = complete_output["result"]["spawned_children"]
    assert len(spawned_children) == 1
    child = spawned_children[0]
    expected_child = scenario["expected_spawned_children"][0]
    assert child["stage_id"] == expected_child["stage_id"]
    assert child["task_kind"] == expected_child["task_kind"]
    assert child["spawn_rule_id"] == expected_child["spawn_rule_id"]

    child_task_rows = harness.query_rows(
        """
        SELECT
            task_run_id,
            stage_id,
            task_kind,
            state,
            spawned_from_task_run_id,
            spawn_rule_id,
            spawn_cause_kind,
            spawn_depth
        FROM task_runs
        WHERE task_run_id = ?
        """,
        (child["task_run_id"],),
    )
    assert len(child_task_rows) == 1
    child_task = child_task_rows[0]
    assert child_task["stage_id"] == "Stage06"
    assert child_task["task_kind"] == "information_request"
    assert child_task["state"] == "READY"
    assert child_task["spawn_rule_id"] == "stage06_request_missing_information"
    assert child_task["spawn_cause_kind"] == "task_completion"
    assert int(child_task["spawn_depth"]) == 1

    child_human_task = harness.show_task(child["human_task_id"])["human_task"]
    assert child_human_task["state"] == "OPEN"
    assert child_human_task["task_kind"] == "information_request"
    assert child_human_task["stage_id"] == "Stage06"
    assert child_human_task["candidate_roles"] == ["fleet_coordinator", "schedule_planner"]

    events = harness.list_events()
    assert any(
        event["event_type"] == "task.completed"
        and event["payload"]["completion_code"] == "review_requires_more_information"
        for event in events
    )
    assert any(
        event["event_type"] == "task.run.created"
        and event["payload"].get("spawn_rule_id") == "stage06_request_missing_information"
        for event in events
    )
    assert any(
        event["event_type"] == "task.created"
        and event["payload"]["task_kind"] == "information_request"
        for event in events
    )
    assert not any(event["event_type"] == "artifact.pointer.promoted" for event in events)

    tasks_payload = harness.list_tasks()
    tasks = tasks_payload["tasks"]
    assert len(tasks) == int(scenario["expected_query_rows"]["task_rows"])
    open_tasks = [row for row in tasks if row["state"] == "OPEN"]
    assert len(open_tasks) == int(scenario["expected_query_rows"]["open_tasks"])
    assert open_tasks[0]["task_kind"] == "information_request"
    assert open_tasks[0]["stage_id"] == "Stage06"

    approvals_payload = harness.list_approvals()
    assert len(approvals_payload["approvals"]) == int(scenario["expected_query_rows"]["approval_rows"])
    pointers_payload = harness.list_pointers()
    assert len(pointers_payload["pointers"]) == int(scenario["expected_query_rows"]["pointer_rows"])
