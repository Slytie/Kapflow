from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"


def test_board_get_is_stable_and_claim_retry_does_not_duplicate_effects(tmp_path: Path) -> None:
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

    board_first = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    board_second = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert board_first.status_code == 200
    assert board_second.status_code == 200
    assert board_first.payload == board_second.payload

    idempotency_key = f"api:{harness.scenario_id}:tasks.claim:retry"
    first_claim = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )
    second_claim = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )

    assert first_claim.status_code == 200
    assert second_claim.status_code == 409
    assert second_claim.payload["error"]["code"] == "duplicate_idempotency_key"

    events = harness.list_events()
    claimed_events = [
        event
        for event in events
        if event["event_type"] == "task.claimed"
        and event["payload"]["human_task_id"] == human_task_id
    ]
    assert len(claimed_events) == 1

    board_after_first = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    board_after_second = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert board_after_first.status_code == 200
    assert board_after_second.status_code == 200
    assert board_after_first.payload == board_after_second.payload
