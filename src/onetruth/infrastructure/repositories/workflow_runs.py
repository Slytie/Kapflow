from __future__ import annotations

import sqlite3
from typing import Any


_ACTIVE_FLAG_STATES = ("open", "triage", "blocked")


def create_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    workflow_id: str,
    workflow_version: str,
    tenant_id: str,
    domain_id: str,
    partition_key: str,
    logical_date: str | None,
    activation_key: str,
    state: str,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO workflow_runs (
            workflow_run_id,
            workflow_id,
            workflow_version,
            tenant_id,
            domain_id,
            partition_key,
            logical_date,
            activation_key,
            state,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workflow_run_id,
            workflow_id,
            workflow_version,
            tenant_id,
            domain_id,
            partition_key,
            logical_date,
            activation_key,
            state,
            created_at,
            created_at,
        ),
    )


def _select_workflow_runs_base() -> str:
    return """
        SELECT
            wr.workflow_run_id,
            wr.workflow_id,
            wr.workflow_version,
            wr.tenant_id,
            wr.domain_id,
            wr.partition_key,
            wr.logical_date,
            wr.activation_key,
            wr.state,
            wr.created_at,
            wr.updated_at,
            COALESCE(fc.active_issue_count, 0) AS active_issue_count
        FROM workflow_runs wr
        LEFT JOIN (
            SELECT
                workflow_run_id,
                COUNT(*) AS active_issue_count
            FROM flags
            WHERE state IN (?, ?, ?)
            GROUP BY workflow_run_id
        ) fc ON fc.workflow_run_id = wr.workflow_run_id
    """


def get_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        _select_workflow_runs_base() + "\nWHERE wr.workflow_run_id = ?",
        [*_ACTIVE_FLAG_STATES, workflow_run_id],
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_workflow_runs(
    connection: sqlite3.Connection,
    *,
    workflow_id: str | None = None,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    state: str | None = None,
) -> list[dict[str, Any]]:
    query = _select_workflow_runs_base()
    where: list[str] = []
    params: list[Any] = [*_ACTIVE_FLAG_STATES]
    if workflow_id is not None:
        where.append("wr.workflow_id = ?")
        params.append(workflow_id)
    if tenant_id is not None:
        where.append("wr.tenant_id = ?")
        params.append(tenant_id)
    if domain_id is not None:
        where.append("wr.domain_id = ?")
        params.append(domain_id)
    if state is not None:
        where.append("wr.state = ?")
        params.append(state)

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY wr.created_at ASC, wr.workflow_run_id ASC"
    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
