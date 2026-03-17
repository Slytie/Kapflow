from __future__ import annotations

from onetruth.api.routes.board import schedule_planning_board_endpoint
from onetruth.api.route_specs._core import NO_BODY, RouteSpec, _exact, _require_page

BOARD_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="board.schedule_planning",
        method="GET",
        pattern=_exact("/api/v1/board/schedule-planning"),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, _params: schedule_planning_board_endpoint(
            execution.connection,
            context=execution.context,
            query=execution.query,
            page=_require_page(execution.page),
        ),
    ),
)
