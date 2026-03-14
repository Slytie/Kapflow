from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Callable, Literal

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.errors import ApiError
from onetruth.api.routes.approvals import (
    get_approval_endpoint,
    list_approvals_endpoint,
    respond_approval_endpoint,
)
from onetruth.api.routes.artifacts import (
    download_artifact_endpoint,
    get_artifact_endpoint,
    ingest_artifact_endpoint,
    list_approval_artifacts_endpoint,
    list_artifacts_endpoint,
    list_flag_artifacts_endpoint,
    list_human_task_artifacts_endpoint,
    list_workflow_run_artifacts_endpoint,
    upload_approval_artifact_endpoint,
    upload_flag_artifact_endpoint,
    upload_human_task_artifact_endpoint,
    upload_workflow_run_artifact_endpoint,
)
from onetruth.api.routes.board import schedule_planning_board_endpoint
from onetruth.api.routes.flags import (
    get_flag_endpoint,
    list_flags_endpoint,
    transition_flag_endpoint,
)
from onetruth.api.routes.human_tasks import (
    claim_human_task_endpoint,
    complete_human_task_endpoint,
    confirm_human_task_review_endpoint,
    get_human_task_endpoint,
    get_human_task_subgraph_endpoint,
    list_human_tasks_endpoint,
    run_stage06_agent_review_endpoint,
    run_weekly_stage04_openai_agent_endpoint,
)
from onetruth.api.routes.logistics_story import (
    logistics_three_workflow_story_endpoint,
)
from onetruth.api.routes.pointers import list_pointers_endpoint
from onetruth.api.routes.templates import (
    download_template_endpoint,
    get_template_endpoint,
    list_templates_endpoint,
)
from onetruth.api.routes.timeline import (
    list_timeline_events_endpoint,
    list_workflow_run_timeline_endpoint,
)
from onetruth.api.routes.workflow_runs import (
    get_workflow_run_detail_endpoint,
    get_workflow_run_workspace_endpoint,
    list_workflow_runs_endpoint,
)

BodyMode = Literal["none", "json"]
RouteDispatcher = Callable[["RouteExecutionContext", dict[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class RoutePattern:
    exact_path: str | None = None
    prefix: str | None = None
    suffix: str = ""
    param_name: str | None = None
    allow_slash: bool = False

    def match(self, path: str) -> dict[str, str] | None:
        if self.exact_path is not None:
            if path == self.exact_path:
                return {}
            return None

        assert self.prefix is not None
        assert self.param_name is not None

        if not path.startswith(self.prefix):
            return None
        if self.suffix:
            if not path.endswith(self.suffix):
                return None
            if len(path) <= len(self.prefix) + len(self.suffix):
                return None
            value = path[len(self.prefix) : -len(self.suffix)]
        else:
            value = path[len(self.prefix) :]
            if not value:
                return None

        if not value:
            return None
        if not self.allow_slash and "/" in value:
            return None
        return {self.param_name: value}


@dataclass(frozen=True)
class RouteSpec:
    name: str
    method: str
    pattern: RoutePattern
    body_mode: BodyMode
    needs_page: bool
    dispatch: RouteDispatcher


@dataclass(frozen=True)
class RouteMatch:
    route: RouteSpec
    params: dict[str, str]

    def dispatch(self, execution: "RouteExecutionContext") -> dict[str, Any]:
        return self.route.dispatch(execution, self.params)


@dataclass(frozen=True)
class RouteExecutionContext:
    connection: sqlite3.Connection
    context: RequestContext
    query: dict[str, str]
    page: Page | None
    payload: dict[str, Any] | None
    db_url: str


def _exact(path: str) -> RoutePattern:
    return RoutePattern(exact_path=path)


def _param(
    prefix: str,
    *,
    param_name: str,
    suffix: str = "",
    allow_slash: bool = False,
) -> RoutePattern:
    return RoutePattern(
        prefix=prefix,
        suffix=suffix,
        param_name=param_name,
        allow_slash=allow_slash,
    )


def _require_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        raise ApiError(
            status_code=400,
            code="invalid_payload",
            message="request body is required",
            details={},
        )
    return payload


def _require_page(page: Page | None) -> Page:
    assert page is not None
    return page


ROUTES: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="human_tasks.list",
        method="GET",
        pattern=_exact("/api/v1/human-tasks"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_human_tasks_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="human_tasks.detail",
        method="GET",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_human_task_endpoint(
            execution.connection,
            context=execution.context,
            human_task_id=params["human_task_id"],
        ),
    ),
    RouteSpec(
        name="human_tasks.subgraph",
        method="GET",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/subgraph",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_human_task_subgraph_endpoint(
            execution.connection,
            context=execution.context,
            human_task_id=params["human_task_id"],
        ),
    ),
    RouteSpec(
        name="human_tasks.artifacts.list",
        method="GET",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/artifacts",
        ),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, params: list_human_task_artifacts_endpoint(
            execution.connection,
            context=execution.context,
            human_task_id=params["human_task_id"],
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="human_tasks.artifacts.upload",
        method="POST",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/artifacts/upload",
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: upload_human_task_artifact_endpoint(
            execution.connection,
            context=execution.context,
            db_url=execution.db_url,
            human_task_id=params["human_task_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="human_tasks.claim",
        method="POST",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/claim",
            allow_slash=True,
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: claim_human_task_endpoint(
            execution.connection,
            context=execution.context,
            human_task_id=params["human_task_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="human_tasks.complete",
        method="POST",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/complete",
            allow_slash=True,
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: complete_human_task_endpoint(
            execution.connection,
            context=execution.context,
            human_task_id=params["human_task_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="human_tasks.confirm_review",
        method="POST",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/confirm-review",
            allow_slash=True,
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: confirm_human_task_review_endpoint(
            execution.connection,
            context=execution.context,
            db_url=execution.db_url,
            human_task_id=params["human_task_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="human_tasks.stage06_agent_review",
        method="POST",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/stage06-agent-review",
            allow_slash=True,
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: run_stage06_agent_review_endpoint(
            execution.connection,
            context=execution.context,
            human_task_id=params["human_task_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="human_tasks.weekly_stage04_openai_agent",
        method="POST",
        pattern=_param(
            "/api/v1/human-tasks/",
            param_name="human_task_id",
            suffix="/weekly-stage04-openai-agent",
            allow_slash=True,
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: run_weekly_stage04_openai_agent_endpoint(
            execution.connection,
            context=execution.context,
            human_task_id=params["human_task_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="approvals.list",
        method="GET",
        pattern=_exact("/api/v1/approvals"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_approvals_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="approvals.detail",
        method="GET",
        pattern=_param(
            "/api/v1/approvals/",
            param_name="approval_id",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_approval_endpoint(
            execution.connection,
            context=execution.context,
            approval_id=params["approval_id"],
        ),
    ),
    RouteSpec(
        name="approvals.artifacts.list",
        method="GET",
        pattern=_param(
            "/api/v1/approvals/",
            param_name="approval_id",
            suffix="/artifacts",
        ),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, params: list_approval_artifacts_endpoint(
            execution.connection,
            context=execution.context,
            approval_id=params["approval_id"],
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="approvals.artifacts.upload",
        method="POST",
        pattern=_param(
            "/api/v1/approvals/",
            param_name="approval_id",
            suffix="/artifacts/upload",
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: upload_approval_artifact_endpoint(
            execution.connection,
            context=execution.context,
            db_url=execution.db_url,
            approval_id=params["approval_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="approvals.respond",
        method="POST",
        pattern=_param(
            "/api/v1/approvals/",
            param_name="approval_id",
            suffix="/respond",
            allow_slash=True,
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: respond_approval_endpoint(
            execution.connection,
            context=execution.context,
            approval_id=params["approval_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="flags.list",
        method="GET",
        pattern=_exact("/api/v1/flags"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_flags_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="flags.detail",
        method="GET",
        pattern=_param(
            "/api/v1/flags/",
            param_name="flag_id",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_flag_endpoint(
            execution.connection,
            context=execution.context,
            flag_id=params["flag_id"],
        ),
    ),
    RouteSpec(
        name="flags.artifacts.list",
        method="GET",
        pattern=_param(
            "/api/v1/flags/",
            param_name="flag_id",
            suffix="/artifacts",
        ),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, params: list_flag_artifacts_endpoint(
            execution.connection,
            context=execution.context,
            flag_id=params["flag_id"],
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="flags.artifacts.upload",
        method="POST",
        pattern=_param(
            "/api/v1/flags/",
            param_name="flag_id",
            suffix="/artifacts/upload",
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: upload_flag_artifact_endpoint(
            execution.connection,
            context=execution.context,
            db_url=execution.db_url,
            flag_id=params["flag_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="flags.transition",
        method="POST",
        pattern=_param(
            "/api/v1/flags/",
            param_name="flag_id",
            suffix="/transition",
            allow_slash=True,
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: transition_flag_endpoint(
            execution.connection,
            context=execution.context,
            flag_id=params["flag_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workflow_runs.list",
        method="GET",
        pattern=_exact("/api/v1/workflow-runs"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_workflow_runs_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="workflow_runs.artifacts.list",
        method="GET",
        pattern=_param(
            "/api/v1/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/artifacts",
        ),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, params: list_workflow_run_artifacts_endpoint(
            execution.connection,
            context=execution.context,
            workflow_run_id=params["workflow_run_id"],
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="workflow_runs.artifacts.upload",
        method="POST",
        pattern=_param(
            "/api/v1/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/artifacts/upload",
        ),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, params: upload_workflow_run_artifact_endpoint(
            execution.connection,
            context=execution.context,
            db_url=execution.db_url,
            workflow_run_id=params["workflow_run_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workflow_runs.timeline",
        method="GET",
        pattern=_param(
            "/api/v1/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/timeline",
            allow_slash=True,
        ),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, params: list_workflow_run_timeline_endpoint(
            execution.connection,
            context=execution.context,
            workflow_run_id=params["workflow_run_id"],
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="workflow_runs.workspace",
        method="GET",
        pattern=_param(
            "/api/v1/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/workspace",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_workflow_run_workspace_endpoint(
            execution.connection,
            context=execution.context,
            workflow_run_id=params["workflow_run_id"],
            query=execution.query,
        ),
    ),
    RouteSpec(
        name="workflow_runs.detail",
        method="GET",
        pattern=_param(
            "/api/v1/workflow-runs/",
            param_name="workflow_run_id",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_workflow_run_detail_endpoint(
            execution.connection,
            context=execution.context,
            workflow_run_id=params["workflow_run_id"],
        ),
    ),
    RouteSpec(
        name="pointers.list",
        method="GET",
        pattern=_exact("/api/v1/pointers"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_pointers_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="templates.list",
        method="GET",
        pattern=_exact("/api/v1/templates"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_templates_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="templates.download",
        method="GET",
        pattern=_param(
            "/api/v1/templates/",
            param_name="template_id",
            suffix="/download",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: download_template_endpoint(
            execution.connection,
            context=execution.context,
            template_id=params["template_id"],
        ),
    ),
    RouteSpec(
        name="templates.detail",
        method="GET",
        pattern=_param(
            "/api/v1/templates/",
            param_name="template_id",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_template_endpoint(
            execution.connection,
            context=execution.context,
            template_id=params["template_id"],
        ),
    ),
    RouteSpec(
        name="artifacts.ingest",
        method="POST",
        pattern=_exact("/api/v1/artifacts/ingest"),
        body_mode="json",
        needs_page=False,
        dispatch=lambda execution, _params: ingest_artifact_endpoint(
            execution.connection,
            context=execution.context,
            db_url=execution.db_url,
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="artifacts.list",
        method="GET",
        pattern=_exact("/api/v1/artifacts"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_artifacts_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="artifacts.download",
        method="GET",
        pattern=_param(
            "/api/v1/artifacts/",
            param_name="artifact_version_id",
            suffix="/download",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: download_artifact_endpoint(
            execution.connection,
            context=execution.context,
            artifact_version_id=params["artifact_version_id"],
        ),
    ),
    RouteSpec(
        name="artifacts.detail",
        method="GET",
        pattern=_param(
            "/api/v1/artifacts/",
            param_name="artifact_version_id",
        ),
        body_mode="none",
        needs_page=False,
        dispatch=lambda execution, params: get_artifact_endpoint(
            execution.connection,
            context=execution.context,
            artifact_version_id=params["artifact_version_id"],
        ),
    ),
    RouteSpec(
        name="timeline_events.list",
        method="GET",
        pattern=_exact("/api/v1/timeline-events"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: list_timeline_events_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="board.schedule_planning",
        method="GET",
        pattern=_exact("/api/v1/board/schedule-planning"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: schedule_planning_board_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="stories.logistics_three_workflow",
        method="GET",
        pattern=_exact("/api/v1/stories/logistics-three-workflow"),
        body_mode="none",
        needs_page=True,
        dispatch=lambda execution, _params: logistics_three_workflow_story_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
)


def match_route(method: str, path: str) -> RouteMatch | None:
    for route in ROUTES:
        if route.method != method:
            continue
        params = route.pattern.match(path)
        if params is not None:
            return RouteMatch(route=route, params=params)
    return None
