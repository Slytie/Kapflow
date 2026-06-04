from __future__ import annotations

from onetruth.api.route_specs._core import (
    JSON_ARTIFACT_BODY,
    JSON_COMMAND_BODY,
    NO_BODY,
    RequestBodyKind,
    RequestBodyPolicy,
    RouteDispatcher,
    RouteExecutionContext,
    RouteMatch,
    RoutePattern,
    RouteResult,
    RouteSpec,
)
from onetruth.api.route_specs.approvals import APPROVAL_ROUTE_SPECS
from onetruth.api.route_specs.artifacts import ARTIFACT_ROUTE_SPECS
from onetruth.api.route_specs.board import BOARD_ROUTE_SPECS
from onetruth.api.route_specs.capex_projects import CAPEX_PROJECT_ROUTE_SPECS
from onetruth.api.route_specs.flags import FLAG_ROUTE_SPECS
from onetruth.api.route_specs.human_tasks import HUMAN_TASK_ROUTE_SPECS
from onetruth.api.route_specs.logistics_story import LOGISTICS_STORY_ROUTE_SPECS
from onetruth.api.route_specs.operator_home import OPERATOR_HOME_ROUTE_SPECS
from onetruth.api.route_specs.ops import OPS_ROUTE_SPECS
from onetruth.api.route_specs.pointers import POINTER_ROUTE_SPECS
from onetruth.api.route_specs.templates import TEMPLATE_ROUTE_SPECS
from onetruth.api.route_specs.timeline import TIMELINE_ROUTE_SPECS
from onetruth.api.route_specs.viewer import VIEWER_ROUTE_SPECS
from onetruth.api.route_specs.workpages import WORKPAGE_ROUTE_SPECS
from onetruth.api.route_specs.workflow_runs import WORKFLOW_RUN_ROUTE_SPECS

ROUTES: tuple[RouteSpec, ...] = (
    *OPS_ROUTE_SPECS,
    *VIEWER_ROUTE_SPECS,
    *OPERATOR_HOME_ROUTE_SPECS,
    *HUMAN_TASK_ROUTE_SPECS,
    *APPROVAL_ROUTE_SPECS,
    *FLAG_ROUTE_SPECS,
    *CAPEX_PROJECT_ROUTE_SPECS,
    *WORKFLOW_RUN_ROUTE_SPECS,
    *POINTER_ROUTE_SPECS,
    *TEMPLATE_ROUTE_SPECS,
    *ARTIFACT_ROUTE_SPECS,
    *TIMELINE_ROUTE_SPECS,
    *BOARD_ROUTE_SPECS,
    *LOGISTICS_STORY_ROUTE_SPECS,
    *WORKPAGE_ROUTE_SPECS,
)


def match_route(method: str, path: str) -> RouteMatch | None:
    for route in ROUTES:
        if route.method != method:
            continue
        params = route.pattern.match(path)
        if params is not None:
            return RouteMatch(route=route, params=params)
    return None


__all__ = [
    "JSON_ARTIFACT_BODY",
    "JSON_COMMAND_BODY",
    "NO_BODY",
    "ROUTES",
    "RequestBodyKind",
    "RequestBodyPolicy",
    "RouteDispatcher",
    "RouteExecutionContext",
    "RouteMatch",
    "RoutePattern",
    "RouteResult",
    "RouteSpec",
    "match_route",
]
