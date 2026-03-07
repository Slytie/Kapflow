from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.api.dependencies import Page, RequestContext, scoped_workflow_run


def list_pointers_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    rows = query_pointers(
        connection,
        context=context,
        pointer_id=query.get("pointer_id"),
        pointer_key=query.get("pointer_key"),
        workflow_run_id=query.get("workflow_run_id"),
        dataset_key=query.get("dataset_key"),
        partition_kind=query.get("partition_kind"),
        partition_key=query.get("partition_key"),
        stream_key=query.get("stream_key"),
        registry_kind=query.get("registry_kind"),
        scope_kind=query.get("scope_kind"),
        scope_ref=query.get("scope_ref"),
        artifact_kind=query.get("artifact_kind"),
        page=page,
    )
    return {
        "command": "api.pointers.list",
        "pointers": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


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
