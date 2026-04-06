from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

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
    _assert_artifact_not_already_superseded,
    _canonical_driver_preferences_ui_route,
    _canonical_route_demand_ui_route,
    _create_or_reuse_route_demand_schedule_refresh_task,
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
from onetruth.application.services.logistics_workpages import latest_driver_preferences_artifact
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    DRIVER_PREFERENCES_DATASET_KEY,
    build_initial_driver_preferences_workbook,
    materialize_driver_preferences_workbook,
)
from onetruth.application.services.schedule_control.draft_workbook import SCHEDULE_WORKFLOW_ID
from onetruth.application.services.schedule_control.route_demand_workbook import (
    ROUTE_DEMAND_DATASET_KEY,
    materialize_route_demand_workbook,
)
from onetruth.application.services.workpage_descriptors import (
    DRIVER_PREFERENCES_WORKPAGE_KIND,
    ROUTE_DEMAND_WORKPAGE_KIND,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
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
        try:
            updated_bytes = materialize_route_demand_workbook(
                workbook_bytes,
                daily_demand_rows=payload.get("daily_demand_rows"),
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
            artifact_kind=ROUTE_DEMAND_DATASET_KEY,
            artifact_bytes=updated_bytes,
            artifact_role=(
                str(base_artifact["artifact_role"])
                if base_artifact.get("artifact_role") is not None
                else None
            ),
            file_name=_route_demand_file_name(base_artifact),
            media_type=str(base_artifact.get("media_type") or "application/json"),
            metadata_json=_route_demand_submitted_metadata(updated_bytes),
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
        artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        _create_or_reuse_route_demand_schedule_refresh_task(
            connection,
            workflow_run_id=workflow_run_id,
            route_demand_artifact_version_id=submitted_artifact_version_id,
            artifacts=artifacts,
            actor_id=actor_id,
            actor_type=actor_type,
        )
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
