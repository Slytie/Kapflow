from __future__ import annotations

import sqlite3

import pytest

from onetruth.api.dependencies import RequestContext
from onetruth.api.errors import ApiError
from onetruth.api.project_scope import (
    assert_workflow_run_in_project,
    attach_project_id,
    caller_project_role,
    decorate_project_payload,
    parse_project_child_ref,
    require_project_viewer,
    rows_with_project_id,
    with_project_query,
)
from onetruth.application.handlers.capex_projects import (
    create_capex_project_command,
    grant_project_membership_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.infrastructure.events.event_store import create_sqlite_substrate

TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-helper-001"
OTHER_PROJECT_ID = "cp-helper-002"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _context(actor_id: str) -> RequestContext:
    return RequestContext(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_type="human",
        actor_id=actor_id,
        actor_roles=("capex_user",),
    )


def _seed(connection: sqlite3.Connection) -> None:
    for project_id in (PROJECT_ID, OTHER_PROJECT_ID):
        create_capex_project_command(
            connection,
            {
                "project_id": project_id,
                "tenant_id": TENANT_ID,
                "domain_id": DOMAIN_ID,
                "project_key": project_id.upper(),
                "name": f"{project_id} project",
                "actor_id": "human:admin",
                "actor_type": "human",
                "idempotency_key": f"helper:{project_id}:create",
            },
        )
        grant_project_membership_command(
            connection,
            {
                "project_id": project_id,
                "tenant_id": TENANT_ID,
                "domain_id": DOMAIN_ID,
                "actor_id": "human:admin",
                "actor_type": "human",
                "target_actor_id": "human:viewer",
                "target_actor_type": "human",
                "role": "project_viewer",
                "idempotency_key": f"helper:{project_id}:viewer",
            },
        )
    create_workflow_run_command(
        connection,
        {
            "workflow_run_id": "wr-helper-001",
            "project_id": PROJECT_ID,
            "workflow_id": "capex.intake.v1",
            "workflow_version": "v1",
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "partition_key": "CAPEX-HELPER",
            "logical_date": "2026-06-04",
            "activation_key": "helper-run",
            "actor_id": "human:admin",
            "actor_type": "human",
        },
    )


def test_project_scope_helpers_resolve_roles_and_preserve_payload_shapes() -> None:
    connection = _connection()
    try:
        _seed(connection)
        context = _context("human:viewer")

        project = require_project_viewer(connection, context=context, project_id=PROJECT_ID)
        assert project["project_id"] == PROJECT_ID
        assert caller_project_role(connection, context=context, project_id=PROJECT_ID) == "project_viewer"

        assert parse_project_child_ref(f"{PROJECT_ID}/workflow-runs/wr-helper-001", "workflow-runs") == (
            PROJECT_ID,
            "wr-helper-001",
        )
        assert with_project_query({"state": "OPEN"}, PROJECT_ID) == {
            "state": "OPEN",
            "project_id": PROJECT_ID,
        }
        assert decorate_project_payload(
            {"workflow_runs": []},
            command="api.example",
            project_id=PROJECT_ID,
        ) == {
            "project_id": PROJECT_ID,
            "workflow_runs": [],
            "command": "api.example",
        }
        assert rows_with_project_id([{"id": "row-1"}], PROJECT_ID) == [
            {"id": "row-1", "project_id": PROJECT_ID}
        ]
        payload = {"items": [{"id": "row-2"}]}
        attach_project_id(payload, "items", PROJECT_ID)
        assert payload["items"] == [{"id": "row-2", "project_id": PROJECT_ID}]
    finally:
        connection.close()


def test_project_scope_helpers_hide_non_members_and_project_mismatches() -> None:
    connection = _connection()
    try:
        _seed(connection)
        outsider = _context("human:outsider")
        viewer = _context("human:viewer")

        with pytest.raises(ApiError) as hidden_project:
            require_project_viewer(connection, context=outsider, project_id=PROJECT_ID)
        assert hidden_project.value.status_code == 404
        assert hidden_project.value.code == "capex_project_not_found"

        with pytest.raises(ApiError) as mismatched_run:
            assert_workflow_run_in_project(
                connection,
                context=viewer,
                project_id=OTHER_PROJECT_ID,
                workflow_run_id="wr-helper-001",
                not_found_code="workflow_run_not_found",
                details={"workflow_run_id": "wr-helper-001"},
            )
        assert mismatched_run.value.status_code == 404
        assert mismatched_run.value.code == "workflow_run_not_found"
    finally:
        connection.close()
