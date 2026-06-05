from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.capex_project_authorization import (
    RUNTIME_ACTIVATION_BLOCKED_REASON,
    RUNTIME_ACTIVATION_FEATURE_KEY,
    clear_project_authorization_projection,
    create_project_authorization_projection,
    create_user_project_view_row,
    list_project_authorizations,
    list_project_ids_for_projection_rebuild,
    project_authorization_id,
    project_feature_id,
    upsert_project_feature,
    user_project_view_id,
)
from onetruth.infrastructure.repositories.capex_projects import (
    get_capex_project,
    list_project_memberships,
)


def refresh_project_authorization_projection(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    now_iso: str | None = None,
) -> tuple[dict[str, Any], ...]:
    now = now_iso or utc_now_iso()
    project = get_capex_project(connection, project_id)
    clear_project_authorization_projection(connection, project_id=project_id)
    if project is None:
        return ()
    ensure_project_feature_defaults(connection, project_id=project_id, now_iso=now)
    for membership in list_project_memberships(connection, project_id=project_id):
        authorization_id = project_authorization_id(
            project_id=project_id,
            actor_type=str(membership["actor_type"]),
            actor_id=str(membership["actor_id"]),
        )
        create_project_authorization_projection(
            connection,
            project_authorization_id=authorization_id,
            project_id=project_id,
            tenant_id=str(project["tenant_id"]),
            domain_id=str(project["domain_id"]),
            actor_type=str(membership["actor_type"]),
            actor_id=str(membership["actor_id"]),
            direct_role=str(membership["role"]),
            effective_role=str(membership["role"]),
            source_membership_id=str(membership["project_membership_id"]),
            state="active",
            created_at=now,
        )
        create_user_project_view_row(
            connection,
            user_project_view_id=user_project_view_id(
                project_id=project_id,
                actor_type=str(membership["actor_type"]),
                actor_id=str(membership["actor_id"]),
            ),
            tenant_id=str(project["tenant_id"]),
            domain_id=str(project["domain_id"]),
            actor_type=str(membership["actor_type"]),
            actor_id=str(membership["actor_id"]),
            project_id=project_id,
            project_key=str(project["project_key"]),
            name=str(project["name"]),
            project_state=str(project["state"]),
            metadata_json=dict(project["metadata_json"]),
            created_by_actor_id=str(project["created_by_actor_id"]),
            created_by_actor_type=str(project["created_by_actor_type"]),
            project_created_at=str(project["created_at"]),
            project_updated_at=str(project["updated_at"]),
            caller_role=str(membership["role"]),
            authorization_state="active",
            source_authorization_id=authorization_id,
            created_at=now,
        )
    return tuple(list_project_authorizations(connection, project_id=project_id))


def rebuild_project_authorization_projections(
    connection: sqlite3.Connection,
    *,
    tenant_id: str | None = None,
    domain_id: str | None = None,
) -> dict[str, int]:
    project_ids = list_project_ids_for_projection_rebuild(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    authorization_count = 0
    for project_id in project_ids:
        authorization_count += len(
            refresh_project_authorization_projection(
                connection,
                project_id=project_id,
            )
        )
    return {
        "projects": len(project_ids),
        "authorizations": authorization_count,
    }


def ensure_project_feature_defaults(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    now_iso: str | None = None,
) -> None:
    project = get_capex_project(connection, project_id)
    if project is None:
        return
    now = now_iso or utc_now_iso()
    upsert_project_feature(
        connection,
        project_feature_id=project_feature_id(
            project_id=project_id,
            feature_key=RUNTIME_ACTIVATION_FEATURE_KEY,
        ),
        project_id=project_id,
        tenant_id=str(project["tenant_id"]),
        domain_id=str(project["domain_id"]),
        feature_key=RUNTIME_ACTIVATION_FEATURE_KEY,
        state="disabled",
        blocked_reason=RUNTIME_ACTIVATION_BLOCKED_REASON,
        metadata_json={"owner_task_ref": "TASK-0563"},
        updated_at=now,
    )


__all__ = [
    "ensure_project_feature_defaults",
    "rebuild_project_authorization_projections",
    "refresh_project_authorization_projection",
]

