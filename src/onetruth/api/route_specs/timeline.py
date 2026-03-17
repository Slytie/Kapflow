from __future__ import annotations

from onetruth.api.routes.timeline import list_timeline_events_endpoint
from onetruth.api.route_specs._core import NO_BODY, RouteSpec, _exact, _require_page

TIMELINE_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="timeline_events.list",
        method="GET",
        pattern=_exact("/api/v1/timeline-events"),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, _params: list_timeline_events_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
)
