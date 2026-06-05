from __future__ import annotations

import sqlite3

from onetruth.application.handlers.capex_projects import (
    create_capex_project_command,
    grant_project_membership_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.application.services.capex_project_access import (
    project_membership_filter_params,
    project_membership_filter_sql,
)
from onetruth.capex_platform.project_access import AuthorizedProjectsQuery
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _create_project(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    project_key: str,
    state: str = "active",
    tenant_id: str = TENANT_ID,
    domain_id: str = DOMAIN_ID,
) -> None:
    create_capex_project_command(
        connection,
        {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "project_key": project_key,
            "name": f"{project_key} project",
            "state": state,
            "actor_id": "human:admin",
            "actor_type": "human",
            "idempotency_key": f"authorized-projects:{project_id}:create",
        },
    )


def _grant(
    connection: sqlite3.Connection,
    *,
    project_id: str,
    target_actor_id: str,
    role: str,
    tenant_id: str = TENANT_ID,
    domain_id: str = DOMAIN_ID,
) -> None:
    grant_project_membership_command(
        connection,
        {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "actor_id": "human:admin",
            "actor_type": "human",
            "target_actor_id": target_actor_id,
            "target_actor_type": "human",
            "role": role,
            "idempotency_key": f"authorized-projects:{project_id}:{target_actor_id}",
        },
    )


def test_authorized_projects_query_returns_active_memberships_deterministically() -> None:
    connection = _connection()
    try:
        _create_project(connection, project_id="cp-b", project_key="CAPEX-B")
        _create_project(connection, project_id="cp-a", project_key="CAPEX-A")
        _create_project(
            connection,
            project_id="cp-archived",
            project_key="CAPEX-C",
            state="archived",
        )
        _create_project(
            connection,
            project_id="cp-other-tenant",
            project_key="CAPEX-Z",
            tenant_id="tenant-b",
        )
        _grant(
            connection,
            project_id="cp-b",
            target_actor_id="human:viewer",
            role="project_viewer",
        )
        _grant(
            connection,
            project_id="cp-a",
            target_actor_id="human:viewer",
            role="project_contributor",
        )
        _grant(
            connection,
            project_id="cp-archived",
            target_actor_id="human:viewer",
            role="project_admin",
        )
        _grant(
            connection,
            project_id="cp-other-tenant",
            target_actor_id="human:viewer",
            role="project_admin",
            tenant_id="tenant-b",
        )

        result = AuthorizedProjectsQuery(connection).for_actor(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            actor_type="human",
            actor_id="human:viewer",
        )

        assert result.project_ids == ("cp-a", "cp-b")
        assert result.role_for_project_id("cp-a") == "project_contributor"
        assert result.to_dicts()[0]["caller_role"] == "project_contributor"
        assert result.to_dicts()[0]["metadata_json"] == {}

        with_inactive = AuthorizedProjectsQuery(connection).for_actor(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            actor_type="human",
            actor_id="human:viewer",
            active_only=False,
        )
        assert with_inactive.project_ids == ("cp-a", "cp-b", "cp-archived")
    finally:
        connection.close()


def test_authorized_projects_query_role_lookup_and_non_members_fail_closed() -> None:
    connection = _connection()
    try:
        _create_project(connection, project_id="cp-visible", project_key="CAPEX-V")
        _create_project(
            connection,
            project_id="cp-archived",
            project_key="CAPEX-X",
            state="archived",
        )
        _grant(
            connection,
            project_id="cp-visible",
            target_actor_id="human:viewer",
            role="project_viewer",
        )
        _grant(
            connection,
            project_id="cp-archived",
            target_actor_id="human:viewer",
            role="project_admin",
        )

        query = AuthorizedProjectsQuery(connection)

        assert query.role_for_project(
            project_id="cp-visible",
            actor_type="human",
            actor_id="human:viewer",
        ) == "project_viewer"
        assert query.role_for_project(
            project_id="cp-archived",
            actor_type="human",
            actor_id="human:viewer",
            active_only=True,
        ) is None
        assert query.for_actor(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            actor_type="human",
            actor_id="human:outsider",
        ).project_ids == ()
    finally:
        connection.close()


def test_authorized_projects_visibility_sql_preserves_no_project_rows() -> None:
    connection = _connection()
    try:
        _create_project(connection, project_id="cp-visible", project_key="CAPEX-V")
        _create_project(connection, project_id="cp-hidden", project_key="CAPEX-H")
        _grant(
            connection,
            project_id="cp-visible",
            target_actor_id="human:viewer",
            role="project_viewer",
        )
        create_workflow_run_command(
            connection,
            {
                "workflow_run_id": "wr-no-project",
                "workflow_id": "capex.reference.v1",
                "workflow_version": "v1",
                "tenant_id": TENANT_ID,
                "domain_id": DOMAIN_ID,
                "partition_key": "NO-PROJECT",
                "logical_date": "2026-06-05",
                "activation_key": "no-project",
            },
        )
        create_workflow_run_command(
            connection,
            {
                "workflow_run_id": "wr-visible",
                "project_id": "cp-visible",
                "workflow_id": "capex.reference.v1",
                "workflow_version": "v1",
                "tenant_id": TENANT_ID,
                "domain_id": DOMAIN_ID,
                "partition_key": "VISIBLE",
                "logical_date": "2026-06-05",
                "activation_key": "visible",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
        )
        create_workflow_run_command(
            connection,
            {
                "workflow_run_id": "wr-hidden",
                "project_id": "cp-hidden",
                "workflow_id": "capex.reference.v1",
                "workflow_version": "v1",
                "tenant_id": TENANT_ID,
                "domain_id": DOMAIN_ID,
                "partition_key": "HIDDEN",
                "logical_date": "2026-06-05",
                "activation_key": "hidden",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
        )

        assert project_membership_filter_sql(
            project_column="wr.project_id"
        ) == AuthorizedProjectsQuery.visibility_sql(project_column="wr.project_id")
        assert project_membership_filter_params(
            actor_type="human",
            actor_id="human:viewer",
        ) == AuthorizedProjectsQuery.visibility_params(
            actor_type="human",
            actor_id="human:viewer",
        )

        rows = connection.execute(
            """
            SELECT wr.workflow_run_id
            FROM workflow_runs wr
            WHERE wr.tenant_id = ?
              AND wr.domain_id = ?
              AND """ + AuthorizedProjectsQuery.visibility_sql(
                project_column="wr.project_id"
            ) + """
            ORDER BY wr.workflow_run_id ASC
            """,
            (
                TENANT_ID,
                DOMAIN_ID,
                *AuthorizedProjectsQuery.visibility_params(
                    actor_type="human",
                    actor_id="human:viewer",
                ),
            ),
        ).fetchall()

        assert [row["workflow_run_id"] for row in rows] == [
            "wr-no-project",
            "wr-visible",
        ]
    finally:
        connection.close()
