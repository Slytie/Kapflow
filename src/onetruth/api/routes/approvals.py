from __future__ import annotations

import json
import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    respond_approval_command,
    show_approval_command,
)
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError
from onetruth.infrastructure.repositories.approvals import get_approval

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
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
    scoped_workflow_run(connection, context, str(approval["workflow_run_id"]))
    _assert_payload_approval_id(payload, approval_id)

    command_payload = {
        "approval_id": approval_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "response_kind": payload.get("response_kind"),
        "response_reason": payload.get("response_reason"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        updated = respond_approval_command(connection, command_payload)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.approvals.respond",
        "approval_id": approval_id,
        "approval": updated,
    }


def query_approvals(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str | None,
    state: str | None,
    approval_kind: str | None,
    required_role: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    if workflow_run_id is not None:
        scoped_workflow_run(connection, context, workflow_run_id)

    query = """
        SELECT
            ap.approval_id,
            ap.workflow_run_id,
            ap.task_run_id,
            ap.approval_kind,
            ap.scope_kind,
            ap.scope_ref,
            ap.state,
            ap.requested_by_task_run_id,
            ap.candidate_roles,
            ap.required_role,
            ap.requested_at,
            ap.responded_at,
            ap.response_kind,
            ap.response_reason,
            ap.decided_by_actor_id,
            ap.decided_by_actor_type,
            ap.generation,
            ap.created_at,
            ap.updated_at
        FROM approvals ap
        JOIN workflow_runs wr ON wr.workflow_run_id = ap.workflow_run_id
        WHERE wr.tenant_id = ? AND wr.domain_id = ?
    """
    params: list[Any] = [context.tenant_id, context.domain_id]

    if workflow_run_id is not None:
        query += " AND ap.workflow_run_id = ?"
        params.append(workflow_run_id)
    if state is not None:
        query += " AND ap.state = ?"
        params.append(state)
    if approval_kind is not None:
        query += " AND ap.approval_kind = ?"
        params.append(approval_kind)
    if required_role is not None:
        query += " AND ap.required_role = ?"
        params.append(required_role)

    query += """
        ORDER BY
            CASE ap.state WHEN 'PENDING' THEN 0 ELSE 1 END ASC,
            ap.requested_at ASC,
            ap.approval_id ASC
        LIMIT ? OFFSET ?
    """
    params.extend([page.limit, page.offset])

    rows = connection.execute(query, params).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["candidate_roles"] = json.loads(item["candidate_roles"])
        results.append(item)
    return results


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
