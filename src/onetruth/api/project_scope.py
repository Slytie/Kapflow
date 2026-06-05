from __future__ import annotations

import sqlite3
from typing import Any
from urllib.parse import unquote

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.services.capex_project_access import (
    PROJECT_VIEWER,
    require_project_access,
)
from onetruth.capex_platform.project_access import AuthorizedProjectsQuery

from onetruth.api.dependencies import RequestContext, scoped_workflow_run
from onetruth.api.errors import ApiError, api_error_from_command


def normalize_project_path_id(value: str) -> str:
    return unquote(value).strip()


def parse_project_child_ref(
    value: str,
    resource: str,
    *,
    allow_slash_id: bool = False,
) -> tuple[str, str]:
    needle = f"/{resource}/"
    project_id, separator, child_id = value.partition(needle)
    if not project_id or not separator or not child_id:
        raise_not_found("not_found", {"path": value})
    if not allow_slash_id and "/" in child_id:
        raise_not_found("not_found", {"path": value})
    return normalize_project_path_id(project_id), unquote(child_id).strip()


def require_project_viewer(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    not_found_code: str = "capex_project_not_found",
) -> dict[str, Any]:
    try:
        return require_project_access(
            connection,
            project_id=project_id,
            tenant_id=context.tenant_id,
            domain_id=context.domain_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            min_role=PROJECT_VIEWER,
            not_found_code=not_found_code,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc


def caller_project_role(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
) -> str | None:
    return AuthorizedProjectsQuery(connection).role_for_project(
        project_id=project_id,
        actor_type=context.actor_type,
        actor_id=context.actor_id,
    )


def with_project_query(query: dict[str, str], project_id: str) -> dict[str, str]:
    return {**query, "project_id": project_id}


def decorate_project_payload(payload: dict[str, Any], *, command: str, project_id: str) -> dict[str, Any]:
    return {"project_id": project_id, **payload, "command": command}


def attach_project_id(payload: dict[str, Any], key: str, project_id: str) -> None:
    value = payload.get(key)
    if isinstance(value, list):
        payload[key] = rows_with_project_id(value, project_id)
    elif isinstance(value, dict):
        payload[key] = {**value, "project_id": project_id}


def rows_with_project_id(rows: list[Any], project_id: str) -> list[Any]:
    return [
        {**item, "project_id": project_id}
        if isinstance(item, dict)
        else item
        for item in rows
    ]


def project_scope_values(project: dict[str, Any]) -> tuple[str, str, str]:
    return str(project["project_id"]), str(project["tenant_id"]), str(project["domain_id"])


def assert_optional_query_workflow_run(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
) -> None:
    workflow_run_id = query.get("workflow_run_id")
    if workflow_run_id is None:
        return
    assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )


def assert_workflow_run_in_project(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    workflow_run_id: str,
    not_found_code: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    try:
        workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    except ApiError as exc:
        if exc.code == "workflow_run_not_found":
            raise_not_found(not_found_code, details)
        raise
    assert_workflow_run_row_project(
        workflow_run,
        project_id=project_id,
        not_found_code=not_found_code,
        details=details,
    )
    return workflow_run


def assert_workflow_run_row_project(
    workflow_run: dict[str, Any],
    *,
    project_id: str | None,
    not_found_code: str,
    details: dict[str, Any],
) -> None:
    if project_id is None:
        return
    if workflow_run.get("project_id") == project_id:
        return
    raise_not_found(not_found_code, details)


def raise_not_found(code: str, details: dict[str, Any]) -> None:
    raise ApiError(
        status_code=404,
        code=code,
        message="resource not found",
        details=details,
    )
