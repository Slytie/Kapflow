from __future__ import annotations

from onetruth.api.errors import ApiError
from onetruth.api.route_specs._core import (
    JSON_COMMAND_BODY,
    NO_BODY,
    RouteSpec,
    _exact,
    _param,
    _require_payload,
    require_connection,
    require_request_context,
)
from onetruth.api.routes.workpages import (
    artifact_workpage_endpoint,
    create_demo_eod_draft_endpoint,
    demo_workpage_endpoint,
    submit_artifact_workpage_endpoint,
    workflow_run_workpage_endpoint,
)


def _split_workflow_run_workpage_path(value: str) -> tuple[str, str]:
    workflow_run_id, separator, workpage_kind = value.partition("/")
    if not separator or not workflow_run_id or not workpage_kind or "/" in workpage_kind:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="route not found",
            details={"path_suffix": value},
        )
    return workflow_run_id, workpage_kind


def _dispatch_workflow_run_workpage(execution, raw_value: str):
    workflow_run_id, workpage_kind = _split_workflow_run_workpage_path(raw_value)
    return workflow_run_workpage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
    )


WORKPAGE_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="workpages.workflow_run.detail",
        method="GET",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_workpage",
            allow_slash=True,
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_workflow_run_workpage(
            execution,
            params["workflow_run_workpage"],
        ),
    ),
    RouteSpec(
        name="workpages.eod_drafts.create",
        method="POST",
        pattern=_exact("/api/v1/workpages/demo/eod-v0/drafts"),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, _params: create_demo_eod_draft_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            db_url=execution.db_url,
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workpages.artifact.detail",
        method="GET",
        pattern=_param(
            "/api/v1/workpages/artifacts/",
            param_name="artifact_version_id",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: artifact_workpage_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            artifact_version_id=params["artifact_version_id"],
        ),
    ),
    RouteSpec(
        name="workpages.artifact.submit",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/artifacts/",
            param_name="artifact_version_id",
            suffix="/submit",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: submit_artifact_workpage_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            db_url=execution.db_url,
            artifact_version_id=params["artifact_version_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workpages.demo.detail",
        method="GET",
        pattern=_param("/api/v1/workpages/demo/", param_name="workpage_id"),
        body_policy=NO_BODY,
        needs_page=False,
        needs_db_connection=False,
        dispatch=lambda execution, params: demo_workpage_endpoint(
            context=require_request_context(execution.context),
            workpage_id=params["workpage_id"],
        ),
    ),
)
