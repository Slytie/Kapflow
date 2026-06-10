from __future__ import annotations

import sqlite3

from onetruth.application.handlers.capex_projects import (
    create_capex_project_command,
    grant_project_membership_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_workflow_run_command,
)
from onetruth.capex_platform.project_access import AuthorizedProjectsQuery
from onetruth.capex_platform.project_authorization import (
    rebuild_project_authorization_projections,
    refresh_project_authorization_projection,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_project_authorization import (
    RUNTIME_ACTIVATION_BLOCKED_REASON,
    RUNTIME_ACTIVATION_FEATURE_KEY,
)


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
    project_id: str = "cp-alpha",
    project_key: str = "CAPEX-A",
    state: str = "active",
) -> dict[str, object]:
    return create_capex_project_command(
        connection,
        {
            "project_id": project_id,
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "project_key": project_key,
            "name": f"{project_key} project",
            "state": state,
            "actor_id": "human:admin",
            "actor_type": "human",
            "idempotency_key": f"projection:{project_id}:create",
        },
    )


def _grant(
    connection: sqlite3.Connection,
    *,
    project_id: str = "cp-alpha",
    target_actor_id: str = "human:viewer",
    role: str = "project_viewer",
) -> dict[str, object]:
    return grant_project_membership_command(
        connection,
        {
            "project_id": project_id,
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "actor_id": "human:admin",
            "actor_type": "human",
            "target_actor_id": target_actor_id,
            "target_actor_type": "human",
            "role": role,
            "idempotency_key": f"projection:{project_id}:{target_actor_id}:{role}",
        },
    )


def test_project_creation_creates_admin_projection_and_disabled_runtime_feature() -> None:
    connection = _connection()
    try:
        result = _create_project(connection)

        membership = result["admin_membership"]
        authorization = connection.execute(
            """
            SELECT *
            FROM capex_project_authorization
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-alpha", "human", "human:admin"),
        ).fetchone()
        user_view = connection.execute(
            """
            SELECT *
            FROM capex_user_project_view
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-alpha", "human", "human:admin"),
        ).fetchone()
        feature = connection.execute(
            """
            SELECT *
            FROM capex_project_feature
            WHERE project_id = ? AND feature_key = ?
            """,
            ("cp-alpha", RUNTIME_ACTIVATION_FEATURE_KEY),
        ).fetchone()

        assert authorization is not None
        assert authorization["direct_role"] == "project_admin"
        assert authorization["effective_role"] == "project_admin"
        assert authorization["source_membership_id"] == membership[
            "project_membership_id"
        ]
        assert user_view is not None
        assert user_view["caller_role"] == "project_admin"
        assert feature is not None
        assert feature["state"] == "disabled"
        assert feature["blocked_reason"] == RUNTIME_ACTIVATION_BLOCKED_REASON
        assert AuthorizedProjectsQuery(connection).for_actor(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            actor_type="human",
            actor_id="human:admin",
        ).project_ids == ("cp-alpha",)
    finally:
        connection.close()


def test_membership_grant_refreshes_projection_and_authorized_query() -> None:
    connection = _connection()
    try:
        _create_project(connection)
        _grant(connection, role="project_contributor")

        query = AuthorizedProjectsQuery(connection)

        assert query.for_actor(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            actor_type="human",
            actor_id="human:viewer",
        ).project_ids == ("cp-alpha",)
        assert query.role_for_project(
            project_id="cp-alpha",
            actor_type="human",
            actor_id="human:viewer",
        ) == "project_contributor"
    finally:
        connection.close()


def test_inactive_source_membership_disappears_after_projection_refresh() -> None:
    connection = _connection()
    try:
        _create_project(connection)
        _grant(connection)
        connection.execute(
            """
            UPDATE project_memberships
            SET state = 'inactive'
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-alpha", "human", "human:viewer"),
        )

        refresh_project_authorization_projection(
            connection,
            project_id="cp-alpha",
        )

        assert AuthorizedProjectsQuery(connection).for_actor(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            actor_type="human",
            actor_id="human:viewer",
        ).project_ids == ()
        assert connection.execute(
            """
            SELECT COUNT(*) AS row_count
            FROM capex_project_authorization
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-alpha", "human", "human:viewer"),
        ).fetchone()["row_count"] == 0
    finally:
        connection.close()


def test_rebuild_corrects_stale_projection_rows() -> None:
    connection = _connection()
    try:
        _create_project(connection)
        _grant(connection, role="project_viewer")
        connection.execute(
            """
            UPDATE capex_project_authorization
            SET effective_role = 'project_admin'
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-alpha", "human", "human:viewer"),
        )
        connection.execute(
            """
            UPDATE capex_user_project_view
            SET caller_role = 'project_admin'
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-alpha", "human", "human:viewer"),
        )
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
            SELECT
                'cpa:stale',
                project_id,
                tenant_id,
                domain_id,
                'human',
                'human:stale',
                role,
                role,
                project_membership_id,
                'active',
                created_at,
                updated_at
            FROM project_memberships
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-alpha", "human", "human:admin"),
        )

        summary = rebuild_project_authorization_projections(connection)

        assert summary == {"projects": 1, "authorizations": 2}
        assert AuthorizedProjectsQuery(connection).role_for_project(
            project_id="cp-alpha",
            actor_type="human",
            actor_id="human:viewer",
        ) == "project_viewer"
        assert AuthorizedProjectsQuery(connection).role_for_project(
            project_id="cp-alpha",
            actor_type="human",
            actor_id="human:stale",
        ) is None
    finally:
        connection.close()


def test_visibility_sql_uses_authorization_projection_and_preserves_no_project_rows() -> None:
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
        for workflow_run_id, project_id in [
            ("wr-visible", "cp-visible"),
            ("wr-hidden", "cp-hidden"),
        ]:
            create_workflow_run_command(
                connection,
                {
                    "workflow_run_id": workflow_run_id,
                    "project_id": project_id,
                    "workflow_id": "capex.reference.v1",
                    "workflow_version": "v1",
                    "tenant_id": TENANT_ID,
                    "domain_id": DOMAIN_ID,
                    "partition_key": workflow_run_id,
                    "logical_date": "2026-06-05",
                    "activation_key": workflow_run_id,
                    "actor_id": "human:admin",
                    "actor_type": "human",
                },
            )

        visibility_sql = AuthorizedProjectsQuery.visibility_sql(
            project_column="wr.project_id",
        )

        assert "capex_project_authorization" in visibility_sql
        assert "project_memberships" in visibility_sql
        rows = connection.execute(
            """
            SELECT wr.workflow_run_id
            FROM workflow_runs wr
            WHERE wr.tenant_id = ?
              AND wr.domain_id = ?
              AND """ + visibility_sql + """
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
