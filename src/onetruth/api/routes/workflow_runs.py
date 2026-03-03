from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    CommandError,
    list_approvals_for_workflow_run_command,
    list_artifacts_for_workflow_run_command,
    list_pointers_for_workflow_run_command,
    list_tasks_for_workflow_run_command,
    list_workflow_runs_command,
)

from onetruth.api.dependencies import (
    Page,
    RequestContext,
    enforce_scope_filter,
    scoped_workflow_run,
)
from onetruth.api.errors import api_error_from_command


def list_workflow_runs_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    workflow_id = query.get("workflow_id")
    state = query.get("state")
    tenant_id = query.get("tenant_id")
    domain_id = query.get("domain_id")

    enforce_scope_filter(
        context=context,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )

    rows = query_workflow_runs(
        connection,
        context=context,
        workflow_id=workflow_id,
        state=state,
        page=page,
    )
    return {
        "command": "api.workflow_runs.list",
        "workflow_runs": rows,
        "page": {"limit": page.limit, "offset": page.offset},
    }


def get_workflow_run_detail_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
) -> dict[str, Any]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    try:
        human_tasks = list_tasks_for_workflow_run_command(connection, workflow_run_id)
        approvals = list_approvals_for_workflow_run_command(connection, workflow_run_id)
        artifact_versions = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
        pointers = list_pointers_for_workflow_run_command(connection, workflow_run_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    return {
        "command": "api.workflow_runs.detail",
        "workflow_run": workflow_run,
        "human_tasks": human_tasks,
        "approvals": approvals,
        "artifact_versions": artifact_versions,
        "pointers": pointers,
        "summary": {
            "human_task_count": len(human_tasks),
            "approval_count": len(approvals),
            "artifact_version_count": len(artifact_versions),
            "pointer_count": len(pointers),
        },
    }


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
