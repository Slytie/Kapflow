from __future__ import annotations

from onetruth.api.route_specs._core import (
    NO_BODY,
    RouteSpec,
    _exact,
    require_connection,
    require_request_context,
)
from onetruth.api.routes.operator_home import get_operator_home_endpoint


OPERATOR_HOME_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="operator.home",
        method="GET",
        pattern=_exact("/api/v1/operator/home"),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, _params: get_operator_home_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            boundary_profile=execution.boundary_profile,
        ),
    ),
)
