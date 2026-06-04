from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.capex_projects import (
    create_capex_project_command,
    grant_project_membership_command,
    list_capex_projects_command,
    list_project_memberships_command,
    show_capex_project_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_workflow_run_command,
)
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.errors import api_error_from_command, api_error_from_duplicate_idempotency


def list_capex_projects_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    page: Page,
) -> dict[str, Any]:
    rows = list_capex_projects_command(
        connection,
        tenant_id=context.tenant_id,
        domain_id=context.domain_id,
        actor_type=context.actor_type,
        actor_id=context.actor_id,
    )
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.capex.projects.list",
        "projects": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def create_capex_project_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    payload: dict[str, Any],
) -> dict[str, Any]:
    command_payload = {
        **payload,
        "tenant_id": context.tenant_id,
        "domain_id": context.domain_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
    }
    try:
        result = create_capex_project_command(
            connection,
            command_payload,
            include_receipt=True,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.capex.projects.create",
        "project": result["result"]["project"],
        "admin_membership": result["result"]["admin_membership"],
        "idempotent_replay": result["idempotent_replay"],
        "receipt": result["receipt"],
    }


def get_capex_project_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
) -> dict[str, Any]:
    try:
        project = show_capex_project_command(
            connection,
            project_id=project_id,
            tenant_id=context.tenant_id,
            domain_id=context.domain_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.capex.projects.detail",
        "project": project,
    }


def list_project_memberships_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    page: Page,
) -> dict[str, Any]:
    try:
        rows = list_project_memberships_command(
            connection,
            project_id=project_id,
            tenant_id=context.tenant_id,
            domain_id=context.domain_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    rows = rows[page.offset : page.offset + page.limit]
    return {
        "command": "api.capex.projects.memberships.list",
        "project_id": project_id,
        "memberships": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def grant_project_membership_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    command_payload = {
        **payload,
        "project_id": project_id,
        "tenant_id": context.tenant_id,
        "domain_id": context.domain_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "target_actor_id": payload.get("actor_id"),
        "target_actor_type": payload.get("actor_type"),
    }
    try:
        result = grant_project_membership_command(
            connection,
            command_payload,
            include_receipt=True,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.capex.projects.memberships.grant",
        "project": result["result"]["project"],
        "membership": result["result"]["membership"],
        "idempotent_replay": result["idempotent_replay"],
        "receipt": result["receipt"],
    }


def create_project_workflow_run_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    command_payload = {
        **payload,
        "tenant_id": context.tenant_id,
        "domain_id": context.domain_id,
        "project_id": project_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
    }
    try:
        result = create_workflow_run_command(
            connection,
            command_payload,
            include_receipt=True,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.capex.projects.workflow_runs.create",
        "project_id": project_id,
        "workflow_run": result["result"],
        "idempotent_replay": result["idempotent_replay"],
        "receipt": result["receipt"],
    }
