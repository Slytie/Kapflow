from __future__ import annotations

from pathlib import Path
import sqlite3

from tests.runtime.helpers.runtime_cli import run_cli, stdout_json


def _query_rows(
    db_path: Path,
    query: str,
    params: tuple[object, ...] = (),
) -> list[dict[str, object]]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(query, params).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def test_logistics_operational_cadence_tick_cli_creates_and_replays_due_state(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "cadence.db"
    db_url = f"sqlite:///{db_path}"
    run_cli("--db-url", db_url, "init-db")

    first = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "cadence",
            "tick-logistics",
            "--service-date-id",
            "SD-2026-03-06",
        )
    )
    second = stdout_json(
        run_cli(
            "--db-url",
            db_url,
            "cadence",
            "tick-logistics",
            "--service-date-id",
            "SD-2026-03-06",
        )
    )

    assert first["status"] == "ok"
    assert first["command"] == "cadence.tick-logistics"
    assert first["effective_service_date_id"] == "SD-2026-03-06"
    assert first["effective_planning_week_id"] == "PW-2026-W10"

    assert first["weekly"]["status"] == "created"
    assert second["weekly"]["status"] == "existing"
    assert first["weekly"]["workflow_run_id"] == second["weekly"]["workflow_run_id"]
    assert first["weekly"]["human_task_id"] == second["weekly"]["human_task_id"]

    assert first["reporting"]["status"] == "created"
    assert second["reporting"]["status"] == "existing"
    assert first["reporting"]["workflow_run_id"] == second["reporting"]["workflow_run_id"]
    assert first["reporting"]["human_task_id"] == second["reporting"]["human_task_id"]

    assert first["live_dispatch"]["status"] == "skipped"
    assert second["live_dispatch"]["status"] == "skipped"
    assert first["live_dispatch"]["skipped_reason"] == "waiting_on_weekly_publish"
    assert second["live_dispatch"]["skipped_reason"] == "waiting_on_weekly_publish"

    workflow_runs = _query_rows(
        db_path,
        """
        SELECT workflow_id, partition_key, COUNT(*) AS run_count
        FROM workflow_runs
        GROUP BY workflow_id, partition_key
        ORDER BY workflow_id ASC, partition_key ASC
        """,
    )
    assert workflow_runs == [
        {
            "workflow_id": "dispatch_reporting.v1",
            "partition_key": "SD-2026-03-06",
            "run_count": 1,
        },
        {
            "workflow_id": "weekly_schedule_planning.v1",
            "partition_key": "PW-2026-W10",
            "run_count": 1,
        },
    ]

    human_tasks = _query_rows(
        db_path,
        """
        SELECT workflow_run_id, task_kind, state, COUNT(*) AS task_count
        FROM human_tasks
        GROUP BY workflow_run_id, task_kind, state
        ORDER BY workflow_run_id ASC, task_kind ASC, state ASC
        """,
    )
    assert human_tasks == [
        {
            "workflow_run_id": first["reporting"]["workflow_run_id"],
            "task_kind": "eos_input_intake",
            "state": "OPEN",
            "task_count": 1,
        },
        {
            "workflow_run_id": first["weekly"]["workflow_run_id"],
            "task_kind": "weekly_input_intake",
            "state": "OPEN",
            "task_count": 1,
        },
    ]

    live_runs = _query_rows(
        db_path,
        """
        SELECT workflow_run_id
        FROM workflow_runs
        WHERE workflow_id = 'live_dispatch.v1'
        """,
    )
    assert live_runs == []
