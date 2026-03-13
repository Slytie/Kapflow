from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_child_issue_branch.yaml"
)


def test_api_reads_are_stable_and_flag_transition_retry_replays_successfully(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created_flag = harness.run_named_step("create_flag")
    flag_id = created_flag["flag"]["flag_id"]
    harness.run_named_step("activate_issue")

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-3",
        actor_type="human",
        actor_roles=["operations_manager"],
    )

    first_flags = client.get(
        "/api/v1/flags",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    second_flags = client.get(
        "/api/v1/flags",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert first_flags.status_code == 200
    assert second_flags.status_code == 200
    assert first_flags.payload == second_flags.payload

    first_board = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    second_board = client.get(
        "/api/v1/board/schedule-planning",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert first_board.status_code == 200
    assert second_board.status_code == 200
    assert first_board.payload == second_board.payload

    first_timeline = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/timeline")
    second_timeline = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/timeline")
    assert first_timeline.status_code == 200
    assert second_timeline.status_code == 200
    assert first_timeline.payload == second_timeline.payload

    idempotency_key = f"api:{harness.scenario_id}:flags.transition:triage-retry"
    first_transition = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "retry-stability check",
            "idempotency_key": idempotency_key,
        },
    )
    second_transition = client.post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "retry-stability check",
            "idempotency_key": idempotency_key,
        },
    )
    assert first_transition.status_code == 200
    assert second_transition.status_code == 200
    assert first_transition.payload["idempotent_replay"] is False
    assert second_transition.payload["idempotent_replay"] is True
    assert first_transition.payload["receipt"] == second_transition.payload["receipt"]

    events = harness.list_events()
    changed_events = [
        event
        for event in events
        if event["event_type"] == "flag.state_changed"
        and event["payload"]["flag_id"] == flag_id
        and event["payload"]["to_state"] == "triage"
    ]
    assert len(changed_events) == 1
