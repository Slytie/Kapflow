from __future__ import annotations

import sqlite3
from pathlib import Path

from onetruth.application.handlers.logistics_handoff import materialize_weekly_seeds_command
from onetruth.application.handlers.schedule_control import (
    STAGE04_OUTPUT_SPECS,
    persist_weekly_stage04_output_payloads,
)
from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from tests.runtime.test_logistics_handoff_runtime import (
    _create_artifact_version,
    _create_workflow_run,
    _init_db,
    _query_rows,
    PLANNING_WEEK_ID,
)


def _memory_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def test_schedule_control_outputs_can_run_inside_outer_transaction_and_rollback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifact-root"))
    connection = _memory_connection()
    workflow_run = create_workflow_run_command(
        connection,
        {
            "workflow_run_id": "wr-schedule-control-nested-tx",
            "workflow_id": "weekly_schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": "tenant-logistics",
            "domain_id": "domain-hub",
            "partition_key": "PW-2026-W10",
            "logical_date": "2026-03-02",
            "activation_key": "weekly_schedule_planning.v1:PW-2026-W10:nested-tx",
        },
    )
    output_payloads = {
        artifact_kind: {
            "artifact_kind": artifact_kind,
            "candidate_delta_id": "candidate-delta-nested-tx",
            "payload": artifact_kind,
        }
        for artifact_kind, _artifact_role in STAGE04_OUTPUT_SPECS
    }

    connection.execute("BEGIN")
    created = persist_weekly_stage04_output_payloads(
        connection,
        workflow_run=workflow_run,
        bundle_id="bundle-nested-tx",
        output_payloads=output_payloads,
        source_input_ids=[],
    )
    assert len(created) == len(STAGE04_OUTPUT_SPECS)
    assert connection.in_transaction is True
    rows_inside_tx = connection.execute(
        "SELECT COUNT(*) AS count FROM artifact_versions WHERE workflow_run_id = ?",
        ("wr-schedule-control-nested-tx",),
    ).fetchone()
    assert rows_inside_tx is not None
    assert int(rows_inside_tx["count"]) == len(STAGE04_OUTPUT_SPECS)

    connection.rollback()
    rows_after_rollback = connection.execute(
        "SELECT COUNT(*) AS count FROM artifact_versions WHERE workflow_run_id = ?",
        ("wr-schedule-control-nested-tx",),
    ).fetchone()
    assert rows_after_rollback is not None
    assert int(rows_after_rollback["count"]) == 0


def test_logistics_handoff_materialization_can_run_inside_outer_transaction_and_rollback(
    tmp_path: Path,
) -> None:
    db_url, db_path = _init_db(tmp_path)
    weekly_run = _create_workflow_run(
        db_url,
        workflow_id="weekly_schedule_planning.v1",
        partition_key=PLANNING_WEEK_ID,
        logical_date="2026-03-02",
        activation_key="weekly_schedule_planning.v1:PW-2026-W10:nested-tx",
        idempotency_key="idem:runs.create:nested-tx",
    )
    published = _create_artifact_version(
        db_url,
        workflow_run_id=str(weekly_run["workflow_run_id"]),
        artifact_kind="planning.published_weekly_schedule.workbook",
        idempotency_key="idem:artifact:weekly-publish-nested-tx",
    )

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("BEGIN")
        result = materialize_weekly_seeds_command(
            connection,
            {
                "workflow_run_id": str(weekly_run["workflow_run_id"]),
                "published_artifact_version_id": str(published["artifact_version_id"]),
                "service_date_id": "SD-2026-03-06",
                "idempotency_key": "idem:handoff:materialize:nested-tx",
            },
        )
        assert len(result["edge_executions"]) == 1
        assert connection.in_transaction is True
        inside_rows = connection.execute(
            "SELECT COUNT(*) AS count FROM edge_executions"
        ).fetchone()
        assert inside_rows is not None
        assert int(inside_rows["count"]) == 1
        connection.rollback()
    finally:
        connection.close()

    assert _query_rows(db_path, "SELECT * FROM edge_executions") == []
