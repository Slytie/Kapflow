from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/logistics/three_workflow_demo_story_seed.yaml"


def _client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        actor_id="human:ops-manager-1",
        actor_type="human",
        actor_roles=["operations_manager", "dispatch_supervisor", "schedule_planner"],
    )


def test_logistics_three_workflow_story_endpoint_returns_authoritative_story_payload(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    notify_result = harness.output("notify_result")["result"]
    live_activation = harness.output("live_activation")["result"]

    reporting_run_id = harness.workflow_run_id
    weekly_run_id = str(notify_result["target_workflow_runs"][0]["workflow_run_id"])
    live_run_id = str(live_activation["target_workflow_run"]["workflow_run_id"])

    client = _client(harness)
    response = client.get(
        "/api/v1/stories/logistics-three-workflow",
        query={
            "planning_week_id": "PW-2026-W10",
            "service_date_id": "SD-2026-03-06",
        },
    )
    assert response.status_code == 200

    payload = response.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.stories.logistics_three_workflow"
    assert set(payload["story"].keys()) >= {
        "story_id",
        "family",
        "partitions",
        "family_graph",
        "linked_workflow_runs",
        "handoff_activity",
        "board",
        "official_outputs",
        "freshness",
        "coherence",
    }

    family_graph = payload["story"]["family_graph"]
    module_ids = {module["module_id"] for module in family_graph["modules"]}
    edge_ids = {edge["edge_id"] for edge in family_graph["edges"]}
    assert module_ids == {"weekly_schedule_planning", "live_dispatch", "dispatch_reporting"}
    assert edge_ids == {"weekly_seed_to_live_dispatch", "reporting_actuals_to_future_planning"}

    linked_runs = payload["story"]["linked_workflow_runs"]
    assert [run["workflow_run_id"] for run in linked_runs["weekly_schedule_planning"]] == [weekly_run_id]
    assert [run["workflow_run_id"] for run in linked_runs["live_dispatch"]] == [live_run_id]
    assert [run["workflow_run_id"] for run in linked_runs["dispatch_reporting"]] == [reporting_run_id]

    edge_summaries = {
        item["edge_id"]: item for item in payload["story"]["handoff_activity"]["edges"]
    }
    assert edge_summaries["weekly_seed_to_live_dispatch"]["status_counts"]["activated"] == 1
    assert edge_summaries["reporting_actuals_to_future_planning"]["status_counts"]["prepared"] == 1

    work_items = payload["story"]["board"]["work_items"]
    assert work_items
    assert {item["workflow_id"] for item in work_items} == {
        "weekly_schedule_planning.v1",
        "live_dispatch.v1",
        "dispatch_reporting.v1",
    }
    assert all(isinstance(item["available_actions"], list) for item in work_items)

    artifact_kind_counts = payload["story"]["official_outputs"]["summary"]["artifact_kind_counts"]
    assert artifact_kind_counts["planning.published_weekly_schedule.workbook"] == 1
    assert artifact_kind_counts["reporting.final_packet.workbook"] == 1

    freshness = payload["story"]["freshness"]
    assert isinstance(freshness["latest_event_sequence"], int)
    assert freshness["latest_event_recorded_at"]
    assert freshness["generated_at"]


def test_logistics_three_workflow_story_endpoint_requires_valid_planning_week_partition(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()
    client = _client(harness)

    missing_partition = client.get("/api/v1/stories/logistics-three-workflow")
    assert missing_partition.status_code == 400
    assert missing_partition.payload["error"]["code"] == "invalid_query_parameter"

    invalid_partition = client.get(
        "/api/v1/stories/logistics-three-workflow",
        query={"planning_week_id": "NOT-A-PLANNING-WEEK"},
    )
    assert invalid_partition.status_code == 400
    assert invalid_partition.payload["error"]["code"] == "invalid_query_parameter"
