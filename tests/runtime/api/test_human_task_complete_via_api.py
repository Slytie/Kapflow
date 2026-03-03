from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"


def test_complete_human_task_via_api_uses_canonical_completion_path(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    harness.run_named_step("claim_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )

    completed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/complete",
        payload={
            "outcome": "draft_is_publish_ready",
            "idempotency_key": f"api:{harness.scenario_id}:tasks.complete",
        },
    )
    assert completed.status_code == 200
    result = completed.payload["result"]
    assert result["human_task"]["state"] == "COMPLETED"
    assert result["task_run"]["state"] == "COMPLETED"
    assert len(result["spawned_children"]) == 1

    child = result["spawned_children"][0]
    child_human_task = harness.show_task(child["human_task_id"])["human_task"]
    assert child_human_task["task_kind"] == "final_review"
    assert child_human_task["state"] == "OPEN"

    events = harness.list_events()
    completed_events = [
        event
        for event in events
        if event["event_type"] == "task.completed"
        and event["payload"]["human_task_id"] == human_task_id
    ]
    child_task_events = [
        event
        for event in events
        if event["event_type"] == "task.run.created"
        and event["payload"].get("task_run_id") == child["task_run_id"]
    ]
    child_human_events = [
        event
        for event in events
        if event["event_type"] == "task.created"
        and event["payload"].get("human_task_id") == child["human_task_id"]
    ]
    assert len(completed_events) == 1
    assert len(child_task_events) == 1
    assert len(child_human_events) == 1
