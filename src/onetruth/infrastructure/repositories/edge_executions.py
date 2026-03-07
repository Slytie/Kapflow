from __future__ import annotations

import json
import sqlite3
from typing import Any


class EdgeExecutionConflictError(ValueError):
    def __init__(self, edge_id: str, correlation_key: str) -> None:
        super().__init__(
            "edge execution already exists for correlation "
            f"(edge_id={edge_id}, correlation_key={correlation_key})"
        )
        self.edge_id = edge_id
        self.correlation_key = correlation_key


def create_edge_execution(
    connection: sqlite3.Connection,
    *,
    edge_execution_id: str,
    edge_id: str,
    source_workflow_run_id: str,
    source_stage_id: str,
    source_artifact_version_id: str,
    source_activation_key: str,
    target_workflow_id: str,
    target_stage_id: str,
    target_partition_kind: str,
    target_partition_key: str,
    target_activation_key: str,
    correlation_key: str,
    materialize_idempotency_key: str,
    status: str,
    cursor_state: dict[str, Any] | None,
    compensation_state: dict[str, Any] | None,
    input_bindings: dict[str, Any] | None,
    trigger_ref: str | None,
    seed_artifact_version_id: str | None,
    target_workflow_run_id: str | None,
    activated_at: str | None,
    created_at: str,
) -> None:
    try:
        connection.execute(
            """
            INSERT INTO edge_executions (
                edge_execution_id,
                edge_id,
                source_workflow_run_id,
                source_stage_id,
                source_artifact_version_id,
                source_activation_key,
                target_workflow_id,
                target_workflow_run_id,
                target_stage_id,
                target_partition_kind,
                target_partition_key,
                target_activation_key,
                correlation_key,
                materialize_idempotency_key,
                activation_idempotency_key,
                status,
                cursor_state_json,
                compensation_state_json,
                input_bindings_json,
                trigger_ref,
                seed_artifact_version_id,
                created_at,
                updated_at,
                activated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge_execution_id,
                edge_id,
                source_workflow_run_id,
                source_stage_id,
                source_artifact_version_id,
                source_activation_key,
                target_workflow_id,
                target_workflow_run_id,
                target_stage_id,
                target_partition_kind,
                target_partition_key,
                target_activation_key,
                correlation_key,
                materialize_idempotency_key,
                None,
                status,
                _json_or_none(cursor_state),
                _json_or_none(compensation_state),
                _json_or_none(input_bindings),
                trigger_ref,
                seed_artifact_version_id,
                created_at,
                created_at,
                activated_at,
            ),
        )
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if (
            "uq_edge_executions_correlation" in message
            or "edge_executions.edge_id, edge_executions.correlation_key" in message
        ):
            raise EdgeExecutionConflictError(edge_id, correlation_key) from exc
        raise


def get_edge_execution(
    connection: sqlite3.Connection,
    edge_execution_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            edge_execution_id,
            edge_id,
            source_workflow_run_id,
            source_stage_id,
            source_artifact_version_id,
            source_activation_key,
            target_workflow_id,
            target_workflow_run_id,
            target_stage_id,
            target_partition_kind,
            target_partition_key,
            target_activation_key,
            correlation_key,
            materialize_idempotency_key,
            activation_idempotency_key,
            status,
            cursor_state_json,
            compensation_state_json,
            input_bindings_json,
            trigger_ref,
            seed_artifact_version_id,
            created_at,
            updated_at,
            activated_at
        FROM edge_executions
        WHERE edge_execution_id = ?
        """,
        (edge_execution_id,),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def get_edge_execution_by_scope(
    connection: sqlite3.Connection,
    *,
    edge_id: str,
    source_workflow_run_id: str,
    source_artifact_version_id: str,
    target_partition_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            edge_execution_id,
            edge_id,
            source_workflow_run_id,
            source_stage_id,
            source_artifact_version_id,
            source_activation_key,
            target_workflow_id,
            target_workflow_run_id,
            target_stage_id,
            target_partition_kind,
            target_partition_key,
            target_activation_key,
            correlation_key,
            materialize_idempotency_key,
            activation_idempotency_key,
            status,
            cursor_state_json,
            compensation_state_json,
            input_bindings_json,
            trigger_ref,
            seed_artifact_version_id,
            created_at,
            updated_at,
            activated_at
        FROM edge_executions
        WHERE edge_id = ?
          AND source_workflow_run_id = ?
          AND source_artifact_version_id = ?
          AND target_partition_key = ?
        LIMIT 1
        """,
        (edge_id, source_workflow_run_id, source_artifact_version_id, target_partition_key),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def get_edge_execution_by_correlation(
    connection: sqlite3.Connection,
    *,
    edge_id: str,
    correlation_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            edge_execution_id,
            edge_id,
            source_workflow_run_id,
            source_stage_id,
            source_artifact_version_id,
            source_activation_key,
            target_workflow_id,
            target_workflow_run_id,
            target_stage_id,
            target_partition_kind,
            target_partition_key,
            target_activation_key,
            correlation_key,
            materialize_idempotency_key,
            activation_idempotency_key,
            status,
            cursor_state_json,
            compensation_state_json,
            input_bindings_json,
            trigger_ref,
            seed_artifact_version_id,
            created_at,
            updated_at,
            activated_at
        FROM edge_executions
        WHERE edge_id = ?
          AND correlation_key = ?
        LIMIT 1
        """,
        (edge_id, correlation_key),
    ).fetchone()
    if row is None:
        return None
    return _decode_row(dict(row))


def list_edge_executions(
    connection: sqlite3.Connection,
    *,
    edge_id: str | None = None,
    source_workflow_run_id: str | None = None,
    status: str | None = None,
    target_workflow_run_id: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            edge_execution_id,
            edge_id,
            source_workflow_run_id,
            source_stage_id,
            source_artifact_version_id,
            source_activation_key,
            target_workflow_id,
            target_workflow_run_id,
            target_stage_id,
            target_partition_kind,
            target_partition_key,
            target_activation_key,
            correlation_key,
            materialize_idempotency_key,
            activation_idempotency_key,
            status,
            cursor_state_json,
            compensation_state_json,
            input_bindings_json,
            trigger_ref,
            seed_artifact_version_id,
            created_at,
            updated_at,
            activated_at
        FROM edge_executions
        WHERE 1 = 1
    """
    params: list[Any] = []

    if edge_id is not None:
        query += " AND edge_id = ?"
        params.append(edge_id)
    if source_workflow_run_id is not None:
        query += " AND source_workflow_run_id = ?"
        params.append(source_workflow_run_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if target_workflow_run_id is not None:
        query += " AND target_workflow_run_id = ?"
        params.append(target_workflow_run_id)

    query += " ORDER BY created_at ASC, edge_execution_id ASC"
    rows = connection.execute(query, params).fetchall()
    return [_decode_row(dict(row)) for row in rows]


def update_edge_execution_activation(
    connection: sqlite3.Connection,
    *,
    edge_execution_id: str,
    target_workflow_run_id: str,
    trigger_ref: str,
    activation_idempotency_key: str,
    status: str,
    cursor_state: dict[str, Any] | None,
    compensation_state: dict[str, Any] | None,
    input_bindings: dict[str, Any] | None,
    activated_at: str,
    updated_at: str,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        UPDATE edge_executions
        SET
            target_workflow_run_id = ?,
            trigger_ref = ?,
            activation_idempotency_key = ?,
            status = ?,
            cursor_state_json = ?,
            compensation_state_json = ?,
            input_bindings_json = ?,
            activated_at = ?,
            updated_at = ?
        WHERE edge_execution_id = ?
        """,
        (
            target_workflow_run_id,
            trigger_ref,
            activation_idempotency_key,
            status,
            _json_or_none(cursor_state),
            _json_or_none(compensation_state),
            _json_or_none(input_bindings),
            activated_at,
            updated_at,
            edge_execution_id,
        ),
    )
    if cursor.rowcount != 1:
        return None
    return get_edge_execution(connection, edge_execution_id)


def update_edge_execution_cursor(
    connection: sqlite3.Connection,
    *,
    edge_execution_id: str,
    status: str,
    cursor_state: dict[str, Any] | None,
    compensation_state: dict[str, Any] | None,
    input_bindings: dict[str, Any] | None,
    updated_at: str,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        UPDATE edge_executions
        SET
            status = ?,
            cursor_state_json = ?,
            compensation_state_json = ?,
            input_bindings_json = ?,
            updated_at = ?
        WHERE edge_execution_id = ?
        """,
        (
            status,
            _json_or_none(cursor_state),
            _json_or_none(compensation_state),
            _json_or_none(input_bindings),
            updated_at,
            edge_execution_id,
        ),
    )
    if cursor.rowcount != 1:
        return None
    return get_edge_execution(connection, edge_execution_id)


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"))


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("cursor_state_json") is not None:
        row["cursor_state"] = json.loads(str(row["cursor_state_json"]))
    else:
        row["cursor_state"] = None
    if row.get("compensation_state_json") is not None:
        row["compensation_state"] = json.loads(str(row["compensation_state_json"]))
    else:
        row["compensation_state"] = None
    if row.get("input_bindings_json") is not None:
        row["input_bindings"] = json.loads(str(row["input_bindings_json"]))
    else:
        row["input_bindings"] = None
    row.pop("cursor_state_json", None)
    row.pop("compensation_state_json", None)
    row.pop("input_bindings_json", None)
    return row
