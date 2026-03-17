from __future__ import annotations

from onetruth.api.routes.artifacts import (
    list_flag_artifacts_endpoint,
    upload_flag_artifact_endpoint,
)
from onetruth.api.routes.flags import (
    get_flag_endpoint,
    list_flags_endpoint,
    transition_flag_endpoint,
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

FLAG_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="flags.list",
        method="GET",
        pattern=_exact("/api/v1/flags"),
        body_policy=NO_BODY,
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
        body_policy=NO_BODY,
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
        body_policy=NO_BODY,
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
        body_policy=JSON_ARTIFACT_BODY,
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
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: transition_flag_endpoint(
            execution.connection,
            context=execution.context,
            flag_id=params["flag_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
)
