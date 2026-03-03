from __future__ import annotations

import json
import sqlite3
from typing import Any


def create_approval(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    workflow_run_id: str,
    task_run_id: str | None,
    approval_kind: str,
    scope_kind: str,
    scope_ref: str,
    state: str,
    requested_by_task_run_id: str | None,
    candidate_roles: list[str],
    required_role: str | None,
    requested_at: str,
    generation: int,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO approvals (
            approval_id,
            workflow_run_id,
            task_run_id,
            approval_kind,
            scope_kind,
            scope_ref,
            state,
            requested_by_task_run_id,
            candidate_roles,
            required_role,
            requested_at,
            generation,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            approval_id,
            workflow_run_id,
            task_run_id,
            approval_kind,
            scope_kind,
            scope_ref,
            state,
            requested_by_task_run_id,
            json.dumps(candidate_roles, separators=(",", ":")),
            required_role,
            requested_at,
            generation,
            created_at,
            created_at,
        ),
    )


def get_approval(
    connection: sqlite3.Connection,
    approval_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            approval_id,
            workflow_run_id,
            task_run_id,
            approval_kind,
            scope_kind,
            scope_ref,
            state,
            requested_by_task_run_id,
            candidate_roles,
            required_role,
            requested_at,
            responded_at,
            response_kind,
            response_reason,
            decided_by_actor_id,
            decided_by_actor_type,
            generation,
            created_at,
            updated_at
        FROM approvals
        WHERE approval_id = ?
        """,
        (approval_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["candidate_roles"] = json.loads(item["candidate_roles"])
    return item


def list_approvals_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            approval_id,
            workflow_run_id,
            task_run_id,
            approval_kind,
            scope_kind,
            scope_ref,
            state,
            requested_by_task_run_id,
            candidate_roles,
            required_role,
            requested_at,
            responded_at,
            response_kind,
            response_reason,
            decided_by_actor_id,
            decided_by_actor_type,
            generation,
            created_at,
            updated_at
        FROM approvals
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC, approval_id ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["candidate_roles"] = json.loads(item["candidate_roles"])
        items.append(item)
    return items


def respond_approval(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
    response_kind: str,
    response_reason: str | None,
    decided_by_actor_id: str,
    decided_by_actor_type: str,
    responded_at: str,
    updated_at: str,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        UPDATE approvals
        SET
            state = 'RESPONDED',
            response_kind = ?,
            response_reason = ?,
            decided_by_actor_id = ?,
            decided_by_actor_type = ?,
            responded_at = ?,
            generation = generation + 1,
            updated_at = ?
        WHERE approval_id = ? AND state = 'PENDING'
        """,
        (
            response_kind,
            response_reason,
            decided_by_actor_id,
            decided_by_actor_type,
            responded_at,
            updated_at,
            approval_id,
        ),
    )
    if cursor.rowcount != 1:
        return None
    return get_approval(connection, approval_id)
