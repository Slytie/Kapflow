from __future__ import annotations

from onetruth.api.routes.logistics_story import (
    logistics_three_workflow_story_endpoint,
)
from onetruth.api.route_specs._core import NO_BODY, RouteSpec, _exact, _require_page

LOGISTICS_STORY_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="stories.logistics_three_workflow",
        method="GET",
        pattern=_exact("/api/v1/stories/logistics-three-workflow"),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, _params: logistics_three_workflow_story_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
)
