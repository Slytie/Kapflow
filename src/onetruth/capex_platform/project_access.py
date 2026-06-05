from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3
from typing import Any


@dataclass(frozen=True)
class AuthorizedProject:
    project_id: str
    tenant_id: str
    domain_id: str
    project_key: str
    name: str
    state: str
    metadata_json: dict[str, Any]
    created_by_actor_id: str
    created_by_actor_type: str
    created_at: str
    updated_at: str
    caller_role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "domain_id": self.domain_id,
            "project_key": self.project_key,
            "name": self.name,
            "state": self.state,
            "metadata_json": self.metadata_json,
            "created_by_actor_id": self.created_by_actor_id,
            "created_by_actor_type": self.created_by_actor_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "caller_role": self.caller_role,
        }


@dataclass(frozen=True)
class AuthorizedProjectsResult:
    tenant_id: str
    domain_id: str
    actor_type: str
    actor_id: str
    projects: tuple[AuthorizedProject, ...]

    @property
    def project_ids(self) -> tuple[str, ...]:
        return tuple(project.project_id for project in self.projects)

    def role_for_project_id(self, project_id: str) -> str | None:
        for project in self.projects:
            if project.project_id == project_id:
                return project.caller_role
        return None

    def to_dicts(self) -> list[dict[str, Any]]:
        return [project.to_dict() for project in self.projects]


class AuthorizedProjectsQuery:
    """Direct-membership prototype for project visibility decisions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def for_actor(
        self,
        *,
        tenant_id: str,
        domain_id: str,
        actor_type: str,
        actor_id: str,
        active_only: bool = True,
    ) -> AuthorizedProjectsResult:
        state_clause = "AND cp.state = 'active'" if active_only else ""
        rows = self._connection.execute(
            f"""
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
             AND pm.tenant_id = cp.tenant_id
             AND pm.domain_id = cp.domain_id
            WHERE cp.tenant_id = ?
              AND cp.domain_id = ?
              AND pm.actor_type = ?
              AND pm.actor_id = ?
              AND pm.state = 'active'
              {state_clause}
            ORDER BY cp.project_key ASC, cp.project_id ASC
            """,
            (tenant_id, domain_id, actor_type, actor_id),
        ).fetchall()
        return AuthorizedProjectsResult(
            tenant_id=tenant_id,
            domain_id=domain_id,
            actor_type=actor_type,
            actor_id=actor_id,
            projects=tuple(_authorized_project(row) for row in rows),
        )

    def role_for_project(
        self,
        *,
        project_id: str,
        actor_type: str,
        actor_id: str,
        active_only: bool = False,
    ) -> str | None:
        state_clause = "AND cp.state = 'active'" if active_only else ""
        row = self._connection.execute(
            f"""
            SELECT pm.role
            FROM project_memberships pm
            JOIN capex_projects cp
              ON cp.project_id = pm.project_id
             AND cp.tenant_id = pm.tenant_id
             AND cp.domain_id = pm.domain_id
            WHERE pm.project_id = ?
              AND pm.actor_type = ?
              AND pm.actor_id = ?
              AND pm.state = 'active'
              {state_clause}
            """,
            (project_id, actor_type, actor_id),
        ).fetchone()
        if row is None:
            return None
        return str(row["role"])

    @staticmethod
    def visibility_sql(*, project_column: str) -> str:
        return f"""
        (
            {project_column} IS NULL
            OR EXISTS (
                SELECT 1
                FROM project_memberships pm_scope
                WHERE pm_scope.project_id = {project_column}
                  AND pm_scope.actor_type = ?
                  AND pm_scope.actor_id = ?
                  AND pm_scope.state = 'active'
            )
        )
    """

    @staticmethod
    def visibility_params(
        *,
        actor_type: str,
        actor_id: str,
    ) -> list[str]:
        return [actor_type, actor_id]


def _authorized_project(row: sqlite3.Row) -> AuthorizedProject:
    return AuthorizedProject(
        project_id=str(row["project_id"]),
        tenant_id=str(row["tenant_id"]),
        domain_id=str(row["domain_id"]),
        project_key=str(row["project_key"]),
        name=str(row["name"]),
        state=str(row["state"]),
        metadata_json=json.loads(str(row["metadata_json"])),
        created_by_actor_id=str(row["created_by_actor_id"]),
        created_by_actor_type=str(row["created_by_actor_type"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        caller_role=str(row["caller_role"]),
    )
