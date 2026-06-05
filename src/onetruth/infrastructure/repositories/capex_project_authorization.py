from __future__ import annotations

import json
import sqlite3
from typing import Any


PROJECT_AUTHORIZATION_COLUMNS = """
    project_authorization_id,
    project_id,
    tenant_id,
    domain_id,
    actor_type,
    actor_id,
    direct_role,
    effective_role,
    source_membership_id,
    state,
    created_at,
    updated_at
"""

PROJECT_FEATURE_COLUMNS = """
    project_feature_id,
    project_id,
    tenant_id,
    domain_id,
    feature_key,
    state,
    blocked_reason,
    metadata_json,
    created_at,
    updated_at
"""

USER_PROJECT_VIEW_COLUMNS = """
    user_project_view_id,
    tenant_id,
    domain_id,
    actor_type,
    actor_id,
    project_id,
    project_key,
    name,
    project_state,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    project_created_at,
    project_updated_at,
    caller_role,
    authorization_state,
    source_authorization_id,
    created_at,
    updated_at
"""

RUNTIME_ACTIVATION_FEATURE_KEY = "capex.runtime_activation"
RUNTIME_ACTIVATION_BLOCKED_REASON = (
    "capex_runtime_activation_blocked_by_future_gates"
)


def project_authorization_id(
    *,
    project_id: str,
    actor_type: str,
    actor_id: str,
) -> str:
    return f"cpa:{project_id}:{actor_type}:{actor_id}"


def project_feature_id(
    *,
    project_id: str,
    feature_key: str,
) -> str:
    return f"cpf:{project_id}:{feature_key}"


def user_project_view_id(
    *,
    project_id: str,
    actor_type: str,
    actor_id: str,
) -> str:
    return f"cpuv:{project_id}:{actor_type}:{actor_id}"


def clear_project_authorization_projection(
    connection: sqlite3.Connection,
    *,
    project_id: str,
) -> None:
    connection.execute(
        """
        DELETE FROM capex_user_project_view
        WHERE project_id = ?
        """,
        (project_id,),
    )
    connection.execute(
        """
        DELETE FROM capex_project_authorization
        WHERE project_id = ?
        """,
        (project_id,),
    )


def create_project_authorization_projection(
    connection: sqlite3.Connection,
    *,
    project_authorization_id: str,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
    direct_role: str,
    effective_role: str,
    source_membership_id: str,
    state: str,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO capex_project_authorization (
            project_authorization_id,
            project_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            direct_role,
            effective_role,
            source_membership_id,
            state,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_authorization_id,
            project_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            direct_role,
            effective_role,
            source_membership_id,
            state,
            created_at,
            created_at,
        ),
    )


def create_user_project_view_row(
    connection: sqlite3.Connection,
    *,
    user_project_view_id: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
    project_id: str,
    project_key: str,
    name: str,
    project_state: str,
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    project_created_at: str,
    project_updated_at: str,
    caller_role: str,
    authorization_state: str,
    source_authorization_id: str,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO capex_user_project_view (
            user_project_view_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            project_id,
            project_key,
            name,
            project_state,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            project_created_at,
            project_updated_at,
            caller_role,
            authorization_state,
            source_authorization_id,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_project_view_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            project_id,
            project_key,
            name,
            project_state,
            json.dumps(metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            project_created_at,
            project_updated_at,
            caller_role,
            authorization_state,
            source_authorization_id,
            created_at,
            created_at,
        ),
    )


def upsert_project_feature(
    connection: sqlite3.Connection,
    *,
    project_feature_id: str,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    feature_key: str,
    state: str,
    blocked_reason: str | None,
    metadata_json: dict[str, Any],
    updated_at: str,
) -> None:
    metadata_payload = json.dumps(
        metadata_json,
        separators=(",", ":"),
        sort_keys=True,
    )
    connection.execute(
        """
        INSERT INTO capex_project_feature (
            project_feature_id,
            project_id,
            tenant_id,
            domain_id,
            feature_key,
            state,
            blocked_reason,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, feature_key) DO UPDATE SET
            tenant_id = excluded.tenant_id,
            domain_id = excluded.domain_id,
            state = excluded.state,
            blocked_reason = excluded.blocked_reason,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            project_feature_id,
            project_id,
            tenant_id,
            domain_id,
            feature_key,
            state,
            blocked_reason,
            metadata_payload,
            updated_at,
            updated_at,
        ),
    )


def get_project_feature(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    feature_key: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {PROJECT_FEATURE_COLUMNS}
        FROM capex_project_feature
        WHERE project_id = ?
          AND feature_key = ?
        """,
        (project_id, feature_key),
    ).fetchone()
    return _feature_row(row)


def list_project_authorizations(
    connection: sqlite3.Connection,
    *,
    project_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {PROJECT_AUTHORIZATION_COLUMNS}
        FROM capex_project_authorization
        WHERE project_id = ?
        ORDER BY actor_type ASC, actor_id ASC
        """,
        (project_id,),
    ).fetchall()
    return [_row(row) for row in rows]


def list_user_project_views_for_actor(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    state_clause = "AND project_state = 'active'" if active_only else ""
    rows = connection.execute(
        f"""
        SELECT {USER_PROJECT_VIEW_COLUMNS}
        FROM capex_user_project_view
        WHERE tenant_id = ?
          AND domain_id = ?
          AND actor_type = ?
          AND actor_id = ?
          AND authorization_state = 'active'
          {state_clause}
        ORDER BY project_key ASC, project_id ASC
        """,
        (tenant_id, domain_id, actor_type, actor_id),
    ).fetchall()
    return [_view_row(row) for row in rows]


def list_project_ids_for_projection_rebuild(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None = None,
    domain_id: str | None = None,
) -> list[str]:
    clauses: list[str] = []
    params: list[str] = []
    if tenant_id is not None:
        clauses.append("tenant_id = ?")
        params.append(tenant_id)
    if domain_id is not None:
        clauses.append("domain_id = ?")
        params.append(domain_id)
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT project_id
        FROM capex_projects
        {where_clause}
        ORDER BY tenant_id ASC, domain_id ASC, project_key ASC, project_id ASC
        """,
        tuple(params),
    ).fetchall()
    return [str(row["project_id"]) for row in rows]


def _feature_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = _row(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _view_row(row: sqlite3.Row) -> dict[str, Any]:
    item = _row(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)
