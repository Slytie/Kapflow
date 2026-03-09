from __future__ import annotations

import json
from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT, run_cli, stdout_json
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
    modules_by_id = {module["module_id"]: module for module in family_graph["modules"]}
    assert modules_by_id["weekly_schedule_planning"]["node_kind"] == "module"
    assert modules_by_id["weekly_schedule_planning"]["drilldown_kind"] == "workflow_run"
    assert modules_by_id["weekly_schedule_planning"]["drilldown_refs"] == [
        {
            "workflow_run_id": weekly_run_id,
            "workflow_id": "weekly_schedule_planning.v1",
            "partition_key": "PW-2026-W10",
        }
    ]
    assert modules_by_id["weekly_schedule_planning"]["artifact_refs"]
    assert {
        "artifact_version_id",
        "label",
        "source_label",
    } == set(modules_by_id["weekly_schedule_planning"]["artifact_refs"][0].keys())
    assert "linked run" in modules_by_id["weekly_schedule_planning"]["selection_summary"]
    assert "downloadable artifact" in modules_by_id["weekly_schedule_planning"]["selection_summary"]
    for module in family_graph["modules"]:
        for artifact_ref in module["artifact_refs"]:
            assert "storage_uri" not in artifact_ref
            assert "byte_size" not in artifact_ref
            assert "content_base64" not in artifact_ref

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


def test_logistics_three_workflow_story_endpoint_marks_multi_run_module_as_run_group(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    live_activation = harness.output("live_activation")["result"]
    base_live_run_id = str(live_activation["target_workflow_run"]["workflow_run_id"])

    extra_live_payload = {
        "workflow_id": "live_dispatch.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-logistics",
        "domain_id": "domain-hub",
        "partition_key": "SD-2026-03-06",
        "logical_date": "2026-03-06",
        "activation_key": "scenario:logistics_three_workflow_demo_story_seed:extra-live-run",
        "idempotency_key": "scenario:logistics_three_workflow_demo_story_seed:runs.create:extra-live-run",
    }
    create_result = run_cli(
        "--db-url",
        harness.db_url,
        "runs",
        "create",
        "--json",
        json.dumps(extra_live_payload, separators=(",", ":")),
    )
    extra_live_run_id = str(stdout_json(create_result)["workflow_run"]["workflow_run_id"])

    client = _client(harness)
    response = client.get(
        "/api/v1/stories/logistics-three-workflow",
        query={
            "planning_week_id": "PW-2026-W10",
            "service_date_id": "SD-2026-03-06",
        },
    )
    assert response.status_code == 200

    family_graph = response.payload["story"]["family_graph"]
    modules_by_id = {module["module_id"]: module for module in family_graph["modules"]}
    live_module = modules_by_id["live_dispatch"]
    assert live_module["drilldown_kind"] == "run_group"
    assert sorted(ref["workflow_run_id"] for ref in live_module["drilldown_refs"]) == sorted(
        [base_live_run_id, extra_live_run_id]
    )
    assert live_module["selection_summary"].startswith("2 linked runs")


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
