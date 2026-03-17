from __future__ import annotations

from onetruth.api.route_specs._core import NO_BODY, RouteSpec, _exact
from onetruth.api.routes.ops import health_endpoint, metrics_endpoint, readiness_endpoint

OPS_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="ops.health",
        method="GET",
        pattern=_exact("/api/v1/ops/health"),
        body_policy=NO_BODY,
        needs_page=False,
        requires_request_context=False,
        needs_db_connection=False,
        dispatch=lambda _execution, _params: health_endpoint(),
    ),
    RouteSpec(
        name="ops.readiness",
        method="GET",
        pattern=_exact("/api/v1/ops/readiness"),
        body_policy=NO_BODY,
        needs_page=False,
        requires_request_context=False,
        needs_db_connection=False,
        dispatch=lambda execution, _params: readiness_endpoint(db_url=execution.db_url),
    ),
    RouteSpec(
        name="ops.metrics",
        method="GET",
        pattern=_exact("/api/v1/ops/metrics"),
        body_policy=NO_BODY,
        needs_page=False,
        requires_request_context=False,
        needs_db_connection=False,
        dispatch=lambda execution, _params: metrics_endpoint(db_url=execution.db_url),
    ),
)
