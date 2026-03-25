from __future__ import annotations

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
)


WORKPAGE_ROUTE_SPECS: tuple[RouteSpec, ...] = (
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
