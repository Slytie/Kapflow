from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)


def test_flag_transition_via_api_updates_canonical_rows_and_events(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_flag")
    flag_id = created["flag"]["flag_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-2",
        actor_type="human",
        actor_roles=["operations_manager"],
    )

    idempotency_key = f"api:{harness.scenario_id}:flags.transition:triage"
    transitioned = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "investigating issue",
            "idempotency_key": idempotency_key,
        },
    )
    assert transitioned.status_code == 200
    assert transitioned.payload["status"] == "ok"
    assert transitioned.payload["command"] == "api.flags.transition"
    assert transitioned.payload["flag"]["state"] == "triage"
    assert transitioned.payload["idempotent_replay"] is False
    assert transitioned.payload["receipt"]["command_name"] == "flags.transition"

    persisted = harness.list_flags()["flags"]
    assert len(persisted) == 1
    assert persisted[0]["flag_id"] == flag_id
    assert persisted[0]["state"] == "triage"

    events = harness.list_events()
    transition_events = [
        event
        for event in events
        if event["event_type"] == "flag.state_changed"
        and event["payload"]["flag_id"] == flag_id
        and event["payload"]["to_state"] == "triage"
    ]
    assert len(transition_events) == 1

    retry = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "investigating issue",
            "idempotency_key": idempotency_key,
        },
    )
    assert retry.status_code == 200
    assert retry.payload["status"] == "ok"
    assert retry.payload["idempotent_replay"] is True
    assert retry.payload["receipt"] == transitioned.payload["receipt"]

    events_after_retry = harness.list_events()
    transition_events_after_retry = [
        event
        for event in events_after_retry
        if event["event_type"] == "flag.state_changed"
        and event["payload"]["flag_id"] == flag_id
        and event["payload"]["to_state"] == "triage"
    ]
    assert len(transition_events_after_retry) == 1


def test_flag_transition_via_api_rejects_wrong_role_without_side_effects(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_flag")
    flag_id = created["flag"]["flag_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:auditor-1",
        actor_type="human",
        actor_roles=["auditor"],
    )

    denied = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "should be denied",
            "idempotency_key": f"api:{harness.scenario_id}:flags.transition:forbidden",
        },
    )
    assert denied.status_code == 403
    error = denied.payload["error"]
    assert error["code"] == "flag_transition_forbidden"
    assert error["details"]["capability_id"] == "flag.transition"
    assert "flag_transition_role_mismatch" in error["details"]["reason_codes"]

    persisted = harness.list_flags()["flags"]
    assert len(persisted) == 1
    assert persisted[0]["flag_id"] == flag_id
    assert persisted[0]["state"] == "open"
    events = harness.list_events()
    assert not any(
        event["event_type"] == "flag.state_changed"
        and event["payload"]["flag_id"] == flag_id
        for event in events
    )
