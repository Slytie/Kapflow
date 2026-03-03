from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness
from tests.runtime.helpers.runtime_cli import REPO_ROOT

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_retry_does_not_duplicate_children.yaml"
)


def test_stage06_retry_with_same_idempotency_key_does_not_duplicate_child_tasks(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    retry_output = harness.output("retry_complete_stage06_review")
    assert retry_output["status"] == "error"
    assert retry_output["error"]["error_code"] == "duplicate_idempotency_key"

    complete_output = harness.output("complete_stage06_review")
    spawned_children = complete_output["result"]["spawned_children"]
    assert len(spawned_children) == 1
    child = spawned_children[0]

    parent_task_run_id = harness.output("create_stage06_review")["result"]["task_run"]["task_run_id"]
    child_rows = harness.query_rows(
        """
        SELECT task_run_id
        FROM task_runs
        WHERE
            workflow_run_id = ?
            AND spawned_from_task_run_id = ?
            AND spawn_rule_id = 'stage06_final_publish_review'
        """,
        (harness.workflow_run_id, parent_task_run_id),
    )
    assert len(child_rows) == 1
    assert child_rows[0]["task_run_id"] == child["task_run_id"]

    events = harness.list_events()
    child_task_run_created = [
        event
        for event in events
        if event["event_type"] == "task.run.created"
        and event["payload"].get("spawn_rule_id") == "stage06_final_publish_review"
    ]
    child_human_task_created = [
        event
        for event in events
        if event["event_type"] == "task.created"
        and event["payload"]["task_kind"] == "final_review"
    ]
    assert len(child_task_run_created) == 1
    assert len(child_human_task_created) == 1
