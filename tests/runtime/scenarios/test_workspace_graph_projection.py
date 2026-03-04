from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_STAGE06_PUBLISH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)
SCENARIO_STAGE06_INFO = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_review_requires_more_information.yaml"
)
SCENARIO_STAGE07_MAJOR = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage07_major_replan_happy.yaml"
)


def _api_client(harness: RuntimeScenarioHarness, *, actor_id: str, actor_roles: list[str]) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def _graph_status_map(graph: dict[str, object]) -> dict[str, str]:
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    return {
        str(node["node_id"]): str(node["status"])
        for node in nodes
        if isinstance(node, dict)
    }


def test_workspace_graph_stage06_publish_ready_statuses(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_PUBLISH, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(
        harness,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    )
    result = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert result.status_code == 200

    graph = result.payload["graph"]
    statuses = _graph_status_map(graph)
    assert statuses["stage06_review"] == "completed"
    assert statuses["stage06_publish_approval"] == "completed"
    assert statuses["stage06_base_published"] == "completed"
    assert statuses["stage07_exception_control"] == "ready"
    assert statuses["stage07_delta_published"] == "not_started"


def test_workspace_graph_stage06_needs_information_shows_blocked_review(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE06_INFO, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(
        harness,
        actor_id="human:dispatch-supervisor-2",
        actor_roles=["dispatch_supervisor"],
    )
    result = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert result.status_code == 200

    graph = result.payload["graph"]
    statuses = _graph_status_map(graph)
    assert statuses["stage06_review"] == "blocked"
    assert statuses["stage06_publish_approval"] == "not_started"
    assert statuses["stage06_base_published"] == "not_started"


def test_workspace_graph_stage07_major_replan_shows_exception_approval_publish(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_STAGE07_MAJOR, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(
        harness,
        actor_id="human:ops-manager-1",
        actor_roles=["operations_manager"],
    )
    result = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/workspace")
    assert result.status_code == 200

    graph = result.payload["graph"]
    statuses = _graph_status_map(graph)
    assert statuses["stage07_exception_control"] == "completed"
    assert statuses["stage07_replan_approval"] == "completed"
    assert statuses["stage07_delta_published"] == "completed"

