from __future__ import annotations

import json
import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    claim_human_task_command,
    complete_human_task_command,
    confirm_human_task_review_command,
    show_human_task_command,
)
from onetruth.application.services.task_actionability import (
    build_artifact_link_count_index,
    compute_human_task_actionability,
)
from onetruth.application.services.stage06_openai_sandbox import (
    run_stage06_openai_review_sandbox,
)
from onetruth.application.services.task_requirements import (
    build_human_task_requirement_index,
)
from onetruth.integrations.openai import OpenAIConfigError, OpenAIResponsesError
from onetruth.infrastructure.events.event_store import DuplicateIdempotencyKeyError
from onetruth.infrastructure.repositories.human_tasks import get_human_task
from onetruth.infrastructure.artifacts.storage import default_storage_root_for_db_url

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
from onetruth.api.errors import (
    ApiError,
    api_error_from_command,
    api_error_from_duplicate_idempotency,
)


def list_human_tasks_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    rows = query_human_tasks(
        connection,
        context=context,
        workflow_run_id=query.get("workflow_run_id"),
        state=query.get("state"),
        stage_id=query.get("stage_id"),
        task_kind=query.get("task_kind"),
        assignee_actor_id=query.get("assignee_actor_id"),
        owner_role=query.get("owner_role"),
        page=page,
    )
    rows = _enrich_human_tasks_with_actionability(
        connection,
        context=context,
        human_tasks=rows,
    )
    return {
        "command": "api.human_tasks.list",
        "human_tasks": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def get_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    try:
        human_task = show_human_task_command(connection, human_task_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    enriched = _enrich_human_tasks_with_actionability(
        connection,
        context=context,
        human_tasks=[human_task],
    )
    return {
        "command": "api.human_tasks.detail",
        "human_task": enriched[0],
    }


def claim_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)

    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "lease_seconds": payload.get("lease_seconds"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        result = claim_human_task_command(connection, command_payload)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.human_tasks.claim",
        "human_task_id": human_task_id,
        "result": result,
    }


def complete_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)

    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "outcome": payload.get("outcome"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        result = complete_human_task_command(connection, command_payload)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc

    return {
        "command": "api.human_tasks.complete",
        "human_task_id": human_task_id,
        "result": result,
    }


def run_stage06_agent_review_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)

    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "actor_roles": context.actor_roles,
        "idempotency_key": payload.get("idempotency_key"),
        "policy_decision": payload.get("policy_decision"),
    }
    try:
        result = run_stage06_openai_review_sandbox(connection, command_payload)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc
    except OpenAIConfigError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            details={},
        ) from exc
    except OpenAIResponsesError as exc:
        status_code = 503 if exc.retryable else 502
        raise ApiError(
            status_code=status_code,
            code=exc.code,
            message=str(exc),
            details=exc.details,
        ) from exc

    return {
        "command": "api.human_tasks.stage06_agent_review",
        "human_task_id": human_task_id,
        "result": result,
    }


def confirm_human_task_review_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    human_task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_human_task_in_scope(connection, context=context, human_task_id=human_task_id)
    _assert_payload_human_task_id(payload, human_task_id)
    command_payload = {
        "human_task_id": human_task_id,
        "actor_id": context.actor_id,
        "actor_type": context.actor_type,
        "reviewed_artifact_version_ids": payload.get("reviewed_artifact_version_ids"),
        "idempotency_key": payload.get("idempotency_key"),
    }
    try:
        result = confirm_human_task_review_command(
            connection,
            command_payload,
            storage_root=default_storage_root_for_db_url(
                db_url,
                override=payload.get("storage_root"),
            ),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except DuplicateIdempotencyKeyError as exc:
        raise api_error_from_duplicate_idempotency(exc) from exc
    return {
        "command": "api.human_tasks.confirm_review",
        "human_task_id": human_task_id,
        "result": result,
    }


def query_human_tasks(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str | None,
    state: str | None,
    stage_id: str | None,
    task_kind: str | None,
    assignee_actor_id: str | None,
    owner_role: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    if workflow_run_id is not None:
        scoped_workflow_run(connection, context, workflow_run_id)

    query = """
        SELECT
            ht.human_task_id,
            ht.workflow_run_id,
            ht.task_run_id,
            ht.task_kind,
            ht.state,
            ht.candidate_roles,
            ht.owner_role,
            ht.assignee_actor_id,
            ht.assignee_actor_type,
            ht.due_at,
            ht.escalation_at,
            ht.lease_version,
            ht.claimed_at,
            ht.claimed_until,
            ht.linked_approval_id,
            ht.reopen_count,
            ht.generation,
            ht.created_at,
            ht.updated_at,
            tr.state AS task_run_state,
            tr.stage_id,
            tr.blocked_on_kind,
            tr.blocked_on_ref,
            tr.spawned_from_flag_id
        FROM human_tasks ht
        JOIN task_runs tr ON tr.task_run_id = ht.task_run_id
        JOIN workflow_runs wr ON wr.workflow_run_id = ht.workflow_run_id
        WHERE wr.tenant_id = ? AND wr.domain_id = ?
    """
    params: list[Any] = [context.tenant_id, context.domain_id]

    if workflow_run_id is not None:
        query += " AND ht.workflow_run_id = ?"
        params.append(workflow_run_id)
    if state is not None:
        query += " AND ht.state = ?"
        params.append(state)
    if stage_id is not None:
        query += " AND tr.stage_id = ?"
        params.append(stage_id)
    if task_kind is not None:
        query += " AND ht.task_kind = ?"
        params.append(task_kind)
    if assignee_actor_id is not None:
        query += " AND ht.assignee_actor_id = ?"
        params.append(assignee_actor_id)
    if owner_role is not None:
        query += " AND ht.owner_role = ?"
        params.append(owner_role)

    query += """
        ORDER BY
            CASE ht.state
                WHEN 'OPEN' THEN 0
                WHEN 'CLAIMED' THEN 1
                ELSE 2
            END ASC,
            COALESCE(ht.due_at, '9999-12-31T23:59:59Z') ASC,
            ht.created_at ASC,
            ht.human_task_id ASC
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


def _enrich_human_tasks_with_actionability(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not human_tasks:
        return []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in human_tasks:
        grouped.setdefault(str(task["workflow_run_id"]), []).append(task)

    link_counts_by_run: dict[str, dict[tuple[str, str], int]] = {}
    requirements_by_run: dict[str, dict[str, dict[str, Any]]] = {}
    for workflow_run_id, tasks in grouped.items():
        link_counts_by_run[workflow_run_id] = build_artifact_link_count_index(
            connection,
            workflow_run_id=workflow_run_id,
        )
        requirements_by_run[workflow_run_id] = build_human_task_requirement_index(
            connection,
            workflow_run_id=workflow_run_id,
            human_tasks=tasks,
        )

    enriched: list[dict[str, Any]] = []
    for task in human_tasks:
        workflow_run_id = str(task["workflow_run_id"])
        human_task_id = str(task["human_task_id"])
        linked_artifact_count = int(
            link_counts_by_run.get(workflow_run_id, {}).get(("human_task", human_task_id), 0)
        )
        actionability = compute_human_task_actionability(
            task=task,
            actor_id=context.actor_id,
            actor_type=context.actor_type,
            actor_roles=context.actor_roles,
            linked_artifact_count=linked_artifact_count,
            requirement_state=requirements_by_run.get(workflow_run_id, {}).get(human_task_id),
        )
        enriched.append({**task, **actionability})
    return enriched


def _ensure_human_task_in_scope(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    human_task_id: str,
) -> dict[str, Any]:
    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise ApiError(
            status_code=404,
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": human_task_id},
        )
    scoped_workflow_run(connection, context, str(human_task["workflow_run_id"]))
    return human_task


def _assert_payload_human_task_id(payload: dict[str, Any], path_human_task_id: str) -> None:
    payload_human_task_id = payload.get("human_task_id")
    if payload_human_task_id is None:
        return
    if str(payload_human_task_id) != path_human_task_id:
        raise ApiError(
            status_code=400,
            code="path_payload_mismatch",
            message="human_task_id in payload does not match URL path",
            details={
                "path_human_task_id": path_human_task_id,
                "payload_human_task_id": str(payload_human_task_id),
            },
        )
