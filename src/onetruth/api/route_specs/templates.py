from __future__ import annotations

from onetruth.api.routes.templates import (
    download_template_binary_endpoint,
    download_template_endpoint,
    get_template_endpoint,
    list_templates_endpoint,
)
from onetruth.api.route_specs._core import NO_BODY, RouteSpec, _exact, _param, _require_page

TEMPLATE_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="templates.list",
        method="GET",
        pattern=_exact("/api/v1/templates"),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, _params: list_templates_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="templates.download.binary",
        method="GET",
        pattern=_param(
            "/api/v1/templates/",
            param_name="template_id",
            suffix="/download.bin",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: download_template_binary_endpoint(
            execution.connection,
            context=execution.context,
            template_id=params["template_id"],
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
        body_policy=NO_BODY,
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
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: get_template_endpoint(
            execution.connection,
            context=execution.context,
            template_id=params["template_id"],
        ),
    ),
)
