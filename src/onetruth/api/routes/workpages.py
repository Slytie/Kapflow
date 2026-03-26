from __future__ import annotations

import sqlite3

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.workpages import (
    create_demo_eod_draft_command,
    create_workflow_run_eod_draft_command,
    submit_eod_artifact_workpage_command,
)
from onetruth.api.dependencies import RequestContext, scoped_workflow_run
from onetruth.api.errors import ApiError, api_error_from_command
from onetruth.application.read_commands import (
    list_artifacts_for_workflow_run_command,
    show_artifact_version_command,
)
from onetruth.application.services.logistics_workpages import (
    DemoWorkpageNotFoundError,
    WorkpageProjectionUnavailableError,
    build_eod_artifact_workpage_contract,
    build_demo_workpage_contract,
    build_eod_workflow_run_workpage_contract,
    build_schedule_workflow_run_workpage_contract,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    DATASET_KEY,
    WORKFLOW_ID,
    project_upd_draft_workbook,
)
from onetruth.infrastructure.artifacts.storage import (
    ArtifactStorageError,
    default_storage_root_for_db_url,
    read_blob,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    get_latest_artifact_version_in_chain,
    get_superseding_artifact_version,
)


def demo_workpage_endpoint(
    *,
    context: RequestContext,
    workpage_id: str,
) -> dict[str, object]:
    del context
    try:
        contract = build_demo_workpage_contract(workpage_id)
    except DemoWorkpageNotFoundError as exc:
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={"workpage_id": exc.workpage_id},
        ) from exc
    return {
        "command": "api.workpages.demo",
        **contract,
    }


def workflow_run_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    workpage_kind: str,
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    workflow_id = str(workflow_run.get("workflow_id") or "")

    if workpage_kind == "schedule-v0" and workflow_id == "weekly_schedule_planning.v1":
        try:
            contract = build_schedule_workflow_run_workpage_contract(
                workflow_run=workflow_run,
                artifacts=list_artifacts_for_workflow_run_command(connection, workflow_run_id),
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
    elif workpage_kind == "eod-v0" and workflow_id == "dispatch_reporting.v1":
        try:
            contract = build_eod_workflow_run_workpage_contract(
                workflow_run=workflow_run,
                artifacts=list_artifacts_for_workflow_run_command(connection, workflow_run_id),
            )
        except CommandError as exc:
            raise api_error_from_command(exc) from exc
    else:
        raise ApiError(
            status_code=404,
            code="workpage_not_found",
            message="workpage not found",
            details={
                "workflow_run_id": workflow_run_id,
                "workpage_id": workpage_kind,
            },
        )

    return {
        "command": "api.workpages.workflow_run",
        **contract,
    }


def create_demo_eod_draft_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    payload: dict[str, object],
) -> dict[str, object]:
    try:
        result = create_demo_eod_draft_command(
            connection,
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


def create_workflow_run_eod_draft_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    workflow_run_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    workflow_run = scoped_workflow_run(connection, context, workflow_run_id)
    if str(workflow_run.get("workflow_id") or "") != WORKFLOW_ID:
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


def artifact_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    artifact_version_id: str,
) -> dict[str, object]:
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    workflow_run_id = str(artifact["workflow_run_id"])
    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    _assert_eod_artifact_family(
        artifact=artifact,
        workflow_id=str(workflow_run["workflow_id"]),
        artifact_version_id=artifact_version_id,
    )

    try:
        workbook_bytes = read_blob(str(artifact["storage_uri"]))
    except ArtifactStorageError as exc:
        raise ApiError(
            status_code=500,
            code="workpage_artifact_unavailable",
            message="artifact-backed workpage storage is unavailable",
            details={"artifact_version_id": artifact_version_id},
        ) from exc

    projection = project_upd_draft_workbook(workbook_bytes)
    latest = get_latest_artifact_version_in_chain(connection, artifact_version_id)
    superseded_by = get_superseding_artifact_version(connection, artifact_version_id)
    metadata_json = artifact.get("metadata_json") or {}
    contract = build_eod_artifact_workpage_contract(
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        supersedes_artifact_version_id=(
            str(artifact["supersedes_artifact_version_id"])
            if artifact.get("supersedes_artifact_version_id") is not None
            else None
        ),
        superseded_by_artifact_version_id=(
            str(superseded_by["artifact_version_id"])
            if superseded_by is not None
            else None
        ),
        latest_in_chain_artifact_version_id=(
            str(latest["artifact_version_id"])
            if latest is not None
            else artifact_version_id
        ),
        download_path=f"/api/v1/artifacts/{artifact_version_id}/download.bin",
        projection=projection,
        source_refs=_artifact_source_refs(metadata_json),
        service_date=_artifact_metadata_value(
            metadata_json,
            "service_date",
            default="2026-03-16",
        ),
        station_code=_artifact_metadata_value(
            metadata_json,
            "station_code",
            default="DVC4",
        ),
        dsp_name=_artifact_metadata_value(
            metadata_json,
            "dsp_name",
            default="QDCI",
        ),
    )
    return {
        "command": "api.workpages.artifact",
        **contract,
    }


def submit_artifact_workpage_endpoint(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    db_url: str,
    artifact_version_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    try:
        artifact = show_artifact_version_command(connection, artifact_version_id)
    except CommandError as exc:
        raise api_error_from_command(exc) from exc

    workflow_run = _scoped_workflow_run_for_artifact(
        connection,
        context=context,
        workflow_run_id=str(artifact["workflow_run_id"]),
        artifact=artifact,
        artifact_version_id=artifact_version_id,
    )
    _assert_eod_artifact_family(
        artifact=artifact,
        workflow_id=str(workflow_run["workflow_id"]),
        artifact_version_id=artifact_version_id,
    )

    try:
        result = submit_eod_artifact_workpage_command(
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
        "command": "api.workpages.artifact.submit",
        **result,
    }


def _scoped_workflow_run_for_artifact(
    connection: sqlite3.Connection,
    *,
    context: RequestContext,
    workflow_run_id: str,
    artifact: dict[str, object],
    artifact_version_id: str,
) -> dict[str, object]:
    try:
        return scoped_workflow_run(connection, context, workflow_run_id)
    except ApiError as exc:
        raise ApiError(
            status_code=404,
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        ) from exc


def _assert_eod_artifact_family(
    *,
    artifact: dict[str, object],
    workflow_id: str,
    artifact_version_id: str,
) -> None:
    if (
        str(artifact.get("artifact_kind") or "") != DATASET_KEY
        or str(artifact.get("dataset_key") or "") != DATASET_KEY
        or workflow_id != WORKFLOW_ID
    ):
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
    return source_refs
