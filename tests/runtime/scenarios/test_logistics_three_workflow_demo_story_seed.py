from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/three_workflow_demo_story_seed.yaml"
)


def test_logistics_three_workflow_demo_story_seed_runs_both_handoff_edges_and_links_all_three_runs(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    notify_edge = harness.output("notify_result")["result"]["edge_executions"][0]
    materialize_edge = harness.output("weekly_to_live_materialized")["result"]["edge_executions"][0]
    live_activation = harness.output("live_activation")["result"]

    assert notify_edge["edge_id"] == "reporting_actuals_to_future_planning"
    assert notify_edge["target_workflow_id"] == "weekly_schedule_planning.v1"
    assert notify_edge["target_partition_key"] == "PW-2026-W10"
    assert notify_edge["status"] == "prepared"

    assert materialize_edge["edge_id"] == "weekly_seed_to_live_dispatch"
    assert materialize_edge["target_workflow_id"] == "live_dispatch.v1"
    assert materialize_edge["target_partition_key"] == "SD-2026-03-06"

    live_run = live_activation["target_workflow_run"]
    assert live_run["workflow_id"] == "live_dispatch.v1"
    assert live_run["partition_key"] == "SD-2026-03-06"

    run_counts = harness.query_rows(
        """
        SELECT workflow_id, COUNT(*) AS run_count
        FROM workflow_runs
        GROUP BY workflow_id
        ORDER BY workflow_id ASC
        """
    )
    assert run_counts == [
        {"workflow_id": "dispatch_reporting.v1", "run_count": 1},
        {"workflow_id": "live_dispatch.v1", "run_count": 1},
        {"workflow_id": "weekly_schedule_planning.v1", "run_count": 1},
    ]

    edge_rows = harness.query_rows(
        """
        SELECT edge_id, status, COUNT(*) AS edge_count
        FROM edge_executions
        GROUP BY edge_id, status
        ORDER BY edge_id ASC, status ASC
        """
    )
    assert edge_rows == [
        {
            "edge_id": "reporting_actuals_to_future_planning",
            "status": "prepared",
            "edge_count": 1,
        },
        {
            "edge_id": "weekly_seed_to_live_dispatch",
            "status": "activated",
            "edge_count": 1,
        },
    ]
