from __future__ import annotations

import sqlite3
from typing import Any, Iterable

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.capex_platform.project_access import AuthorizedProjectsQuery
from onetruth.infrastructure.repositories.capex_projects import (
    get_capex_project,
)

PROJECT_VIEWER = "project_viewer"
PROJECT_CONTRIBUTOR = "project_contributor"
PROJECT_ADMIN = "project_admin"
PROJECT_ROLES = (PROJECT_VIEWER, PROJECT_CONTRIBUTOR, PROJECT_ADMIN)
PROJECT_ROLE_RANKS = {
    PROJECT_VIEWER: 1,
    PROJECT_CONTRIBUTOR: 2,
    PROJECT_ADMIN: 3,
}


def validate_project_role(role: str) -> str:
    normalized = str(role).strip()
    if normalized not in PROJECT_ROLE_RANKS:
        raise CommandError(
            code="invalid_project_role",
            message=f"unsupported project role: {normalized}",
            details={"allowed_roles": list(PROJECT_ROLES)},
        )
    return normalized


def project_role_rank(role: str | None) -> int:
    if role is None:
        return 0
    return PROJECT_ROLE_RANKS.get(str(role), 0)


def has_project_role(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    actor_type: str,
    actor_id: str,
    min_role: str,
) -> bool:
    role = AuthorizedProjectsQuery(connection).role_for_project(
        project_id=project_id,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return project_role_rank(role) >= project_role_rank(min_role)


def require_project_access(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
    min_role: str,
    not_found_code: str = "capex_project_not_found",
) -> dict[str, Any]:
    validate_project_role(min_role)
    project = get_capex_project(connection, project_id)
    if (
        project is None
        or str(project["tenant_id"]) != tenant_id
        or str(project["domain_id"]) != domain_id
    ):
        raise CommandError(
            code=not_found_code,
            message="CAPEX project not found",
            details={"project_id": project_id},
        )
    if not has_project_role(
        connection,
        project_id=project_id,
        actor_type=actor_type,
        actor_id=actor_id,
        min_role=min_role,
    ):
        raise CommandError(
            code=not_found_code,
            message="CAPEX project not found",
            details={"project_id": project_id},
        )
    return project


def require_project_membership_role(
    connection: sqlite3.Connection,
    *,
    project: dict[str, Any],
    actor_type: str,
    actor_id: str,
    min_role: str,
    denied_code: str = "capex_project_access_forbidden",
) -> None:
    validate_project_role(min_role)
    if has_project_role(
        connection,
        project_id=str(project["project_id"]),
        actor_type=actor_type,
        actor_id=actor_id,
        min_role=min_role,
    ):
        return
    raise CommandError(
        code=denied_code,
        message="actor does not have the required project role",
        details={
            "project_id": str(project["project_id"]),
            "required_role": min_role,
        },
    )


def project_membership_filter_sql(*, project_column: str) -> str:
    return AuthorizedProjectsQuery.visibility_sql(project_column=project_column)


def project_membership_filter_params(
    *,
    actor_type: str,
    actor_id: str,
) -> list[str]:
    return AuthorizedProjectsQuery.visibility_params(
        actor_type=actor_type,
        actor_id=actor_id,
    )


def filter_project_authorized_rows(
    connection: sqlite3.Connection,
    *,
    rows: Iterable[dict[str, Any]],
    actor_type: str,
    actor_id: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in rows:
        project_id = row.get("project_id")
        if project_id is None:
            results.append(row)
            continue
        if has_project_role(
            connection,
            project_id=str(project_id),
            actor_type=actor_type,
            actor_id=actor_id,
            min_role=PROJECT_VIEWER,
        ):
            results.append(row)
    return results
