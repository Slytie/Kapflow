from __future__ import annotations

from onetruth.api.routes.capex_projects import (
    create_capex_project_endpoint,
    create_project_workflow_run_endpoint,
    get_capex_project_endpoint,
    grant_project_membership_endpoint,
    list_capex_projects_endpoint,
    list_project_memberships_endpoint,
)
from onetruth.api.route_specs._core import (
    JSON_COMMAND_BODY,
    NO_BODY,
    RouteSpec,
    _exact,
    _param,
    _require_page,
    _require_payload,
)

CAPEX_PROJECT_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="capex.projects.list",
        method="GET",
        pattern=_exact("/api/v1/capex/projects"),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, _params: list_capex_projects_endpoint(
            execution.connection,
            context=execution.context,
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="capex.projects.create",
        method="POST",
        pattern=_exact("/api/v1/capex/projects"),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, _params: create_capex_project_endpoint(
            execution.connection,
            context=execution.context,
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="capex.projects.memberships.list",
        method="GET",
        pattern=_param(
            "/api/v1/capex/projects/",
            param_name="project_id",
            suffix="/memberships",
        ),
        body_policy=NO_BODY,
        needs_page=True,
        dispatch=lambda execution, params: list_project_memberships_endpoint(
            execution.connection,
            context=execution.context,
            project_id=params["project_id"],
            page=_require_page(execution.page),
        ),
    ),
    RouteSpec(
        name="capex.projects.memberships.grant",
        method="POST",
        pattern=_param(
            "/api/v1/capex/projects/",
            param_name="project_id",
            suffix="/memberships",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: grant_project_membership_endpoint(
            execution.connection,
            context=execution.context,
            project_id=params["project_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="capex.projects.workflow_runs.create",
        method="POST",
        pattern=_param(
            "/api/v1/capex/projects/",
            param_name="project_id",
            suffix="/workflow-runs",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: create_project_workflow_run_endpoint(
            execution.connection,
            context=execution.context,
            project_id=params["project_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="capex.projects.detail",
        method="GET",
        pattern=_param("/api/v1/capex/projects/", param_name="project_id"),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: get_capex_project_endpoint(
            execution.connection,
            context=execution.context,
            project_id=params["project_id"],
        ),
    ),
)
