from __future__ import annotations

import json
import sqlite3
from typing import Any

ACTIVE_FLAG_STATES = ("open", "triage", "blocked")


def create_flag(
    connection: sqlite3.Connection,
    *,
    flag_id: str,
    workflow_run_id: str,
    tenant_id: str,
    domain_id: str,
    workflow_id: str,
    partition_key: str,
    kind: str,
    severity: str,
    state: str,
    summary: str,
    details_json: dict[str, Any],
    assigned_group: str | None,
    created_at: str,
    closed_at: str | None,
    created_by_actor_id: str,
    created_by_actor_type: str,
    source_event_id: str | None,
    dedupe_key: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO flags (
            flag_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            workflow_id,
            partition_key,
            kind,
            severity,
            state,
            summary,
            details_json,
            assigned_group,
            created_at,
            closed_at,
            created_by_actor_id,
            created_by_actor_type,
            source_event_id,
            dedupe_key,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            flag_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            workflow_id,
            partition_key,
            kind,
            severity,
            state,
            summary,
            json.dumps(details_json, separators=(",", ":")),
            assigned_group,
            created_at,
            closed_at,
            created_by_actor_id,
            created_by_actor_type,
            source_event_id,
            dedupe_key,
            created_at,
        ),
    )


def get_flag(
    connection: sqlite3.Connection,
    flag_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            flag_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            workflow_id,
            partition_key,
            kind,
            severity,
            state,
            summary,
            details_json,
            assigned_group,
            created_at,
            closed_at,
            created_by_actor_id,
            created_by_actor_type,
            source_event_id,
            dedupe_key,
            updated_at
        FROM flags
        WHERE flag_id = ?
        """,
        (flag_id,),
    ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["details_json"] = json.loads(item["details_json"])
    return item


def list_flags_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            flag_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            workflow_id,
            partition_key,
            kind,
            severity,
            state,
            summary,
            details_json,
            assigned_group,
            created_at,
            closed_at,
            created_by_actor_id,
            created_by_actor_type,
            source_event_id,
            dedupe_key,
            updated_at
        FROM flags
        WHERE workflow_run_id = ?
        ORDER BY created_at ASC, flag_id ASC
        """,
        (workflow_run_id,),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["details_json"] = json.loads(item["details_json"])
        items.append(item)
    return items


def list_open_flags_for_workflow_run(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            flag_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            workflow_id,
            partition_key,
            kind,
            severity,
            state,
            summary,
            details_json,
            assigned_group,
            created_at,
            closed_at,
            created_by_actor_id,
            created_by_actor_type,
            source_event_id,
            dedupe_key,
            updated_at
        FROM flags
        WHERE workflow_run_id = ? AND state IN (?, ?, ?)
        ORDER BY created_at ASC, flag_id ASC
        """,
        (workflow_run_id, *ACTIVE_FLAG_STATES),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["details_json"] = json.loads(item["details_json"])
        items.append(item)
    return items


def transition_flag_state(
    connection: sqlite3.Connection,
    *,
    flag_id: str,
    expected_from_state: str,
    to_state: str,
    updated_at: str,
) -> dict[str, Any] | None:
    closed_at = updated_at if to_state in {"closed", "waived"} else None
    cursor = connection.execute(
        """
        UPDATE flags
        SET
            state = ?,
            closed_at = ?,
            updated_at = ?
        WHERE flag_id = ? AND state = ?
        """,
        (
            to_state,
            closed_at,
            updated_at,
            flag_id,
            expected_from_state,
        ),
    )
    if cursor.rowcount != 1:
        return None
    return get_flag(connection, flag_id)
