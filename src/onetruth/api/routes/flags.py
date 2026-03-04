from __future__ import annotations

import json
import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    show_flag_command,
    transition_flag_state_command,
)
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
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
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        transitioned = transition_flag_state_command(connection, command_payload)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.flags.transition",
        "flag_id": flag_id,
        "flag": transitioned,
    }


def query_flags(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str | None,
    state: str | None,
    kind: str | None,
    severity: str | None,
    assigned_group: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    if workflow_run_id is not None:
        scoped_workflow_run(connection, context, workflow_run_id)

    query = """
        SELECT
            f.flag_id,
            f.workflow_run_id,
            f.tenant_id,
            f.domain_id,
            f.workflow_id,
            f.partition_key,
            f.kind,
            f.severity,
            f.state,
            f.summary,
            f.details_json,
            f.assigned_group,
            f.created_at,
            f.closed_at,
            f.created_by_actor_id,
            f.created_by_actor_type,
            f.source_event_id,
            f.dedupe_key,
            f.updated_at
        FROM flags f
        JOIN workflow_runs wr ON wr.workflow_run_id = f.workflow_run_id
        WHERE wr.tenant_id = ? AND wr.domain_id = ?
    """
    params: list[Any] = [context.tenant_id, context.domain_id]

    if workflow_run_id is not None:
        query += " AND f.workflow_run_id = ?"
        params.append(workflow_run_id)
    if state is not None:
        query += " AND f.state = ?"
        params.append(state)
    if kind is not None:
        query += " AND f.kind = ?"
        params.append(kind)
    if severity is not None:
        query += " AND f.severity = ?"
        params.append(severity)
    if assigned_group is not None:
        query += " AND f.assigned_group = ?"
        params.append(assigned_group)

    query += """
        ORDER BY
            CASE f.state
                WHEN 'open' THEN 0
                WHEN 'triage' THEN 1
                WHEN 'blocked' THEN 2
                WHEN 'resolved' THEN 3
                WHEN 'closed' THEN 4
                ELSE 5
            END ASC,
            CASE f.severity
                WHEN 'critical' THEN 0
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
                ELSE 4
            END ASC,
            f.created_at ASC,
            f.flag_id ASC
        LIMIT ? OFFSET ?
    """
    params.extend([page.limit, page.offset])

    rows = connection.execute(query, params).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["details_json"] = json.loads(item["details_json"])
        results.append(item)
    return results


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
