from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage07_lease_expiry_recovery.yaml"
)


def test_stage07_lease_expiry_reopens_task_and_emits_evidence(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    sweep = harness.output("sweep_leases")["result"]
    assert sweep["processed_count"] == 1
    assert sweep["reopened_human_task_ids"] == [harness.output("activate_issue")["result"]["human_task"]["human_task_id"]]

    task = harness.show_task(harness.output("activate_issue")["result"]["human_task"]["human_task_id"])["human_task"]
    assert task["state"] == "OPEN"
    assert task["assignee_actor_id"] is None
    assert task["claimed_until"] is None
    assert int(task["reopen_count"]) == 1
    assert task["task_run_state"] == "READY"

    events = harness.list_events()
    lease_expired = [event for event in events if event["event_type"] == "task.lease_expired"]
    state_changes = [
        event
        for event in events
        if event["event_type"] == "task.run.state_changed"
        and event["payload"].get("reason") == "human_task_lease_expired"
    ]
    assert len(lease_expired) == 1
    assert lease_expired[0]["payload"]["reopened"] is True
    assert lease_expired[0]["payload"]["escalated"] is False
    assert len(state_changes) == 1
    assert state_changes[0]["payload"]["to_state"] == "READY"

    root_task_rows = harness.query_rows(
        """
        SELECT task_run_id, activation_key, state
        FROM task_runs
        WHERE workflow_run_id = ? AND stage_id = 'Stage07' AND task_kind = 'exception_triage'
        """,
        (harness.workflow_run_id,),
    )
    assert len(root_task_rows) == 1
    assert root_task_rows[0]["state"] == "READY"
