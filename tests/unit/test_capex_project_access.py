from __future__ import annotations

import sqlite3

import pytest

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.queries import query_workflow_runs
from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.capex_projects import (
    PROJECT_ADMIN,
    PROJECT_CONTRIBUTOR,
    PROJECT_VIEWER,
    create_capex_project_command,
    grant_project_membership_command,
    list_project_memberships_command,
    revoke_project_membership_command,
    show_capex_project_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_workflow_run_command,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _context(actor_id: str) -> RequestContext:
    return RequestContext(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_id=actor_id,
        actor_type="human",
        actor_roles=("capex_user",),
    )


def _create_project(connection: sqlite3.Connection) -> dict[str, object]:
    return create_capex_project_command(
        connection,
        {
            "project_id": "cp-unit-001",
            "project_key": "CAPEX-UNIT-001",
            "name": "Unit test project",
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "actor_id": "human:admin",
            "actor_type": "human",
            "idempotency_key": "unit:capex-project:create",
        },
    )


def _grant(
    connection: sqlite3.Connection,
    *,
    target_actor_id: str,
    role: str,
    key: str,
) -> dict[str, object]:
    return grant_project_membership_command(
        connection,
        {
            "project_id": "cp-unit-001",
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "actor_id": "human:admin",
            "actor_type": "human",
            "target_actor_id": target_actor_id,
            "target_actor_type": "human",
            "role": role,
            "idempotency_key": key,
        },
    )


def _run_payload(
    *,
    workflow_run_id: str,
    activation_key: str,
    project_id: str | None,
    actor_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "capex.intake.v1",
        "workflow_version": "v1",
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "partition_key": "CAPEX-UNIT-001",
        "logical_date": "2026-06-04",
        "activation_key": activation_key,
    }
    if project_id is not None:
        payload["project_id"] = project_id
    if actor_id is not None:
        payload["actor_id"] = actor_id
        payload["actor_type"] = "human"
    return payload


def test_project_creation_grants_creator_admin_and_emits_project_events() -> None:
    connection = _connection()
    result = _create_project(connection)

    assert result["project"]["project_id"] == "cp-unit-001"
    assert result["project"]["project_key"] == "CAPEX-UNIT-001"
    assert result["admin_membership"]["actor_id"] == "human:admin"
    assert result["admin_membership"]["role"] == PROJECT_ADMIN

    project = show_capex_project_command(
        connection,
        project_id="cp-unit-001",
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_type="human",
        actor_id="human:admin",
    )
    assert project["project_id"] == "cp-unit-001"

    memberships = list_project_memberships_command(
        connection,
        project_id="cp-unit-001",
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_type="human",
        actor_id="human:admin",
    )
    assert [(row["actor_id"], row["role"]) for row in memberships] == [
        ("human:admin", PROJECT_ADMIN)
    ]

    events = list_events(connection, limit=20)
    project_events = [
        event for event in events if str(event["event_type"]).startswith("capex.project")
    ]
    assert [event["event_type"] for event in project_events] == [
        "capex.project.created",
        "capex.project_membership.granted",
    ]
    assert all(event["project_id"] == "cp-unit-001" for event in project_events)


def test_project_membership_revoke_is_audited_and_idempotent() -> None:
    connection = _connection()
    _create_project(connection)
    grant = _grant(
        connection,
        target_actor_id="human:viewer",
        role=PROJECT_VIEWER,
        key="unit:capex-project:grant-revoke-viewer",
    )
    membership_id = str(grant["membership"]["project_membership_id"])

    revoked = revoke_project_membership_command(
        connection,
        {
            "project_id": "cp-unit-001",
            "project_membership_id": membership_id,
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "actor_id": "human:admin",
            "actor_type": "human",
            "idempotency_key": "unit:capex-project:revoke-viewer",
        },
        include_receipt=True,
    )
    replay = revoke_project_membership_command(
        connection,
        {
            "project_id": "cp-unit-001",
            "project_membership_id": membership_id,
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "actor_id": "human:admin",
            "actor_type": "human",
            "idempotency_key": "unit:capex-project:revoke-viewer",
        },
        include_receipt=True,
    )

    assert revoked["idempotent_replay"] is False
    assert replay["idempotent_replay"] is True
    assert revoked["result"]["membership"]["state"] == "revoked"
    assert replay["result"]["membership"] == revoked["result"]["membership"]

    events = list_events(connection, limit=20)
    revoke_events = [
        event
        for event in events
        if event["event_type"] == "capex.project_membership.revoked"
    ]
    assert len(revoke_events) == 1
    assert revoke_events[0]["payload"]["previous_role"] == PROJECT_VIEWER
    assert revoke_events[0]["project_id"] == "cp-unit-001"


def test_project_roles_gate_project_bound_workflow_run_creation() -> None:
    connection = _connection()
    _create_project(connection)
    _grant(
        connection,
        target_actor_id="human:viewer",
        role=PROJECT_VIEWER,
        key="unit:capex-project:grant-viewer",
    )
    _grant(
        connection,
        target_actor_id="human:contributor",
        role=PROJECT_CONTRIBUTOR,
        key="unit:capex-project:grant-contributor",
    )

    with pytest.raises(CommandError) as viewer_denied:
        create_workflow_run_command(
            connection,
            _run_payload(
                workflow_run_id="wr-viewer-denied",
                activation_key="viewer-denied",
                project_id="cp-unit-001",
                actor_id="human:viewer",
            ),
        )
    assert viewer_denied.value.code == "capex_project_access_forbidden"

    with pytest.raises(CommandError) as outsider_hidden:
        create_workflow_run_command(
            connection,
            _run_payload(
                workflow_run_id="wr-outsider-hidden",
                activation_key="outsider-hidden",
                project_id="cp-unit-001",
                actor_id="human:outsider",
            ),
        )
    assert outsider_hidden.value.code == "capex_project_not_found"

    workflow_run = create_workflow_run_command(
        connection,
        _run_payload(
            workflow_run_id="wr-contributor-created",
            activation_key="contributor-created",
            project_id="cp-unit-001",
            actor_id="human:contributor",
        ),
    )
    assert workflow_run["project_id"] == "cp-unit-001"


def test_project_bound_rows_are_hidden_from_same_scope_non_members() -> None:
    connection = _connection()
    _create_project(connection)
    _grant(
        connection,
        target_actor_id="human:viewer",
        role=PROJECT_VIEWER,
        key="unit:capex-project:grant-viewer-for-list",
    )
    create_workflow_run_command(
        connection,
        _run_payload(
            workflow_run_id="wr-no-project",
            activation_key="no-project",
            project_id=None,
        ),
    )
    create_workflow_run_command(
        connection,
        _run_payload(
            workflow_run_id="wr-project",
            activation_key="project",
            project_id="cp-unit-001",
            actor_id="human:admin",
        ),
    )

    page = Page(limit=50, offset=0)
    outsider_rows = query_workflow_runs(
        connection,
        context=_context("human:outsider"),
        workflow_id=None,
        project_id=None,
        state=None,
        page=page,
    )
    assert [row["workflow_run_id"] for row in outsider_rows] == ["wr-no-project"]

    viewer_rows = query_workflow_runs(
        connection,
        context=_context("human:viewer"),
        workflow_id=None,
        project_id=None,
        state=None,
        page=page,
    )
    assert [row["workflow_run_id"] for row in viewer_rows] == [
        "wr-no-project",
        "wr-project",
    ]

    project_rows = query_workflow_runs(
        connection,
        context=_context("human:viewer"),
        workflow_id=None,
        project_id="cp-unit-001",
        state=None,
        page=page,
    )
    assert [row["workflow_run_id"] for row in project_rows] == ["wr-project"]
