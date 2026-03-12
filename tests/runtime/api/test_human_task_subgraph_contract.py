from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


LOGISTICS_SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/three_workflow_demo_story_seed.yaml"
)
SCHEDULE_SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
)


def _logistics_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        actor_id="human:ops-manager-1",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def _schedule_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_human_task_subgraph_contract_for_composite_logistics_task(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(LOGISTICS_SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    notify_result = harness.output("notify_result")["result"]
    weekly_run_id = str(notify_result["target_workflow_runs"][0]["workflow_run_id"])

    client = _logistics_client(harness)
    listed = client.get("/api/v1/human-tasks", query={"workflow_run_id": weekly_run_id})
    assert listed.status_code == 200
    weekly_review = next(
        row
        for row in listed.payload["human_tasks"]
        if row["task_kind"] in {"actual_hours_review", "planning_feedback_review"}
    )
    human_task_id = str(weekly_review["human_task_id"])

    detail = client.get(f"/api/v1/human-tasks/{human_task_id}")
    assert detail.status_code == 200
    assert detail.payload["human_task"]["is_composite"] is True
    assert detail.payload["human_task"]["expansion_kind"] == "task_subgraph"
    assert detail.payload["human_task"]["subgraph_ref"] == {
        "human_task_id": human_task_id,
        "endpoint": f"/api/v1/human-tasks/{human_task_id}/subgraph",
    }

    subgraph = client.get(f"/api/v1/human-tasks/{human_task_id}/subgraph")
    assert subgraph.status_code == 200
    assert subgraph.payload["command"] == "api.human_tasks.subgraph"
    assert subgraph.payload["human_task_id"] == human_task_id
    assert subgraph.payload["is_composite"] is True
    assert subgraph.payload["expansion_kind"] == "task_subgraph"
    graph_payload = subgraph.payload["subgraph"]
    assert graph_payload["nodes"]
    assert graph_payload["edges"]
    assert {"status", "as_of", "note"} <= set(graph_payload["freshness"].keys())
    assert all(
        {"artifact_version_id", "label", "source_label"} <= set(ref.keys())
        for ref in graph_payload["artifact_refs"]
    )
    assert all("content_base64" not in ref for ref in graph_payload["artifact_refs"])


def test_human_task_subgraph_contract_rejects_non_composite_tasks(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCHEDULE_SCENARIO_PATH, tmp_path).prepare()
    harness.run_named_step("create_stage06_review")

    client = _schedule_client(harness)
    listed = client.get(
        "/api/v1/human-tasks",
        query={"workflow_run_id": harness.workflow_run_id},
    )
    assert listed.status_code == 200
    review_task = next(
        row for row in listed.payload["human_tasks"] if row["task_kind"] == "review_packet"
    )
    human_task_id = str(review_task["human_task_id"])

    detail = client.get(f"/api/v1/human-tasks/{human_task_id}")
    assert detail.status_code == 200
    assert detail.payload["human_task"]["is_composite"] is False
    assert detail.payload["human_task"]["expansion_kind"] == "none"
    assert detail.payload["human_task"]["subgraph_ref"] is None

    subgraph = client.get(f"/api/v1/human-tasks/{human_task_id}/subgraph")
    assert subgraph.status_code == 409
    assert subgraph.payload["error"]["code"] == "task_subgraph_not_available"
