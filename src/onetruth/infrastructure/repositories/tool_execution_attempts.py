from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Any


ATTEMPT_COLUMNS = """
    tool_execution_attempt_id,
    tool_execution_id,
    execution_session_id,
    attempt_no,
    lease_token,
    state,
    active_tool_execution_id,
    output_artifact_version_ids,
    started_at,
    completed_at,
    error_code,
    created_at,
    updated_at
"""

ACTIVE_ATTEMPT_STATES = {"RUNNING"}
TERMINAL_ATTEMPT_STATES = {"COMPLETED", "FAILED", "CANCELED"}
ATTEMPT_STATES = ACTIVE_ATTEMPT_STATES | TERMINAL_ATTEMPT_STATES


@dataclass(frozen=True)
class ToolExecutionAttemptError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def create_tool_execution_attempt(
    connection: sqlite3.Connection,
    *,
    tool_execution_attempt_id: str,
    tool_execution_id: str,
    execution_session_id: str,
    lease_token: str,
    started_at: str,
) -> dict[str, Any]:
    _require_nonempty(tool_execution_attempt_id, "tool_execution_attempt_id")
    _require_nonempty(tool_execution_id, "tool_execution_id")
    _require_nonempty(execution_session_id, "execution_session_id")
    _require_nonempty(lease_token, "lease_token")
    active = get_active_tool_execution_attempt(connection, tool_execution_id=tool_execution_id)
    if active is not None:
        raise ToolExecutionAttemptError(
            code="tool_execution_attempt_active_conflict",
            details={
                "tool_execution_id": tool_execution_id,
                "active_tool_execution_attempt_id": active["tool_execution_attempt_id"],
            },
        )
    attempt_no = next_tool_execution_attempt_no(
        connection,
        tool_execution_id=tool_execution_id,
    )
    connection.execute(
        """
        INSERT INTO tool_execution_attempts (
            tool_execution_attempt_id,
            tool_execution_id,
            execution_session_id,
            attempt_no,
            lease_token,
            state,
            active_tool_execution_id,
            output_artifact_version_ids,
            started_at,
            completed_at,
            error_code,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, 'RUNNING', ?, NULL, ?, NULL, NULL, ?, ?)
        """,
        (
            tool_execution_attempt_id,
            tool_execution_id,
            execution_session_id,
            attempt_no,
            lease_token,
            tool_execution_id,
            started_at,
            started_at,
            started_at,
        ),
    )
    attempt = get_tool_execution_attempt(connection, tool_execution_attempt_id)
    if attempt is None:
        raise RuntimeError("tool execution attempt insert failed")
    return attempt


def get_tool_execution_attempt(
    connection: sqlite3.Connection,
    tool_execution_attempt_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {ATTEMPT_COLUMNS}
        FROM tool_execution_attempts
        WHERE tool_execution_attempt_id = ?
        """,
        (tool_execution_attempt_id,),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def get_active_tool_execution_attempt(
    connection: sqlite3.Connection,
    *,
    tool_execution_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {ATTEMPT_COLUMNS}
        FROM tool_execution_attempts
        WHERE tool_execution_id = ?
          AND state = 'RUNNING'
          AND active_tool_execution_id = ?
        ORDER BY attempt_no DESC
        LIMIT 1
        """,
        (tool_execution_id, tool_execution_id),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def list_tool_execution_attempts(
    connection: sqlite3.Connection,
    *,
    tool_execution_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {ATTEMPT_COLUMNS}
        FROM tool_execution_attempts
        WHERE tool_execution_id = ?
        ORDER BY attempt_no ASC, tool_execution_attempt_id ASC
        """,
        (tool_execution_id,),
    ).fetchall()
    return [_decode_row(dict(row)) for row in rows]


def next_tool_execution_attempt_no(
    connection: sqlite3.Connection,
    *,
    tool_execution_id: str,
) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(MAX(attempt_no), 0) AS max_attempt_no
        FROM tool_execution_attempts
        WHERE tool_execution_id = ?
        """,
        (tool_execution_id,),
    ).fetchone()
    return int(row["max_attempt_no"]) + 1


def complete_tool_execution_attempt(
    connection: sqlite3.Connection,
    *,
    tool_execution_attempt_id: str,
    tool_execution_id: str,
    lease_token: str,
    state: str,
    output_artifact_version_ids: list[str] | None,
    completed_at: str,
    error_code: str | None,
) -> dict[str, Any]:
    if state not in TERMINAL_ATTEMPT_STATES:
        raise ToolExecutionAttemptError(
            code="tool_execution_attempt_state_invalid",
            details={"state": state, "allowed_states": sorted(TERMINAL_ATTEMPT_STATES)},
        )
    attempt = get_tool_execution_attempt(connection, tool_execution_attempt_id)
    if attempt is None:
        raise ToolExecutionAttemptError(
            code="tool_execution_attempt_not_found",
            details={"tool_execution_attempt_id": tool_execution_attempt_id},
        )
    if (
        attempt["tool_execution_id"] != tool_execution_id
        or attempt["lease_token"] != lease_token
        or attempt["state"] != "RUNNING"
        or attempt["active_tool_execution_id"] != tool_execution_id
    ):
        raise ToolExecutionAttemptError(
            code="tool_execution_attempt_stale_completion",
            details={
                "tool_execution_attempt_id": tool_execution_attempt_id,
                "tool_execution_id": tool_execution_id,
            },
        )
    cursor = connection.execute(
        """
        UPDATE tool_execution_attempts
        SET state = ?,
            active_tool_execution_id = NULL,
            output_artifact_version_ids = ?,
            completed_at = ?,
            error_code = ?,
            updated_at = ?
        WHERE tool_execution_attempt_id = ?
          AND tool_execution_id = ?
          AND lease_token = ?
          AND state = 'RUNNING'
          AND active_tool_execution_id = ?
        """,
        (
            state,
            _json_or_none(output_artifact_version_ids),
            completed_at,
            error_code,
            completed_at,
            tool_execution_attempt_id,
            tool_execution_id,
            lease_token,
            tool_execution_id,
        ),
    )
    if cursor.rowcount != 1:
        raise ToolExecutionAttemptError(
            code="tool_execution_attempt_stale_completion",
            details={
                "tool_execution_attempt_id": tool_execution_attempt_id,
                "tool_execution_id": tool_execution_id,
            },
        )
    completed = get_tool_execution_attempt(connection, tool_execution_attempt_id)
    if completed is None:
        raise RuntimeError("tool execution attempt update failed")
    return completed


def _require_nonempty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ToolExecutionAttemptError(
            code="tool_execution_attempt_field_required",
            details={"field": field},
        )


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("output_artifact_version_ids") is not None:
        row["output_artifact_version_ids"] = json.loads(row["output_artifact_version_ids"])
    return row
