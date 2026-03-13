from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"


def test_claim_human_task_via_api_updates_canonical_rows_and_events(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )

    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:tasks.claim",
        },
    )
    assert claimed.status_code == 200
    assert claimed.payload["status"] == "ok"
    assert claimed.payload["result"]["human_task"]["state"] == "CLAIMED"

    persisted = harness.show_task(human_task_id)["human_task"]
    assert persisted["state"] == "CLAIMED"
    assert persisted["assignee_actor_id"] == "human:dispatch-supervisor-1"

    events = harness.list_events()
    claimed_events = [
        event
        for event in events
        if event["event_type"] == "task.claimed"
        and event["payload"]["human_task_id"] == human_task_id
    ]
    state_changed_events = [
        event
        for event in events
        if event["event_type"] == "task.run.state_changed"
        and event["payload"]["reason"] == "human_task_claimed"
    ]
    assert len(claimed_events) == 1
    assert len(state_changed_events) == 1


def test_claim_human_task_via_api_rejects_wrong_role_without_side_effects(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:schedule-planner-9",
        actor_type="human",
        actor_roles=["schedule_planner"],
    )

    denied = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:tasks.claim:forbidden",
        },
    )
    assert denied.status_code == 403
    error = denied.payload["error"]
    assert error["code"] == "task_claim_forbidden"
    assert error["details"]["capability_id"] == "task.claim"
    assert "candidate_role_mismatch" in error["details"]["reason_codes"]

    persisted = harness.show_task(human_task_id)["human_task"]
    assert persisted["state"] == "OPEN"
    assert persisted["assignee_actor_id"] is None
    assert persisted["task_run_state"] == "READY"

    events = harness.list_events()
    assert not any(event["event_type"] == "task.claimed" for event in events)
    assert not any(
        event["event_type"] == "task.run.state_changed"
        and event["payload"].get("reason") == "human_task_claimed"
        for event in events
    )
