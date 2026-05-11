from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _event_idempotency_key,
    _command_receipt_payload,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
)
from onetruth.application.handlers.availability_exceptions import (
    materialize_weekly_approved_availability_exceptions,
)
from onetruth.application.handlers.human_tasks import (
    claim_human_task_command,
    complete_human_task_command,
)
from onetruth.application.handlers.workpage_action_resolution import (
    _require_non_empty_string,
    _resolve_workpage_action_subject,
)
from onetruth.application.handlers.workpage_command_support import (
    _assert_artifact_not_already_superseded,
    _canonical_driver_preferences_ui_route,
    _canonical_route_demand_ui_route,
    _create_workbook_artifact_version,
    _driver_preferences_bundle_for_run,
    _driver_preferences_file_name,
    _driver_preferences_submitted_metadata,
    _read_driver_preferences_artifact_bytes,
    _read_route_demand_artifact_bytes,
    _require_driver_preferences_artifact_version,
    _require_route_demand_artifact_version,
    _route_demand_file_name,
    _route_demand_submitted_metadata,
)
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_task_run_command,
    create_workflow_run_command,
)
from onetruth.application.services.logistics_workpages import (
    canonical_schedule_route_demand_coverage_apply_path,
    canonical_schedule_route_demand_coverage_candidates_path,
    canonical_route_demand_artifact_route,
    latest_driver_preferences_artifact,
    latest_route_demand_artifact,
    latest_schedule_draft_artifact,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    DRIVER_PREFERENCES_DATASET_KEY,
    build_initial_driver_preferences_workbook,
    materialize_driver_preferences_workbook,
)
from onetruth.application.services.schedule_control.draft_workbook import SCHEDULE_WORKFLOW_ID
from onetruth.application.services.schedule_control.route_demand_workbook import (
    ROUTE_DEMAND_DATASET_KEY,
    materialize_route_demand_workbook,
    project_route_demand_workbook,
    seed_future_week_route_demand_workbook,
)
from onetruth.application.services.workpage_descriptors import (
    DRIVER_PREFERENCES_WORKPAGE_KIND,
    ROUTE_DEMAND_WORKPAGE_KIND,
    canonical_workflow_run_workpage_route,
)
from onetruth.application.services.weekly_stage04_openai_agent import (
    run_weekly_stage04_openai_agent,
)
from onetruth.domain.partition_codec import service_day_to_future_planning_week
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.artifact_links import create_artifact_link
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.human_tasks import (
    get_human_task,
    get_human_task_by_task_run_id,
)
from onetruth.infrastructure.repositories.task_runs import (
    get_task_run_by_activation_key,
)
from onetruth.infrastructure.repositories.workflow_runs import (
    get_workflow_run,
    list_workflow_runs,
)


def create_workflow_run_driver_preferences_snapshot_command(
    connection: sqlite3.Connection,
    workflow_run: Mapping[str, Any],
    payload: dict[str, Any],
    *,
    storage_root: Path,
    include_receipt: bool = False,
) -> dict[str, Any]:
    workflow_run_id = _require_non_empty_string(
        workflow_run.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    tenant_id = _require_non_empty_string(payload.get("tenant_id"), field_name="tenant_id")
    domain_id = _require_non_empty_string(payload.get("domain_id"), field_name="domain_id")
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    _subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=SCHEDULE_WORKFLOW_ID,
        workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
        flow_kind="create",
        artifact_version_id=None,
        raw_action_ref=payload.get("action_ref"),
        raw_subject_link=payload.get("subject_link"),
    )

    receipt = _prepare_command_receipt(
        command_name="workpages.driver-preferences.snapshots.create",
        payload={
            **payload,
            "workflow_run_id": workflow_run_id,
            "workflow_id": SCHEDULE_WORKFLOW_ID,
            "workpage_id": "driver-preferences-v0",
        },
        fingerprint_payload={
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "workflow_run_id": workflow_run_id,
            "workflow_id": SCHEDULE_WORKFLOW_ID,
            "workpage_id": DRIVER_PREFERENCES_WORKPAGE_KIND,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
        },
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.driver-preferences.snapshots.create.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        workflow_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        existing_snapshot = latest_driver_preferences_artifact(workflow_artifacts)
        if existing_snapshot is not None:
            existing_artifact_version_id = _require_non_empty_string(
                existing_snapshot.get("artifact_version_id"),
                field_name="artifact_version_id",
            )
            raise CommandError(
                code="driver_preferences_snapshot_exists",
                message="driver preferences snapshot already exists for this workflow run",
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_version_id": existing_artifact_version_id,
                    "route": _canonical_driver_preferences_ui_route(
                        workflow_run_id=workflow_run_id,
                        artifact_version_id=existing_artifact_version_id,
                    ),
                },
            )
        bundle = _driver_preferences_bundle_for_run(
            workflow_run=workflow_run,
            artifacts=workflow_artifacts,
        )
        workbook_payload = build_initial_driver_preferences_workbook(bundle=bundle)
        workbook_bytes = json.dumps(
            workbook_payload,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        new_artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            artifact_kind=DRIVER_PREFERENCES_DATASET_KEY,
            artifact_bytes=workbook_bytes,
            artifact_role="official_input",
            file_name=_driver_preferences_file_name(workflow_run),
            media_type="application/json",
            metadata_json=workbook_payload,
            parent_artifact_version_id=None,
            supersedes_artifact_version_id=None,
            lineage_note="Created initial driver preferences snapshot.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=None,
        )
        created_artifact_version_id = str(new_artifact["artifact_version_id"])
        return {
            "created": {
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": created_artifact_version_id,
                "route": _canonical_driver_preferences_ui_route(
                    workflow_run_id=workflow_run_id,
                    artifact_version_id=created_artifact_version_id,
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

def submit_route_demand_artifact_workpage_command(
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
    base_artifact = _require_route_demand_artifact_version(connection, artifact_version_id)
    _subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        workflow_id=SCHEDULE_WORKFLOW_ID,
        workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
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
            "daily_demand_rows": payload.get("daily_demand_rows"),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
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

    def _operation() -> dict[str, Any]:
        _assert_artifact_not_already_superseded(
            connection,
            artifact_version_id,
            route_builder=_canonical_route_demand_ui_route,
        )
        workbook_bytes = _read_route_demand_artifact_bytes(base_artifact)
        base_projection = project_route_demand_workbook(workbook_bytes)
        try:
            normalized_submitted_rows = _normalize_submitted_route_demand_rows(
                payload.get("daily_demand_rows")
            )
            updated_bytes = materialize_route_demand_workbook(
                workbook_bytes,
                daily_demand_rows=_route_demand_rows_for_materialization(
                    base_projection=base_projection,
                    submitted_rows=normalized_submitted_rows,
                ),
            )
        except (CommandError, ValueError) as exc:
            raise CommandError(
                code="invalid_payload",
                message=str(exc),
                details={},
            ) from exc

        new_artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=str(base_artifact["workflow_run_id"]),
            artifact_kind=ROUTE_DEMAND_DATASET_KEY,
            artifact_bytes=updated_bytes,
            artifact_role=(
                str(base_artifact["artifact_role"])
                if base_artifact.get("artifact_role") is not None
                else None
            ),
            file_name=_route_demand_file_name(base_artifact),
            media_type=str(base_artifact.get("media_type") or "application/json"),
            metadata_json=_merged_route_demand_submitted_metadata(
                base_artifact=base_artifact,
                updated_bytes=updated_bytes,
            ),
            parent_artifact_version_id=artifact_version_id,
            supersedes_artifact_version_id=artifact_version_id,
            lineage_note="Submitted artifact-backed route demand version.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=None,
        )
        workflow_run_id = str(base_artifact["workflow_run_id"])
        submitted_artifact_version_id = str(new_artifact["artifact_version_id"])
        return {
            "submitted": {
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": submitted_artifact_version_id,
                "supersedes_artifact_version_id": artifact_version_id,
                "route": _canonical_route_demand_ui_route(
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


def create_workflow_run_route_demand_next_week_command(
    connection: sqlite3.Connection,
    workflow_run: Mapping[str, Any],
    payload: dict[str, Any],
    *,
    storage_root: Path,
    include_receipt: bool = False,
) -> dict[str, Any]:
    workflow_run_id = _require_non_empty_string(
        workflow_run.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    tenant_id = _require_non_empty_string(payload.get("tenant_id"), field_name="tenant_id")
    domain_id = _require_non_empty_string(payload.get("domain_id"), field_name="domain_id")
    actor_id = _require_non_empty_string(payload.get("actor_id"), field_name="actor_id")
    actor_type = _require_non_empty_string(payload.get("actor_type"), field_name="actor_type")
    _subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=SCHEDULE_WORKFLOW_ID,
        workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
        flow_kind="create",
        artifact_version_id=None,
        raw_action_ref=payload.get("action_ref"),
        raw_subject_link=payload.get("subject_link"),
    )
    receipt = _prepare_command_receipt(
        command_name="workpages.route-demand.next-week.create",
        payload={
            **payload,
            "workflow_run_id": workflow_run_id,
            "workflow_id": SCHEDULE_WORKFLOW_ID,
            "workpage_id": ROUTE_DEMAND_WORKPAGE_KIND,
        },
        fingerprint_payload={
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "workflow_run_id": workflow_run_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
        },
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.route-demand.next-week.create.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        source_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        latest_source_route_demand = latest_route_demand_artifact(source_artifacts)
        if latest_source_route_demand is None:
            raise CommandError(
                code="workpage_projection_unavailable",
                message="route demand source artifact is unavailable for next-week creation",
                details={
                    "workflow_run_id": workflow_run_id,
                    "workpage_id": ROUTE_DEMAND_WORKPAGE_KIND,
                    "missing_dataset_keys": [ROUTE_DEMAND_DATASET_KEY],
                },
            )
        source_projection = project_route_demand_workbook(
            _read_route_demand_artifact_bytes(latest_source_route_demand)
        )
        current_week = _route_demand_operational_week_context(
            artifact=latest_source_route_demand,
            projection=source_projection,
        )
        next_week = _next_operational_week_context(current_week["operational_week_start"])
        target_workflow_run, _created = _ensure_weekly_workflow_run(
            connection,
            tenant_id=tenant_id,
            domain_id=domain_id,
            planning_week_id=next_week["planning_week_id"],
            logical_date=next_week["workflow_run_logical_date"],
            actor_id=actor_id,
            actor_type=actor_type,
        )
        _ensure_weekly_input_intake_task(
            connection,
            workflow_run_id=str(target_workflow_run["workflow_run_id"]),
            actor_id=actor_id,
            actor_type=actor_type,
        )
        target_workflow_run_id = str(target_workflow_run["workflow_run_id"])
        target_artifacts = list_artifact_versions_for_workflow_run(connection, target_workflow_run_id)
        existing_target_route_demand = latest_route_demand_artifact(target_artifacts)
        if existing_target_route_demand is not None:
            target_artifact_version_id = _require_non_empty_string(
                existing_target_route_demand.get("artifact_version_id"),
                field_name="artifact_version_id",
            )
            return {
                "created": {
                    "workflow_run_id": target_workflow_run_id,
                    "artifact_version_id": target_artifact_version_id,
                    "route": canonical_route_demand_artifact_route(
                        workflow_run_id=target_workflow_run_id,
                        artifact_version_id=target_artifact_version_id,
                    ),
                }
            }

        seeded_bytes = seed_future_week_route_demand_workbook(
            _read_route_demand_artifact_bytes(latest_source_route_demand)
        )
        seeded_metadata = _route_demand_submitted_metadata(seeded_bytes)
        seeded_metadata["future_week_seed"] = True
        seeded_metadata["future_week_planning_week_id"] = _route_demand_planning_week_id_from_metadata(
            seeded_metadata
        ) or next_week["planning_week_id"]
        seeded_metadata["future_week_source_workflow_run_id"] = workflow_run_id
        seeded_metadata["future_week_source_artifact_version_id"] = _require_non_empty_string(
            latest_source_route_demand.get("artifact_version_id"),
            field_name="artifact_version_id",
        )

        created_artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=target_workflow_run_id,
            artifact_kind=ROUTE_DEMAND_DATASET_KEY,
            artifact_bytes=seeded_bytes,
            artifact_role=str(latest_source_route_demand.get("artifact_role") or "official_input"),
            file_name=_route_demand_file_name(latest_source_route_demand),
            media_type=str(latest_source_route_demand.get("media_type") or "application/json"),
            metadata_json=seeded_metadata,
            parent_artifact_version_id=None,
            supersedes_artifact_version_id=None,
            lineage_note="Created future-week route demand seed artifact.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=None,
        )
        created_artifact_version_id = _require_non_empty_string(
            created_artifact.get("artifact_version_id"),
            field_name="artifact_version_id",
        )
        return {
            "created": {
                "workflow_run_id": target_workflow_run_id,
                "artifact_version_id": created_artifact_version_id,
                "route": canonical_route_demand_artifact_route(
                    workflow_run_id=target_workflow_run_id,
                    artifact_version_id=created_artifact_version_id,
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


def save_and_run_route_demand_artifact_workpage_command(
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
    actor_roles = [
        str(role).strip()
        for role in payload.get("actor_roles") or []
        if str(role).strip()
    ]
    base_artifact = _require_route_demand_artifact_version(connection, artifact_version_id)
    _subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        workflow_id=SCHEDULE_WORKFLOW_ID,
        workpage_kind=ROUTE_DEMAND_WORKPAGE_KIND,
        flow_kind="submit",
        artifact_version_id=artifact_version_id,
        raw_action_ref=payload.get("action_ref"),
        raw_subject_link=payload.get("subject_link"),
        expected_action_id="workpage.route-demand-v0.save_and_run",
    )
    receipt = _prepare_command_receipt(
        command_name="workpages.route-demand.save-and-run",
        payload=payload,
        fingerprint_payload={
            "artifact_version_id": artifact_version_id,
            "daily_demand_rows": payload.get("daily_demand_rows"),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "actor_roles": sorted(actor_roles),
            "action_ref": action_ref,
        },
        tenant_id=str(base_artifact.get("tenant_id") or ""),
        domain_id=str(base_artifact.get("domain_id") or ""),
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        idempotency_required=True,
    )
    artifact_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "workpages.route-demand.save-and-run.artifact.version.created",
    )

    def _operation() -> dict[str, Any]:
        _assert_artifact_not_already_superseded(
            connection,
            artifact_version_id,
            route_builder=_canonical_route_demand_ui_route,
        )
        workflow_run_id = _require_non_empty_string(
            base_artifact.get("workflow_run_id"),
            field_name="workflow_run_id",
        )
        workflow_run = get_workflow_run(connection, workflow_run_id)
        if workflow_run is None:
            raise CommandError(
                code="workflow_run_not_found",
                message="workflow run not found for route-demand save-and-run",
                details={"workflow_run_id": workflow_run_id},
            )
        base_projection = project_route_demand_workbook(
            _read_route_demand_artifact_bytes(base_artifact)
        )
        normalized_submitted_rows = _normalize_submitted_route_demand_rows(
            payload.get("daily_demand_rows")
        )
        if _artifact_is_future_week_seed(base_artifact):
            return _save_and_run_future_week_route_demand(
                connection,
                storage_root=storage_root,
                base_artifact=base_artifact,
                base_projection=base_projection,
                normalized_submitted_rows=normalized_submitted_rows,
                workflow_run=workflow_run,
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_version_id,
                actor_id=actor_id,
                actor_type=actor_type,
                actor_roles=actor_roles,
                artifact_event_idempotency=artifact_event_idempotency,
                receipt=receipt,
            )
        return _save_and_prepare_existing_week_route_demand_coverage(
            connection,
            storage_root=storage_root,
            base_artifact=base_artifact,
            base_projection=base_projection,
            normalized_submitted_rows=normalized_submitted_rows,
            workflow_run_id=workflow_run_id,
            artifact_version_id=artifact_version_id,
            actor_id=actor_id,
            actor_type=actor_type,
            artifact_event_idempotency=artifact_event_idempotency,
        )

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


def _save_and_run_future_week_route_demand(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    base_artifact: Mapping[str, Any],
    base_projection: Mapping[str, Any],
    normalized_submitted_rows: list[dict[str, int | str]],
    workflow_run: Mapping[str, Any],
    workflow_run_id: str,
    artifact_version_id: str,
    actor_id: str,
    actor_type: str,
    actor_roles: list[str],
    artifact_event_idempotency: str | None,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    visible_base_rows = _visible_route_demand_rows_for_comparison(base_projection)
    visible_submitted_rows = _visible_submitted_route_demand_rows(
        visible_base_rows=visible_base_rows,
        submitted_rows=normalized_submitted_rows,
    )
    _assert_visible_zero_to_n_change(
        base_rows=visible_base_rows,
        submitted_rows=visible_submitted_rows,
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )

    current_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    if _future_run_has_schedule_truth(current_artifacts):
        raise _future_run_already_scheduled_error(
            workflow_run_id=workflow_run_id,
        )

    source_workflow_run_id = _future_week_source_workflow_run_id(base_artifact)
    source_workflow_run = get_workflow_run(connection, source_workflow_run_id)
    if source_workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="source workflow run not found for future-week carry-forward",
            details={"workflow_run_id": source_workflow_run_id},
        )
    source_artifacts = list_artifact_versions_for_workflow_run(connection, source_workflow_run_id)

    target_route_demand_artifact = _save_route_demand_if_needed(
        connection,
        storage_root=storage_root,
        base_artifact=base_artifact,
        submitted_rows=normalized_submitted_rows,
        base_projection=base_projection,
        actor_id=actor_id,
        actor_type=actor_type,
        event_idempotency=artifact_event_idempotency,
    )
    target_route_demand_artifact_version_id = _require_non_empty_string(
        target_route_demand_artifact.get("artifact_version_id"),
        field_name="artifact_version_id",
    )

    intake_task = _ensure_weekly_input_intake_task(
        connection,
        workflow_run_id=workflow_run_id,
        actor_id=actor_id,
        actor_type=actor_type,
    )
    intake_human_task_id = _require_non_empty_string(
        intake_task.get("human_task_id"),
        field_name="human_task_id",
    )
    _attach_existing_artifact_to_human_task(
        connection,
        workflow_run_id=workflow_run_id,
        artifact_version_id=target_route_demand_artifact_version_id,
        human_task_id=intake_human_task_id,
        actor_id=actor_id,
        actor_type=actor_type,
    )
    _provision_future_week_stage04_inputs(
        connection,
        storage_root=storage_root,
        workflow_run=workflow_run,
        route_demand_artifact=target_route_demand_artifact,
        source_artifacts=source_artifacts,
        intake_human_task_id=intake_human_task_id,
        actor_id=actor_id,
        actor_type=actor_type,
        idempotency_base=_receipt_event_idempotency_key(
            receipt,
            "workpages.route-demand.save-and-run.input-provision",
        ),
    )
    materialize_weekly_approved_availability_exceptions(
        connection,
        workflow_run=workflow_run,
        storage_root=storage_root,
        actor_id=actor_id,
        actor_type=actor_type,
        receipt_event_idempotency_base=_receipt_event_idempotency_key(
            receipt,
            "workpages.route-demand.save-and-run.approved-availability-overlay",
        ),
    )
    latest_run_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    latest_approved_availability = _latest_artifact_for_kind(
        latest_run_artifacts,
        "planning.approved_availability.workbook",
    )
    if latest_approved_availability is not None:
        _attach_existing_artifact_to_human_task(
            connection,
            workflow_run_id=workflow_run_id,
            artifact_version_id=_require_non_empty_string(
                latest_approved_availability.get("artifact_version_id"),
                field_name="artifact_version_id",
            ),
            human_task_id=intake_human_task_id,
            actor_id=actor_id,
            actor_type=actor_type,
        )

    _claim_human_task_if_needed(
        connection,
        human_task_id=intake_human_task_id,
        actor_id=actor_id,
        actor_type=actor_type,
        actor_roles=actor_roles,
        idempotency_key_suffix=f"{artifact_version_id}:intake:claim",
    )
    completed_intake = complete_human_task_command(
        connection,
        {
            "human_task_id": intake_human_task_id,
            "outcome": "complete",
            "idempotency_key": f"{artifact_version_id}:intake:complete",
            "actor_id": actor_id,
            "actor_type": actor_type,
            "actor_roles": actor_roles,
        },
        storage_root=storage_root,
    )
    build_human_task_id = _spawned_weekly_stage04_build_human_task_id(completed_intake)
    _claim_human_task_if_needed(
        connection,
        human_task_id=build_human_task_id,
        actor_id=actor_id,
        actor_type=actor_type,
        actor_roles=actor_roles,
        idempotency_key_suffix=f"{artifact_version_id}:build:claim",
    )
    run_weekly_stage04_openai_agent(
        connection,
        {
            "human_task_id": build_human_task_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "actor_roles": actor_roles,
            "idempotency_key": f"{artifact_version_id}:stage04:run",
        },
    )
    complete_human_task_command(
        connection,
        {
            "human_task_id": build_human_task_id,
            "outcome": "complete",
            "idempotency_key": f"{artifact_version_id}:stage04:complete",
            "actor_id": actor_id,
            "actor_type": actor_type,
            "actor_roles": actor_roles,
        },
        storage_root=storage_root,
    )

    final_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    latest_schedule_draft = latest_schedule_draft_artifact(final_artifacts)
    if latest_schedule_draft is None:
        raise CommandError(
            code="required_artifact_missing",
            message="weekly Stage04 agent did not produce a draft weekly schedule artifact",
            details={
                "workflow_run_id": workflow_run_id,
                "artifact_kind": "planning.draft_weekly_schedule.workbook",
            },
        )
    return {
        "submitted": {
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": target_route_demand_artifact_version_id,
            "supersedes_artifact_version_id": artifact_version_id,
            "route": _canonical_route_demand_ui_route(
                workflow_run_id=workflow_run_id,
                artifact_version_id=target_route_demand_artifact_version_id,
            ),
            "target_workflow_run_id": workflow_run_id,
            "target_schedule_route": canonical_workflow_run_workpage_route(
                workflow_run_id=workflow_run_id,
                workpage_kind="schedule-v0",
            ),
            "target_schedule_artifact_version_id": _require_non_empty_string(
                latest_schedule_draft.get("artifact_version_id"),
                field_name="artifact_version_id",
            ),
        }
    }


def _save_and_prepare_existing_week_route_demand_coverage(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    base_artifact: Mapping[str, Any],
    base_projection: Mapping[str, Any],
    normalized_submitted_rows: list[dict[str, int | str]],
    workflow_run_id: str,
    artifact_version_id: str,
    actor_id: str,
    actor_type: str,
    artifact_event_idempotency: str | None,
) -> dict[str, Any]:
    visible_base_rows = _visible_route_demand_rows_for_comparison(base_projection)
    visible_submitted_rows = _visible_submitted_route_demand_rows(
        visible_base_rows=visible_base_rows,
        submitted_rows=normalized_submitted_rows,
    )
    positive_delta_summary = _route_demand_positive_delta_summary(
        base_rows=visible_base_rows,
        submitted_rows=visible_submitted_rows,
    )
    if int(positive_delta_summary["added_route_count"]) <= 0:
        raise CommandError(
            code="route_demand_increase_required",
            message="running the coverage agent requires at least one increased planned route count",
            details={
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": artifact_version_id,
                **positive_delta_summary,
            },
        )
    current_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    latest_schedule_draft = latest_schedule_draft_artifact(current_artifacts)
    if latest_schedule_draft is None:
        raise CommandError(
            code="schedule_draft_required",
            message="route-demand coverage recommendations require an existing draft weekly schedule",
            details={
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": artifact_version_id,
            },
        )
    target_route_demand_artifact = _save_route_demand_if_needed(
        connection,
        storage_root=storage_root,
        base_artifact=base_artifact,
        submitted_rows=normalized_submitted_rows,
        base_projection=base_projection,
        actor_id=actor_id,
        actor_type=actor_type,
        event_idempotency=artifact_event_idempotency,
        lineage_note="Submitted route-demand version for existing-week coverage recommendations.",
    )
    target_route_demand_artifact_version_id = _require_non_empty_string(
        target_route_demand_artifact.get("artifact_version_id"),
        field_name="artifact_version_id",
    )
    latest_schedule_draft_artifact_version_id = _require_non_empty_string(
        latest_schedule_draft.get("artifact_version_id"),
        field_name="artifact_version_id",
    )
    coverage_context = {
        "workflow_run_id": workflow_run_id,
        "schedule_artifact_version_id": latest_schedule_draft_artifact_version_id,
        "route_demand_artifact_version_id": target_route_demand_artifact_version_id,
        "coverage_candidates_path": canonical_schedule_route_demand_coverage_candidates_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=latest_schedule_draft_artifact_version_id,
        ),
        "coverage_apply_path": canonical_schedule_route_demand_coverage_apply_path(
            workflow_run_id=workflow_run_id,
            artifact_version_id=latest_schedule_draft_artifact_version_id,
        ),
        "service_dates": list(positive_delta_summary["service_dates"]),
        "added_route_count": int(positive_delta_summary["added_route_count"]),
        "deltas": list(positive_delta_summary["deltas"]),
    }
    return {
        "submitted": {
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": target_route_demand_artifact_version_id,
            "supersedes_artifact_version_id": artifact_version_id,
            "route": _canonical_route_demand_ui_route(
                workflow_run_id=workflow_run_id,
                artifact_version_id=target_route_demand_artifact_version_id,
            ),
            "target_workflow_run_id": workflow_run_id,
            "target_schedule_route": canonical_workflow_run_workpage_route(
                workflow_run_id=workflow_run_id,
                workpage_kind="schedule-v0",
            ),
            "target_schedule_artifact_version_id": latest_schedule_draft_artifact_version_id,
            "route_demand_coverage_context": coverage_context,
        },
        "route_demand_coverage_context": coverage_context,
    }

def submit_driver_preferences_artifact_workpage_command(
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
    base_artifact = _require_driver_preferences_artifact_version(
        connection,
        artifact_version_id,
    )
    _subject_link, action_ref = _resolve_workpage_action_subject(
        connection,
        workflow_run_id=str(base_artifact["workflow_run_id"]),
        workflow_id=SCHEDULE_WORKFLOW_ID,
        workpage_kind=DRIVER_PREFERENCES_WORKPAGE_KIND,
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
            "driver_rows": payload.get("driver_rows"),
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
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

    def _operation() -> dict[str, Any]:
        _assert_artifact_not_already_superseded(
            connection,
            artifact_version_id,
            route_builder=_canonical_driver_preferences_ui_route,
        )
        workbook_bytes = _read_driver_preferences_artifact_bytes(base_artifact)
        try:
            updated_bytes = materialize_driver_preferences_workbook(
                workbook_bytes,
                driver_rows=payload.get("driver_rows"),
            )
        except ValueError as exc:
            raise CommandError(
                code="invalid_payload",
                message=str(exc),
                details={},
            ) from exc

        new_artifact = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=str(base_artifact["workflow_run_id"]),
            artifact_kind=DRIVER_PREFERENCES_DATASET_KEY,
            artifact_bytes=updated_bytes,
            artifact_role=(
                str(base_artifact["artifact_role"])
                if base_artifact.get("artifact_role") is not None
                else None
            ),
            file_name=_driver_preferences_file_name(base_artifact),
            media_type=str(base_artifact.get("media_type") or "application/json"),
            metadata_json=_driver_preferences_submitted_metadata(updated_bytes),
            parent_artifact_version_id=artifact_version_id,
            supersedes_artifact_version_id=artifact_version_id,
            lineage_note="Submitted artifact-backed driver preferences snapshot.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=artifact_event_idempotency,
            links=None,
        )
        workflow_run_id = str(base_artifact["workflow_run_id"])
        submitted_artifact_version_id = str(new_artifact["artifact_version_id"])
        return {
            "submitted": {
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": submitted_artifact_version_id,
                "supersedes_artifact_version_id": artifact_version_id,
                "route": _canonical_driver_preferences_ui_route(
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


def _route_demand_operational_week_context(
    *,
    artifact: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> dict[str, str]:
    visible_service_dates = _route_demand_visible_service_dates(projection)
    if visible_service_dates:
        current_start = date.fromisoformat(visible_service_dates[0])
        current_end_exclusive = current_start + timedelta(days=len(visible_service_dates))
        current_monday = current_start + timedelta(days=1)
        return {
            "planning_week_id": service_day_to_future_planning_week(
                f"SD-{current_monday.isoformat()}"
            ),
            "operational_week_start": current_start.isoformat(),
            "operational_week_end_exclusive": current_end_exclusive.isoformat(),
            "operational_week_end": (current_end_exclusive - timedelta(days=1)).isoformat(),
            "workflow_run_logical_date": current_monday.isoformat(),
        }
    scope_start, scope_end_exclusive = _route_demand_scope_bounds_from_artifact(artifact)
    current_start = date.fromisoformat(scope_start)
    current_end_exclusive = date.fromisoformat(scope_end_exclusive)
    current_monday = current_start + timedelta(days=1)
    return {
        "planning_week_id": service_day_to_future_planning_week(
            f"SD-{current_monday.isoformat()}"
        ),
        "operational_week_start": current_start.isoformat(),
        "operational_week_end_exclusive": current_end_exclusive.isoformat(),
        "operational_week_end": (current_end_exclusive - timedelta(days=1)).isoformat(),
        "workflow_run_logical_date": current_monday.isoformat(),
    }


def _next_operational_week_context(current_operational_week_start: str) -> dict[str, str]:
    current_start = date.fromisoformat(current_operational_week_start)
    next_start = current_start + timedelta(days=7)
    next_end_exclusive = next_start + timedelta(days=7)
    next_monday = next_start + timedelta(days=1)
    planning_week_id = service_day_to_future_planning_week(f"SD-{next_monday.isoformat()}")
    return {
        "planning_week_id": planning_week_id,
        "operational_week_start": next_start.isoformat(),
        "operational_week_end_exclusive": next_end_exclusive.isoformat(),
        "operational_week_end": (next_end_exclusive - timedelta(days=1)).isoformat(),
        "workflow_run_logical_date": next_monday.isoformat(),
    }


def _ensure_weekly_workflow_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    planning_week_id: str,
    logical_date: str,
    actor_id: str,
    actor_type: str,
) -> tuple[dict[str, Any], bool]:
    existing = _find_weekly_workflow_run(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        planning_week_id=planning_week_id,
    )
    if existing is not None:
        return existing, False
    created = create_workflow_run_command(
        connection,
        {
            "workflow_id": SCHEDULE_WORKFLOW_ID,
            "workflow_version": "v1",
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "partition_key": planning_week_id,
            "logical_date": logical_date,
            "activation_key": f"logistics-cadence:weekly:{planning_week_id}",
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )
    return created, True


def _find_weekly_workflow_run(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    planning_week_id: str,
) -> dict[str, Any] | None:
    matches = [
        run
        for run in list_workflow_runs(
            connection,
            workflow_id=SCHEDULE_WORKFLOW_ID,
            tenant_id=tenant_id,
            domain_id=domain_id,
        )
        if str(run.get("partition_key") or "") == planning_week_id
    ]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("workflow_run_id") or ""),
        ),
    )[-1]


def _ensure_weekly_input_intake_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    actor_id: str,
    actor_type: str,
) -> dict[str, Any]:
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found for weekly input intake task",
            details={"workflow_run_id": workflow_run_id},
        )
    activation_key = f"logistics-cadence:weekly:{workflow_run['partition_key']}:stage04:weekly_input_intake"
    task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if task_run is not None:
        human_task = get_human_task_by_task_run_id(connection, str(task_run["task_run_id"]))
        if human_task is None:
            raise CommandError(
                code="human_task_not_found",
                message="weekly input intake task is missing its human task",
                details={"workflow_run_id": workflow_run_id, "task_run_id": str(task_run["task_run_id"])},
            )
        return human_task
    created = create_task_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "stage_id": "Stage04",
            "task_kind": "weekly_input_intake",
            "activation_key": activation_key,
            "candidate_roles": ["schedule_planner"],
            "owner_role": "schedule_planner",
            "create_human_task": True,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
    )
    human_task = created.get("human_task")
    if not isinstance(human_task, Mapping):
        raise CommandError(
            code="human_task_not_found",
            message="weekly input intake human task was not created",
            details={"workflow_run_id": workflow_run_id},
        )
    return dict(human_task)


def _artifact_is_future_week_seed(artifact: Mapping[str, Any]) -> bool:
    metadata = artifact.get("metadata_json")
    return isinstance(metadata, Mapping) and bool(metadata.get("future_week_seed"))


def _future_week_source_workflow_run_id(artifact: Mapping[str, Any]) -> str:
    metadata = artifact.get("metadata_json")
    if isinstance(metadata, Mapping):
        source_workflow_run_id = str(metadata.get("future_week_source_workflow_run_id") or "").strip()
        if source_workflow_run_id:
            return source_workflow_run_id
    return _require_non_empty_string(artifact.get("workflow_run_id"), field_name="workflow_run_id")


def _normalize_submitted_route_demand_rows(raw_rows: Any) -> list[dict[str, int | str]]:
    if not isinstance(raw_rows, list):
        raise CommandError(
            code="invalid_payload",
            message="daily_demand_rows must be a list",
            details={},
        )
    normalized: list[dict[str, int | str]] = []
    seen: set[str] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise CommandError(
                code="invalid_payload",
                message=f"daily_demand_rows[{index}] must be an object",
                details={},
            )
        service_date = str(row.get("service_date") or "").strip()
        if not service_date or service_date in seen:
            raise CommandError(
                code="invalid_payload",
                message="daily_demand_rows contains duplicate or empty service_date values",
                details={},
            )
        seen.add(service_date)
        try:
            planned_route_count = int(row.get("planned_route_count"))
        except (TypeError, ValueError) as exc:
            raise CommandError(
                code="invalid_payload",
                message=f"daily_demand_rows[{index}].planned_route_count must be an integer",
                details={},
            ) from exc
        if planned_route_count < 0:
            raise CommandError(
                code="invalid_payload",
                message=f"daily_demand_rows[{index}].planned_route_count must be non-negative",
                details={},
            )
        normalized.append(
            {
                "service_date": service_date,
                "planned_route_count": planned_route_count,
            }
        )
    return normalized


def _route_demand_visible_service_dates(projection: Mapping[str, Any]) -> list[str]:
    service_dates: list[str] = []
    for row in list(projection.get("daily_demand_rows") or []):
        if not isinstance(row, Mapping):
            continue
        service_date = str(row.get("service_date") or "").strip()
        if not service_date:
            continue
        service_dates.append(service_date)
        if len(service_dates) == 7:
            break
    return service_dates


def _visible_route_demand_rows_for_comparison(
    projection: Mapping[str, Any],
) -> list[dict[str, Any]]:
    day_cards = list((projection.get("daily_demand_rows") or []))
    return [dict(row) for row in day_cards[:7] if isinstance(row, Mapping)]


def _route_demand_rows_for_materialization(
    *,
    base_projection: Mapping[str, Any],
    submitted_rows: list[dict[str, int | str]],
) -> list[dict[str, int | str]]:
    base_rows = [
        {
            "service_date": str(row.get("service_date") or "").strip(),
            "planned_route_count": int(row.get("planned_route_count") or 0),
        }
        for row in list(base_projection.get("daily_demand_rows") or [])
        if isinstance(row, Mapping)
    ]
    if len(submitted_rows) == len(base_rows):
        return submitted_rows
    if len(submitted_rows) != 7 or len(base_rows) <= len(submitted_rows):
        raise CommandError(
            code="invalid_payload",
            message="daily_demand_rows must match the editable route-demand week",
            details={},
        )
    submitted_by_date = {
        str(row["service_date"]): row
        for row in submitted_rows
    }
    base_dates = {
        str(row.get("service_date") or "").strip()
        for row in base_rows
    }
    if not all(str(row["service_date"]) in base_dates for row in submitted_rows):
        raise CommandError(
            code="invalid_payload",
            message="daily_demand_rows contains service dates outside the editable route-demand week",
            details={},
        )
    return [
        submitted_by_date.get(
            str(base_row.get("service_date") or "").strip(),
            {
                "service_date": str(base_row.get("service_date") or "").strip(),
                "planned_route_count": int(base_row.get("planned_route_count") or 0),
            },
        )
        for base_row in base_rows
    ]


def _visible_submitted_route_demand_rows(
    *,
    visible_base_rows: list[dict[str, Any]],
    submitted_rows: list[dict[str, int | str]],
) -> list[dict[str, int | str]]:
    submitted_by_date = {
        str(row["service_date"]): row
        for row in submitted_rows
    }
    visible_rows: list[dict[str, int | str]] = []
    for base_row in visible_base_rows:
        service_date = str(base_row.get("service_date") or "").strip()
        submitted = submitted_by_date.get(service_date)
        if submitted is None:
            raise CommandError(
                code="invalid_payload",
                message=f"daily_demand_rows is missing visible service_date {service_date}",
                details={"service_date": service_date},
            )
        visible_rows.append(submitted)
    return visible_rows


def _assert_visible_zero_to_n_change(
    *,
    base_rows: list[dict[str, Any]],
    submitted_rows: list[dict[str, int | str]],
    workflow_run_id: str,
    artifact_version_id: str,
) -> None:
    for base_row, submitted_row in zip(base_rows, submitted_rows):
        base_count = max(int(base_row.get("planned_route_count") or 0), 0)
        next_count = int(submitted_row["planned_route_count"])
        if base_count == 0 and next_count > 0:
            return
    raise CommandError(
        code="route_demand_run_requires_new_routes",
        message="save and run scheduling agent requires at least one visible future-week day to move from 0 to more than 0 routes",
        details={
            "workflow_run_id": workflow_run_id,
            "artifact_version_id": artifact_version_id,
        },
    )


def _route_demand_positive_delta_summary(
    *,
    base_rows: list[dict[str, Any]],
    submitted_rows: list[dict[str, int | str]],
) -> dict[str, Any]:
    submitted_by_date = {
        str(row["service_date"]): int(row["planned_route_count"])
        for row in submitted_rows
    }
    deltas: list[dict[str, int | str]] = []
    service_dates: list[str] = []
    added_route_count = 0
    for base_row in base_rows:
        service_date = str(base_row.get("service_date") or "").strip()
        if not service_date or service_date not in submitted_by_date:
            continue
        previous_planned_route_count = max(int(base_row.get("planned_route_count") or 0), 0)
        planned_route_count = max(submitted_by_date[service_date], 0)
        delta = planned_route_count - previous_planned_route_count
        if delta <= 0:
            continue
        service_dates.append(service_date)
        added_route_count += delta
        deltas.append(
            {
                "service_date": service_date,
                "previous_planned_route_count": previous_planned_route_count,
                "planned_route_count": planned_route_count,
                "delta": delta,
            }
        )
    return {
        "service_dates": service_dates,
        "added_route_count": added_route_count,
        "deltas": deltas,
    }


def _save_route_demand_if_needed(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    base_artifact: Mapping[str, Any],
    submitted_rows: list[dict[str, int | str]],
    base_projection: Mapping[str, Any],
    actor_id: str,
    actor_type: str,
    event_idempotency: str | None,
    lineage_note: str = "Submitted future-week route demand version for scheduling activation.",
) -> Mapping[str, Any]:
    materialization_rows = _route_demand_rows_for_materialization(
        base_projection=base_projection,
        submitted_rows=submitted_rows,
    )
    base_rows = [
        {
            "service_date": str(row.get("service_date") or "").strip(),
            "planned_route_count": int(row.get("planned_route_count") or 0),
        }
        for row in list(base_projection.get("daily_demand_rows") or [])
        if isinstance(row, Mapping)
    ]
    if _route_demand_rows_match(base_rows, materialization_rows):
        return base_artifact
    updated_bytes = materialize_route_demand_workbook(
        _read_route_demand_artifact_bytes(base_artifact),
        daily_demand_rows=materialization_rows,
    )
    workflow_run_id = _require_non_empty_string(
        base_artifact.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    new_artifact = _create_workbook_artifact_version(
        connection,
        storage_root=storage_root,
        workflow_run_id=workflow_run_id,
        artifact_kind=ROUTE_DEMAND_DATASET_KEY,
        artifact_bytes=updated_bytes,
        artifact_role=str(base_artifact.get("artifact_role") or "official_input"),
        file_name=_route_demand_file_name(base_artifact),
        media_type=str(base_artifact.get("media_type") or "application/json"),
        metadata_json=_merged_route_demand_submitted_metadata(
            base_artifact=base_artifact,
            updated_bytes=updated_bytes,
        ),
        parent_artifact_version_id=_require_non_empty_string(
            base_artifact.get("artifact_version_id"),
            field_name="artifact_version_id",
        ),
        supersedes_artifact_version_id=_require_non_empty_string(
            base_artifact.get("artifact_version_id"),
            field_name="artifact_version_id",
        ),
        lineage_note=lineage_note,
        actor_id=actor_id,
        actor_type=actor_type,
        event_idempotency=event_idempotency,
        links=None,
    )
    return new_artifact


def _route_demand_rows_match(
    base_rows: list[dict[str, Any]],
    submitted_rows: list[dict[str, int | str]],
) -> bool:
    if len(base_rows) != len(submitted_rows):
        return False
    submitted_by_date = {
        str(row["service_date"]): int(row["planned_route_count"])
        for row in submitted_rows
    }
    for row in base_rows:
        service_date = str(row.get("service_date") or "").strip()
        if service_date not in submitted_by_date:
            return False
        if int(row.get("planned_route_count") or 0) != submitted_by_date[service_date]:
            return False
    return True


def _merged_route_demand_submitted_metadata(
    *,
    base_artifact: Mapping[str, Any],
    updated_bytes: bytes,
) -> dict[str, Any]:
    metadata = base_artifact.get("metadata_json")
    merged = dict(metadata) if isinstance(metadata, Mapping) else {}
    merged.update(_route_demand_submitted_metadata(updated_bytes))
    if merged.get("future_week_seed"):
        planning_week_id = _route_demand_planning_week_id_from_metadata(merged)
        if planning_week_id:
            merged["future_week_planning_week_id"] = planning_week_id
    return merged


def _future_run_has_schedule_truth(artifacts: list[dict[str, Any]]) -> bool:
    return latest_schedule_draft_artifact(artifacts) is not None


def _future_run_already_scheduled_error(*, workflow_run_id: str) -> CommandError:
    return CommandError(
        code="future_run_already_scheduled",
        message="the added future week already has weekly schedule draft truth and must continue from schedule-v0",
        details={
            "workflow_run_id": workflow_run_id,
            "route": canonical_workflow_run_workpage_route(
                workflow_run_id=workflow_run_id,
                workpage_kind="schedule-v0",
            ),
        },
    )


def _attach_existing_artifact_to_human_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    artifact_version_id: str,
    human_task_id: str,
    actor_id: str,
    actor_type: str,
) -> None:
    now = utc_now_iso()
    try:
        create_artifact_link(
            connection,
            artifact_version_id=artifact_version_id,
            workflow_run_id=workflow_run_id,
            subject_kind="human_task",
            subject_id=human_task_id,
            relation_kind="attachment",
            created_at=now,
            created_by_actor_id=actor_id,
            created_by_actor_type=actor_type,
        )
    except sqlite3.IntegrityError:
        pass


def _provision_future_week_stage04_inputs(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run: Mapping[str, Any],
    route_demand_artifact: Mapping[str, Any],
    source_artifacts: list[dict[str, Any]],
    intake_human_task_id: str,
    actor_id: str,
    actor_type: str,
    idempotency_base: str | None,
) -> None:
    workflow_run_id = _require_non_empty_string(
        workflow_run.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    target_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    for artifact_kind in (
        "planning.driver_capabilities.workbook",
        "planning.actual_hours_snapshot.workbook",
    ):
        existing = _latest_artifact_for_kind(target_artifacts, artifact_kind)
        if existing is None:
            source_artifact = _latest_artifact_for_kind(source_artifacts, artifact_kind)
            if source_artifact is None:
                if artifact_kind == "planning.actual_hours_snapshot.workbook":
                    continue
                raise CommandError(
                    code="stage04_input_artifact_missing",
                    message=f"{artifact_kind} is unavailable for future-week activation",
                    details={"artifact_kind": artifact_kind},
                )
            created = _copy_json_artifact_to_workflow_run(
                connection,
                storage_root=storage_root,
                workflow_run_id=workflow_run_id,
                source_artifact=source_artifact,
                actor_id=actor_id,
                actor_type=actor_type,
                event_idempotency=_event_idempotency_key(idempotency_base, artifact_kind),
                lineage_note="Copied forward future-week scheduling input.",
                attach_to_human_task_id=intake_human_task_id,
            )
            target_artifacts.append(dict(created))
        elif artifact_kind != "planning.actual_hours_snapshot.workbook":
            _attach_existing_artifact_to_human_task(
                connection,
                workflow_run_id=workflow_run_id,
                artifact_version_id=_require_non_empty_string(
                    existing.get("artifact_version_id"),
                    field_name="artifact_version_id",
                ),
                human_task_id=intake_human_task_id,
                actor_id=actor_id,
                actor_type=actor_type,
            )

    existing_availability = _latest_artifact_for_kind(
        target_artifacts,
        "planning.approved_availability.workbook",
    )
    if existing_availability is None:
        source_availability = _latest_artifact_for_kind(
            source_artifacts,
            "planning.approved_availability.workbook",
        )
        if source_availability is None:
            raise CommandError(
                code="stage04_input_artifact_missing",
                message="planning.approved_availability.workbook is unavailable for future-week activation",
                details={"artifact_kind": "planning.approved_availability.workbook"},
            )
        availability_payload = _build_future_approved_availability_payload(
            source_artifact=source_availability,
            route_demand_artifact=route_demand_artifact,
        )
        _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            artifact_kind="planning.approved_availability.workbook",
            artifact_bytes=json.dumps(availability_payload, indent=2, sort_keys=True).encode("utf-8"),
            artifact_role=str(source_availability.get("artifact_role") or "official_input"),
            file_name=_file_name_from_artifact(
                source_availability,
                default="planning_approved_availability.json",
            ),
            media_type=str(source_availability.get("media_type") or "application/json"),
            metadata_json=availability_payload,
            parent_artifact_version_id=None,
            supersedes_artifact_version_id=None,
            lineage_note="Copied forward approved availability for future-week scheduling activation.",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=_event_idempotency_key(
                idempotency_base,
                "planning.approved_availability.workbook",
            ),
            links=[
                {
                    "subject_kind": "human_task",
                    "subject_id": intake_human_task_id,
                    "relation_kind": "attachment",
                }
            ],
        )
    else:
        _attach_existing_artifact_to_human_task(
            connection,
            workflow_run_id=workflow_run_id,
            artifact_version_id=_require_non_empty_string(
                existing_availability.get("artifact_version_id"),
                field_name="artifact_version_id",
            ),
            human_task_id=intake_human_task_id,
            actor_id=actor_id,
            actor_type=actor_type,
        )


def _copy_json_artifact_to_workflow_run(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    source_artifact: Mapping[str, Any],
    actor_id: str,
    actor_type: str,
    event_idempotency: str | None,
    lineage_note: str,
    attach_to_human_task_id: str | None,
) -> Mapping[str, Any]:
    metadata = source_artifact.get("metadata_json")
    if not isinstance(metadata, Mapping):
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact metadata is unavailable for copy-forward",
            details={
                "artifact_version_id": str(source_artifact.get("artifact_version_id") or ""),
            },
        )
    return _create_workbook_artifact_version(
        connection,
        storage_root=storage_root,
        workflow_run_id=workflow_run_id,
        artifact_kind=_require_non_empty_string(
            source_artifact.get("artifact_kind"),
            field_name="artifact_kind",
        ),
        artifact_bytes=json.dumps(dict(metadata), indent=2, sort_keys=True).encode("utf-8"),
        artifact_role=str(source_artifact.get("artifact_role") or "official_input"),
        file_name=_file_name_from_artifact(source_artifact, default="artifact.json"),
        media_type=str(source_artifact.get("media_type") or "application/json"),
        metadata_json=dict(metadata),
        parent_artifact_version_id=None,
        supersedes_artifact_version_id=None,
        lineage_note=lineage_note,
        actor_id=actor_id,
        actor_type=actor_type,
        event_idempotency=event_idempotency,
        links=(
            [
                {
                    "subject_kind": "human_task",
                    "subject_id": attach_to_human_task_id,
                    "relation_kind": "attachment",
                }
            ]
            if attach_to_human_task_id
            else None
        ),
    )


def _build_future_approved_availability_payload(
    *,
    source_artifact: Mapping[str, Any],
    route_demand_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = source_artifact.get("metadata_json")
    if not isinstance(metadata, Mapping):
        raise CommandError(
            code="artifact_version_not_found",
            message="approved availability artifact metadata is unavailable",
            details={"artifact_version_id": str(source_artifact.get("artifact_version_id") or "")},
        )
    payload = dict(metadata)
    columns = [str(column) for column in payload.get("columns") or []]
    rows = list(payload.get("rows") or [])
    scope_start_text, scope_end_exclusive_text = _route_demand_scope_bounds_from_artifact(
        route_demand_artifact
    )
    target_start = date.fromisoformat(scope_start_text)
    target_end_exclusive = date.fromisoformat(scope_end_exclusive_text)
    target_dates = [
        target_start + timedelta(days=offset)
        for offset in range((target_end_exclusive - target_start).days)
    ]
    if "service_date" not in set(columns) or "availability_state" not in set(columns):
        payload["scope_start"] = scope_start_text
        payload["scope_end_exclusive"] = scope_end_exclusive_text
        payload.pop("availability_exception_overlay", None)
        return payload

    row_dicts = [
        {
            columns[index]: value
            for index, value in enumerate(row)
            if index < len(columns)
        }
        for row in rows
        if isinstance(row, list)
    ]
    template_by_driver_weekday: dict[tuple[str, int], dict[str, Any]] = {}
    for row in row_dicts:
        driver_id = str(row.get("driver_id") or "").strip()
        service_date = str(row.get("service_date") or "").strip()
        if not driver_id or not service_date:
            continue
        weekday = date.fromisoformat(service_date).weekday()
        key = (driver_id, weekday)
        existing = template_by_driver_weekday.get(key)
        if existing is None:
            template_by_driver_weekday[key] = dict(row)
            continue
        existing_penalty = 1 if str(existing.get("source_exception_id") or "").strip() else 0
        candidate_penalty = 1 if str(row.get("source_exception_id") or "").strip() else 0
        if candidate_penalty < existing_penalty:
            template_by_driver_weekday[key] = dict(row)

    next_rows: list[list[Any]] = []
    for target_date in target_dates:
        weekday = target_date.weekday()
        for (driver_id, row_weekday), template in sorted(
            template_by_driver_weekday.items(),
            key=lambda item: (item[0][0], item[0][1]),
        ):
            if row_weekday != weekday:
                continue
            next_row = dict(template)
            next_row["driver_id"] = driver_id
            next_row["service_date"] = target_date.isoformat()
            for key in (
                "source_exception_id",
                "source_workflow_run_id",
                "source_artifact_version_id",
                "reason_code",
                "reason_note",
                "exception_status",
                "locked_by_manager",
            ):
                if key in next_row:
                    next_row[key] = ""
            next_rows.append([next_row.get(column, "") for column in columns])
    payload["columns"] = columns
    payload["rows"] = next_rows
    payload["scope_start"] = scope_start_text
    payload["scope_end_exclusive"] = scope_end_exclusive_text
    payload.pop("availability_exception_overlay", None)
    return payload


def _route_demand_scope_bounds_from_artifact(
    artifact: Mapping[str, Any],
) -> tuple[str, str]:
    metadata = artifact.get("metadata_json")
    if isinstance(metadata, Mapping):
        scope_start = str(metadata.get("scope_start") or "").strip()
        scope_end_exclusive = str(metadata.get("scope_end_exclusive") or "").strip()
        if scope_start and scope_end_exclusive:
            return scope_start, scope_end_exclusive
    projection = project_route_demand_workbook(_read_route_demand_artifact_bytes(artifact))
    visible_service_dates = _route_demand_visible_service_dates(projection)
    if visible_service_dates:
        scope_start = visible_service_dates[0]
        scope_end_exclusive = (
            date.fromisoformat(scope_start) + timedelta(days=len(visible_service_dates))
        ).isoformat()
        return scope_start, scope_end_exclusive
    raise CommandError(
        code="workpage_projection_unavailable",
        message="route demand artifact is missing explicit operational scope bounds",
        details={
            "artifact_version_id": str(artifact.get("artifact_version_id") or ""),
        },
    )


def _route_demand_planning_week_id_from_metadata(metadata: Mapping[str, Any]) -> str | None:
    planning_week_id = str(metadata.get("planning_week_id") or "").strip()
    if planning_week_id:
        return planning_week_id
    scope_start = str(metadata.get("scope_start") or "").strip()
    if not scope_start:
        return None
    planning_week_monday = date.fromisoformat(scope_start) + timedelta(days=1)
    return service_day_to_future_planning_week(f"SD-{planning_week_monday.isoformat()}")


def _file_name_from_artifact(artifact: Mapping[str, Any], *, default: str) -> str:
    metadata = artifact.get("metadata_json")
    if isinstance(metadata, Mapping):
        for key in ("file_name", "ingress_file_name"):
            value = str(metadata.get(key) or "").strip()
            if value:
                return value
    return default


def _claim_human_task_if_needed(
    connection: sqlite3.Connection,
    *,
    human_task_id: str,
    actor_id: str,
    actor_type: str,
    actor_roles: list[str],
    idempotency_key_suffix: str,
) -> None:
    task = get_human_task(connection, human_task_id)
    if task is None:
        raise CommandError(
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": human_task_id},
        )
    state = str(task.get("state") or "")
    if state == "CLAIMED":
        if str(task.get("assignee_actor_id") or "") == actor_id:
            return
        raise CommandError(
            code="task_not_claimable",
            message="human task is already claimed by another actor",
            details={
                "human_task_id": human_task_id,
                "assignee_actor_id": str(task.get("assignee_actor_id") or ""),
            },
        )
    if state == "COMPLETED":
        return
    claim_human_task_command(
        connection,
        {
            "human_task_id": human_task_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "actor_roles": actor_roles,
            "lease_seconds": 900,
            "idempotency_key": idempotency_key_suffix,
        },
    )


def _spawned_weekly_stage04_build_human_task_id(result: Mapping[str, Any]) -> str:
    for item in result.get("spawned_children") or []:
        if not isinstance(item, Mapping):
            continue
        if (
            str(item.get("stage_id") or "") == "Stage04"
            and str(item.get("task_kind") or "") == "work_item"
        ):
            return _require_non_empty_string(item.get("human_task_id"), field_name="human_task_id")
    raise CommandError(
        code="human_task_not_found",
        message="weekly Stage04 build task was not spawned from intake completion",
        details={},
    )


def _latest_artifact_for_kind(
    artifacts: list[dict[str, Any]],
    artifact_kind: str,
) -> dict[str, Any] | None:
    matches = [
        artifact
        for artifact in artifacts
        if str(artifact.get("artifact_kind") or "") == artifact_kind
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
