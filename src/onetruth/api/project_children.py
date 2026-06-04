from __future__ import annotations

import sqlite3
from typing import Any
from urllib.parse import unquote

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.approvals import show_approval_command
from onetruth.application.handlers.capex_projects import show_capex_project_command
from onetruth.application.read_commands import (
    show_artifact_version_command,
    show_flag_command,
    show_human_task_command,
)
from onetruth.infrastructure.repositories.artifact_pointers import get_pointer_by_id
from onetruth.infrastructure.repositories.capex_projects import get_project_membership_for_actor

from onetruth.api.dependencies import BoundaryProfile, Page, RequestContext, scoped_workflow_run
from onetruth.api.errors import ApiError, api_error_from_command
from onetruth.api.queries import (
    query_approvals,
    query_flags,
    query_human_tasks,
    query_pointers,
    query_workflow_runs,
)
from onetruth.api.responses import BinaryResponse
from onetruth.api.routes.approvals import (
    get_approval_endpoint,
    list_approvals_endpoint,
    respond_approval_endpoint,
)
from onetruth.api.routes.artifacts import (
    download_artifact_binary_endpoint,
    download_artifact_endpoint,
    get_artifact_endpoint,
    list_approval_artifacts_endpoint,
    list_artifacts_endpoint,
    list_flag_artifacts_endpoint,
    list_human_task_artifacts_endpoint,
    list_workflow_run_artifacts_endpoint,
    query_artifacts_in_scope,
    upload_approval_artifact_endpoint,
    upload_flag_artifact_endpoint,
    upload_human_task_artifact_endpoint,
    upload_workflow_run_artifact_endpoint,
)
from onetruth.api.routes.flags import get_flag_endpoint, list_flags_endpoint, transition_flag_endpoint
from onetruth.api.routes.human_tasks import (
    claim_human_task_endpoint,
    complete_human_task_endpoint,
    confirm_human_task_review_endpoint,
    get_human_task_endpoint,
    get_human_task_subgraph_endpoint,
    list_human_tasks_endpoint,
)
from onetruth.api.routes.pointers import list_pointers_endpoint
from onetruth.api.routes.timeline import (
    list_timeline_events_endpoint,
    list_workflow_run_timeline_endpoint,
    query_timeline_events,
)
from onetruth.api.routes.workflow_runs import (
    get_workflow_run_detail_endpoint,
    get_workflow_run_workspace_endpoint,
    list_workflow_runs_endpoint,
)

ACTIVE_FLAG_STATES = ("open", "triage", "blocked")
PROJECT_DASHBOARD_SCHEMA_VERSION = "capex_project_dashboard.v1"


def list_project_workflow_runs_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    _require_project(connection, context=context, project_id=project_id)
    payload = list_workflow_runs_endpoint(
        connection,
        context=context,
        query=_with_project_query(query, project_id),
        page=page,
    )
    return _decorate(payload, command="api.capex.projects.workflow_runs.list", project_id=project_id)


def get_project_workflow_run_detail_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_workflow_run: str,
) -> dict[str, Any]:
    project_id, workflow_run_id = _parse_child_ref(project_workflow_run, "workflow-runs")
    _require_project(connection, context=context, project_id=project_id)
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )
    payload = get_workflow_run_detail_endpoint(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
    )
    return _decorate(payload, command="api.capex.projects.workflow_runs.detail", project_id=project_id)


def get_project_workflow_run_workspace_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_workflow_run: str,
    query: dict[str, str],
) -> dict[str, Any]:
    project_id, workflow_run_id = _parse_child_ref(project_workflow_run, "workflow-runs")
    _require_project(connection, context=context, project_id=project_id)
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )
    payload = get_workflow_run_workspace_endpoint(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        query=query,
    )
    return _decorate(payload, command="api.capex.projects.workflow_runs.workspace", project_id=project_id)


def list_project_workflow_run_timeline_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_workflow_run: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id, workflow_run_id = _parse_child_ref(project_workflow_run, "workflow-runs")
    _require_project(connection, context=context, project_id=project_id)
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )
    payload = list_workflow_run_timeline_endpoint(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        query=query,
        page=page,
    )
    return _decorate(payload, command="api.capex.projects.workflow_runs.timeline", project_id=project_id)


def list_project_workflow_run_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_workflow_run: str,
    page: Page,
) -> dict[str, Any]:
    project_id, workflow_run_id = _parse_child_ref(project_workflow_run, "workflow-runs")
    _require_project(connection, context=context, project_id=project_id)
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )
    payload = list_workflow_run_artifacts_endpoint(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        page=page,
    )
    _attach_project_id(payload, "artifact_versions", project_id)
    return _decorate(payload, command="api.capex.projects.workflow_runs.artifacts.list", project_id=project_id)


def upload_project_workflow_run_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    project_workflow_run: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, workflow_run_id = _parse_child_ref(project_workflow_run, "workflow-runs")
    _require_project(connection, context=context, project_id=project_id)
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )
    result = upload_workflow_run_artifact_endpoint(
        connection,
        context=context,
        db_url=db_url,
        workflow_run_id=workflow_run_id,
        payload=payload,
    )
    _attach_project_id(result, "artifact_version", project_id)
    return _decorate(payload=result, command="api.capex.projects.workflow_runs.artifacts.upload", project_id=project_id)


def list_project_human_tasks_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    _require_project(connection, context=context, project_id=project_id)
    _assert_optional_query_workflow_run(connection, context=context, project_id=project_id, query=query)
    payload = list_human_tasks_endpoint(
        connection,
        context=context,
        query=_with_project_query(query, project_id),
        page=page,
    )
    _attach_project_id(payload, "human_tasks", project_id)
    return _decorate(payload, command="api.capex.projects.human_tasks.list", project_id=project_id)


def get_project_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_human_task: str,
) -> dict[str, Any]:
    project_id, human_task_id = _parse_child_ref(project_human_task, "human-tasks")
    _assert_human_task_in_project(connection, context=context, project_id=project_id, human_task_id=human_task_id)
    payload = get_human_task_endpoint(connection, context=context, human_task_id=human_task_id)
    _attach_project_id(payload, "human_task", project_id)
    return _decorate(payload, command="api.capex.projects.human_tasks.detail", project_id=project_id)


def get_project_human_task_subgraph_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_human_task: str,
) -> dict[str, Any]:
    project_id, human_task_id = _parse_child_ref(project_human_task, "human-tasks")
    _assert_human_task_in_project(connection, context=context, project_id=project_id, human_task_id=human_task_id)
    payload = get_human_task_subgraph_endpoint(connection, context=context, human_task_id=human_task_id)
    return _decorate(payload, command="api.capex.projects.human_tasks.subgraph", project_id=project_id)


def claim_project_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_human_task: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, human_task_id = _parse_child_ref(project_human_task, "human-tasks")
    _assert_human_task_in_project(connection, context=context, project_id=project_id, human_task_id=human_task_id)
    result = claim_human_task_endpoint(
        connection,
        context=context,
        human_task_id=human_task_id,
        payload=payload,
    )
    return _decorate(result, command="api.capex.projects.human_tasks.claim", project_id=project_id)


def complete_project_human_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    project_human_task: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, human_task_id = _parse_child_ref(project_human_task, "human-tasks")
    _assert_human_task_in_project(connection, context=context, project_id=project_id, human_task_id=human_task_id)
    result = complete_human_task_endpoint(
        connection,
        context=context,
        db_url=db_url,
        human_task_id=human_task_id,
        payload=payload,
    )
    return _decorate(result, command="api.capex.projects.human_tasks.complete", project_id=project_id)


def confirm_project_human_task_review_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    project_human_task: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, human_task_id = _parse_child_ref(project_human_task, "human-tasks")
    _assert_human_task_in_project(connection, context=context, project_id=project_id, human_task_id=human_task_id)
    result = confirm_human_task_review_endpoint(
        connection,
        context=context,
        db_url=db_url,
        human_task_id=human_task_id,
        payload=payload,
    )
    return _decorate(result, command="api.capex.projects.human_tasks.confirm_review", project_id=project_id)


def list_project_human_task_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_human_task: str,
    page: Page,
) -> dict[str, Any]:
    project_id, human_task_id = _parse_child_ref(project_human_task, "human-tasks")
    _assert_human_task_in_project(connection, context=context, project_id=project_id, human_task_id=human_task_id)
    payload = list_human_task_artifacts_endpoint(
        connection,
        context=context,
        human_task_id=human_task_id,
        page=page,
    )
    _attach_project_id(payload, "artifact_versions", project_id)
    return _decorate(payload, command="api.capex.projects.human_tasks.artifacts.list", project_id=project_id)


def upload_project_human_task_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    project_human_task: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, human_task_id = _parse_child_ref(project_human_task, "human-tasks")
    _assert_human_task_in_project(connection, context=context, project_id=project_id, human_task_id=human_task_id)
    result = upload_human_task_artifact_endpoint(
        connection,
        context=context,
        db_url=db_url,
        human_task_id=human_task_id,
        payload=payload,
    )
    _attach_project_id(result, "artifact_version", project_id)
    return _decorate(result, command="api.capex.projects.human_tasks.artifacts.upload", project_id=project_id)


def list_project_approvals_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    _require_project(connection, context=context, project_id=project_id)
    _assert_optional_query_workflow_run(connection, context=context, project_id=project_id, query=query)
    payload = list_approvals_endpoint(
        connection,
        context=context,
        query=_with_project_query(query, project_id),
        page=page,
    )
    _attach_project_id(payload, "approvals", project_id)
    return _decorate(payload, command="api.capex.projects.approvals.list", project_id=project_id)


def get_project_approval_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_approval: str,
) -> dict[str, Any]:
    project_id, approval_id = _parse_child_ref(project_approval, "approvals")
    _assert_approval_in_project(connection, context=context, project_id=project_id, approval_id=approval_id)
    payload = get_approval_endpoint(connection, context=context, approval_id=approval_id)
    _attach_project_id(payload, "approval", project_id)
    return _decorate(payload, command="api.capex.projects.approvals.detail", project_id=project_id)


def respond_project_approval_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_approval: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, approval_id = _parse_child_ref(project_approval, "approvals")
    _assert_approval_in_project(connection, context=context, project_id=project_id, approval_id=approval_id)
    result = respond_approval_endpoint(
        connection,
        context=context,
        approval_id=approval_id,
        payload=payload,
    )
    return _decorate(result, command="api.capex.projects.approvals.respond", project_id=project_id)


def list_project_approval_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_approval: str,
    page: Page,
) -> dict[str, Any]:
    project_id, approval_id = _parse_child_ref(project_approval, "approvals")
    _assert_approval_in_project(connection, context=context, project_id=project_id, approval_id=approval_id)
    payload = list_approval_artifacts_endpoint(
        connection,
        context=context,
        approval_id=approval_id,
        page=page,
    )
    _attach_project_id(payload, "artifact_versions", project_id)
    return _decorate(payload, command="api.capex.projects.approvals.artifacts.list", project_id=project_id)


def upload_project_approval_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    project_approval: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, approval_id = _parse_child_ref(project_approval, "approvals")
    _assert_approval_in_project(connection, context=context, project_id=project_id, approval_id=approval_id)
    result = upload_approval_artifact_endpoint(
        connection,
        context=context,
        db_url=db_url,
        approval_id=approval_id,
        payload=payload,
    )
    _attach_project_id(result, "artifact_version", project_id)
    return _decorate(result, command="api.capex.projects.approvals.artifacts.upload", project_id=project_id)


def list_project_flags_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    _require_project(connection, context=context, project_id=project_id)
    _assert_optional_query_workflow_run(connection, context=context, project_id=project_id, query=query)
    payload = list_flags_endpoint(
        connection,
        context=context,
        query=_with_project_query(query, project_id),
        page=page,
    )
    _attach_project_id(payload, "flags", project_id)
    return _decorate(payload, command="api.capex.projects.flags.list", project_id=project_id)


def get_project_flag_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_flag: str,
) -> dict[str, Any]:
    project_id, flag_id = _parse_child_ref(project_flag, "flags")
    _assert_flag_in_project(connection, context=context, project_id=project_id, flag_id=flag_id)
    payload = get_flag_endpoint(connection, context=context, flag_id=flag_id)
    _attach_project_id(payload, "flag", project_id)
    return _decorate(payload, command="api.capex.projects.flags.detail", project_id=project_id)


def transition_project_flag_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_flag: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, flag_id = _parse_child_ref(project_flag, "flags")
    _assert_flag_in_project(connection, context=context, project_id=project_id, flag_id=flag_id)
    result = transition_flag_endpoint(
        connection,
        context=context,
        flag_id=flag_id,
        payload=payload,
    )
    return _decorate(result, command="api.capex.projects.flags.transition", project_id=project_id)


def list_project_flag_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_flag: str,
    page: Page,
) -> dict[str, Any]:
    project_id, flag_id = _parse_child_ref(project_flag, "flags")
    _assert_flag_in_project(connection, context=context, project_id=project_id, flag_id=flag_id)
    payload = list_flag_artifacts_endpoint(
        connection,
        context=context,
        flag_id=flag_id,
        page=page,
    )
    _attach_project_id(payload, "artifact_versions", project_id)
    return _decorate(payload, command="api.capex.projects.flags.artifacts.list", project_id=project_id)


def upload_project_flag_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    project_flag: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    project_id, flag_id = _parse_child_ref(project_flag, "flags")
    _assert_flag_in_project(connection, context=context, project_id=project_id, flag_id=flag_id)
    result = upload_flag_artifact_endpoint(
        connection,
        context=context,
        db_url=db_url,
        flag_id=flag_id,
        payload=payload,
    )
    _attach_project_id(result, "artifact_version", project_id)
    return _decorate(result, command="api.capex.projects.flags.artifacts.upload", project_id=project_id)


def list_project_artifacts_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    _require_project(connection, context=context, project_id=project_id)
    _assert_optional_query_workflow_run(connection, context=context, project_id=project_id, query=query)
    payload = list_artifacts_endpoint(
        connection,
        context=context,
        query=_with_project_query(query, project_id),
        page=page,
    )
    _attach_project_id(payload, "artifact_versions", project_id)
    return _decorate(payload, command="api.capex.projects.artifacts.list", project_id=project_id)


def get_project_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_artifact: str,
) -> dict[str, Any]:
    project_id, artifact_version_id = _parse_child_ref(project_artifact, "artifacts")
    _assert_artifact_in_project(
        connection,
        context=context,
        project_id=project_id,
        artifact_version_id=artifact_version_id,
    )
    payload = get_artifact_endpoint(
        connection,
        context=context,
        artifact_version_id=artifact_version_id,
    )
    _attach_project_id(payload, "artifact_version", project_id)
    return _decorate(payload, command="api.capex.projects.artifacts.detail", project_id=project_id)


def download_project_artifact_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    boundary_profile: BoundaryProfile,
    db_url: str,
    project_artifact: str,
) -> dict[str, Any]:
    project_id, artifact_version_id = _parse_child_ref(project_artifact, "artifacts")
    _assert_artifact_in_project(
        connection,
        context=context,
        project_id=project_id,
        artifact_version_id=artifact_version_id,
    )
    payload = download_artifact_endpoint(
        connection,
        context=context,
        boundary_profile=boundary_profile,
        db_url=db_url,
        artifact_version_id=artifact_version_id,
    )
    _attach_project_id(payload, "artifact_version", project_id)
    return _decorate(payload, command="api.capex.projects.artifacts.download", project_id=project_id)


def download_project_artifact_binary_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    boundary_profile: BoundaryProfile,
    db_url: str,
    project_artifact: str,
) -> BinaryResponse:
    project_id, artifact_version_id = _parse_child_ref(project_artifact, "artifacts")
    _assert_artifact_in_project(
        connection,
        context=context,
        project_id=project_id,
        artifact_version_id=artifact_version_id,
    )
    return download_artifact_binary_endpoint(
        connection,
        context=context,
        boundary_profile=boundary_profile,
        db_url=db_url,
        artifact_version_id=artifact_version_id,
    )


def list_project_pointers_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    _require_project(connection, context=context, project_id=project_id)
    _assert_optional_query_workflow_run(connection, context=context, project_id=project_id, query=query)
    payload = list_pointers_endpoint(
        connection,
        context=context,
        query=_with_project_query(query, project_id),
        page=page,
    )
    _attach_project_id(payload, "pointers", project_id)
    return _decorate(payload, command="api.capex.projects.pointers.list", project_id=project_id)


def get_project_pointer_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_pointer: str,
) -> dict[str, Any]:
    project_id, pointer_id = _parse_child_ref(project_pointer, "pointers", allow_slash_id=True)
    _require_project(connection, context=context, project_id=project_id)
    pointer = get_pointer_by_id(connection, pointer_id=pointer_id)
    if pointer is None:
        _raise_not_found("pointer_not_found", {"pointer_id": pointer_id})
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=str(pointer["workflow_run_id"]),
        not_found_code="pointer_not_found",
        details={"pointer_id": pointer_id},
    )
    return {
        "command": "api.capex.projects.pointers.detail",
        "project_id": project_id,
        "pointer": {**pointer, "project_id": project_id},
    }


def list_project_timeline_events_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    _require_project(connection, context=context, project_id=project_id)
    _assert_optional_query_workflow_run(connection, context=context, project_id=project_id, query=query)
    payload = list_timeline_events_endpoint(
        connection,
        context=context,
        query=_with_project_query(query, project_id),
        page=page,
    )
    return _decorate(payload, command="api.capex.projects.timeline_events.list", project_id=project_id)


def get_project_dashboard_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    page: Page,
) -> dict[str, Any]:
    project_id = _normalize_id(project_id)
    project = _require_project(connection, context=context, project_id=project_id)
    excerpt_page = Page(limit=min(page.limit, 25), offset=page.offset)
    workflow_runs = query_workflow_runs(
        connection,
        context=context,
        workflow_id=None,
        project_id=project_id,
        state=None,
        page=excerpt_page,
    )
    human_tasks = query_human_tasks(
        connection,
        context=context,
        workflow_run_id=None,
        state="OPEN",
        stage_id=None,
        task_kind=None,
        assignee_actor_id=None,
        owner_role=None,
        page=excerpt_page,
        project_id=project_id,
    )
    approvals = query_approvals(
        connection,
        context=context,
        workflow_run_id=None,
        state="PENDING",
        approval_kind=None,
        required_role=None,
        page=excerpt_page,
        project_id=project_id,
    )
    flags = query_flags(
        connection,
        context=context,
        workflow_run_id=None,
        state=None,
        kind=None,
        severity=None,
        assigned_group=None,
        page=excerpt_page,
        project_id=project_id,
    )
    active_flags = [flag for flag in flags if str(flag.get("state")) in ACTIVE_FLAG_STATES]
    artifacts = query_artifacts_in_scope(
        connection,
        context=context,
        artifact_kind=None,
        page=excerpt_page,
        project_id=project_id,
    )
    pointers = query_pointers(
        connection,
        context=context,
        pointer_id=None,
        pointer_key=None,
        workflow_run_id=None,
        dataset_key=None,
        partition_kind=None,
        partition_key=None,
        stream_key=None,
        registry_kind=None,
        scope_kind=None,
        scope_ref=None,
        artifact_kind=None,
        page=excerpt_page,
        project_id=project_id,
    )
    events = query_timeline_events(
        connection,
        tenant_id=context.tenant_id,
        domain_id=context.domain_id,
        actor_type=context.actor_type,
        actor_id=context.actor_id,
        workflow_run_id=None,
        project_id=project_id,
        event_type=None,
        page=excerpt_page,
    )
    counts = _project_dashboard_counts(connection, project=project)
    human_tasks = _rows_with_project_id(human_tasks, project_id)
    approvals = _rows_with_project_id(approvals, project_id)
    active_flags = _rows_with_project_id(active_flags, project_id)
    artifacts = _rows_with_project_id(artifacts, project_id)
    pointers = _rows_with_project_id(pointers, project_id)
    return {
        "command": "api.capex.projects.dashboard",
        "project_id": project_id,
        "dashboard": {
            "schema_version": PROJECT_DASHBOARD_SCHEMA_VERSION,
            "project": {**project, "caller_role": _caller_role(connection, context=context, project_id=project_id)},
            "caller_role": _caller_role(connection, context=context, project_id=project_id),
            "counts": counts,
            "workflow_runs": workflow_runs,
            "human_tasks": human_tasks,
            "approvals": approvals,
            "flags": active_flags,
            "artifact_versions": artifacts,
            "pointers": pointers,
            "timeline_events": events,
            "page": {"limit": excerpt_page.limit, "offset": excerpt_page.offset},
        },
    }


def _normalize_id(value: str) -> str:
    return unquote(value).strip()


def _parse_child_ref(
    value: str,
    resource: str,
    *,
    allow_slash_id: bool = False,
) -> tuple[str, str]:
    needle = f"/{resource}/"
    project_id, separator, child_id = value.partition(needle)
    if not project_id or not separator or not child_id:
        _raise_not_found("not_found", {"path": value})
    if not allow_slash_id and "/" in child_id:
        _raise_not_found("not_found", {"path": value})
    return _normalize_id(project_id), unquote(child_id).strip()


def _with_project_query(query: dict[str, str], project_id: str) -> dict[str, str]:
    return {**query, "project_id": project_id}


def _decorate(payload: dict[str, Any], *, command: str, project_id: str) -> dict[str, Any]:
    return {"project_id": project_id, **payload, "command": command}


def _attach_project_id(payload: dict[str, Any], key: str, project_id: str) -> None:
    value = payload.get(key)
    if isinstance(value, list):
        payload[key] = _rows_with_project_id(value, project_id)
    elif isinstance(value, dict):
        payload[key] = {**value, "project_id": project_id}


def _rows_with_project_id(rows: list[Any], project_id: str) -> list[Any]:
    return [
        {**item, "project_id": project_id}
        if isinstance(item, dict)
        else item
        for item in rows
    ]


def _require_project(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
) -> dict[str, Any]:
    try:
        return show_capex_project_command(
            connection,
            project_id=project_id,
            tenant_id=context.tenant_id,
            domain_id=context.domain_id,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc


def _caller_role(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
) -> str | None:
    membership = get_project_membership_for_actor(
        connection,
        project_id=project_id,
        actor_type=context.actor_type,
        actor_id=context.actor_id,
    )
    if membership is None:
        return None
    return str(membership["role"])


def _assert_optional_query_workflow_run(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    query: dict[str, str],
) -> None:
    workflow_run_id = query.get("workflow_run_id")
    if workflow_run_id is None:
        return
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=workflow_run_id,
        not_found_code="workflow_run_not_found",
        details={"workflow_run_id": workflow_run_id},
    )


def _assert_workflow_run_in_project(
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
            _raise_not_found(not_found_code, details)
        raise
    if workflow_run.get("project_id") != project_id:
        _raise_not_found(not_found_code, details)
    return workflow_run


def _assert_human_task_in_project(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    human_task_id: str,
) -> None:
    _require_project(connection, context=context, project_id=project_id)
    try:
        human_task = show_human_task_command(connection, human_task_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=str(human_task["workflow_run_id"]),
        not_found_code="human_task_not_found",
        details={"human_task_id": human_task_id},
    )


def _assert_approval_in_project(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    approval_id: str,
) -> None:
    _require_project(connection, context=context, project_id=project_id)
    try:
        approval = show_approval_command(connection, approval_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=str(approval["workflow_run_id"]),
        not_found_code="approval_not_found",
        details={"approval_id": approval_id},
    )


def _assert_flag_in_project(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    flag_id: str,
) -> None:
    _require_project(connection, context=context, project_id=project_id)
    try:
        flag = show_flag_command(connection, flag_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=str(flag["workflow_run_id"]),
        not_found_code="flag_not_found",
        details={"flag_id": flag_id},
    )


def _assert_artifact_in_project(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    project_id: str,
    artifact_version_id: str,
) -> None:
    _require_project(connection, context=context, project_id=project_id)
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    _assert_workflow_run_in_project(
        connection,
        context=context,
        project_id=project_id,
        workflow_run_id=str(artifact["workflow_run_id"]),
        not_found_code="artifact_version_not_found",
        details={"artifact_version_id": artifact_version_id},
    )


def _project_dashboard_counts(
    connection: sqlite3.Connection,
    *,
    project: dict[str, Any],
) -> dict[str, int]:
    project_id = str(project["project_id"])
    tenant_id = str(project["tenant_id"])
    domain_id = str(project["domain_id"])
    return {
        "workflow_run_count": _count(
            connection,
            """
            SELECT COUNT(*) AS count
            FROM workflow_runs
            WHERE project_id = ? AND tenant_id = ? AND domain_id = ?
            """,
            (project_id, tenant_id, domain_id),
        ),
        "open_human_task_count": _count_child(
            connection,
            "human_tasks ht",
            "ht.workflow_run_id",
            project_id,
            tenant_id,
            domain_id,
            "AND ht.state = 'OPEN'",
        ),
        "pending_approval_count": _count_child(
            connection,
            "approvals ap",
            "ap.workflow_run_id",
            project_id,
            tenant_id,
            domain_id,
            "AND ap.state = 'PENDING'",
        ),
        "active_flag_count": _count_child(
            connection,
            "flags f",
            "f.workflow_run_id",
            project_id,
            tenant_id,
            domain_id,
            "AND f.state IN ('open', 'triage', 'blocked')",
        ),
        "artifact_version_count": _count_child(
            connection,
            "artifact_versions av",
            "av.workflow_run_id",
            project_id,
            tenant_id,
            domain_id,
            "",
        ),
        "pointer_count": _count_child(
            connection,
            "artifact_pointers ap",
            "ap.workflow_run_id",
            project_id,
            tenant_id,
            domain_id,
            "",
        ),
        "timeline_event_count": _count(
            connection,
            """
            SELECT COUNT(*) AS count
            FROM timeline_events te
            LEFT JOIN workflow_runs wr ON wr.workflow_run_id = te.workflow_run_id
            WHERE te.tenant_id = ?
              AND te.domain_id = ?
              AND COALESCE(te.project_id, wr.project_id) = ?
            """,
            (tenant_id, domain_id, project_id),
        ),
    }


def _count_child(
    connection: sqlite3.Connection,
    table_ref: str,
    workflow_column: str,
    project_id: str,
    tenant_id: str,
    domain_id: str,
    extra_predicate: str,
) -> int:
    query = f"""
        SELECT COUNT(*) AS count
        FROM {table_ref}
        JOIN workflow_runs wr ON wr.workflow_run_id = {workflow_column}
        WHERE wr.project_id = ?
          AND wr.tenant_id = ?
          AND wr.domain_id = ?
          {extra_predicate}
    """
    return _count(connection, query, (project_id, tenant_id, domain_id))


def _count(connection: sqlite3.Connection, query: str, params: tuple[Any, ...]) -> int:
    row = connection.execute(query, params).fetchone()
    return int(row["count"])


def _raise_not_found(code: str, details: dict[str, Any]) -> None:
    raise ApiError(
        status_code=404,
        code=code,
        message="resource not found",
        details=details,
    )
