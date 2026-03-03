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
        workflow_run_id=query.get("workflow_run_id"),
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
    workflow_run_id: str | None,
    scope_kind: str | None,
    scope_ref: str | None,
    artifact_kind: str | None,
    page: Page,
) -> list[dict[str, Any]]:
    if workflow_run_id is not None:
        scoped_workflow_run(connection, context, workflow_run_id)

    query = """
        SELECT
            ap.workflow_run_id,
            ap.pointer_key,
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
        JOIN workflow_runs wr ON wr.workflow_run_id = ap.workflow_run_id
        WHERE wr.tenant_id = ? AND wr.domain_id = ?
    """
    params: list[Any] = [context.tenant_id, context.domain_id]

    if workflow_run_id is not None:
        query += " AND ap.workflow_run_id = ?"
        params.append(workflow_run_id)
    if scope_kind is not None:
        query += " AND ap.scope_kind = ?"
        params.append(scope_kind)
    if scope_ref is not None:
        query += " AND ap.scope_ref = ?"
        params.append(scope_ref)
    if artifact_kind is not None:
        query += " AND ap.artifact_kind = ?"
        params.append(artifact_kind)

    query += " ORDER BY ap.updated_at DESC, ap.pointer_key ASC LIMIT ? OFFSET ?"
    params.extend([page.limit, page.offset])

    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
