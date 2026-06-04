from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.approvals import (
    respond_approval_command,
    show_approval_command,
)
from onetruth.application.services.logistics_approval_response_hooks import (
    logistics_approval_response_hooks_for_workflow,
)
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError
from onetruth.infrastructure.repositories.approvals import get_approval

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
from onetruth.api.queries import query_approvals
from onetruth.api.errors import (
    ApiError,
    api_error_from_command,
    api_error_from_duplicate_idempotency,
)


def list_approvals_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    rows = query_approvals(
        connection,
        context=context,
        workflow_run_id=query.get("workflow_run_id"),
        state=query.get("state"),
        approval_kind=query.get("approval_kind"),
        required_role=query.get("required_role"),
        page=page,
    )
    return {
        "command": "api.approvals.list",
        "approvals": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def get_approval_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    approval_id: str,
) -> dict[str, Any]:
    try:
        approval = show_approval_command(connection, approval_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    scoped_workflow_run(connection, context, str(approval["workflow_run_id"]))
    return {
        "command": "api.approvals.detail",
        "approval": approval,
    }


def respond_approval_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    approval_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    approval = get_approval(connection, approval_id)
    if approval is None:
        raise ApiError(
            status_code=404,
            code="approval_not_found",
            message="approval not found",
            details={"approval_id": approval_id},
        )
    workflow_run = scoped_workflow_run(connection, context, str(approval["workflow_run_id"]))
    _assert_payload_approval_id(payload, approval_id)

    command_payload = {
        "approval_id": approval_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "actor_roles": context.actor_roles,
        "response_kind": payload.get("response_kind"),
        "response_reason": payload.get("response_reason"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        updated = respond_approval_command(
            connection,
            command_payload,
            include_receipt=True,
            approval_response_hooks=logistics_approval_response_hooks_for_workflow(
                str(workflow_run.get("workflow_id") or "")
            ),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.approvals.respond",
        "approval_id": approval_id,
        "approval": updated["result"],
        "idempotent_replay": updated["idempotent_replay"],
        "receipt": updated["receipt"],
    }


def _assert_payload_approval_id(payload: dict[str, Any], path_approval_id: str) -> None:
    payload_approval_id = payload.get("approval_id")
    if payload_approval_id is None:
        return
    if str(payload_approval_id) != path_approval_id:
        raise ApiError(
            status_code=400,
            code="path_payload_mismatch",
            message="approval_id in payload does not match URL path",
            details={
                "path_approval_id": path_approval_id,
                "payload_approval_id": str(payload_approval_id),
            },
        )
