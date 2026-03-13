from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT
    / "fixtures/scenarios/schedule_planning/stage06_publish_ready_confirm_review.yaml"
)


def _client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-6",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_confirm_review_endpoint_is_idempotent_and_unblocks_completion(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_named_step("create_stage06_final_review")
    harness.run_named_step("claim_stage06_final_review")
    packet = harness.run_named_step("create_draft_publish_packet")
    workbook = harness.run_named_step("create_draft_published_schedule")

    human_task_id = str(
        harness.output("create_stage06_final_review")["result"]["human_task"]["human_task_id"]
    )
    reviewed_ids = [
        str(packet["artifact_version"]["artifact_version_id"]),
        str(workbook["artifact_version"]["artifact_version_id"]),
    ]
    client = _client(harness)

    first = client.post(
        f"/api/v1/human-tasks/{human_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": reviewed_ids,
            "idempotency_key": f"api:{harness.scenario_id}:confirm-review",
        },
    )
    assert first.status_code == 200
    first_result = first.payload["result"]
    assert first_result["artifact_version"]["artifact_kind"] == "human_task.review_confirmation.json"
    assert first.payload["idempotent_replay"] is False
    assert first.payload["receipt"]["command_name"] == "tasks.confirm-review"

    second = client.post(
        f"/api/v1/human-tasks/{human_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": reviewed_ids,
            "idempotency_key": f"api:{harness.scenario_id}:confirm-review",
        },
    )
    assert second.status_code == 200
    second_result = second.payload["result"]
    assert second.payload["idempotent_replay"] is True
    assert second.payload["receipt"] == first.payload["receipt"]
    assert (
        second_result["artifact_version"]["artifact_version_id"]
        == first_result["artifact_version"]["artifact_version_id"]
    )

    completed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/complete",
        payload={
            "outcome": "review_complete",
            "idempotency_key": f"api:{harness.scenario_id}:complete-after-confirm",
        },
    )
    assert completed.status_code == 200


def test_confirm_review_endpoint_rejects_non_assignee_without_side_effects(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_named_step("create_stage06_final_review")
    harness.run_named_step("claim_stage06_final_review")
    packet = harness.run_named_step("create_draft_publish_packet")
    workbook = harness.run_named_step("create_draft_published_schedule")

    human_task_id = str(
        harness.output("create_stage06_final_review")["result"]["human_task"]["human_task_id"]
    )
    reviewed_ids = [
        str(packet["artifact_version"]["artifact_version_id"]),
        str(workbook["artifact_version"]["artifact_version_id"]),
    ]
    before_artifact_ids = {
        str(row["artifact_version_id"]) for row in harness.list_artifacts()["artifact_versions"]
    }
    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-7",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )

    denied = client.post(
        f"/api/v1/human-tasks/{human_task_id}/confirm-review",
        payload={
            "reviewed_artifact_version_ids": reviewed_ids,
            "idempotency_key": f"api:{harness.scenario_id}:confirm-review:forbidden",
        },
    )
    assert denied.status_code == 403
    error = denied.payload["error"]
    assert error["code"] == "task_confirm_review_forbidden"
    assert error["details"]["capability_id"] == "task.confirm_review"
    assert "claimed_by_other_actor" in error["details"]["reason_codes"]

    after_artifact_ids = {
        str(row["artifact_version_id"]) for row in harness.list_artifacts()["artifact_versions"]
    }
    assert after_artifact_ids == before_artifact_ids
    assert not any(
        row["artifact_kind"] == "human_task.review_confirmation.json"
        and row["task_run_id"] == harness.output("create_stage06_final_review")["result"]["task_run"]["task_run_id"]
        for row in harness.list_artifacts()["artifact_versions"]
    )
