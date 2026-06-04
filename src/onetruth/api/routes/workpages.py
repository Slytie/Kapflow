from __future__ import annotations

import sqlite3

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.workpages import (
    add_driver_availability_exception_command,
    apply_schedule_route_demand_coverage_command,
    create_workflow_run_driver_preferences_snapshot_command,
    create_workflow_run_route_demand_next_week_command,
    create_workflow_run_eod_draft_command,
    ensure_workflow_run_eod_intake_task_command,
    mark_schedule_sick_no_show_command,
    preview_schedule_artifact_workpage_command,
    recommend_schedule_route_demand_coverage_command,
    save_and_run_route_demand_artifact_workpage_command,
    submit_driver_preferences_artifact_workpage_command,
    submit_route_demand_artifact_workpage_command,
    submit_eod_artifact_workpage_command,
    submit_schedule_artifact_workpage_command,
)
from onetruth.api.dependencies import RequestContext, scoped_workflow_run
from onetruth.api.errors import ApiError, api_error_from_command
from onetruth.application.read_commands import (
    list_artifacts_for_workflow_run_command,
    show_artifact_version_command,
)
from onetruth.application.services.logistics_workpages import (
    WorkpageProjectionUnavailableError,
    build_eod_artifact_workpage_contract,
    build_driver_preferences_artifact_workpage_contract,
    build_driver_preferences_workflow_run_workpage_contract,
    build_eod_workflow_run_workpage_contract,
    build_route_demand_artifact_workpage_contract,
    build_schedule_previous_week_reality_contract,
    build_route_demand_workflow_run_workpage_contract,
    build_schedule_artifact_workpage_contract,
    build_schedule_workflow_run_workpage_contract,
)
from onetruth.application.services.logistics_workpage_descriptors import (
    logistics_workpage_descriptor_registry,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    DATASET_KEY as EOD_DATASET_KEY,
    WORKFLOW_ID as EOD_WORKFLOW_ID,
    project_upd_draft_workbook,
)
from onetruth.application.services.schedule_control.draft_workbook import (
    draft_workbook_bytes_from_metadata_json,
    project_stage04_draft_weekly_schedule_workbook,
)
from onetruth.application.services.schedule_control.route_demand_workbook import (
    project_route_demand_workbook,
    route_demand_workbook_bytes_from_metadata_json,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    project_driver_preferences_workbook,
    driver_preferences_workbook_bytes_from_metadata_json,
)
from onetruth.application.services.workpage_descriptors import (
    DRIVER_PREFERENCES_WORKPAGE_KIND,
    EOD_WORKPAGE_KIND,
    ROUTE_DEMAND_WORKPAGE_KIND,
    SCHEDULE_WORKPAGE_KIND,
    WorkpageDescriptor,
)
from onetruth.infrastructure.artifacts.storage import (
    ArtifactStorageError,
    default_storage_root_for_db_url,
    read_blob,
)
from onetruth.integrations.openai import (
    OpenAIConfigError,
    OpenAIResponsesError,
)


def workflow_run_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    workflow_id = str(workflow_run.get("workflow_id") or "")
    descriptor = logistics_workpage_descriptor_registry().descriptor_for_public_run(
        workpage_kind=workpage_kind,
        workflow_id=workflow_id,
    )
    if descriptor is None:
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={
                "workflow_run_id": workflow_run_id,
                "workpage_id": workpage_kind,
            },
        )

    try:
        contract = _build_workflow_run_workpage_contract(
            connection,
            descriptor=descriptor,
            workflow_run=workflow_run,
        )
    except WorkpageProjectionUnavailableError as exc:
        raise ApiError(
            status_code=409,
            code="workpage_projection_unavailable",
            message=str(exc),
            details={
                "workflow_run_id": exc.workflow_run_id,
                "workpage_id": exc.workpage_id,
                "missing_dataset_keys": exc.missing_dataset_keys,
            },
        ) from exc
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    return {
        "command": "api.workpages.workflow_run",
        **contract,
    }


def workflow_run_artifact_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
) -> dict[str, object]:
    contract = _artifact_workpage_contract(
        connection,
        context=context,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
    )
    return {
        "command": "api.workpages.artifact",
        **contract,
    }


def schedule_artifact_previous_week_reality_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
) -> dict[str, object]:
    artifact, workflow_run, _descriptor = _editable_schedule_artifact_projection_context(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
    )
    artifacts = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
    try:
        workbook_bytes = _artifact_workpage_bytes(
            artifact=artifact,
            descriptor=_descriptor,
            artifact_version_id=artifact_version_id,
        )
    except ArtifactStorageError as exc:
        raise ApiError(
            status_code=500,
            code="workpage_artifact_unavailable",
            message="artifact-backed workpage storage is unavailable",
            details={"artifact_version_id": artifact_version_id},
        ) from exc
    try:
        contract = build_schedule_previous_week_reality_contract(
            connection,
            artifact_version_id=artifact_version_id,
            artifact=artifact,
            workflow_run=workflow_run,
            artifacts=artifacts,
            projection=project_stage04_draft_weekly_schedule_workbook(workbook_bytes),
            download_path=f"/api/v1/artifacts/{artifact_version_id}/download.bin",
        )
    except WorkpageProjectionUnavailableError as exc:
        raise ApiError(
            status_code=409,
            code="workpage_projection_unavailable",
            message=str(exc),
            details={
                "workflow_run_id": exc.workflow_run_id,
                "workpage_id": exc.workpage_id,
                "missing_dataset_keys": exc.missing_dataset_keys,
            },
        ) from exc
    return {
        "command": "api.workpages.schedule.previous_week_reality",
        **contract,
    }


def submit_workflow_run_artifact_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    result = _submit_artifact_workpage(
        connection,
        context=context,
        db_url=db_url,
        artifact_version_id=artifact_version_id,
        payload=payload,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
    )
    return {
        "command": "api.workpages.artifact.submit",
        **result,
    }


def preview_workflow_run_artifact_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    result = _preview_artifact_workpage(
        connection,
        context=context,
        artifact_version_id=artifact_version_id,
        payload=payload,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
    )
    return {
        "command": "api.workpages.artifact.preview",
        **result,
    }


def mark_schedule_sick_no_show_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    if workpage_kind != SCHEDULE_WORKPAGE_KIND:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    artifact_workflow_run_id = str(artifact["workflow_run_id"])
    if artifact_workflow_run_id != workflow_run_id:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=artifact_workflow_run_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    descriptor = _resolve_public_artifact_descriptor(
        workflow_id=str(workflow_run["workflow_id"]),
        artifact=artifact,
        artifact_version_id=artifact_version_id,
        workpage_kind=workpage_kind,
    )
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    if not descriptor.supports_editable_artifact_kind(artifact_kind):
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    try:
        result = mark_schedule_sick_no_show_command(
            connection,
            {
                **payload,
                "artifact_version_id": artifact_version_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.schedule.sick_no_show",
        **result,
    }


def recommend_schedule_route_demand_coverage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    _editable_schedule_artifact_endpoint_context(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
    )
    try:
        result = recommend_schedule_route_demand_coverage_command(
            connection,
            {
                **payload,
                "artifact_version_id": artifact_version_id,
            },
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.schedule.route_demand_coverage_candidates",
        **result,
    }


def apply_schedule_route_demand_coverage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    _editable_schedule_artifact_endpoint_context(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
    )
    try:
        result = apply_schedule_route_demand_coverage_command(
            connection,
            {
                **payload,
                "artifact_version_id": artifact_version_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.schedule.route_demand_coverage",
        **result,
    }


def create_workflow_run_eod_draft_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    if str(workflow_run.get("workflow_id") or "") != EOD_WORKFLOW_ID:
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={
                "workflow_run_id": workflow_run_id,
                "workpage_id": "eod-v0",
            },
        )
    try:
        result = create_workflow_run_eod_draft_command(
            connection,
            workflow_run,
            {
                **payload,
                "tenant_id": context.tenant_id,
                "domain_id": context.domain_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.eod_drafts.create",
        **result,
    }


def ensure_workflow_run_eod_intake_task_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    if str(workflow_run.get("workflow_id") or "") != EOD_WORKFLOW_ID:
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={
                "workflow_run_id": workflow_run_id,
                "workpage_id": "eod-v0",
            },
        )
    try:
        result = ensure_workflow_run_eod_intake_task_command(
            connection,
            workflow_run,
            {
                **payload,
                "tenant_id": context.tenant_id,
                "domain_id": context.domain_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
                "actor_roles": list(context.actor_roles),
            },
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.eod_intake_task.ensure",
        **result,
    }


def create_workflow_run_driver_preferences_snapshot_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    if str(workflow_run.get("workflow_id") or "") != "weekly_schedule_planning.v1":
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={
                "workflow_run_id": workflow_run_id,
                "workpage_id": DRIVER_PREFERENCES_WORKPAGE_KIND,
            },
        )
    try:
        result = create_workflow_run_driver_preferences_snapshot_command(
            connection,
            workflow_run,
            {
                **payload,
                "tenant_id": context.tenant_id,
                "domain_id": context.domain_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.driver_preferences.snapshots.create",
        **result,
    }


def create_workflow_run_route_demand_next_week_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    if str(workflow_run.get("workflow_id") or "") != "weekly_schedule_planning.v1":
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={
                "workflow_run_id": workflow_run_id,
                "workpage_id": ROUTE_DEMAND_WORKPAGE_KIND,
            },
        )
    try:
        result = create_workflow_run_route_demand_next_week_command(
            connection,
            workflow_run,
            {
                **payload,
                "tenant_id": context.tenant_id,
                "domain_id": context.domain_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.route_demand.next_week.create",
        **result,
    }


def save_and_run_route_demand_artifact_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    artifact_version_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    artifact_workflow_run_id = str(artifact["workflow_run_id"])
    if artifact_workflow_run_id != workflow_run_id:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=artifact_workflow_run_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    descriptor = _resolve_public_artifact_descriptor(
        workflow_id=str(workflow_run["workflow_id"]),
        artifact=artifact,
        artifact_version_id=artifact_version_id,
        workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
    )
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    if not descriptor.supports_editable_artifact_kind(artifact_kind):
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    try:
        result = save_and_run_route_demand_artifact_workpage_command(
            connection,
            {
                **payload,
                "artifact_version_id": artifact_version_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
                "actor_roles": list(context.actor_roles),
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    except OpenAIConfigError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            details={},
        ) from exc
    except OpenAIResponsesError as exc:
        status_code = 503 if exc.retryable else 502
        raise ApiError(
            status_code=status_code,
            code=exc.code,
            message=str(exc),
            details=exc.details,
        ) from exc
    return {
        "command": "api.workpages.route_demand.artifact.save_and_run",
        **result,
    }


def add_workflow_run_driver_availability_exception_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    if str(workflow_run.get("workflow_id") or "") != "weekly_schedule_planning.v1":
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={
                "workflow_run_id": workflow_run_id,
                "workpage_id": DRIVER_PREFERENCES_WORKPAGE_KIND,
            },
        )
    try:
        result = add_driver_availability_exception_command(
            connection,
            workflow_run,
            {
                **payload,
                "tenant_id": context.tenant_id,
                "domain_id": context.domain_id,
                "actor_id": context.actor_id,
                "actor_type": context.actor_type,
            },
            storage_root=default_storage_root_for_db_url(db_url),
        )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    return {
        "command": "api.workpages.driver_preferences.availability_exceptions.add",
        **result,
    }


def _build_workflow_run_workpage_contract(
    connection: sqlite3.Connection,
    *,
    descriptor: WorkpageDescriptor,
    workflow_run: dict[str, object],
) -> dict[str, object]:
    workflow_run_id = str(workflow_run["workflow_run_id"])
    artifacts = list_artifacts_for_workflow_run_command(connection, workflow_run_id)
    if descriptor.kind == SCHEDULE_WORKPAGE_KIND:
        return build_schedule_workflow_run_workpage_contract(
            connection,
            workflow_run=workflow_run,
            artifacts=artifacts,
        )
    if descriptor.kind == ROUTE_DEMAND_WORKPAGE_KIND:
        return build_route_demand_workflow_run_workpage_contract(
            connection,
            workflow_run=workflow_run,
            artifacts=artifacts,
        )
    if descriptor.kind == DRIVER_PREFERENCES_WORKPAGE_KIND:
        return build_driver_preferences_workflow_run_workpage_contract(
            connection,
            workflow_run=workflow_run,
            artifacts=artifacts,
        )
    if descriptor.kind == EOD_WORKPAGE_KIND:
        return build_eod_workflow_run_workpage_contract(
            workflow_run=workflow_run,
            artifacts=artifacts,
        )
    raise ApiError(
        status_code=404,
        code="workpage_not_found",
        message="workpage not found",
        details={
            "workflow_run_id": workflow_run_id,
            "workpage_id": descriptor.kind,
        },
    )


def _artifact_workpage_contract(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    artifact_version_id: str,
    workflow_run_id: str,
    workpage_kind: str,
) -> dict[str, object]:
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    artifact_workflow_run_id = str(artifact["workflow_run_id"])
    if artifact_workflow_run_id != workflow_run_id:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=artifact_workflow_run_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    workflow_id = str(workflow_run["workflow_id"])
    descriptor = _resolve_public_artifact_descriptor(
        workflow_id=workflow_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
        workpage_kind=workpage_kind,
    )
    artifacts = list_artifacts_for_workflow_run_command(connection, artifact_workflow_run_id)

    try:
        workbook_bytes = _artifact_workpage_bytes(
            artifact=artifact,
            descriptor=descriptor,
            artifact_version_id=artifact_version_id,
        )
    except ArtifactStorageError as exc:
        raise ApiError(
            status_code=500,
            code="workpage_artifact_unavailable",
            message="artifact-backed workpage storage is unavailable",
            details={"artifact_version_id": artifact_version_id},
        ) from exc

    if descriptor.kind == EOD_WORKPAGE_KIND:
        metadata_json = artifact.get("metadata_json") or {}
        return build_eod_artifact_workpage_contract(
            connection,
            artifact_version_id=artifact_version_id,
            artifact=artifact,
            workflow_run=workflow_run,
            artifacts=artifacts,
            download_path=f"/api/v1/artifacts/{artifact_version_id}/download.bin",
            projection=project_upd_draft_workbook(workbook_bytes),
            source_refs=_artifact_source_refs(metadata_json),
        )
    if descriptor.kind == SCHEDULE_WORKPAGE_KIND:
        return build_schedule_artifact_workpage_contract(
            connection,
            artifact_version_id=artifact_version_id,
            artifact=artifact,
            workflow_run=workflow_run,
            artifacts=artifacts,
            download_path=f"/api/v1/artifacts/{artifact_version_id}/download.bin",
            projection=project_stage04_draft_weekly_schedule_workbook(workbook_bytes),
        )
    if descriptor.kind == ROUTE_DEMAND_WORKPAGE_KIND:
        return build_route_demand_artifact_workpage_contract(
            connection,
            artifact_version_id=artifact_version_id,
            artifact=artifact,
            workflow_run=workflow_run,
            artifacts=artifacts,
            download_path=f"/api/v1/artifacts/{artifact_version_id}/download.bin",
            projection=project_route_demand_workbook(workbook_bytes),
        )
    if descriptor.kind == DRIVER_PREFERENCES_WORKPAGE_KIND:
        return build_driver_preferences_artifact_workpage_contract(
            connection,
            artifact_version_id=artifact_version_id,
            artifact=artifact,
            workflow_run=workflow_run,
            artifacts=artifacts,
            download_path=f"/api/v1/artifacts/{artifact_version_id}/download.bin",
            projection=project_driver_preferences_workbook(workbook_bytes),
        )
    raise ApiError(
        status_code=404,
        code="workpage_artifact_not_found",
        message="artifact-backed workpage not found",
        details={"artifact_version_id": artifact_version_id},
    )


def _submit_artifact_workpage(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    artifact_version_id: str,
    payload: dict[str, object],
    workflow_run_id: str,
    workpage_kind: str,
) -> dict[str, object]:
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    artifact_workflow_run_id = str(artifact["workflow_run_id"])
    if artifact_workflow_run_id != workflow_run_id:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=artifact_workflow_run_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    descriptor = _resolve_public_artifact_descriptor(
        workflow_id=str(workflow_run["workflow_id"]),
        artifact=artifact,
        artifact_version_id=artifact_version_id,
        workpage_kind=workpage_kind,
    )
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    if not descriptor.submit_enabled or not descriptor.supports_editable_artifact_kind(artifact_kind):
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )

    try:
        if descriptor.kind == EOD_WORKPAGE_KIND:
            return submit_eod_artifact_workpage_command(
                connection,
                {
                    **payload,
                    "artifact_version_id": artifact_version_id,
                    "actor_id": context.actor_id,
                    "actor_type": context.actor_type,
                },
                storage_root=default_storage_root_for_db_url(db_url),
            )
        if descriptor.kind == SCHEDULE_WORKPAGE_KIND:
            return submit_schedule_artifact_workpage_command(
                connection,
                {
                    **payload,
                    "artifact_version_id": artifact_version_id,
                    "actor_id": context.actor_id,
                    "actor_type": context.actor_type,
                },
                storage_root=default_storage_root_for_db_url(db_url),
            )
        if descriptor.kind == ROUTE_DEMAND_WORKPAGE_KIND:
            return submit_route_demand_artifact_workpage_command(
                connection,
                {
                    **payload,
                    "artifact_version_id": artifact_version_id,
                    "actor_id": context.actor_id,
                    "actor_type": context.actor_type,
                },
                storage_root=default_storage_root_for_db_url(db_url),
            )
        if descriptor.kind == DRIVER_PREFERENCES_WORKPAGE_KIND:
            return submit_driver_preferences_artifact_workpage_command(
                connection,
                {
                    **payload,
                    "artifact_version_id": artifact_version_id,
                    "actor_id": context.actor_id,
                    "actor_type": context.actor_type,
                },
                storage_root=default_storage_root_for_db_url(db_url),
            )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    raise ApiError(
        status_code=404,
        code="workpage_artifact_not_found",
        message="artifact-backed workpage not found",
        details={"artifact_version_id": artifact_version_id},
    )


def _preview_artifact_workpage(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    artifact_version_id: str,
    payload: dict[str, object],
    workflow_run_id: str,
    workpage_kind: str,
) -> dict[str, object]:
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    artifact_workflow_run_id = str(artifact["workflow_run_id"])
    if artifact_workflow_run_id != workflow_run_id:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=artifact_workflow_run_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    descriptor = _resolve_public_artifact_descriptor(
        workflow_id=str(workflow_run["workflow_id"]),
        artifact=artifact,
        artifact_version_id=artifact_version_id,
        workpage_kind=workpage_kind,
    )
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    if (
        descriptor.backend_artifact_preview_path_builder is None
        or not descriptor.supports_editable_artifact_kind(artifact_kind)
    ):
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    try:
        if descriptor.kind == SCHEDULE_WORKPAGE_KIND:
            return preview_schedule_artifact_workpage_command(
                connection,
                {
                    **payload,
                    "artifact_version_id": artifact_version_id,
                },
            )
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    raise ApiError(
        status_code=404,
        code="workpage_artifact_not_found",
        message="artifact-backed workpage not found",
        details={"artifact_version_id": artifact_version_id},
    )


def _resolve_public_artifact_descriptor(
    *,
    workflow_id: str,
    artifact: dict[str, object],
    artifact_version_id: str,
    workpage_kind: str,
) -> WorkpageDescriptor:
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    descriptor = logistics_workpage_descriptor_registry().get_descriptor(workpage_kind)
    if descriptor is not None:
        if (
            not descriptor.artifact_enabled
            or not descriptor.supports_workflow(workflow_id)
            or not descriptor.supports_artifact_kind(artifact_kind)
        ):
            descriptor = None
    if descriptor is None:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return descriptor


def _editable_schedule_artifact_endpoint_context(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
) -> tuple[dict[str, object], WorkpageDescriptor]:
    _artifact, workflow_run, descriptor = _editable_schedule_artifact_projection_context(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        workpage_kind=workpage_kind,
        artifact_version_id=artifact_version_id,
    )
    return workflow_run, descriptor


def _editable_schedule_artifact_projection_context(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
    artifact_version_id: str,
) -> tuple[dict[str, object], dict[str, object], WorkpageDescriptor]:
    if workpage_kind != SCHEDULE_WORKPAGE_KIND:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc
    artifact_workflow_run_id = str(artifact["workflow_run_id"])
    if artifact_workflow_run_id != workflow_run_id:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=artifact_workflow_run_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    descriptor = _resolve_public_artifact_descriptor(
        workflow_id=str(workflow_run["workflow_id"]),
        artifact=artifact,
        artifact_version_id=artifact_version_id,
        workpage_kind=workpage_kind,
    )
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    if not descriptor.supports_editable_artifact_kind(artifact_kind):
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact, workflow_run, descriptor


def _scoped_workflow_run_for_artifact(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    artifact: dict[str, object],
    artifact_version_id: str,
) -> dict[str, object]:
    del artifact
    try:
        return scoped_workflow_run(connection, context, workflow_run_id)
    except ApiError as exc:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        ) from exc


def _artifact_workpage_bytes(
    *,
    artifact: dict[str, object],
    descriptor: WorkpageDescriptor,
    artifact_version_id: str,
) -> bytes:
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    if descriptor.kind == SCHEDULE_WORKPAGE_KIND and descriptor.supports_artifact_kind(artifact_kind):
        storage_uri = str(artifact.get("storage_uri") or "")
        if storage_uri.startswith("file:"):
            return read_blob(storage_uri)
        try:
            return draft_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))
        except ValueError as exc:
            raise ArtifactStorageError(str(exc)) from exc
    if descriptor.kind == ROUTE_DEMAND_WORKPAGE_KIND and descriptor.supports_artifact_kind(artifact_kind):
        storage_uri = str(artifact.get("storage_uri") or "")
        if storage_uri.startswith("file:"):
            return read_blob(storage_uri)
        try:
            return route_demand_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))
        except ValueError as exc:
            raise ArtifactStorageError(str(exc)) from exc
    if descriptor.kind == DRIVER_PREFERENCES_WORKPAGE_KIND and descriptor.supports_artifact_kind(artifact_kind):
        storage_uri = str(artifact.get("storage_uri") or "")
        if storage_uri.startswith("file:"):
            return read_blob(storage_uri)
        try:
            return driver_preferences_workbook_bytes_from_metadata_json(
                artifact.get("metadata_json")
            )
        except ValueError as exc:
            raise ArtifactStorageError(str(exc)) from exc
    if descriptor.kind == EOD_WORKPAGE_KIND and artifact_kind == EOD_DATASET_KEY:
        return read_blob(str(artifact["storage_uri"]))
    raise ApiError(
        status_code=404,
        code="workpage_artifact_not_found",
        message="artifact-backed workpage not found",
        details={"artifact_version_id": artifact_version_id},
    )


def _artifact_metadata_value(
    metadata_json: object,
    key: str,
    *,
    default: str,
) -> str:
    if isinstance(metadata_json, dict):
        value = metadata_json.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return default


def _artifact_source_refs(metadata_json: object) -> list[str]:
    if not isinstance(metadata_json, dict):
        return []
    source_refs: list[str] = []
    for key in ("seed_source_path", "template_source_path", "ingress_source_path"):
        value = metadata_json.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in source_refs:
            source_refs.append(text)
    for key in ("source_eos_artifact_version_id", "normalized_artifact_version_id"):
        value = metadata_json.get(key)
        if value is None:
            continue
        text = str(value).strip()
        ref = f"/api/v1/artifacts/{text}" if text else ""
        if ref and ref not in source_refs:
            source_refs.append(ref)
    return source_refs


def _superseded_by_artifact_version_id(
    artifacts: list[dict[str, object]],
    artifact: dict[str, object],
) -> str | None:
    artifact_version_id = str(artifact.get("artifact_version_id") or "")
    latest: tuple[str, str] | None = None
    for item in artifacts:
        if str(item.get("supersedes_artifact_version_id") or "") != artifact_version_id:
            continue
        candidate_id = str(item.get("artifact_version_id") or "")
        created_at = str(item.get("created_at") or "")
        if not candidate_id:
            continue
        candidate = (created_at, candidate_id)
        if latest is None or candidate > latest:
            latest = candidate
    return latest[1] if latest is not None else None


def _latest_artifact_version_id(
    artifacts: list[dict[str, object]],
    artifact: dict[str, object],
) -> str:
    artifact_map = {
        str(item.get("artifact_version_id") or ""): item
        for item in artifacts
        if item.get("artifact_version_id") is not None
    }
    current_id = str(artifact.get("artifact_version_id") or "")
    seen_ids = {current_id}
    while True:
        next_id = _superseded_by_artifact_version_id(
            artifacts,
            artifact_map.get(current_id, artifact),
        )
        if not next_id or next_id in seen_ids:
            return current_id
        seen_ids.add(next_id)
        current_id = next_id
