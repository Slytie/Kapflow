from __future__ import annotations

from onetruth.api.routes.approvals import (
    get_approval_endpoint,
    list_approvals_endpoint,
    respond_approval_endpoint,
)
from onetruth.api.routes.artifacts import (
    list_approval_artifacts_endpoint,
    upload_approval_artifact_endpoint,
)
from onetruth.api.route_specs._core import (
    JSON_ARTIFACT_BODY,
    JSON_COMMAND_BODY,
    NO_BODY,
    RouteSpec,
    _exact,
    _param,
    _require_page,
    _require_payload,
)

APPROVAL_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="approvals.list",
        method="GET",
        pattern=_exact("/api/v1/approvals"),
        body_policy=NO_BODY,
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
        body_policy=NO_BODY,
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
        body_policy=NO_BODY,
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
        body_policy=JSON_ARTIFACT_BODY,
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
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: respond_approval_endpoint(
            execution.connection,
            context=execution.context,
            approval_id=params["approval_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
)
