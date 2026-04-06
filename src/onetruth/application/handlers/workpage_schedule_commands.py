from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
)
from onetruth.application.handlers.workpage_action_resolution import (
    _require_non_empty_string,
    _resolve_workpage_action_subject,
)
from onetruth.application.handlers.workpage_command_support import (
    _artifact_links_for_workpage_subject,
    _assert_artifact_not_already_superseded,
    _canonical_schedule_ui_route,
    _create_schedule_companion_artifacts,
    _create_workbook_artifact_version,
    _driver_preferences_artifact_version_id_from_manifest,
    _pin_latest_driver_preferences_dependency,
    _read_schedule_draft_artifact_bytes,
    _require_schedule_artifact_version,
    _schedule_draft_file_name,
    _schedule_preview_context,
    _schedule_submitted_metadata,
)
from onetruth.application.services.schedule_control.draft_workbook import (
    SCHEDULE_DRAFT_DATASET_KEY,
    SCHEDULE_WORKFLOW_ID,
    materialize_stage04_draft_weekly_schedule_workbook,
    project_stage04_draft_weekly_schedule_workbook,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    driver_preferences_workbook_bytes_from_metadata_json,
    project_driver_preferences_workbook,
)
from onetruth.application.services.schedule_control.workpage_calculations import (
    build_schedule_calculations,
    schedule_preview_disabled_reason,
    schedule_save_disabled_reason,
)
from onetruth.application.services.logistics_workpages import latest_driver_preferences_artifact
from onetruth.application.services.workpage_descriptors import SCHEDULE_WORKPAGE_KIND


def preview_schedule_artifact_workpage_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    artifact_version_id = _require_non_empty_string(
        payload.get("artifact_version_id"),
        field_name="artifact_version_id",
    )
    base_artifact = _require_schedule_artifact_version(connection, artifact_version_id)
    workbook_bytes = _read_schedule_draft_artifact_bytes(base_artifact)
    try:
        updated_bytes = materialize_stage04_draft_weekly_schedule_workbook(
            workbook_bytes,
            rows=payload.get("rows"),
            reserve_rows=payload.get("reserve_rows"),
        )
    except ValueError as exc:
        raise CommandError(
            code="invalid_payload",
            message=str(exc),
            details={},
        ) from exc
    preview_projection = project_stage04_draft_weekly_schedule_workbook(updated_bytes)
    workflow_run, artifacts, dependency_projection, bundle, driver_preferences_projection = _schedule_preview_context(
        connection,
        artifact=base_artifact,
    )
    disabled_reason = schedule_preview_disabled_reason(dependency_projection.dependencies)
    if disabled_reason is not None or bundle is None:
        raise CommandError(
            code="dependency_baseline_unavailable",
            message="schedule preview requires a pinned dependency baseline",
            details={
                "artifact_version_id": artifact_version_id,
                "dependency_state": dependency_projection.dependency_state,
                "dependencies": dependency_projection.dependencies,
            },
        )
    calculations = build_schedule_calculations(
        bundle=bundle,
        assignment_rows=preview_projection["rows"],
        reserve_rows=preview_projection["reserve_rows"],
        driver_preferences_projection=driver_preferences_projection,
    )
    return {
        "preview": {
            "workflow_run_id": str(workflow_run["workflow_run_id"]),
            "artifact_version_id": artifact_version_id,
            "dirty": updated_bytes != workbook_bytes,
            "dependency_state": dependency_projection.dependency_state,
            "dependencies": dependency_projection.dependencies,
            "calculations": calculations,
        }
    }

def submit_schedule_artifact_workpage_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    storage_root: Path,
    include_receipt: bool = False,
) -> dict[str, Any]:
    artifact_version_id = _require_non_empty_string(
        payload.get("artifact_version_id"),
        field_name="artifact_version_id",
    )
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    base_artifact = _require_schedule_artifact_version(connection, artifact_version_id)
    subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        workflow_id=SCHEDULE_WORKFLOW_ID,
        workpage_kind=SCHEDULE_WORKPAGE_KIND,
        flow_kind="submit",
        artifact_version_id=artifact_version_id,
        raw_action_ref=payload.get("action_ref"),
        raw_subject_link=payload.get("subject_link"),
    )

    receipt = _prepare_command_receipt(
        command_name="workpages.artifact.submit",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": artifact_version_id,
            "rows": payload.get("rows"),
            "reserve_rows": payload.get("reserve_rows"),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
            "subject_link": subject_link,
        },
        tenant_id=str(base_artifact.get("tenant_id") or ""),
        domain_id=str(base_artifact.get("domain_id") or ""),
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        idempotency_required=True,
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.artifact.submit.artifact.version.created",
    )
    validation_summary_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.artifact.submit.schedule.validation-summary.artifact.version.created",
    )
    draft_doc_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.artifact.submit.schedule.draft-doc.artifact.version.created",
    )
    calculation_snapshot_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.artifact.submit.schedule.calculation-snapshot.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        _assert_artifact_not_already_superseded(
            connection,
            artifact_version_id,
            route_builder=_canonical_schedule_ui_route,
        )
        workbook_bytes = _read_schedule_draft_artifact_bytes(base_artifact)
        try:
            updated_bytes = materialize_stage04_draft_weekly_schedule_workbook(
                workbook_bytes,
                rows=payload.get("rows"),
                reserve_rows=payload.get("reserve_rows"),
            )
        except ValueError as exc:
            raise CommandError(
                code="invalid_payload",
                message=str(exc),
                details={},
            ) from exc
        workflow_run, artifacts, dependency_projection, bundle, driver_preferences_projection = _schedule_preview_context(
            connection,
            artifact=base_artifact,
        )
        disabled_reason = schedule_save_disabled_reason(dependency_projection.dependencies)
        if disabled_reason is not None or bundle is None:
            raise CommandError(
                code=disabled_reason or "dependency_baseline_unavailable",
                message=(
                    "schedule draft save requires aligned pinned dependencies"
                    if disabled_reason == "dependency_drift_detected"
                    else "schedule draft save requires a pinned dependency baseline"
                ),
                details={
                    "artifact_version_id": artifact_version_id,
                    "dependency_state": dependency_projection.dependency_state,
                    "dependencies": dependency_projection.dependencies,
                },
            )
        updated_projection = project_stage04_draft_weekly_schedule_workbook(updated_bytes)
        effective_driver_preferences_projection = driver_preferences_projection
        calculations = build_schedule_calculations(
            bundle=bundle,
            assignment_rows=updated_projection["rows"],
            reserve_rows=updated_projection["reserve_rows"],
            driver_preferences_projection=effective_driver_preferences_projection,
        )
        metadata_json = _schedule_submitted_metadata(updated_bytes)
        latest_driver_preferences = latest_driver_preferences_artifact(artifacts)
        if latest_driver_preferences is not None:
            had_pinned_driver_preferences = bool(
                _driver_preferences_artifact_version_id_from_manifest(
                    metadata_json.get("dependency_manifest")
                )
            )
            metadata_json["dependency_manifest"] = _pin_latest_driver_preferences_dependency(
                metadata_json.get("dependency_manifest"),
                latest_driver_preferences=latest_driver_preferences,
            )
            if not had_pinned_driver_preferences:
                try:
                    effective_driver_preferences_projection = project_driver_preferences_workbook(
                        driver_preferences_workbook_bytes_from_metadata_json(
                            latest_driver_preferences.get("metadata_json")
                        )
                    )
                except ValueError:
                    effective_driver_preferences_projection = None
                calculations = build_schedule_calculations(
                    bundle=bundle,
                    assignment_rows=updated_projection["rows"],
                    reserve_rows=updated_projection["reserve_rows"],
                    driver_preferences_projection=effective_driver_preferences_projection,
                )
        new_artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=str(base_artifact["workflow_run_id"]),
            artifact_kind=SCHEDULE_DRAFT_DATASET_KEY,
            artifact_bytes=updated_bytes,
            artifact_role=(
                str(base_artifact["artifact_role"])
                if base_artifact.get("artifact_role") is not None
                else None
            ),
            file_name=_schedule_draft_file_name(base_artifact),
            media_type=str(base_artifact.get("media_type") or "application/json"),
            metadata_json=metadata_json,
            parent_artifact_version_id=artifact_version_id,
            supersedes_artifact_version_id=artifact_version_id,
            lineage_note="Submitted artifact-backed schedule draft version.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=_artifact_links_for_workpage_subject(
                subject_link,
                relation_kind="response",
            ),
        )
        submitted_artifact_version_id = str(new_artifact["artifact_version_id"])
        workflow_run_id = str(workflow_run["workflow_run_id"])
        _create_schedule_companion_artifacts(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            base_artifact=base_artifact,
            draft_artifact_version_id=submitted_artifact_version_id,
            bundle=bundle,
            dependency_state=dependency_projection.dependency_state,
            dependencies=dependency_projection.dependencies,
            calculations=calculations,
            assignment_rows=updated_projection["rows"],
            reserve_rows=updated_projection["reserve_rows"],
            driver_preferences_projection=effective_driver_preferences_projection,
            actor_id=actor_id,
            actor_type=actor_type,
            validation_summary_event_idempotency=validation_summary_event_idempotency,
            draft_doc_event_idempotency=draft_doc_event_idempotency,
            calculation_snapshot_event_idempotency=calculation_snapshot_event_idempotency,
        )
        return {
            "submitted": {
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": submitted_artifact_version_id,
                "supersedes_artifact_version_id": artifact_version_id,
                "route": _canonical_schedule_ui_route(
                    workflow_run_id=workflow_run_id,
                    artifact_version_id=submitted_artifact_version_id,
                ),
            }
        }

    result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )
    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )
