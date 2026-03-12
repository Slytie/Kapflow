from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"

EXPECTED_BASE_KEYS = {
    "human_task_id",
    "workflow_run_id",
    "task_run_id",
    "task_kind",
    "state",
    "candidate_roles",
    "owner_role",
    "assignee_actor_id",
    "assignee_actor_type",
    "due_at",
    "escalation_at",
    "lease_version",
    "claimed_at",
    "claimed_until",
    "linked_approval_id",
    "reopen_count",
    "generation",
    "created_at",
    "updated_at",
    "task_run_state",
    "stage_id",
    "blocked_on_kind",
    "blocked_on_ref",
    "spawned_from_flag_id",
}

EXPECTED_ACTIONABILITY_KEYS = {
    "available_actions",
    "blocking_requirements",
    "required_uploads",
    "required_reviews",
    "blocking_reason_codes",
    "linked_artifact_count",
    "missing_required_inputs",
    "can_complete",
    "can_confirm_review",
    "can_upload_attachment",
    "can_run_stage06_agent_review",
    "can_run_weekly_stage04_openai_agent",
}

EXPECTED_EXPANSION_KEYS = {
    "is_composite",
    "expansion_kind",
    "subgraph_ref",
}


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_human_task_list_contract_and_filters(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_named_step("create_stage06_review")
    harness.run_named_step("claim_stage06_review")

    client = _api_client(harness)

    listed = client.get(
        "/api/v1/human-tasks",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert listed.status_code == 200
    assert listed.payload["status"] == "ok"
    rows = listed.payload["human_tasks"]
    assert len(rows) == 1
    assert EXPECTED_BASE_KEYS.issubset(set(rows[0].keys()))
    assert EXPECTED_ACTIONABILITY_KEYS.issubset(set(rows[0].keys()))
    assert EXPECTED_EXPANSION_KEYS.issubset(set(rows[0].keys()))
    assert rows[0]["state"] == "CLAIMED"
    assert rows[0]["assignee_actor_id"] == "human:dispatch-supervisor-1"

    detail = client.get(f"/api/v1/human-tasks/{rows[0]['human_task_id']}")
    assert detail.status_code == 200
    assert detail.payload["status"] == "ok"
    assert detail.payload["command"] == "api.human_tasks.detail"
    assert EXPECTED_BASE_KEYS.issubset(set(detail.payload["human_task"].keys()))
    assert EXPECTED_ACTIONABILITY_KEYS.issubset(set(detail.payload["human_task"].keys()))
    assert EXPECTED_EXPANSION_KEYS.issubset(set(detail.payload["human_task"].keys()))

    filtered_claimed = client.get(
        "/api/v1/human-tasks",
        query={
            "workflow_run_id": harness.workflow_run_id,
            "state": "CLAIMED",
            "stage_id": "Stage06",
            "task_kind": "review_packet",
            "assignee_actor_id": "human:dispatch-supervisor-1",
            "owner_role": "dispatch_supervisor",
        },
    )
    assert filtered_claimed.status_code == 200
    assert len(filtered_claimed.payload["human_tasks"]) == 1

    filtered_open = client.get(
        "/api/v1/human-tasks",
        query={"workflow_run_id": harness.workflow_run_id, "state": "OPEN"},
    )
    assert filtered_open.status_code == 200
    assert filtered_open.payload["human_tasks"] == []
