from __future__ import annotations

from onetruth.api.routes.pointers import list_pointers_endpoint
from onetruth.api.route_specs._core import NO_BODY, RouteSpec, _exact, _require_page

POINTER_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="pointers.list",
        method="GET",
        pattern=_exact("/api/v1/pointers"),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, _params: list_pointers_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
)
