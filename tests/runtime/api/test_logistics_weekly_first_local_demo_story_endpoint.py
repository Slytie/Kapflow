from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/weekly_first_local_demo_seed.yaml"
)


def _client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        actor_id="human:demo-operator",
        actor_type="human",
        actor_roles=["schedule_planner", "dispatch_supervisor", "operations_manager"],
    )


def test_weekly_first_local_demo_story_endpoint_is_honest_about_partial_progress(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    client = _client(harness)
    response = client.get(
        "/api/v1/stories/logistics-three-workflow",
        query={
            "planning_week_id": "PW-2026-W10",
            "service_date_id": "SD-2026-03-06",
        },
    )
    assert response.status_code == 200, response.payload

    story = response.payload["story"]
    linked = story["linked_workflow_runs"]
    assert [run["workflow_id"] for run in linked["weekly_schedule_planning"]] == [
        "weekly_schedule_planning.v1"
    ]
    assert [run["workflow_id"] for run in linked["dispatch_reporting"]] == [
        "dispatch_reporting.v1",
        "dispatch_reporting.v1",
    ]
    assert linked["live_dispatch"] == []
    assert linked["summary"] == {
        "weekly_schedule_planning_count": 1,
        "live_dispatch_count": 0,
        "dispatch_reporting_count": 2,
    }

    modules = {module["module_id"]: module for module in story["family_graph"]["modules"]}
    assert modules["weekly_schedule_planning"]["drilldown_kind"] == "workflow_run"
    assert modules["weekly_schedule_planning"]["artifact_refs"] == [
        {
            "artifact_version_id": modules["weekly_schedule_planning"]["artifact_refs"][0][
                "artifact_version_id"
            ],
            "label": "planning.actual_hours_snapshot.workbook",
            "source_label": "Official input",
        }
    ]
    assert modules["dispatch_reporting"]["drilldown_kind"] == "run_group"
    assert len(modules["dispatch_reporting"]["drilldown_refs"]) == 2
    assert modules["live_dispatch"]["drilldown_kind"] == "none"
    assert modules["live_dispatch"]["drilldown_refs"] == []

    work_items = story["board"]["work_items"]
    assert {(item["stage_id"], item["task_kind"]) for item in work_items} == {
        ("Stage04", "weekly_input_intake"),
        ("Stage01", "eos_input_intake"),
    }

    handoff_edges = {edge["edge_id"]: edge for edge in story["handoff_activity"]["edges"]}
    assert handoff_edges["reporting_actuals_to_future_planning"]["status_counts"] == {
        "prepared": 1
    }
    assert handoff_edges["weekly_seed_to_live_dispatch"]["execution_count"] == 0

    summary = story["official_outputs"]["summary"]
    assert summary["artifact_kind_counts"] == {
        "reporting.final_packet.workbook": 1
    }
    assert "planning.published_weekly_schedule.workbook" not in summary["artifact_kind_counts"]
