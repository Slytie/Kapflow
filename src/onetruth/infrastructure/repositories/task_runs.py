from __future__ import annotations

import sqlite3
from typing import Any


def create_task_run(
    connection: sqlite3.Connection,
    *,
    task_run_id: str,
    workflow_run_id: str,
    stage_id: str,
    task_kind: str,
    state: str,
    generation: int,
    activation_key: str,
    blocked_on_kind: str | None,
    blocked_on_ref: str | None,
    spawned_from_flag_id: str | None,
    spawned_from_task_run_id: str | None,
    spawn_rule_id: str | None,
    spawn_cause_kind: str | None,
    spawn_cause_event_id: str | None,
    spawn_depth: int,
    spawn_budget_key: str | None,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO task_runs (
            task_run_id,
            workflow_run_id,
            stage_id,
            task_kind,
            state,
            generation,
            activation_key,
            blocked_on_kind,
            blocked_on_ref,
            spawned_from_flag_id,
            spawned_from_task_run_id,
            spawn_rule_id,
            spawn_cause_kind,
            spawn_cause_event_id,
            spawn_depth,
            spawn_budget_key,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_run_id,
            workflow_run_id,
            stage_id,
            task_kind,
            state,
            generation,
            activation_key,
            blocked_on_kind,
            blocked_on_ref,
            spawned_from_flag_id,
            spawned_from_task_run_id,
            spawn_rule_id,
            spawn_cause_kind,
            spawn_cause_event_id,
            spawn_depth,
            spawn_budget_key,
            created_at,
            created_at,
        ),
    )


def _select_task_run_base() -> str:
    return """
        SELECT
            task_run_id,
            workflow_run_id,
            stage_id,
            task_kind,
            state,
            generation,
            activation_key,
            blocked_on_kind,
            blocked_on_ref,
            spawned_from_flag_id,
            spawned_from_task_run_id,
            spawn_rule_id,
            spawn_cause_kind,
            spawn_cause_event_id,
            spawn_depth,
            spawn_budget_key,
            created_at,
            updated_at
        FROM task_runs
    """


def get_task_run(
    connection: sqlite3.Connection,
    task_run_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        _select_task_run_base() + "\nWHERE task_run_id = ?",
        (task_run_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_task_run_by_activation_key(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    activation_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        _select_task_run_base() + "\nWHERE workflow_run_id = ? AND activation_key = ?",
        (workflow_run_id, activation_key),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_task_run_for_human_task(
    connection: sqlite3.Connection,
    human_task_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT tr.*
        FROM task_runs tr
        JOIN human_tasks ht ON ht.task_run_id = tr.task_run_id
        WHERE ht.human_task_id = ?
        """,
        (human_task_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def transition_task_run_state(
    connection: sqlite3.Connection,
    *,
    task_run_id: str,
    expected_from_state: str,
    to_state: str,
    updated_at: str,
) -> str | None:
    current = get_task_run(connection, task_run_id)
    if current is None:
        return None
    from_state = str(current["state"])
    if from_state != expected_from_state:
        return from_state

    connection.execute(
        """
        UPDATE task_runs
        SET state = ?, updated_at = ?
        WHERE task_run_id = ? AND state = ?
        """,
        (to_state, updated_at, task_run_id, expected_from_state),
    )
    return from_state
