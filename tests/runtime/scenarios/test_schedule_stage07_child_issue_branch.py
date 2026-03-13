from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_child_issue_branch.yaml"
)


def test_stage07_child_issue_branch_and_retry_no_duplicate_child(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    for step_id in [
        "create_flag",
        "activate_issue",
        "claim_issue",
        "upload_exception_board",
        "complete_issue",
    ]:
        harness.run_named_step(step_id)

    complete = harness.output("complete_issue")["result"]
    spawned_children = complete["spawned_children"]
    assert len(spawned_children) == 1
    child = spawned_children[0]
    assert child["task_kind"] == "exception_triage"
    assert child["spawn_rule_id"] == "stage07_follow_on_exception_triage"
    assert child["spawned_from_flag_id"] == harness.output("create_flag")["flag"]["flag_id"]

    retry = harness.run_action(
        action="tasks.complete",
        payload={
            "human_task_id": harness.output("activate_issue")["result"]["human_task"]["human_task_id"],
            "actor_id": "human:ops-manager-3",
            "actor_type": "human",
            "outcome": "resolution_creates_child_issue",
            "idempotency_key": f"scenario:{harness.scenario_id}:tasks.complete:root",
        },
    )
    assert retry["status"] == "ok"
    assert retry["idempotent_replay"] is True

    child_rows = harness.query_rows(
        """
        SELECT task_run_id, spawned_from_flag_id, spawn_rule_id, spawn_cause_kind, spawn_depth
        FROM task_runs
        WHERE workflow_run_id = ? AND task_kind = 'exception_triage'
        ORDER BY created_at ASC, task_run_id ASC
        """,
        (harness.workflow_run_id,),
    )
    assert len(child_rows) == 2
    assert child_rows[1]["task_run_id"] == child["task_run_id"]
    assert child_rows[1]["spawned_from_flag_id"] == harness.output("create_flag")["flag"]["flag_id"]
    assert child_rows[1]["spawn_rule_id"] == "stage07_follow_on_exception_triage"
    assert child_rows[1]["spawn_cause_kind"] == "task_completion"
    assert int(child_rows[1]["spawn_depth"]) == 1

    events = harness.list_events()
    child_created_events = [
        event
        for event in events
        if event["event_type"] == "task.run.created"
        and event["payload"].get("spawn_rule_id") == "stage07_follow_on_exception_triage"
    ]
    child_human_events = [
        event
        for event in events
        if event["event_type"] == "task.created"
        and event["payload"].get("task_kind") == "exception_triage"
        and event["payload"].get("human_task_id")
        == harness.output("complete_issue")["result"]["spawned_children"][0]["human_task_id"]
    ]
    assert len(child_created_events) == 1
    assert len(child_human_events) == 1
