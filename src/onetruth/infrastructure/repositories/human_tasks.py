from __future__ import annotations

import json
import sqlite3
from typing import Any


def create_human_task(
    connection: sqlite3.Connection,
    *,
    human_task_id: str,
    workflow_run_id: str,
    task_run_id: str,
    task_kind: str,
    state: str,
    candidate_roles: list[str],
    owner_role: str | None,
    due_at: str | None,
    escalation_at: str | None,
    generation: int,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO human_tasks (
            human_task_id,
            workflow_run_id,
            task_run_id,
            task_kind,
            state,
            candidate_roles,
            owner_role,
            due_at,
            escalation_at,
            generation,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            human_task_id,
            workflow_run_id,
            task_run_id,
            task_kind,
            state,
            json.dumps(candidate_roles, separators=(",", ":")),
            owner_role,
            due_at,
            escalation_at,
            generation,
            created_at,
            created_at,
        ),
    )


def get_human_task(
    connection: sqlite3.Connection,
    human_task_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            human_task_id,
            workflow_run_id,
            task_run_id,
            task_kind,
            state,
            candidate_roles,
            owner_role,
            assignee_actor_id,
            assignee_actor_type,
            due_at,
            escalation_at,
            lease_version,
            claimed_at,
            claimed_until,
            linked_approval_id,
            reopen_count,
            generation,
            created_at,
            updated_at
        FROM human_tasks
        WHERE human_task_id = ?
        """,
        (human_task_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["candidate_roles"] = json.loads(item["candidate_roles"])
    return item


def list_human_tasks_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            human_task_id,
            workflow_run_id,
            task_run_id,
            task_kind,
            state,
            candidate_roles,
            owner_role,
            assignee_actor_id,
            assignee_actor_type,
            due_at,
            escalation_at,
            lease_version,
            claimed_at,
            claimed_until,
            linked_approval_id,
            reopen_count,
            generation,
            created_at,
            updated_at
        FROM human_tasks
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC, human_task_id ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["candidate_roles"] = json.loads(item["candidate_roles"])
        items.append(item)
    return items


def claim_human_task(
    connection: sqlite3.Connection,
    *,
    human_task_id: str,
    actor_id: str,
    actor_type: str,
    claimed_at: str,
    claimed_until: str,
    updated_at: str,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        UPDATE human_tasks
        SET
            state = 'CLAIMED',
            assignee_actor_id = ?,
            assignee_actor_type = ?,
            lease_version = lease_version + 1,
            claimed_at = ?,
            claimed_until = ?,
            updated_at = ?
        WHERE human_task_id = ? AND state = 'OPEN'
        """,
        (
            actor_id,
            actor_type,
            claimed_at,
            claimed_until,
            updated_at,
            human_task_id,
        ),
    )
    if cursor.rowcount != 1:
        return None
    return get_human_task(connection, human_task_id)


def complete_human_task(
    connection: sqlite3.Connection,
    *,
    human_task_id: str,
    actor_id: str,
    actor_type: str,
    updated_at: str,
) -> dict[str, Any] | None:
    cursor = connection.execute(
        """
        UPDATE human_tasks
        SET
            state = 'COMPLETED',
            updated_at = ?,
            claimed_until = NULL
        WHERE
            human_task_id = ?
            AND state = 'CLAIMED'
            AND assignee_actor_id = ?
            AND assignee_actor_type = ?
        """,
        (
            updated_at,
            human_task_id,
            actor_id,
            actor_type,
        ),
    )
    if cursor.rowcount != 1:
        return None
    return get_human_task(connection, human_task_id)

