from __future__ import annotations

import json
import sqlite3
from typing import Any


def create_tool_execution(
    connection: sqlite3.Connection,
    *,
    tool_execution_id: str,
    execution_session_id: str,
    tool_class: str,
    tool_name: str | None,
    state: str,
    idempotency_key: str,
    attempt_no: int,
    policy_decision_id: str | None,
    output_artifact_version_ids: list[str] | None,
    requested_at: str,
    completed_at: str | None,
    error_code: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO tool_executions (
            tool_execution_id,
            execution_session_id,
            tool_class,
            tool_name,
            state,
            idempotency_key,
            attempt_no,
            policy_decision_id,
            output_artifact_version_ids,
            requested_at,
            completed_at,
            error_code
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tool_execution_id,
            execution_session_id,
            tool_class,
            tool_name,
            state,
            idempotency_key,
            attempt_no,
            policy_decision_id,
            _json_or_none(output_artifact_version_ids),
            requested_at,
            completed_at,
            error_code,
        ),
    )


def get_tool_execution(
    connection: sqlite3.Connection,
    tool_execution_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            tool_execution_id,
            execution_session_id,
            tool_class,
            tool_name,
            state,
            idempotency_key,
            attempt_no,
            policy_decision_id,
            output_artifact_version_ids,
            requested_at,
            completed_at,
            error_code
        FROM tool_executions
        WHERE tool_execution_id = ?
        """,
        (tool_execution_id,),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def get_tool_execution_by_session_idempotency(
    connection: sqlite3.Connection,
    *,
    execution_session_id: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            tool_execution_id,
            execution_session_id,
            tool_class,
            tool_name,
            state,
            idempotency_key,
            attempt_no,
            policy_decision_id,
            output_artifact_version_ids,
            requested_at,
            completed_at,
            error_code
        FROM tool_executions
        WHERE execution_session_id = ? AND idempotency_key = ?
        """,
        (execution_session_id, idempotency_key),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def list_tool_executions_for_session(
    connection: sqlite3.Connection,
    execution_session_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            tool_execution_id,
            execution_session_id,
            tool_class,
            tool_name,
            state,
            idempotency_key,
            attempt_no,
            policy_decision_id,
            output_artifact_version_ids,
            requested_at,
            completed_at,
            error_code
        FROM tool_executions
        WHERE execution_session_id = ?
        ORDER BY requested_at ASC, tool_execution_id ASC
        """,
        (execution_session_id,),
    ).fetchall()
    return [_decode_row(dict(row)) for row in rows]


def transition_tool_execution_state(
    connection: sqlite3.Connection,
    *,
    tool_execution_id: str,
    from_states: list[str],
    to_state: str,
    policy_decision_id: str | None,
    output_artifact_version_ids: list[str] | None,
    completed_at: str | None,
    error_code: str | None,
) -> dict[str, Any] | None:
    if not from_states:
        raise ValueError("from_states must be non-empty")
    placeholders = ",".join("?" for _ in from_states)
    params: list[Any] = [
        to_state,
        policy_decision_id,
        _json_or_none(output_artifact_version_ids),
        completed_at,
        error_code,
        tool_execution_id,
        *from_states,
    ]
    cursor = connection.execute(
        f"""
        UPDATE tool_executions
        SET
            state = ?,
            policy_decision_id = ?,
            output_artifact_version_ids = ?,
            completed_at = ?,
            error_code = ?
        WHERE tool_execution_id = ?
          AND state IN ({placeholders})
        """,
        params,
    )
    if cursor.rowcount != 1:
        return None
    return get_tool_execution(connection, tool_execution_id)


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"))


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("output_artifact_version_ids") is not None:
        row["output_artifact_version_ids"] = json.loads(row["output_artifact_version_ids"])
    return row
