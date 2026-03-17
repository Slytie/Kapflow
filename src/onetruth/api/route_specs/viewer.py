from __future__ import annotations

from onetruth.api.routes.viewer import get_viewer_session_endpoint
from onetruth.api.route_specs._core import NO_BODY, RouteSpec, _exact

VIEWER_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="viewer.bootstrap",
        method="GET",
        pattern=_exact("/api/v1/viewer"),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, _params: get_viewer_session_endpoint(
            context=execution.context,
            boundary_profile=execution.boundary_profile,
        ),
    ),
)
