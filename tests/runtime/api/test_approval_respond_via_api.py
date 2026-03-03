from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"


def test_approval_respond_via_api_updates_canonical_rows_and_events(tmp_path: Path) -> None:
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

    approval_id = harness.output("request_publish_approval")["approval"]["approval_id"]

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )

    responded = client.post(
        f"/api/v1/approvals/{approval_id}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "approved through API",
            "idempotency_key": f"api:{harness.scenario_id}:approvals.respond",
        },
    )
    assert responded.status_code == 200
    assert responded.payload["approval"]["state"] == "RESPONDED"
    assert responded.payload["approval"]["response_kind"] == "approve"

    approvals_rows = harness.list_approvals()["approvals"]
    assert approvals_rows[0]["state"] == "RESPONDED"
    assert approvals_rows[0]["response_kind"] == "approve"

    events = harness.list_events()
    responded_events = [
        event
        for event in events
        if event["event_type"] == "approval.responded"
        and event["payload"]["approval_id"] == approval_id
    ]
    assert len(responded_events) == 1
