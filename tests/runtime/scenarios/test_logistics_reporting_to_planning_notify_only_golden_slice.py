from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/reporting_to_planning_notify_only_golden_slice.yaml"
)


def test_logistics_reporting_to_planning_notify_only_golden_slice_materializes_feedback_without_target_output_mutation(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    final_packet = harness.output("final_packet")["artifact_version"]
    notified = harness.output("notify_result")["result"]
    retry = harness.output("notify_retry")["result"]

    edge_execution = notified["edge_executions"][0]
    target_workflow_run = notified["target_workflow_runs"][0]
    target_input_artifact = notified["target_input_artifacts"][0]

    assert edge_execution["edge_id"] == "reporting_actuals_to_future_planning"
    assert edge_execution["target_partition_kind"] == "PlanningWeekID"
    assert edge_execution["target_partition_key"] == "PW-2026-W11"
    assert target_workflow_run["workflow_id"] == "weekly_schedule_planning.v1"
    assert target_workflow_run["partition_key"] == "PW-2026-W11"
    assert target_input_artifact["artifact_kind"] == "planning.actual_hours_snapshot.workbook"
    assert str(target_input_artifact["parent_artifact_version_id"]) == str(
        final_packet["artifact_version_id"]
    )
    assert target_input_artifact["metadata_json"]["rows"] == [
        [
            "2026-03-06",
            "A1NQEGRS26IBJA",
            "Suraj Pratap Singh",
            "WORKED",
            540,
            "CX93",
            "",
            0,
            0,
            0,
            target_input_artifact["metadata_json"]["rows"][0][10],
        ]
    ]
    assert (
        retry["edge_executions"][0]["edge_execution_id"]
        == edge_execution["edge_execution_id"]
    )

    edge_rows = harness.query_rows(
        """
        SELECT edge_execution_id, status
        FROM edge_executions
        WHERE edge_id = 'reporting_actuals_to_future_planning'
        """
    )
    assert len(edge_rows) == 1

    target_run_rows = harness.query_rows(
        """
        SELECT workflow_run_id, workflow_id, partition_key
        FROM workflow_runs
        WHERE workflow_id = 'weekly_schedule_planning.v1'
          AND partition_key = 'PW-2026-W11'
        """
    )
    assert len(target_run_rows) == 1

    input_rows = harness.query_rows(
        """
        SELECT binding_key, source_ref, artifact_version_id
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        """,
        (str(target_workflow_run["workflow_run_id"]),),
    )
    assert input_rows == [
        {
            "binding_key": "stage03.actual_hours_snapshot",
            "source_ref": str(final_packet["artifact_version_id"]),
            "artifact_version_id": str(target_input_artifact["artifact_version_id"]),
        }
    ]

    pointer_rows = harness.query_rows(
        "SELECT pointer_key FROM artifact_pointers WHERE workflow_run_id = ?",
        (str(target_workflow_run["workflow_run_id"]),),
    )
    assert pointer_rows == []

    official_output_rows = harness.query_rows(
        """
        SELECT artifact_version_id
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_role = 'official_output'
        """,
        (str(target_workflow_run["workflow_run_id"]),),
    )
    assert official_output_rows == []
