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


def test_logistics_weekly_to_live_golden_slice_retries_are_replay_safe(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    weekly_publish = harness.output("weekly_publish")["artifact_version"]
    materialized = harness.output("handoff_materialized")["result"]
    activated = harness.output("activate_live_dispatch")["result"]
    route_delta = harness.output("route_delta")["artifact_version"]
    actual_hours = harness.output("actual_hours_source")["artifact_version"]
    edge_execution_id = str(materialized["edge_executions"][0]["edge_execution_id"])
    target_workflow_run_id = str(activated["target_workflow_run"]["workflow_run_id"])

    retry_materialize = harness.run_action(
        action="handoffs.materialize-weekly-seeds",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "published_artifact_version_id": str(weekly_publish["artifact_version_id"]),
            "service_date_id": "SD-2026-03-06",
            "idempotency_key": "scenario:logistics_weekly_to_live_dispatch_golden_slice:handoff:materialize:retry",
        },
    )
    retry_activation = harness.run_action(
        action="handoffs.activate-live-dispatch",
        payload={
            "edge_execution_id": edge_execution_id,
            "route_delta_source_artifact_version_id": str(route_delta["artifact_version_id"]),
            "actual_hours_source_artifact_version_id": str(actual_hours["artifact_version_id"]),
            "idempotency_key": "scenario:logistics_weekly_to_live_dispatch_golden_slice:handoff:activate:retry",
        },
    )

    assert (
        retry_materialize["result"]["edge_executions"][0]["edge_execution_id"]
        == edge_execution_id
    )
    assert (
        str(retry_activation["result"]["target_workflow_run"]["workflow_run_id"])
        == target_workflow_run_id
    )

    edge_rows = harness.query_rows(
        """
        SELECT edge_execution_id
        FROM edge_executions
        WHERE edge_id = 'weekly_seed_to_live_dispatch'
        """
    )
    live_run_rows = harness.query_rows(
        """
        SELECT workflow_run_id
        FROM workflow_runs
        WHERE workflow_id = 'live_dispatch.v1'
          AND partition_key = 'SD-2026-03-06'
        """
    )
    binding_rows = harness.query_rows(
        """
        SELECT binding_key
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        """,
        (target_workflow_run_id,),
    )
    assert len(edge_rows) == 1
    assert len(live_run_rows) == 1
    assert len(binding_rows) == 3
