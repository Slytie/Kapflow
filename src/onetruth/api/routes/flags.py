from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.flags import (
    transition_flag_state_command,
)
from onetruth.application.read_commands import show_flag_command
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
from onetruth.api.queries import query_flags
from onetruth.api.errors import (
    ApiError,
    api_error_from_command,
    api_error_from_duplicate_idempotency,
)


def list_flags_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    rows = query_flags(
        connection,
        context=context,
        workflow_run_id=query.get("workflow_run_id"),
        state=query.get("state"),
        kind=query.get("kind"),
        severity=query.get("severity"),
        assigned_group=query.get("assigned_group"),
        page=page,
        project_id=query.get("project_id"),
    )
    return {
        "command": "api.flags.list",
        "flags": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def get_flag_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    flag_id: str,
) -> dict[str, Any]:
    try:
        flag = show_flag_command(connection, flag_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    scoped_workflow_run(connection, context, str(flag["workflow_run_id"]))
    return {
        "command": "api.flags.detail",
        "flag": flag,
    }


def transition_flag_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    flag_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        flag = show_flag_command(connection, flag_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    scoped_workflow_run(connection, context, str(flag["workflow_run_id"]))
    _assert_payload_flag_id(payload, flag_id)

    command_payload = {
        "flag_id": flag_id,
        "to_state": payload.get("to_state"),
        "reason": payload.get("reason"),
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "actor_roles": context.actor_roles,
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        transitioned = transition_flag_state_command(connection, command_payload, include_receipt=True)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.flags.transition",
        "flag_id": flag_id,
        "flag": transitioned["result"],
        "idempotent_replay": transitioned["idempotent_replay"],
        "receipt": transitioned["receipt"],
    }


def _assert_payload_flag_id(payload: dict[str, Any], path_flag_id: str) -> None:
    payload_flag_id = payload.get("flag_id")
    if payload_flag_id is None:
        return
    if str(payload_flag_id) != path_flag_id:
        raise ApiError(
            status_code=400,
            code="path_payload_mismatch",
            message="flag_id in payload does not match URL path",
            details={
                "path_flag_id": path_flag_id,
                "payload_flag_id": str(payload_flag_id),
            },
        )
