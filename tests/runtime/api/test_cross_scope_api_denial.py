from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"


def test_cross_scope_requests_are_denied_and_do_not_leak_rows(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    wrong_scope_client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-b",
        domain_id="domain-y",
        actor_id="human:other-actor",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )

    detail_denied = wrong_scope_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}")
    assert detail_denied.status_code == 404
    assert detail_denied.payload["error"]["code"] == "workflow_run_not_found"

    scoped_list_denied = wrong_scope_client.get(
        "/api/v1/human-tasks",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert scoped_list_denied.status_code == 404
    assert scoped_list_denied.payload["error"]["code"] == "workflow_run_not_found"

    mutation_denied = wrong_scope_client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:cross-scope-claim",
        },
    )
    assert mutation_denied.status_code == 404
    assert mutation_denied.payload["error"]["code"] == "workflow_run_not_found"

    list_no_leak = wrong_scope_client.get("/api/v1/workflow-runs")
    assert list_no_leak.status_code == 200
    assert list_no_leak.payload["workflow_runs"] == []
