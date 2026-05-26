from __future__ import annotations

from onetruth.api.errors import ApiError
from onetruth.api.route_specs._core import (
    JSON_COMMAND_BODY,
    NO_BODY,
    RouteSpec,
    _param,
    _require_payload,
    require_connection,
    require_request_context,
)
from onetruth.api.routes.workpages import (
    add_workflow_run_driver_availability_exception_endpoint,
    apply_schedule_route_demand_coverage_endpoint,
    create_workflow_run_driver_preferences_snapshot_endpoint,
    create_workflow_run_route_demand_next_week_endpoint,
    create_workflow_run_eod_draft_endpoint,
    ensure_workflow_run_eod_intake_task_endpoint,
    mark_schedule_sick_no_show_endpoint,
    preview_workflow_run_artifact_workpage_endpoint,
    recommend_schedule_route_demand_coverage_endpoint,
    schedule_artifact_previous_week_reality_endpoint,
    save_and_run_route_demand_artifact_workpage_endpoint,
    submit_workflow_run_artifact_workpage_endpoint,
    workflow_run_artifact_workpage_endpoint,
    workflow_run_workpage_endpoint,
)


def _split_workflow_run_workpage_path(value: str) -> tuple[str, str]:
    workflow_run_id, separator, workpage_kind = value.partition("/")
    if not separator or not workflow_run_id or not workpage_kind or "/" in workpage_kind:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="route not found",
            details={"path_suffix": value},
        )
    return workflow_run_id, workpage_kind


def _dispatch_workflow_run_workpage(execution, raw_value: str):
    workflow_run_id, workpage_kind = _split_workflow_run_workpage_path(raw_value)
    return workflow_run_workpage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
    )


def _split_workflow_run_artifact_path(value: str) -> tuple[str, str, str]:
    workflow_run_id, separator, remainder = value.partition("/")
    if not separator or not workflow_run_id:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="route not found",
            details={"path_suffix": value},
        )
    workpage_kind, separator, artifact_segment = remainder.partition("/artifacts/")
    if not separator or not workpage_kind or not artifact_segment or "/" in workpage_kind:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="route not found",
            details={"path_suffix": value},
        )
    if "/" in artifact_segment:
        raise ApiError(
            status_code=404,
            code="not_found",
            message="route not found",
            details={"path_suffix": value},
        )
    return workflow_run_id, workpage_kind, artifact_segment


def _dispatch_workflow_run_artifact_workpage(execution, raw_value: str):
    workflow_run_id, workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return workflow_run_artifact_workpage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
    )


def _dispatch_schedule_previous_week_reality(execution, raw_value: str):
    workflow_run_id, workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return schedule_artifact_previous_week_reality_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
    )


def _dispatch_workflow_run_artifact_submit(execution, raw_value: str):
    workflow_run_id, workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return submit_workflow_run_artifact_workpage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        db_url=execution.db_url,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
        payload=_require_payload(execution.payload),
    )


def _dispatch_workflow_run_artifact_save_and_run(execution, raw_value: str):
    workflow_run_id, _workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return save_and_run_route_demand_artifact_workpage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        db_url=execution.db_url,
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
        payload=_require_payload(execution.payload),
    )


def _dispatch_workflow_run_artifact_preview(execution, raw_value: str):
    workflow_run_id, workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return preview_workflow_run_artifact_workpage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
        payload=_require_payload(execution.payload),
    )


def _dispatch_schedule_sick_no_show(execution, raw_value: str):
    workflow_run_id, workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return mark_schedule_sick_no_show_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        db_url=execution.db_url,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
        payload=_require_payload(execution.payload),
    )


def _dispatch_schedule_route_demand_coverage_candidates(execution, raw_value: str):
    workflow_run_id, workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return recommend_schedule_route_demand_coverage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
        payload=_require_payload(execution.payload),
    )


def _dispatch_schedule_route_demand_coverage(execution, raw_value: str):
    workflow_run_id, workpage_kind, artifact_version_id = _split_workflow_run_artifact_path(
        raw_value
    )
    return apply_schedule_route_demand_coverage_endpoint(
        require_connection(execution.connection),
        context=require_request_context(execution.context),
        db_url=execution.db_url,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
        payload=_require_payload(execution.payload),
    )


WORKPAGE_ROUTE_SPECS: tuple[RouteSpec, ...] = (
    RouteSpec(
        name="workpages.workflow_run.artifact.preview",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_artifact_preview",
            suffix="/preview",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_workflow_run_artifact_preview(
            execution,
            params["workflow_run_artifact_preview"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.route_demand.artifact.save_and_run",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_artifact_save_and_run",
            suffix="/save-and-run",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_workflow_run_artifact_save_and_run(
            execution,
            params["workflow_run_artifact_save_and_run"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.schedule.sick_no_show",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_schedule_sick_no_show",
            suffix="/sick-no-show",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_schedule_sick_no_show(
            execution,
            params["workflow_run_schedule_sick_no_show"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.schedule.route_demand_coverage_candidates",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_schedule_route_demand_coverage_candidates",
            suffix="/route-demand-coverage-candidates",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_schedule_route_demand_coverage_candidates(
            execution,
            params["workflow_run_schedule_route_demand_coverage_candidates"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.schedule.route_demand_coverage",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_schedule_route_demand_coverage",
            suffix="/route-demand-coverage",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_schedule_route_demand_coverage(
            execution,
            params["workflow_run_schedule_route_demand_coverage"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.schedule.previous_week_reality",
        method="GET",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_schedule_previous_week_reality",
            suffix="/reality/previous-week",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_schedule_previous_week_reality(
            execution,
            params["workflow_run_schedule_previous_week_reality"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.artifact.detail",
        method="GET",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_artifact",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_workflow_run_artifact_workpage(
            execution,
            params["workflow_run_artifact"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.artifact.submit",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_artifact_submit",
            suffix="/submit",
            allow_slash=True,
            required_substring="/artifacts/",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_workflow_run_artifact_submit(
            execution,
            params["workflow_run_artifact_submit"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.detail",
        method="GET",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_workpage",
            allow_slash=True,
        ),
        body_policy=NO_BODY,
        needs_page=False,
        dispatch=lambda execution, params: _dispatch_workflow_run_workpage(
            execution,
            params["workflow_run_workpage"],
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.eod_drafts.create",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/eod-v0/drafts",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: create_workflow_run_eod_draft_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            db_url=execution.db_url,
            workflow_run_id=params["workflow_run_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.route_demand.next_week.create",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/route-demand-v0/next-week",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: create_workflow_run_route_demand_next_week_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            db_url=execution.db_url,
            workflow_run_id=params["workflow_run_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.eod_intake.ensure",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/eod-v0/intake-task",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: ensure_workflow_run_eod_intake_task_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            workflow_run_id=params["workflow_run_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.driver_preferences.snapshots.create",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/driver-preferences-v0/snapshots",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: create_workflow_run_driver_preferences_snapshot_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            db_url=execution.db_url,
            workflow_run_id=params["workflow_run_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
    RouteSpec(
        name="workpages.workflow_run.driver_preferences.availability_exceptions.add",
        method="POST",
        pattern=_param(
            "/api/v1/workpages/workflow-runs/",
            param_name="workflow_run_id",
            suffix="/driver-preferences-v0/availability-exceptions",
        ),
        body_policy=JSON_COMMAND_BODY,
        needs_page=False,
        dispatch=lambda execution, params: add_workflow_run_driver_availability_exception_endpoint(
            require_connection(execution.connection),
            context=require_request_context(execution.context),
            db_url=execution.db_url,
            workflow_run_id=params["workflow_run_id"],
            payload=_require_payload(execution.payload),
        ),
    ),
)
