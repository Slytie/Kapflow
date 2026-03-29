from __future__ import annotations

from onetruth.api.routes.artifacts import (
    list_workflow_run_artifacts_endpoint,
    upload_workflow_run_artifact_endpoint,
)
from onetruth.api.routes.timeline import list_workflow_run_timeline_endpoint
from onetruth.api.routes.workflow_runs import (
    get_workflow_run_detail_endpoint,
    get_workflow_run_workspace_endpoint,
    list_workflow_runs_endpoint,
    prepare_live_dispatch_day_endpoint,
)
from onetruth.api.route_specs._core import (
    JSON_ARTIFACT_BODY,
    NO_BODY,
    RouteSpec,
    _exact,
    _param,
    _require_page,
    _require_payload,
)

WORKFLOW_RUN_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="workflow_runs.list",
        method="GET",
        pattern=_exact("/api/v1/workflow-runs"),
        body_policy=NO_BODY,
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
        body_policy=NO_BODY,
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
        body_policy=JSON_ARTIFACT_BODY,
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
        body_policy=NO_BODY,
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
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: get_workflow_run_workspace_endpoint(
            execution.connection,
            context=execution.context,
            workflow_run_id=params["workflow_run_id"],
            query=execution.query,
        ),
    ),
    RouteSpec(
        name="workflow_runs.prepare_live_dispatch_day",
        method="POST",
        pattern=_param(
            "/api/v1/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/prepare-live-dispatch-day",
        ),
        body_policy=JSON_ARTIFACT_BODY,
        needs_page=False,
        dispatch=lambda execution, params: prepare_live_dispatch_day_endpoint(
            execution.connection,
            context=execution.context,
            workflow_run_id=params["workflow_run_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workflow_runs.detail",
        method="GET",
        pattern=_param(
            "/api/v1/workflow-runs/",
            param_name="workflow_run_id",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: get_workflow_run_detail_endpoint(
            execution.connection,
            context=execution.context,
            workflow_run_id=params["workflow_run_id"],
        ),
    ),
)
