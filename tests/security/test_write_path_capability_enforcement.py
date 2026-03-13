from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

STAGE06_PUBLISH_SCENARIO = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
STAGE06_CONFIRM_REVIEW_SCENARIO = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_publish_ready_confirm_review.yaml"
)
STAGE07_INFO_SCENARIO = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_missing_information_branch.yaml"
)


def _client(
    harness: RuntimeScenarioHarness,
    *,
    actor_id: str,
    actor_roles: list[str],
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def test_denied_claim_leaves_task_and_events_unchanged(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(STAGE06_PUBLISH_SCENARIO, tmp_path / "claim").prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = str(created["result"]["human_task"]["human_task_id"])

    denied = _client(
        harness,
        actor_id="human:schedule-planner-99",
        actor_roles=["schedule_planner"],
    ).post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:security:claim-forbidden",
        },
    )

    assert denied.status_code == 403
    assert denied.payload["error"]["code"] == "task_claim_forbidden"
    persisted = harness.show_task(human_task_id)["human_task"]
    assert persisted["state"] == "OPEN"
    assert persisted["assignee_actor_id"] is None
    assert not any(event["event_type"] == "task.claimed" for event in harness.list_events())


def test_denied_confirm_review_does_not_create_confirmation_artifact(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(
        STAGE06_CONFIRM_REVIEW_SCENARIO,
        tmp_path / "confirm-review",
    ).prepare()
    harness.run_named_step("create_stage06_final_review")
    harness.run_named_step("claim_stage06_final_review")
    packet = harness.run_named_step("create_draft_publish_packet")
    workbook = harness.run_named_step("create_draft_published_schedule")
    human_task_id = str(
        harness.output("create_stage06_final_review")["result"]["human_task"]["human_task_id"]
    )
    before_ids = {
        str(row["artifact_version_id"]) for row in harness.list_artifacts()["artifact_versions"]
    }

    denied = _client(
        harness,
        actor_id="human:dispatch-supervisor-77",
        actor_roles=["dispatch_supervisor"],
    ).post(
        f"/api/v1/human-tasks/{human_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": [
                str(packet["artifact_version"]["artifact_version_id"]),
                str(workbook["artifact_version"]["artifact_version_id"]),
            ],
            "idempotency_key": f"api:{harness.scenario_id}:security:confirm-review-forbidden",
        },
    )

    assert denied.status_code == 403
    assert denied.payload["error"]["code"] == "task_confirm_review_forbidden"
    after_ids = {
        str(row["artifact_version_id"]) for row in harness.list_artifacts()["artifact_versions"]
    }
    assert after_ids == before_ids


def test_denied_approval_response_leaves_pending_row_and_no_event(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(STAGE06_PUBLISH_SCENARIO, tmp_path / "approval").prepare()
    for step_id in [
        "create_stage06_review",
        "claim_stage06_review",
        "complete_stage06_review",
        "claim_final_review",
        "complete_final_review",
        "request_publish_approval",
    ]:
        harness.run_named_step(step_id)
    approval_id = str(harness.output("request_publish_approval")["approval"]["approval_id"])

    denied = _client(
        harness,
        actor_id="human:schedule-planner-55",
        actor_roles=["schedule_planner"],
    ).post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "idempotency_key": f"api:{harness.scenario_id}:security:approval-forbidden",
        },
    )

    assert denied.status_code == 403
    assert denied.payload["error"]["code"] == "approval_respond_forbidden"
    approval = harness.list_approvals()["approvals"][0]
    assert approval["state"] == "PENDING"
    assert not any(
        event["event_type"] == "approval.responded"
        and event["payload"]["approval_id"] == approval_id
        for event in harness.list_events()
    )


def test_denied_flag_transition_leaves_state_unchanged(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(STAGE07_INFO_SCENARIO, tmp_path / "flag").prepare()
    created = harness.run_named_step("create_flag")
    flag_id = str(created["flag"]["flag_id"])

    denied = _client(
        harness,
        actor_id="human:auditor-44",
        actor_roles=["auditor"],
    ).post(
        f"/api/v1/flags/{flag_id}/transition",
        payload={
            "to_state": "triage",
            "reason": "security denial check",
            "idempotency_key": f"api:{harness.scenario_id}:security:flag-forbidden",
        },
    )

    assert denied.status_code == 403
    assert denied.payload["error"]["code"] == "flag_transition_forbidden"
    flag = harness.list_flags()["flags"][0]
    assert flag["state"] == "open"
    assert not any(
        event["event_type"] == "flag.state_changed"
        and event["payload"]["flag_id"] == flag_id
        for event in harness.list_events()
    )
