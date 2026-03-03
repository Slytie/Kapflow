from __future__ import annotations

import sqlite3
from typing import Any


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


def get_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
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
        FROM workflow_runs
        WHERE workflow_run_id = ?
        """,
        (workflow_run_id,),
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
    query = """
        SELECT
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
        FROM workflow_runs
    """
    where: list[str] = []
    params: list[Any] = []
    if workflow_id is not None:
        where.append("workflow_id = ?")
        params.append(workflow_id)
    if tenant_id is not None:
        where.append("tenant_id = ?")
        params.append(tenant_id)
    if domain_id is not None:
        where.append("domain_id = ?")
        params.append(domain_id)
    if state is not None:
        where.append("state = ?")
        params.append(state)

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY created_at ASC, workflow_run_id ASC"
    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
