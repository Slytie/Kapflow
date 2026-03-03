from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_workflow_run_detail_contract_is_coherent(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(harness)
    result = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}")
    assert result.status_code == 200

    payload = result.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workflow_runs.detail"

    workflow_run = payload["workflow_run"]
    human_tasks = payload["human_tasks"]
    approvals = payload["approvals"]
    artifact_versions = payload["artifact_versions"]
    pointers = payload["pointers"]
    flags = payload["flags"]
    summary = payload["summary"]

    assert workflow_run["workflow_run_id"] == harness.workflow_run_id
    assert workflow_run["workflow_id"] == "schedule_planning.v1"

    assert summary["human_task_count"] == len(human_tasks)
    assert summary["approval_count"] == len(approvals)
    assert summary["artifact_version_count"] == len(artifact_versions)
    assert summary["pointer_count"] == len(pointers)
    assert summary["flag_count"] == len(flags)
    assert summary["active_issue_count"] == workflow_run["active_issue_count"]

    assert len(human_tasks) == 2
    assert {row["task_kind"] for row in human_tasks} == {"review_packet", "final_review"}
    assert all(row["workflow_run_id"] == harness.workflow_run_id for row in human_tasks)

    assert len(approvals) == 1
    assert approvals[0]["workflow_run_id"] == harness.workflow_run_id
    assert approvals[0]["state"] == "RESPONDED"

    assert any(
        row["artifact_kind"] == "schedule.published_schedule.workbook"
        for row in artifact_versions
    )
    assert len(pointers) == 1
    assert pointers[0]["pointer_key"] == "official:schedule.published_schedule.workbook"
    assert flags == []
