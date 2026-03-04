from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"

EXPECTED_KEYS = {
    "approval_id",
    "workflow_run_id",
    "task_run_id",
    "approval_kind",
    "scope_kind",
    "scope_ref",
    "state",
    "requested_by_task_run_id",
    "candidate_roles",
    "required_role",
    "requested_at",
    "responded_at",
    "response_kind",
    "response_reason",
    "decided_by_actor_id",
    "decided_by_actor_type",
    "generation",
    "created_at",
    "updated_at",
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


def test_approval_list_contract_filters_and_state(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    for step_id in [
        "create_stage06_review",
        "claim_stage06_review",
        "complete_stage06_review",
        "claim_final_review",
        "complete_final_review",
        "request_publish_approval",
    ]:
        harness.run_named_step(step_id)

    client = _api_client(harness)
    pending = client.get(
        "/api/v1/approvals",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert pending.status_code == 200
    rows = pending.payload["approvals"]
    assert len(rows) == 1
    assert set(rows[0].keys()) == EXPECTED_KEYS
    assert rows[0]["state"] == "PENDING"

    detail = client.get(f"/api/v1/approvals/{rows[0]['approval_id']}")
    assert detail.status_code == 200
    assert detail.payload["status"] == "ok"
    assert detail.payload["command"] == "api.approvals.detail"
    assert set(detail.payload["approval"].keys()) == EXPECTED_KEYS

    filtered = client.get(
        "/api/v1/approvals",
        query={
            "workflow_run_id": harness.workflow_run_id,
            "state": "PENDING",
            "approval_kind": "business_decision",
            "required_role": "dispatch_supervisor",
        },
    )
    assert filtered.status_code == 200
    assert len(filtered.payload["approvals"]) == 1

    harness.run_named_step("respond_publish_approval")
    responded = client.get(
        "/api/v1/approvals",
        query={"workflow_run_id": harness.workflow_run_id, "state": "RESPONDED"},
    )
    assert responded.status_code == 200
    assert len(responded.payload["approvals"]) == 1
    assert responded.payload["approvals"][0]["response_kind"] == "approve"
