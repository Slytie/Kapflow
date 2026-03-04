from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_STAGE06_PUBLISH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
SCENARIO_STAGE07_MAJOR = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_major_replan_happy.yaml"
)


def _client(
    harness: RuntimeScenarioHarness,
    *,
    tenant_id: str,
    domain_id: str,
    actor_id: str,
    actor_roles: list[str],
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id=tenant_id,
        domain_id=domain_id,
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def test_workspace_endpoint_returns_expected_envelope(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    stage06_human_task_id = str(created["result"]["human_task"]["human_task_id"])
    harness.run_named_step("claim_stage06_review")

    client = _client(
        harness,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )
    result = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert result.status_code == 200

    payload = result.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.workflow_runs.workspace"
    assert set(payload.keys()) >= {
        "status",
        "command",
        "workflow_run",
        "graph",
        "user_work",
        "blocking_work",
        "official_outputs",
        "timeline_excerpt",
        "freshness",
    }
    assert set(payload["graph"].keys()) >= {
        "nodes",
        "edges",
        "summary",
        "latest_event_sequence",
        "warnings",
    }
    assert isinstance(payload["user_work"], list)
    assert isinstance(payload["blocking_work"], list)
    assert isinstance(payload["timeline_excerpt"]["events"], list)
    assert isinstance(payload["official_outputs"]["pointers"], list)

    matching_items = [
        item
        for item in payload["user_work"]
        if item["subject_kind"] == "human_task"
        and item["subject_id"] == stage06_human_task_id
    ]
    assert len(matching_items) == 1
    item = matching_items[0]
    assert set(item.keys()) >= {
        "id",
        "subject_kind",
        "subject_id",
        "canonical_state",
        "available_actions",
        "linked_artifact_count",
        "missing_required_inputs",
        "metadata",
    }


def test_workspace_endpoint_cross_scope_access_fails_closed(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    harness.run_steps()

    wrong_scope_client = _client(
        harness,
        tenant_id="tenant-b",
        domain_id="domain-y",
        actor_id="human:other-user",
        actor_roles=["dispatch_supervisor"],
    )
    denied = wrong_scope_client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert denied.status_code == 404
    assert denied.payload["status"] == "error"
    assert denied.payload["error"]["code"] == "workflow_run_not_found"


def test_workspace_endpoint_exposes_latest_event_sequence_and_freshness(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE07_MAJOR, tmp_path).prepare()
    harness.run_steps()

    client = _client(
        harness,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:ops-manager-1",
        actor_roles=["operations_manager"],
    )
    response = client.get(
        f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace",
        query={"timeline_limit": 30},
    )
    assert response.status_code == 200
    graph = response.payload["graph"]
    freshness = response.payload["freshness"]

    assert isinstance(graph["latest_event_sequence"], int)
    assert int(graph["latest_event_sequence"]) > 0
    assert freshness["latest_event_sequence"] == graph["latest_event_sequence"]
    assert freshness["latest_event_recorded_at"]
    assert freshness["generated_at"]
    assert response.payload["timeline_excerpt"]["events"]

