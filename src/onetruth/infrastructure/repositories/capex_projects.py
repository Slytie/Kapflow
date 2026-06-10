from __future__ import annotations

import json
import sqlite3
from typing import Any


PROJECT_COLUMNS = """
    project_id,
    tenant_id,
    domain_id,
    project_key,
    name,
    state,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    created_at,
    updated_at
"""

MEMBERSHIP_COLUMNS = """
    project_membership_id,
    project_id,
    tenant_id,
    domain_id,
    actor_type,
    actor_id,
    role,
    state,
    granted_by_actor_id,
    granted_by_actor_type,
    created_at,
    updated_at
"""


def create_capex_project(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    project_key: str,
    name: str,
    state: str,
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO capex_projects (
            project_id,
            tenant_id,
            domain_id,
            project_key,
            name,
            state,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            tenant_id,
            domain_id,
            project_key,
            name,
            state,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            created_at,
        ),
    )


def get_capex_project(
    connection: sqlite3.Connection,
    project_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {PROJECT_COLUMNS}
        FROM capex_projects
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()
    return _project_row(row)


def get_capex_project_by_key(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {PROJECT_COLUMNS}
        FROM capex_projects
        WHERE tenant_id = ?
          AND domain_id = ?
          AND project_key = ?
        """,
        (tenant_id, domain_id, project_key),
    ).fetchone()
    return _project_row(row)


def list_capex_projects_for_actor(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            cp.project_id,
            cp.tenant_id,
            cp.domain_id,
            cp.project_key,
            cp.name,
            cp.state,
            cp.metadata_json,
            cp.created_by_actor_id,
            cp.created_by_actor_type,
            cp.created_at,
            cp.updated_at,
            pm.role AS caller_role
        FROM capex_projects cp
        JOIN project_memberships pm
          ON pm.project_id = cp.project_id
        WHERE cp.tenant_id = ?
          AND cp.domain_id = ?
          AND pm.actor_type = ?
          AND pm.actor_id = ?
          AND pm.state = 'active'
          AND cp.state = 'active'
        ORDER BY cp.project_key ASC, cp.project_id ASC
        """,
        (tenant_id, domain_id, actor_type, actor_id),
    ).fetchall()
    return [_project_row(row) for row in rows if row is not None]


def create_project_membership(
    connection: sqlite3.Connection,
    *,
    project_membership_id: str,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
    role: str,
    state: str,
    granted_by_actor_id: str,
    granted_by_actor_type: str,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO project_memberships (
            project_membership_id,
            project_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            role,
            state,
            granted_by_actor_id,
            granted_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_membership_id,
            project_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            role,
            state,
            granted_by_actor_id,
            granted_by_actor_type,
            created_at,
            created_at,
        ),
    )


def update_project_membership_grant(
    connection: sqlite3.Connection,
    *,
    project_membership_id: str,
    role: str,
    state: str,
    granted_by_actor_id: str,
    granted_by_actor_type: str,
    updated_at: str,
) -> None:
    connection.execute(
        """
        UPDATE project_memberships
        SET role = ?,
            state = ?,
            granted_by_actor_id = ?,
            granted_by_actor_type = ?,
            updated_at = ?
        WHERE project_membership_id = ?
        """,
        (
            role,
            state,
            granted_by_actor_id,
            granted_by_actor_type,
            updated_at,
            project_membership_id,
        ),
    )


def revoke_project_membership(
    connection: sqlite3.Connection,
    *,
    project_membership_id: str,
    updated_at: str,
) -> None:
    connection.execute(
        """
        UPDATE project_memberships
        SET state = 'revoked',
            updated_at = ?
        WHERE project_membership_id = ?
        """,
        (updated_at, project_membership_id),
    )


def get_project_membership(
    connection: sqlite3.Connection,
    project_membership_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {MEMBERSHIP_COLUMNS}
        FROM project_memberships
        WHERE project_membership_id = ?
        """,
        (project_membership_id,),
    ).fetchone()
    return _membership_row(row)


def get_any_project_membership_for_actor(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    actor_type: str,
    actor_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {MEMBERSHIP_COLUMNS}
        FROM project_memberships
        WHERE project_id = ?
          AND actor_type = ?
          AND actor_id = ?
        """,
        (project_id, actor_type, actor_id),
    ).fetchone()
    return _membership_row(row)


def get_project_membership_for_actor(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    actor_type: str,
    actor_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {MEMBERSHIP_COLUMNS}
        FROM project_memberships
        WHERE project_id = ?
          AND actor_type = ?
          AND actor_id = ?
          AND state = 'active'
        """,
        (project_id, actor_type, actor_id),
    ).fetchone()
    return _membership_row(row)


def list_project_memberships(
    connection: sqlite3.Connection,
    *,
    project_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {MEMBERSHIP_COLUMNS}
        FROM project_memberships
        WHERE project_id = ?
          AND state = 'active'
        ORDER BY actor_type ASC, actor_id ASC
        """,
        (project_id,),
    ).fetchall()
    return [_membership_row(row) for row in rows if row is not None]


def _project_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(item["metadata_json"])
    return item


def _membership_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)
