from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


CLAIM_SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
FLAG_SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)


def _dispatch_supervisor_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_claim_retry_replays_success_without_duplicate_effects(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(CLAIM_SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])
    client = _dispatch_supervisor_client(harness)

    idempotency_key = f"api:{harness.scenario_id}:tasks.claim:replay"
    first = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )
    second = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.payload["idempotent_replay"] is False
    assert second.payload["idempotent_replay"] is True
    assert first.payload["receipt"] == second.payload["receipt"]
    assert (
        first.payload["result"]["human_task"]["human_task_id"]
        == second.payload["result"]["human_task"]["human_task_id"]
    )

    claimed_events = [
        event
        for event in harness.list_events()
        if event["event_type"] == "task.claimed"
        and event["payload"]["human_task_id"] == human_task_id
    ]
    assert len(claimed_events) == 1


def test_same_scoped_key_with_different_payload_returns_receipt_mismatch(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(CLAIM_SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])
    client = _dispatch_supervisor_client(harness)

    idempotency_key = f"api:{harness.scenario_id}:tasks.claim:mismatch"
    first = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": idempotency_key},
    )
    mismatch = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={"lease_seconds": 600, "idempotency_key": idempotency_key},
    )

    assert first.status_code == 200
    assert mismatch.status_code == 409
    assert mismatch.payload["error"]["code"] == "command_receipt_mismatch"
    assert mismatch.payload["error"]["details"]["command_name"] == "tasks.claim"

    claimed_events = [
        event
        for event in harness.list_events()
        if event["event_type"] == "task.claimed"
        and event["payload"]["human_task_id"] == human_task_id
    ]
    assert len(claimed_events) == 1


def test_same_client_key_can_be_reused_across_distinct_claim_scopes(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(CLAIM_SCENARIO_PATH, tmp_path).prepare()
    first_created = harness.run_named_step("create_stage06_review")
    second_created = harness.run_action(
        action="tasks.create",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "stage_id": "Stage06",
            "task_kind": "final_review",
            "activation_key": f"scenario:{harness.scenario_id}:tasks.create:extra",
            "candidate_roles": ["dispatch_supervisor"],
            "owner_role": "dispatch_supervisor",
            "create_human_task": True,
            "idempotency_key": f"scenario:{harness.scenario_id}:tasks.create:extra",
        },
    )
    first_human_task_id = str(first_created["result"]["human_task"]["human_task_id"])
    second_human_task_id = str(second_created["result"]["human_task"]["human_task_id"])
    client = _dispatch_supervisor_client(harness)

    shared_idempotency_key = f"api:{harness.scenario_id}:tasks.claim:shared-key"
    first_claim = client.post(
        f"/api/v1/human-tasks/{first_human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": shared_idempotency_key},
    )
    second_claim = client.post(
        f"/api/v1/human-tasks/{second_human_task_id}/claim",
        payload={"lease_seconds": 300, "idempotency_key": shared_idempotency_key},
    )

    assert first_claim.status_code == 200
    assert second_claim.status_code == 200
    assert first_claim.payload["idempotent_replay"] is False
    assert second_claim.payload["idempotent_replay"] is False
    assert first_claim.payload["receipt"]["scope_key"] != second_claim.payload["receipt"]["scope_key"]

    claimed_events = [
        event for event in harness.list_events() if event["event_type"] == "task.claimed"
    ]
    assert len(claimed_events) == 2


def test_flag_transition_retry_replays_success_and_reason_mismatch_conflicts(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(FLAG_SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_flag")
    flag_id = str(created["flag"]["flag_id"])
    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager"],
    )

    idempotency_key = f"api:{harness.scenario_id}:flags.transition:replay"
    first = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "investigating issue",
            "idempotency_key": idempotency_key,
        },
    )
    replay = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "investigating issue",
            "idempotency_key": idempotency_key,
        },
    )
    mismatch = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "different fingerprint",
            "idempotency_key": idempotency_key,
        },
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.payload["idempotent_replay"] is True
    assert mismatch.status_code == 409
    assert mismatch.payload["error"]["code"] == "command_receipt_mismatch"

    transition_events = [
        event
        for event in harness.list_events()
        if event["event_type"] == "flag.state_changed"
        and event["payload"]["flag_id"] == flag_id
        and event["payload"]["to_state"] == "triage"
    ]
    assert len(transition_events) == 1
