from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/weekly_to_live_dispatch_golden_slice.yaml"
)


def test_logistics_weekly_to_live_golden_slice_fixture_runs_through_handoff_activation(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    activation = harness.output("activate_live_dispatch")["result"]
    edge_execution = activation["edge_execution"]
    target_workflow_run = activation["target_workflow_run"]

    assert edge_execution["edge_id"] == "weekly_seed_to_live_dispatch"
    assert edge_execution["status"] == "activated"
    assert target_workflow_run["workflow_id"] == "live_dispatch.v1"
    assert target_workflow_run["partition_key"] == "SD-2026-03-06"

    edge_rows = harness.query_rows(
        "SELECT edge_execution_id, status FROM edge_executions ORDER BY edge_execution_id ASC"
    )
    assert len(edge_rows) == 1
    assert edge_rows[0]["status"] == "activated"

    live_runs = harness.query_rows(
        """
        SELECT workflow_run_id, workflow_id, partition_key
        FROM workflow_runs
        WHERE workflow_id = 'live_dispatch.v1'
        """
    )
    assert len(live_runs) == 1
    assert live_runs[0]["partition_key"] == "SD-2026-03-06"
