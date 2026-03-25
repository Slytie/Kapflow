from __future__ import annotations

from onetruth.api.route_specs._core import (
    NO_BODY,
    RouteSpec,
    _param,
    require_request_context,
)
from onetruth.api.routes.workpages import demo_workpage_endpoint


WORKPAGE_ROUTE_SPECS: tuple[RouteSpec, ...] = (
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
