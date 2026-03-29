from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness


SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/weekly_first_local_demo_seed.yaml"
)


def test_weekly_first_local_demo_seed_keeps_live_unprepared_and_binds_prior_reporting_feedback(
    tmp_path: Path,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    run_counts = harness.query_rows(
        """
        SELECT workflow_id, COUNT(*) AS run_count
        FROM workflow_runs
        GROUP BY workflow_id
        ORDER BY workflow_id ASC
        """
    )
    assert run_counts == [
        {"workflow_id": "dispatch_reporting.v1", "run_count": 2},
        {"workflow_id": "weekly_schedule_planning.v1", "run_count": 1},
    ]

    live_rows = harness.query_rows(
        """
        SELECT workflow_run_id
        FROM workflow_runs
        WHERE workflow_id = 'live_dispatch.v1'
        """
    )
    assert live_rows == []

    weekly_tasks = harness.query_rows(
        """
        SELECT tr.stage_id, ht.task_kind, ht.state
        FROM human_tasks AS ht
        JOIN task_runs AS tr ON tr.task_run_id = ht.task_run_id
        WHERE ht.workflow_run_id = ?
        ORDER BY ht.created_at ASC
        """,
        (harness.workflow_run_id,),
    )
    assert weekly_tasks == [
        {
            "stage_id": "Stage04",
            "task_kind": "weekly_input_intake",
            "state": "OPEN",
        }
    ]

    reporting_tasks = harness.query_rows(
        """
        SELECT tr.stage_id, ht.task_kind, ht.state
        FROM human_tasks AS ht
        JOIN task_runs AS tr ON tr.task_run_id = ht.task_run_id
        WHERE ht.workflow_run_id = 'wr-demo-reporting-current'
        ORDER BY ht.created_at ASC
        """
    )
    assert reporting_tasks == [
        {
            "stage_id": "Stage01",
            "task_kind": "eos_input_intake",
            "state": "OPEN",
        }
    ]

    weekly_inputs = harness.query_rows(
        """
        SELECT binding_key, source_ref, artifact_version_id
        FROM workflow_run_inputs
        WHERE workflow_run_id = ?
        ORDER BY binding_key ASC
        """,
        (harness.workflow_run_id,),
    )
    assert weekly_inputs == [
        {
            "binding_key": "stage03.actual_hours_snapshot",
            "source_ref": "av-demo-reporting-feedback-final",
            "artifact_version_id": weekly_inputs[0]["artifact_version_id"],
        }
    ]

    actual_hours_artifacts = harness.query_rows(
        """
        SELECT artifact_kind, artifact_role, workflow_run_id
        FROM artifact_versions
        WHERE workflow_run_id = ? AND artifact_kind = 'planning.actual_hours_snapshot.workbook'
        ORDER BY created_at ASC
        """,
        (harness.workflow_run_id,),
    )
    assert actual_hours_artifacts == [
        {
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "artifact_role": "official_input",
            "workflow_run_id": harness.workflow_run_id,
        }
    ]
