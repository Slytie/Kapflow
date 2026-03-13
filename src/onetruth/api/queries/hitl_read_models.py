from __future__ import annotations

import json
import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    list_workflow_runs_command,
)
from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run
from onetruth.api.errors import api_error_from_command


def query_workflow_runs(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_id: str | None,
    state: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    try:
        rows = list_workflow_runs_command(
            connection,
            workflow_id=workflow_id,
            tenant_id=context.tenant_id,
            domain_id=context.domain_id,
            state=state,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return rows[page.offset : page.offset + page.limit]


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


def query_pointers(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    pointer_id: str | None,
    pointer_key: str | None,
    workflow_run_id: str | None,
    dataset_key: str | None,
    partition_kind: str | None,
    partition_key: str | None,
    stream_key: str | None,
    registry_kind: str | None,
    scope_kind: str | None,
    scope_ref: str | None,
    artifact_kind: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    compatibility_partition_key: str | None = None
    if workflow_run_id is not None:
        workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
        compatibility_partition_key = str(workflow_run["partition_key"])

    query = """
        SELECT
            ap.pointer_id,
            ap.workflow_run_id,
            ap.pointer_key,
            ap.tenant_id,
            ap.domain_id,
            ap.dataset_key,
            ap.partition_kind,
            ap.partition_key,
            ap.stream_key,
            ap.registry_kind,
            ap.scope_kind,
            ap.scope_ref,
            ap.artifact_kind,
            ap.artifact_version_id,
            ap.promotion_reason,
            ap.promoted_by_task_run_id,
            ap.approved_by_approval_id,
            ap.generation,
            ap.updated_at
        FROM artifact_pointers ap
        WHERE ap.tenant_id = ? AND ap.domain_id = ?
    """
    params: list[Any] = [context.tenant_id, context.domain_id]

    if pointer_id is not None:
        query += " AND ap.pointer_id = ?"
        params.append(pointer_id)
    if pointer_key is not None:
        query += " AND ap.pointer_key = ?"
        params.append(pointer_key)
    if dataset_key is not None:
        query += " AND ap.dataset_key = ?"
        params.append(dataset_key)
    if partition_kind is not None:
        query += " AND ap.partition_kind = ?"
        params.append(partition_kind)
    if partition_key is not None:
        query += " AND ap.partition_key = ?"
        params.append(partition_key)
    if stream_key is not None:
        query += " AND ap.stream_key = ?"
        params.append(stream_key)
    if registry_kind is not None:
        query += " AND ap.registry_kind = ?"
        params.append(registry_kind)
    if workflow_run_id is not None:
        query += " AND (ap.workflow_run_id = ? OR ap.partition_key = ?)"
        params.append(workflow_run_id)
        params.append(compatibility_partition_key)
    if scope_kind is not None:
        query += " AND ap.scope_kind = ?"
        params.append(scope_kind)
    if scope_ref is not None:
        query += " AND ap.scope_ref = ?"
        params.append(scope_ref)
    if artifact_kind is not None:
        query += " AND ap.artifact_kind = ?"
        params.append(artifact_kind)

    query += " ORDER BY ap.updated_at DESC, ap.pointer_id ASC LIMIT ? OFFSET ?"
    params.extend([page.limit, page.offset])

    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
