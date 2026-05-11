from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any, Mapping, Sequence

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
from onetruth.application.handlers.availability_exceptions import (
    create_approved_driver_availability_exception,
)
from onetruth.application.services.availability_exceptions import (
    PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
    parse_iso_service_date,
)
from onetruth.application.services.schedule_control.draft_workbook import (
    SCHEDULE_DRAFT_DATASET_KEY,
    SCHEDULE_WORKFLOW_ID,
    append_stage04_draft_weekly_schedule_assignment_rows,
    materialize_stage04_draft_weekly_schedule_workbook,
    project_stage04_draft_weekly_schedule_workbook,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    DRIVER_PREFERENCES_DATASET_KEY,
    driver_preferences_workbook_bytes_from_metadata_json,
    project_driver_preferences_workbook,
)
from onetruth.application.services.schedule_control.route_demand_coverage_recommendations import (
    DEFAULT_MAX_ROUTE_DEMAND_COVERAGE_CANDIDATES,
    apply_route_demand_coverage_candidates,
    recommend_route_demand_coverage,
)
from onetruth.application.services.schedule_control.route_demand_workbook import (
    ROUTE_DEMAND_DATASET_KEY,
)
from onetruth.application.services.schedule_control.workpage_calculations import (
    build_schedule_bundle_from_dependencies,
    build_schedule_calculations,
    normalize_schedule_dependency_manifest,
    project_schedule_dependency_state,
    resolve_schedule_dependency_artifacts,
    schedule_preview_disabled_reason,
    schedule_save_disabled_reason,
)
from onetruth.application.services.logistics_workpages import latest_driver_preferences_artifact
from onetruth.application.services.workpage_descriptors import SCHEDULE_WORKPAGE_KIND
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    list_artifact_versions_for_workflow_run,
)


_SICK_NO_SHOW_ACTION_ID = "workpage.schedule-v0.mark_sick_no_show"


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


def recommend_schedule_route_demand_coverage_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    artifact_version_id = _require_non_empty_string(
        payload.get("artifact_version_id"),
        field_name="artifact_version_id",
    )
    route_demand_artifact_version_id = _require_non_empty_string(
        payload.get("route_demand_artifact_version_id"),
        field_name="route_demand_artifact_version_id",
    )
    base_artifact = _require_schedule_artifact_version(connection, artifact_version_id)
    route_demand_artifact = _require_route_demand_coverage_artifact(
        connection,
        artifact_version_id=route_demand_artifact_version_id,
    )
    _assert_schedule_route_demand_same_workflow_run(
        schedule_artifact=base_artifact,
        route_demand_artifact=route_demand_artifact,
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
    updated_projection = project_stage04_draft_weekly_schedule_workbook(updated_bytes)
    workflow_run, artifacts, dependency_projection, bundle, _driver_preferences_projection = _schedule_preview_context(
        connection,
        artifact=base_artifact,
    )
    disabled_reason = schedule_preview_disabled_reason(dependency_projection.dependencies)
    if disabled_reason is not None or bundle is None:
        raise CommandError(
            code=disabled_reason or "dependency_baseline_unavailable",
            message="schedule route-demand coverage requires a pinned dependency baseline",
            details={
                "artifact_version_id": artifact_version_id,
                "dependency_state": dependency_projection.dependency_state,
                "dependencies": dependency_projection.dependencies,
            },
        )
    updated_manifest = _pin_schedule_dependency_artifact(
        base_artifact.get("metadata_json", {}).get("dependency_manifest"),
        dependency_key="route_slot_requirements",
        artifact_kind=ROUTE_DEMAND_DATASET_KEY,
        artifact_version_id=route_demand_artifact_version_id,
        impact_class="hard",
    )
    dependency_artifacts_after = resolve_schedule_dependency_artifacts(
        workflow_run_id=str(workflow_run["workflow_run_id"]),
        artifacts=artifacts,
        dependency_manifest=updated_manifest,
    )
    try:
        updated_bundle = build_schedule_bundle_from_dependencies(
            workflow_run=workflow_run,
            dependency_artifacts_by_key=dependency_artifacts_after,
        )
    except ValueError as exc:
        raise CommandError(
            code="dependency_baseline_unavailable",
            message="route-demand coverage requires a complete pinned dependency baseline",
            details={"artifact_version_id": artifact_version_id},
        ) from exc
    dependency_projection_after = project_schedule_dependency_state(
        dependency_manifest=updated_manifest,
        artifacts=artifacts,
    )
    recommendations = recommend_route_demand_coverage(
        old_bundle=bundle,
        updated_bundle=updated_bundle,
        assignment_rows=updated_projection["rows"],
        reserve_rows=updated_projection["reserve_rows"],
        service_dates=_normalize_route_demand_coverage_service_dates(payload.get("service_dates")),
        max_candidates=_coerce_route_demand_coverage_max_candidates(payload.get("max_candidates")),
    )
    return {
        "route_demand_coverage_recommendations": {
            "workflow_run_id": str(workflow_run["workflow_run_id"]),
            "artifact_version_id": artifact_version_id,
            "route_demand_artifact_version_id": route_demand_artifact_version_id,
            "dependency_state": dependency_projection_after.dependency_state,
            "dependencies": dependency_projection_after.dependencies,
            **recommendations,
        }
    }


def apply_schedule_route_demand_coverage_command(
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
    route_demand_artifact_version_id = _require_non_empty_string(
        payload.get("route_demand_artifact_version_id"),
        field_name="route_demand_artifact_version_id",
    )
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    base_artifact = _require_schedule_artifact_version(connection, artifact_version_id)
    route_demand_artifact = _require_route_demand_coverage_artifact(
        connection,
        artifact_version_id=route_demand_artifact_version_id,
    )
    _assert_schedule_route_demand_same_workflow_run(
        schedule_artifact=base_artifact,
        route_demand_artifact=route_demand_artifact,
    )
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
        command_name="workpages.schedule.route_demand_coverage.apply",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": artifact_version_id,
            "route_demand_artifact_version_id": route_demand_artifact_version_id,
            "selections": payload.get("selections"),
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
        "workpages.schedule.route-demand-coverage.artifact.version.created",
    )
    validation_summary_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.schedule.route-demand-coverage.validation-summary.artifact.version.created",
    )
    draft_doc_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.schedule.route-demand-coverage.draft-doc.artifact.version.created",
    )
    calculation_snapshot_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.schedule.route-demand-coverage.calculation-snapshot.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        _assert_artifact_not_already_superseded(
            connection,
            artifact_version_id,
            route_builder=_canonical_schedule_ui_route,
        )
        workbook_bytes = _read_schedule_draft_artifact_bytes(base_artifact)
        try:
            validated_bytes = materialize_stage04_draft_weekly_schedule_workbook(
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
        validated_projection = project_stage04_draft_weekly_schedule_workbook(validated_bytes)
        workflow_run, artifacts, dependency_projection, bundle, driver_preferences_projection = _schedule_preview_context(
            connection,
            artifact=base_artifact,
        )
        disabled_reason = schedule_preview_disabled_reason(dependency_projection.dependencies)
        if disabled_reason is not None or bundle is None:
            raise CommandError(
                code=disabled_reason or "dependency_baseline_unavailable",
                message="schedule route-demand coverage requires a pinned dependency baseline",
                details={
                    "artifact_version_id": artifact_version_id,
                    "dependency_state": dependency_projection.dependency_state,
                    "dependencies": dependency_projection.dependencies,
                },
            )
        updated_manifest = _pin_schedule_dependency_artifact(
            base_artifact.get("metadata_json", {}).get("dependency_manifest"),
            dependency_key="route_slot_requirements",
            artifact_kind=ROUTE_DEMAND_DATASET_KEY,
            artifact_version_id=route_demand_artifact_version_id,
            impact_class="hard",
        )
        dependency_artifacts_after = resolve_schedule_dependency_artifacts(
            workflow_run_id=str(workflow_run["workflow_run_id"]),
            artifacts=artifacts,
            dependency_manifest=updated_manifest,
        )
        try:
            updated_bundle = build_schedule_bundle_from_dependencies(
                workflow_run=workflow_run,
                dependency_artifacts_by_key=dependency_artifacts_after,
            )
        except ValueError as exc:
            raise CommandError(
                code="dependency_baseline_unavailable",
                message="route-demand coverage requires a complete pinned dependency baseline",
                details={"artifact_version_id": artifact_version_id},
            ) from exc
        recommendations = recommend_route_demand_coverage(
            old_bundle=bundle,
            updated_bundle=updated_bundle,
            assignment_rows=validated_projection["rows"],
            reserve_rows=validated_projection["reserve_rows"],
            service_dates=_normalize_route_demand_coverage_service_dates(payload.get("service_dates")),
            max_candidates=_coerce_route_demand_coverage_max_candidates(payload.get("max_candidates")),
        )
        try:
            applied = apply_route_demand_coverage_candidates(
                bundle=updated_bundle,
                assignment_rows=validated_projection["rows"],
                reserve_rows=validated_projection["reserve_rows"],
                selections=_normalize_route_demand_coverage_selections(payload.get("selections")),
                recommendations=recommendations,
                route_demand_artifact_version_id=route_demand_artifact_version_id,
            )
        except ValueError as exc:
            raise CommandError(
                code="route_demand_coverage_candidate_unavailable",
                message="the selected route-demand coverage candidate is no longer available",
                details={
                    "artifact_version_id": artifact_version_id,
                    "route_demand_artifact_version_id": route_demand_artifact_version_id,
                    "reason": str(exc),
                },
            ) from exc
        except RuntimeError as exc:
            raise CommandError(
                code="route_demand_coverage_candidate_blocked",
                message="the selected route-demand coverage candidate is now blocked",
                details={
                    "artifact_version_id": artifact_version_id,
                    "route_demand_artifact_version_id": route_demand_artifact_version_id,
                    "reason": str(exc),
                },
            ) from exc
        try:
            updated_bytes = append_stage04_draft_weekly_schedule_assignment_rows(
                workbook_bytes,
                rows=validated_projection["rows"],
                reserve_rows=applied["reserve_rows"],
                appended_rows=applied["appended_rows"],
            )
        except ValueError as exc:
            raise CommandError(
                code="invalid_payload",
                message=str(exc),
                details={},
            ) from exc
        updated_projection = project_stage04_draft_weekly_schedule_workbook(updated_bytes)
        metadata_json = _schedule_submitted_metadata(updated_bytes)
        metadata_json["dependency_manifest"] = updated_manifest
        effective_driver_preferences_projection = driver_preferences_projection
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
        dependency_projection_after = project_schedule_dependency_state(
            dependency_manifest=metadata_json["dependency_manifest"],
            artifacts=artifacts,
        )
        calculations = build_schedule_calculations(
            bundle=updated_bundle,
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
            lineage_note="Applied route-demand coverage recommendation after route count increase.",
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
            bundle=updated_bundle,
            dependency_state=dependency_projection_after.dependency_state,
            dependencies=dependency_projection_after.dependencies,
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
            },
            "route_demand_coverage": {
                "route_demand_artifact_version_id": route_demand_artifact_version_id,
                "assigned_count": int(applied["assigned_count"]),
                "appended_assignment_count": int(applied["appended_assignment_count"]),
                "cleared_same_day_reserve_count": int(applied["cleared_same_day_reserve_count"]),
                "selected": applied["selected"],
            },
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


def mark_schedule_sick_no_show_command(
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
    driver_id = _require_non_empty_string(payload.get("driver_id"), field_name="driver_id")
    service_date = _require_non_empty_string(
        payload.get("service_date"),
        field_name="service_date",
    )
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    idempotency_key = _require_non_empty_string(
        payload.get("idempotency_key"),
        field_name="idempotency_key",
    )
    reason_note = str(payload.get("reason_note") or "").strip()
    base_artifact = _require_schedule_artifact_version(connection, artifact_version_id)
    workflow_run_id = _require_non_empty_string(
        base_artifact.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    action_ref = _normalize_schedule_sick_no_show_action_ref(
        payload.get("action_ref"),
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )

    receipt = _prepare_command_receipt(
        command_name="workpages.schedule.sick_no_show",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": artifact_version_id,
            "driver_id": driver_id,
            "service_date": service_date,
            "reason_note": reason_note,
            "rows": payload.get("rows"),
            "reserve_rows": payload.get("reserve_rows"),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
        },
        tenant_id=str(base_artifact.get("tenant_id") or ""),
        domain_id=str(base_artifact.get("domain_id") or ""),
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.schedule.sick-no-show.schedule-artifact.version.created",
    )
    validation_summary_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.schedule.sick-no-show.validation-summary.artifact.version.created",
    )
    draft_doc_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.schedule.sick-no-show.draft-doc.artifact.version.created",
    )
    calculation_snapshot_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.schedule.sick-no-show.calculation-snapshot.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        _assert_artifact_not_already_superseded(
            connection,
            artifact_version_id,
            route_builder=_canonical_schedule_ui_route,
        )
        workbook_bytes = _read_schedule_draft_artifact_bytes(base_artifact)
        try:
            submitted_bytes = materialize_stage04_draft_weekly_schedule_workbook(
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
        disabled_reason = schedule_preview_disabled_reason(dependency_projection.dependencies)
        if disabled_reason is not None or bundle is None:
            raise CommandError(
                code=disabled_reason or "dependency_baseline_unavailable",
                message="schedule sick/no-show requires a pinned dependency baseline",
                details={
                    "artifact_version_id": artifact_version_id,
                    "dependency_state": dependency_projection.dependency_state,
                    "dependencies": dependency_projection.dependencies,
                },
            )
        _validate_sick_no_show_target(
            bundle=bundle,
            driver_id=driver_id,
            service_date=service_date,
        )

        try:
            parsed_service_date = parse_iso_service_date(
                service_date,
                field_name="service_date",
            )
        except ValueError as exc:
            raise CommandError(code="invalid_payload", message=str(exc), details={}) from exc

        availability_result = create_approved_driver_availability_exception(
            connection,
            workflow_run=workflow_run,
            storage_root=storage_root,
            tenant_id=str(base_artifact.get("tenant_id") or ""),
            domain_id=str(base_artifact.get("domain_id") or ""),
            actor_id=actor_id,
            actor_type=actor_type,
            driver_id=driver_id,
            start_date=parsed_service_date,
            end_date=parsed_service_date,
            reason_code="sick_no_show",
            reason_note=reason_note,
            receipt=receipt,
            event_idempotency_prefix="schedule-sick-no-show.availability-exception",
        )
        artifacts_after_availability = list_artifact_versions_for_workflow_run(
            connection,
            workflow_run_id,
        )
        approved_availability_artifact = _resolve_created_weekly_availability_artifact(
            artifacts=artifacts_after_availability,
            availability_result=availability_result,
        )

        submitted_projection = project_stage04_draft_weekly_schedule_workbook(submitted_bytes)
        cleared_assignment_rows, cleared_reserve_rows, cleared_counts = _clear_sick_no_show_rows(
            assignment_rows=submitted_projection["rows"],
            reserve_rows=submitted_projection["reserve_rows"],
            driver_id=driver_id,
            service_date=service_date,
        )
        try:
            updated_bytes = materialize_stage04_draft_weekly_schedule_workbook(
                workbook_bytes,
                rows=cleared_assignment_rows,
                reserve_rows=cleared_reserve_rows,
            )
        except ValueError as exc:
            raise CommandError(
                code="invalid_payload",
                message=str(exc),
                details={},
            ) from exc
        updated_projection = project_stage04_draft_weekly_schedule_workbook(updated_bytes)

        metadata_json = _schedule_submitted_metadata(updated_bytes)
        metadata_json["dependency_manifest"] = _pin_schedule_dependency_artifact(
            metadata_json.get("dependency_manifest"),
            dependency_key="approved_availability",
            artifact_kind=PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
            artifact_version_id=str(approved_availability_artifact["artifact_version_id"]),
            impact_class="hard",
        )

        effective_driver_preferences_projection = driver_preferences_projection
        latest_driver_preferences = latest_driver_preferences_artifact(artifacts_after_availability)
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

        dependency_projection_after = project_schedule_dependency_state(
            dependency_manifest=metadata_json["dependency_manifest"],
            artifacts=artifacts_after_availability,
        )
        dependency_artifacts_after = resolve_schedule_dependency_artifacts(
            workflow_run_id=workflow_run_id,
            artifacts=artifacts_after_availability,
            dependency_manifest=metadata_json["dependency_manifest"],
        )
        try:
            updated_bundle = build_schedule_bundle_from_dependencies(
                workflow_run=workflow_run,
                dependency_artifacts_by_key=dependency_artifacts_after,
            )
        except ValueError as exc:
            raise CommandError(
                code="dependency_baseline_unavailable",
                message="schedule sick/no-show could not rebuild the updated dependency bundle",
                details={"artifact_version_id": artifact_version_id},
            ) from exc
        calculations = build_schedule_calculations(
            bundle=updated_bundle,
            assignment_rows=updated_projection["rows"],
            reserve_rows=updated_projection["reserve_rows"],
            driver_preferences_projection=effective_driver_preferences_projection,
        )

        new_artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
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
            lineage_note="Marked Sick / No Show and cleared affected schedule cells.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=None,
        )
        submitted_artifact_version_id = str(new_artifact["artifact_version_id"])
        _create_schedule_companion_artifacts(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            base_artifact=base_artifact,
            draft_artifact_version_id=submitted_artifact_version_id,
            bundle=updated_bundle,
            dependency_state=dependency_projection_after.dependency_state,
            dependencies=dependency_projection_after.dependencies,
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
            },
            "sick_no_show": {
                "driver_id": driver_id,
                "service_date": service_date,
                "reason_code": "sick_no_show",
                "availability_exception": availability_result["created"]["exception"],
                "approved_availability_artifact_version_id": str(
                    approved_availability_artifact["artifact_version_id"]
                ),
                "cleared_assignment_count": cleared_counts["assignment"],
                "cleared_reserve_count": cleared_counts["reserve"],
            },
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


def _validate_sick_no_show_target(
    *,
    bundle: Any,
    driver_id: str,
    service_date: str,
) -> None:
    if service_date not in set(bundle.daily_demand_by_service_date.keys()):
        raise CommandError(
            code="invalid_service_date",
            message="service_date is not in the schedule planning scope",
            details={"service_date": service_date},
        )
    driver_ids = {str(driver.driver_id) for driver in bundle.drivers}
    if driver_id not in driver_ids:
        raise CommandError(
            code="invalid_driver_id",
            message="driver_id is not available in this weekly planning run",
            details={"driver_id": driver_id},
        )


def _clear_sick_no_show_rows(
    *,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    driver_id: str,
    service_date: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    assignment_count = 0
    reserve_count = 0

    def _clear_row(row: dict[str, Any]) -> dict[str, Any]:
        next_row = dict(row)
        next_row["assigned_driver_id"] = ""
        next_row["assignment_status"] = "manual_override"
        return next_row

    next_assignment_rows: list[dict[str, Any]] = []
    for row in assignment_rows:
        if (
            str(row.get("assigned_driver_id") or "").strip() == driver_id
            and str(row.get("service_date") or "").strip() == service_date
        ):
            next_assignment_rows.append(_clear_row(row))
            assignment_count += 1
            continue
        next_assignment_rows.append(dict(row))

    next_reserve_rows: list[dict[str, Any]] = []
    for row in reserve_rows:
        if (
            str(row.get("assigned_driver_id") or "").strip() == driver_id
            and str(row.get("service_date") or "").strip() == service_date
        ):
            next_reserve_rows.append(_clear_row(row))
            reserve_count += 1
            continue
        next_reserve_rows.append(dict(row))

    return next_assignment_rows, next_reserve_rows, {
        "assignment": assignment_count,
        "reserve": reserve_count,
    }


def _resolve_created_weekly_availability_artifact(
    *,
    artifacts: list[dict[str, Any]],
    availability_result: Mapping[str, Any],
) -> dict[str, Any]:
    created = availability_result.get("created")
    if not isinstance(created, Mapping):
        raise CommandError(
            code="availability_exception_unavailable",
            message="sick/no-show availability exception did not return created metadata",
            details={},
        )
    artifact_ids = {
        str(item)
        for item in created.get("weekly_approved_availability_artifact_version_ids") or []
        if str(item).strip()
    }
    for artifact in artifacts:
        artifact_version_id = str(artifact.get("artifact_version_id") or "")
        if (
            artifact_version_id in artifact_ids
            and str(artifact.get("artifact_kind") or "")
            == PLANNING_APPROVED_AVAILABILITY_DATASET_KEY
        ):
            return artifact
    latest = _latest_artifact_for_kind(
        artifacts,
        PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
    )
    if latest is not None:
        return latest
    raise CommandError(
        code="availability_exception_unavailable",
        message="sick/no-show availability exception did not create weekly availability truth",
        details={},
    )


def _pin_schedule_dependency_artifact(
    raw_manifest: object,
    *,
    dependency_key: str,
    artifact_kind: str,
    artifact_version_id: str,
    impact_class: str,
) -> list[dict[str, Any]]:
    normalized = normalize_schedule_dependency_manifest(raw_manifest)
    for row in normalized:
        if str(row.get("dependency_key") or "") != dependency_key:
            continue
        row["artifact_kind"] = artifact_kind
        row["artifact_version_id"] = artifact_version_id
        row["impact_class"] = str(row.get("impact_class") or impact_class)
        row["source_ref"] = f"/api/v1/artifacts/{artifact_version_id}"
        return normalized
    normalized.append(
        {
            "dependency_key": dependency_key,
            "artifact_kind": artifact_kind,
            "artifact_version_id": artifact_version_id,
            "impact_class": impact_class,
            "source_ref": f"/api/v1/artifacts/{artifact_version_id}",
        }
    )
    return normalized


def _require_route_demand_coverage_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found",
            details={"artifact_version_id": artifact_version_id},
        )
    artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
    if artifact_kind != ROUTE_DEMAND_DATASET_KEY:
        raise CommandError(
            code="invalid_route_demand_artifact",
            message="route-demand coverage requires a route-demand artifact version",
            details={"artifact_version_id": artifact_version_id},
        )
    return dict(artifact)


def _assert_schedule_route_demand_same_workflow_run(
    *,
    schedule_artifact: Mapping[str, Any],
    route_demand_artifact: Mapping[str, Any],
) -> None:
    schedule_workflow_run_id = _require_non_empty_string(
        schedule_artifact.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    route_demand_workflow_run_id = _require_non_empty_string(
        route_demand_artifact.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    if schedule_workflow_run_id != route_demand_workflow_run_id:
        raise CommandError(
            code="invalid_route_demand_artifact",
            message="route-demand coverage requires schedule and route-demand artifacts from the same workflow run",
            details={
                "workflow_run_id": schedule_workflow_run_id,
                "route_demand_workflow_run_id": route_demand_workflow_run_id,
            },
        )


def _normalize_route_demand_coverage_service_dates(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if not isinstance(raw_value, list):
        raise CommandError(
            code="invalid_payload",
            message="service_dates must be a list",
            details={},
        )
    return [
        _require_non_empty_string(item, field_name="service_date")
        for item in raw_value
    ]


def _normalize_route_demand_coverage_selections(
    raw_value: Any,
) -> list[dict[str, str]]:
    if not isinstance(raw_value, list):
        raise CommandError(
            code="invalid_payload",
            message="selections must be a list",
            details={},
        )
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(raw_value):
        if not isinstance(item, Mapping):
            raise CommandError(
                code="invalid_payload",
                message=f"selections[{index}] must be an object",
                details={},
            )
        normalized.append(
            {
                "route_slot_id": _require_non_empty_string(
                    item.get("route_slot_id"),
                    field_name=f"selections[{index}].route_slot_id",
                ),
                "driver_id": _require_non_empty_string(
                    item.get("driver_id"),
                    field_name=f"selections[{index}].driver_id",
                ),
                "row_kind": _require_non_empty_string(
                    item.get("row_kind"),
                    field_name=f"selections[{index}].row_kind",
                ),
            }
        )
    if not normalized:
        raise CommandError(
            code="invalid_payload",
            message="selections must not be empty",
            details={},
        )
    return normalized


def _coerce_route_demand_coverage_max_candidates(raw_value: Any) -> int:
    if raw_value is None:
        return DEFAULT_MAX_ROUTE_DEMAND_COVERAGE_CANDIDATES
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise CommandError(
            code="invalid_payload",
            message="max_candidates must be an integer",
            details={},
        ) from exc
    if value <= 0:
        raise CommandError(
            code="invalid_payload",
            message="max_candidates must be positive",
            details={},
        )
    return value


def _normalize_schedule_sick_no_show_action_ref(
    raw_action_ref: Any,
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> dict[str, Any] | None:
    if raw_action_ref is None:
        return None
    if not isinstance(raw_action_ref, Mapping):
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref must be an object",
            details={},
        )
    action_id = _require_non_empty_string(
        raw_action_ref.get("action_id"),
        field_name="action_ref.action_id",
    )
    action_workpage_kind = _require_non_empty_string(
        raw_action_ref.get("workpage_kind"),
        field_name="action_ref.workpage_kind",
    )
    action_workflow_run_id = _require_non_empty_string(
        raw_action_ref.get("workflow_run_id"),
        field_name="action_ref.workflow_run_id",
    )
    action_artifact_version_id = _require_non_empty_string(
        raw_action_ref.get("artifact_version_id"),
        field_name="action_ref.artifact_version_id",
    )
    if action_id != _SICK_NO_SHOW_ACTION_ID:
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref action_id does not match the sick/no-show flow",
            details={"action_id": action_id, "expected_action_id": _SICK_NO_SHOW_ACTION_ID},
        )
    if action_workpage_kind != SCHEDULE_WORKPAGE_KIND:
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref workpage_kind does not match the sick/no-show flow",
            details={"workpage_kind": action_workpage_kind},
        )
    if action_workflow_run_id != workflow_run_id:
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref workflow_run_id does not match the sick/no-show flow",
            details={
                "workflow_run_id": workflow_run_id,
                "action_workflow_run_id": action_workflow_run_id,
            },
        )
    if action_artifact_version_id != artifact_version_id:
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref artifact_version_id does not match the sick/no-show flow",
            details={
                "artifact_version_id": artifact_version_id,
                "action_artifact_version_id": action_artifact_version_id,
            },
        )
    return {
        "action_id": action_id,
        "workpage_kind": action_workpage_kind,
        "workflow_run_id": action_workflow_run_id,
        "artifact_version_id": action_artifact_version_id,
        "subject": None,
    }


def _latest_artifact_for_kind(
    artifacts: list[dict[str, Any]],
    artifact_kind: str,
) -> dict[str, Any] | None:
    matches = [
        artifact
        for artifact in artifacts
        if str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
        == artifact_kind
    ]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("artifact_version_id") or ""),
        ),
    )[-1]
