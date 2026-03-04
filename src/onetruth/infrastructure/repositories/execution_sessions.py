from __future__ import annotations

import json
import sqlite3
from typing import Any


def create_execution_session(
    connection: sqlite3.Connection,
    *,
    execution_session_id: str,
    workflow_run_id: str,
    task_run_id: str,
    execution_spec_id: str,
    state: str,
    owner_mode: str,
    principal_actor: dict[str, Any] | None,
    budget: dict[str, Any] | None,
    tool_call_count: int,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO execution_sessions (
            execution_session_id,
            workflow_run_id,
            task_run_id,
            execution_spec_id,
            state,
            owner_mode,
            principal_actor,
            budget,
            tool_call_count,
            created_at,
            updated_at,
            closed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            execution_session_id,
            workflow_run_id,
            task_run_id,
            execution_spec_id,
            state,
            owner_mode,
            _json_or_none(principal_actor),
            _json_or_none(budget),
            tool_call_count,
            created_at,
            created_at,
            None,
        ),
    )


def get_execution_session(
    connection: sqlite3.Connection,
    execution_session_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            execution_session_id,
            workflow_run_id,
            task_run_id,
            execution_spec_id,
            state,
            owner_mode,
            principal_actor,
            budget,
            tool_call_count,
            created_at,
            updated_at,
            closed_at
        FROM execution_sessions
        WHERE execution_session_id = ?
        """,
        (execution_session_id,),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def list_execution_sessions_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            execution_session_id,
            workflow_run_id,
            task_run_id,
            execution_spec_id,
            state,
            owner_mode,
            principal_actor,
            budget,
            tool_call_count,
            created_at,
            updated_at,
            closed_at
        FROM execution_sessions
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC, execution_session_id ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    return [_decode_row(dict(row)) for row in rows]


def list_reconcilable_execution_sessions(
    connection: sqlite3.Connection,
    *,
    stale_before_iso: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            execution_session_id,
            workflow_run_id,
            task_run_id,
            execution_spec_id,
            state,
            owner_mode,
            principal_actor,
            budget,
            tool_call_count,
            created_at,
            updated_at,
            closed_at
        FROM execution_sessions
        WHERE state IN ('CREATED', 'RUNNING', 'WAITING_POLICY', 'WAITING_APPROVAL')
          AND updated_at <= ?
        ORDER BY updated_at ASC, execution_session_id ASC
        """,
        (stale_before_iso,),
    ).fetchall()
    return [_decode_row(dict(row)) for row in rows]


def transition_execution_session_state(
    connection: sqlite3.Connection,
    *,
    execution_session_id: str,
    from_states: list[str],
    to_state: str,
    updated_at: str,
    closed_at: str | None,
) -> dict[str, Any] | None:
    if not from_states:
        raise ValueError("from_states must be non-empty")
    placeholders = ",".join("?" for _ in from_states)
    params: list[Any] = [to_state, updated_at, closed_at, execution_session_id, *from_states]
    cursor = connection.execute(
        f"""
        UPDATE execution_sessions
        SET
            state = ?,
            updated_at = ?,
            closed_at = ?
        WHERE execution_session_id = ?
          AND state IN ({placeholders})
        """,
        params,
    )
    if cursor.rowcount != 1:
        return None
    return get_execution_session(connection, execution_session_id)


def increment_tool_call_count(
    connection: sqlite3.Connection,
    *,
    execution_session_id: str,
    updated_at: str,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        UPDATE execution_sessions
        SET
            tool_call_count = tool_call_count + 1,
            updated_at = ?
        WHERE execution_session_id = ?
        """,
        (updated_at, execution_session_id),
    )
    if cursor.rowcount != 1:
        return None
    return get_execution_session(connection, execution_session_id)


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"))


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("principal_actor") is not None:
        row["principal_actor"] = json.loads(row["principal_actor"])
    if row.get("budget") is not None:
        row["budget"] = json.loads(row["budget"])
    return row
