from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping
from uuid import uuid4

from onetruth.application.handlers._shared.artifact_effects import (
    _create_artifact_version_effects,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _event_envelope,
)
from onetruth.application.handlers.workpage_action_resolution import (
    _require_non_empty_string,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    DATASET_KEY as EOD_DATASET_KEY,
    WORKFLOW_ID as EOD_WORKFLOW_ID,
)
from onetruth.application.services.schedule_control import (
    build_weekly_schedule_control_bundle,
)
from onetruth.application.services.schedule_control.draft_workbook import (
    SCHEDULE_DRAFT_DATASET_KEY,
    SCHEDULE_WORKFLOW_ID,
    draft_workbook_bytes_from_metadata_json,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    DRIVER_PREFERENCES_DATASET_KEY,
    driver_preferences_workbook_bytes_from_metadata_json,
    project_driver_preferences_workbook,
)
from onetruth.application.services.schedule_control.route_demand_workbook import (
    ROUTE_DEMAND_DATASET_KEY,
    route_demand_workbook_bytes_from_metadata_json,
)
from onetruth.application.services.schedule_control.stage04_input_registry import (
    resolve_weekly_stage04_input_artifacts,
)
from onetruth.application.services.schedule_control.workpage_calculations import (
    SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY,
    build_schedule_bundle_from_dependencies,
    build_schedule_calculation_snapshot_payload,
    build_schedule_manual_draft_doc_payload,
    build_schedule_manual_validation_summary_payload,
    normalize_schedule_dependency_manifest,
    project_schedule_dependency_state,
    resolve_schedule_dependency_artifacts,
)
from onetruth.application.services.logistics_workpages import (
    ROUTE_DEMAND_REFRESH_TASK_ACTIVATION_PREFIX,
    build_route_demand_refresh_activation_key,
    canonical_driver_preferences_artifact_route,
    canonical_eod_artifact_route,
    canonical_route_demand_artifact_route,
    canonical_schedule_artifact_route,
    latest_schedule_draft_artifact,
)
from onetruth.application.services.template_registry import (
    TemplateRecord,
    load_template_registry_catalog,
)
from onetruth.infrastructure.artifacts.storage import (
    ArtifactStorageError,
    read_blob,
    write_blob,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    get_latest_artifact_version_in_chain,
    get_superseding_artifact_version,
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.human_tasks import (
    create_human_task,
    get_human_task,
    list_human_tasks_for_workflow_run,
)
from onetruth.infrastructure.repositories.task_runs import create_task_run, get_task_run
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run

EOD_DEFAULT_SERVICE_DATE = "2026-03-16"
EOD_DEFAULT_STATION_CODE = "DVC4"
EOD_DEFAULT_DSP_NAME = "QDCI"
EOD_TEMPLATE_ID = "dispatch_reporting.stage03.upd_draft.workbook.empty.v1"


def _create_workbook_artifact_version(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    artifact_kind: str,
    artifact_bytes: bytes,
    artifact_role: str | None,
    file_name: str,
    media_type: str,
    metadata_json: dict[str, Any],
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    lineage_note: str,
    actor_id: str,
    actor_type: str,
    event_idempotency: str | None,
    links: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    storage_uri, content_digest, byte_size = write_blob(
        storage_root=storage_root,
        workflow_run_id=workflow_run_id,
        file_name=file_name,
        content=artifact_bytes,
    )
    return _create_artifact_version_effects(
        connection,
        {
            "artifact_version_id": f"av-{uuid4()}",
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": artifact_role,
            "media_type": media_type,
            "storage_uri": storage_uri,
            "content_digest": content_digest,
            "byte_size": byte_size,
            "metadata_json": {
                **metadata_json,
                "file_name": file_name,
                "ingress_file_name": file_name,
                "ingress_media_type": media_type,
            },
            "parent_artifact_version_id": parent_artifact_version_id,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "lineage_note": lineage_note,
            "links": links,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=event_idempotency,
    )

def _schedule_submitted_metadata(updated_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(updated_bytes.decode("utf-8"))
    except Exception as exc:
        raise CommandError(
            code="invalid_payload",
            message="updated schedule draft workbook must remain valid JSON",
            details={},
        ) from exc
    if not isinstance(payload, Mapping):
        raise CommandError(
            code="invalid_payload",
            message="updated schedule draft workbook must decode to an object",
            details={},
        )
    return dict(payload)

def _route_demand_submitted_metadata(updated_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(updated_bytes.decode("utf-8"))
    except Exception as exc:
        raise CommandError(
            code="invalid_payload",
            message="updated route demand workbook must remain valid JSON",
            details={},
        ) from exc
    if not isinstance(payload, Mapping):
        raise CommandError(
            code="invalid_payload",
            message="updated route demand workbook must decode to an object",
            details={},
        )
    return dict(payload)

def _driver_preferences_submitted_metadata(updated_bytes: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(updated_bytes.decode("utf-8"))
    except Exception as exc:
        raise CommandError(
            code="invalid_payload",
            message="updated driver preferences workbook must remain valid JSON",
            details={},
        ) from exc
    if not isinstance(payload, Mapping):
        raise CommandError(
            code="invalid_payload",
            message="updated driver preferences workbook must decode to an object",
            details={},
        )
    return dict(payload)

def _schedule_preview_context(
    connection: sqlite3.Connection,
    *,
    artifact: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], Any, Any, dict[str, Any] | None]:
    workflow_run_id = _require_non_empty_string(
        artifact.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found for schedule workpage artifact",
            details={"workflow_run_id": workflow_run_id},
        )
    artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    dependency_projection = project_schedule_dependency_state(
        dependency_manifest=_schedule_dependency_manifest(artifact),
        artifacts=artifacts,
    )
    dependency_artifacts = resolve_schedule_dependency_artifacts(
        workflow_run_id=workflow_run_id,
        artifacts=artifacts,
        dependency_manifest=_schedule_dependency_manifest(artifact),
    )
    try:
        bundle = build_schedule_bundle_from_dependencies(
            workflow_run=workflow_run,
            dependency_artifacts_by_key=dependency_artifacts,
        )
    except ValueError:
        bundle = None
    driver_preferences_projection = _driver_preferences_projection_from_dependency_artifacts(
        dependency_artifacts
    )
    return workflow_run, artifacts, dependency_projection, bundle, driver_preferences_projection

def _schedule_dependency_manifest(artifact: Mapping[str, Any]) -> object:
    metadata_json = artifact.get("metadata_json")
    if isinstance(metadata_json, Mapping):
        return metadata_json.get("dependency_manifest")
    return None

def _driver_preferences_projection_from_dependency_artifacts(
    dependency_artifacts: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any] | None:
    artifact = dependency_artifacts.get("driver_preferences")
    if artifact is None:
        return None
    try:
        return project_driver_preferences_workbook(
            driver_preferences_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))
        )
    except ValueError:
        return None

def _pin_latest_driver_preferences_dependency(
    raw_manifest: object,
    *,
    latest_driver_preferences: Mapping[str, Any],
) -> list[dict[str, Any]]:
    normalized = normalize_schedule_dependency_manifest(raw_manifest)
    latest_artifact_version_id = _require_non_empty_string(
        latest_driver_preferences.get("artifact_version_id"),
        field_name="artifact_version_id",
    )
    for row in normalized:
        if str(row.get("dependency_key") or "") != "driver_preferences":
            continue
        if str(row.get("artifact_version_id") or "").strip():
            return normalized
        row["artifact_version_id"] = latest_artifact_version_id
        row["source_ref"] = f"/api/v1/artifacts/{latest_artifact_version_id}"
        return normalized
    normalized.append(
        {
            "dependency_key": "driver_preferences",
            "artifact_kind": DRIVER_PREFERENCES_DATASET_KEY,
            "artifact_version_id": latest_artifact_version_id,
            "impact_class": "soft",
            "source_ref": f"/api/v1/artifacts/{latest_artifact_version_id}",
        }
    )
    return normalized

def _driver_preferences_artifact_version_id_from_manifest(raw_manifest: object) -> str | None:
    for row in normalize_schedule_dependency_manifest(raw_manifest):
        if str(row.get("dependency_key") or "") != "driver_preferences":
            continue
        artifact_version_id = str(row.get("artifact_version_id") or "").strip()
        return artifact_version_id or None
    return None

def _create_schedule_companion_artifacts(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    base_artifact: Mapping[str, Any],
    draft_artifact_version_id: str,
    bundle: Any,
    dependency_state: str,
    dependencies: list[dict[str, Any]],
    calculations: dict[str, Any],
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    driver_preferences_projection: Mapping[str, Any] | None,
    actor_id: str,
    actor_type: str,
    validation_summary_event_idempotency: str | None,
    draft_doc_event_idempotency: str | None,
    calculation_snapshot_event_idempotency: str | None,
) -> None:
    validation_payload = build_schedule_manual_validation_summary_payload(
        bundle=bundle,
        dependency_state=dependency_state,
        dependencies=dependencies,
        calculations=calculations,
    )
    draft_doc_payload = build_schedule_manual_draft_doc_payload(
        bundle=bundle,
        dependency_state=dependency_state,
        calculations=calculations,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
    )
    calculation_snapshot_payload = build_schedule_calculation_snapshot_payload(
        bundle=bundle,
        dependency_state=dependency_state,
        dependencies=dependencies,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
        driver_preferences_projection=driver_preferences_projection,
    )

    for artifact_kind, payload, file_name, event_idempotency in (
        (
            "planning.validation_summary.doc",
            validation_payload,
            _schedule_companion_file_name(
                base_artifact=base_artifact,
                suffix="validation_summary.json",
            ),
            validation_summary_event_idempotency,
        ),
        (
            "planning.draft_weekly_schedule.doc",
            draft_doc_payload,
            _schedule_companion_file_name(
                base_artifact=base_artifact,
                suffix="draft_doc.json",
            ),
            draft_doc_event_idempotency,
        ),
        (
            SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY,
            calculation_snapshot_payload,
            _schedule_companion_file_name(
                base_artifact=base_artifact,
                suffix="calculation_snapshot.json",
            ),
            calculation_snapshot_event_idempotency,
        ),
    ):
        companion_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            artifact_kind=artifact_kind,
            artifact_bytes=companion_bytes,
            artifact_role="evidence",
            file_name=file_name,
            media_type="application/json",
            metadata_json={
                **payload,
                "draft_artifact_version_id": draft_artifact_version_id,
            },
            parent_artifact_version_id=draft_artifact_version_id,
            supersedes_artifact_version_id=None,
            lineage_note="schedule_workpage_companion",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=event_idempotency,
            links=None,
        )

def _create_or_reuse_route_demand_schedule_refresh_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    route_demand_artifact_version_id: str,
    artifacts: list[dict[str, Any]],
    actor_id: str,
    actor_type: str,
) -> dict[str, Any] | None:
    latest_schedule_draft = latest_schedule_draft_artifact(artifacts)
    if latest_schedule_draft is None:
        return None
    dependency_projection = project_schedule_dependency_state(
        dependency_manifest=_schedule_dependency_manifest(latest_schedule_draft),
        artifacts=artifacts,
    )
    route_dependency = next(
        (
            row
            for row in dependency_projection.dependencies
            if str(row.get("dependency_key") or "") == "route_slot_requirements"
        ),
        None,
    )
    if route_dependency is not None and str(route_dependency.get("state") or "") == "aligned":
        return None

    existing = _active_route_demand_refresh_task(
        connection,
        workflow_run_id=workflow_run_id,
    )
    if existing is not None:
        return existing

    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found for route-demand refresh task creation",
            details={"workflow_run_id": workflow_run_id},
        )

    now = utc_now_iso()
    task_run_id = f"tr-{uuid4()}"
    human_task_id = f"ht-{uuid4()}"
    activation_key = build_route_demand_refresh_activation_key(
        artifact_version_id=route_demand_artifact_version_id
    )

    create_task_run(
        connection,
        task_run_id=task_run_id,
        workflow_run_id=workflow_run_id,
        stage_id="Stage04",
        task_kind="work_item",
        state="READY",
        generation=0,
        activation_key=activation_key,
        blocked_on_kind="artifact_version",
        blocked_on_ref=route_demand_artifact_version_id,
        spawned_from_flag_id=None,
        spawned_from_task_run_id=None,
        spawn_rule_id=None,
        spawn_cause_kind="route_demand_refresh",
        spawn_cause_event_id=None,
        spawn_depth=0,
        spawn_budget_key=None,
        created_at=now,
    )
    create_human_task(
        connection,
        human_task_id=human_task_id,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        task_kind="work_item",
        state="OPEN",
        candidate_roles=["schedule_planner"],
        owner_role="schedule_planner",
        due_at=None,
        escalation_at=None,
        generation=0,
        created_at=now,
    )
    append_event(
        connection,
        _event_envelope(
            event_type="task.run.created",
            tenant_id=str(workflow_run["tenant_id"]),
            domain_id=str(workflow_run["domain_id"]),
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {"rel": "subject", "type": "task_run", "id": task_run_id},
            ],
            payload={
                "task_run_id": task_run_id,
                "stage_id": "Stage04",
                "task_kind": "work_item",
                "activation_key": activation_key,
                "generation": 0,
                "spawned_from_flag_id": None,
                "spawned_from_task_run_id": None,
                "spawn_rule_id": None,
                "spawn_cause_kind": "route_demand_refresh",
                "spawn_cause_event_id": None,
                "spawn_budget_key": None,
                "spawn_depth": 0,
            },
            idempotency_key=None,
        ),
    )
    append_event(
        connection,
        _event_envelope(
            event_type="task.created",
            tenant_id=str(workflow_run["tenant_id"]),
            domain_id=str(workflow_run["domain_id"]),
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {"rel": "subject", "type": "task_run", "id": task_run_id},
                {"rel": "subject", "type": "human_task", "id": human_task_id},
            ],
            payload={
                "human_task_id": human_task_id,
                "task_kind": "work_item",
                "state": "OPEN",
                "candidate_roles": ["schedule_planner"],
            },
            idempotency_key=None,
        ),
    )
    task_run = get_task_run(connection, task_run_id)
    human_task = get_human_task(connection, human_task_id)
    if task_run is None or human_task is None:
        raise CommandError(
            code="refresh_task_not_found",
            message="route-demand refresh task was not found after creation",
            details={
                "task_run_id": task_run_id,
                "human_task_id": human_task_id,
            },
        )
    return {
        "task_run": task_run,
        "human_task": human_task,
    }

def _active_route_demand_refresh_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    for task in reversed(list_human_tasks_for_workflow_run(connection, workflow_run_id)):
        task_run = get_task_run(connection, str(task.get("task_run_id") or ""))
        if task_run is None:
            continue
        activation_key = str(task_run.get("activation_key") or "")
        if not activation_key.startswith(ROUTE_DEMAND_REFRESH_TASK_ACTIVATION_PREFIX):
            continue
        if str(task_run.get("stage_id") or "") != "Stage04":
            continue
        if str(task.get("task_kind") or "") != "work_item":
            continue
        if str(task.get("state") or "") not in {"OPEN", "CLAIMED"}:
            continue
        return {
            "task_run": task_run,
            "human_task": task,
        }
    return None

def _driver_preferences_bundle_for_run(
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
):
    try:
        resolved_inputs = resolve_weekly_stage04_input_artifacts(
            artifacts=artifacts,
            stage_spec={
                "required_evidence_keys": [
                    ROUTE_DEMAND_DATASET_KEY,
                    "planning.driver_capabilities.workbook",
                ]
            },
        )
        return build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=_require_stage04_input_artifact(
                resolved_inputs.get("route_slot_requirements"),
                field_name="route_slot_requirements",
            ),
            driver_capabilities_artifact=_require_stage04_input_artifact(
                resolved_inputs.get("driver_capabilities"),
                field_name="driver_capabilities",
            ),
            approved_availability_artifact=_optional_stage04_input_artifact(
                resolved_inputs.get("approved_availability")
            ),
            actual_hours_artifact=_optional_stage04_input_artifact(
                resolved_inputs.get("actual_hours")
            ),
            route_horizon_artifact=None,
        )
    except CommandError as exc:
        if exc.code != "stage04_input_artifact_missing":
            raise
        missing_slots = exc.details.get("missing_slots", [])
        missing_dataset_keys = [
            str(slot.get("dataset_key") or "").strip()
            for slot in missing_slots
            if isinstance(slot, Mapping) and str(slot.get("dataset_key") or "").strip()
        ]
        raise CommandError(
            code="workpage_projection_unavailable",
            message="driver preferences snapshot requires weekly Stage04 roster inputs",
            details={
                "workflow_run_id": str(workflow_run.get("workflow_run_id") or ""),
                "workpage_id": "driver-preferences-v0",
                "missing_dataset_keys": missing_dataset_keys,
            },
        ) from exc
    except ValueError as exc:
        raise CommandError(
            code="workpage_projection_unavailable",
            message=str(exc),
            details={
                "workflow_run_id": str(workflow_run.get("workflow_run_id") or ""),
                "workpage_id": "driver-preferences-v0",
            },
        ) from exc

def _load_eod_template_record() -> TemplateRecord:
    try:
        return load_template_registry_catalog().template_by_id(EOD_TEMPLATE_ID)
    except ValueError as exc:
        raise CommandError(
            code="template_not_found",
            message="required EOD draft template is unavailable",
            details={"template_id": EOD_TEMPLATE_ID},
        ) from exc

def _read_workbook_bytes(artifact: Mapping[str, Any]) -> bytes:
    storage_uri = _require_non_empty_string(
        artifact.get("storage_uri"),
        field_name="storage_uri",
    )
    try:
        return read_blob(storage_uri)
    except ArtifactStorageError as exc:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact blob not found",
            details={"artifact_version_id": str(artifact.get("artifact_version_id") or "")},
        ) from exc

def _assert_artifact_not_already_superseded(
    connection: sqlite3.Connection,
    artifact_version_id: str,
    *,
    route_builder,
) -> None:
    superseding = get_superseding_artifact_version(connection, artifact_version_id)
    if superseding is None:
        return
    latest = get_latest_artifact_version_in_chain(connection, artifact_version_id)
    latest_id = (
        str(latest["artifact_version_id"])
        if latest is not None
        else str(superseding["artifact_version_id"])
    )
    raise CommandError(
        code="workpage_artifact_conflict",
        message="artifact-backed workpage submit references a stale base artifact version",
        details={
            "artifact_version_id": artifact_version_id,
            "latest_artifact_version_id": latest_id,
            "workflow_run_id": str(superseding["workflow_run_id"]),
            "route": route_builder(
                workflow_run_id=str(superseding["workflow_run_id"]),
                artifact_version_id=latest_id,
            ),
        },
    )

def _require_eod_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    if str(artifact.get("artifact_kind") or "") != EOD_DATASET_KEY:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = get_workflow_run(connection, str(artifact["workflow_run_id"]))
    if workflow_run is None or str(workflow_run.get("workflow_id") or "") != EOD_WORKFLOW_ID:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact

def _require_schedule_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    if str(artifact.get("artifact_kind") or "") != SCHEDULE_DRAFT_DATASET_KEY:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = get_workflow_run(connection, str(artifact["workflow_run_id"]))
    if workflow_run is None or str(workflow_run.get("workflow_id") or "") != SCHEDULE_WORKFLOW_ID:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact

def _require_route_demand_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    if str(artifact.get("artifact_kind") or "") != ROUTE_DEMAND_DATASET_KEY:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = get_workflow_run(connection, str(artifact["workflow_run_id"]))
    if workflow_run is None or str(workflow_run.get("workflow_id") or "") != SCHEDULE_WORKFLOW_ID:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact

def _require_driver_preferences_artifact_version(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    if str(artifact.get("artifact_kind") or "") != DRIVER_PREFERENCES_DATASET_KEY:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    workflow_run = get_workflow_run(connection, str(artifact["workflow_run_id"]))
    if workflow_run is None or str(workflow_run.get("workflow_id") or "") != SCHEDULE_WORKFLOW_ID:
        raise CommandError(
            code="workpage_artifact_not_found",
            message="artifact-backed workpage not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact

def _read_schedule_draft_artifact_bytes(artifact: Mapping[str, Any]) -> bytes:
    storage_uri = str(artifact.get("storage_uri") or "")
    if storage_uri.startswith("file:"):
        return _read_workbook_bytes(artifact)
    metadata_json = artifact.get("metadata_json")
    try:
        return draft_workbook_bytes_from_metadata_json(metadata_json)
    except ValueError as exc:
        raise CommandError(
            code="artifact_version_not_found",
            message=str(exc),
            details={"artifact_version_id": str(artifact.get("artifact_version_id") or "")},
        ) from exc

def _read_route_demand_artifact_bytes(artifact: Mapping[str, Any]) -> bytes:
    storage_uri = str(artifact.get("storage_uri") or "")
    if storage_uri.startswith("file:"):
        return _read_workbook_bytes(artifact)
    try:
        return route_demand_workbook_bytes_from_metadata_json(artifact.get("metadata_json"))
    except ValueError as exc:
        raise CommandError(
            code="artifact_version_not_found",
            message=str(exc),
            details={"artifact_version_id": str(artifact.get("artifact_version_id") or "")},
        ) from exc

def _read_driver_preferences_artifact_bytes(artifact: Mapping[str, Any]) -> bytes:
    storage_uri = str(artifact.get("storage_uri") or "")
    if storage_uri.startswith("file:"):
        return _read_workbook_bytes(artifact)
    try:
        return driver_preferences_workbook_bytes_from_metadata_json(
            artifact.get("metadata_json")
        )
    except ValueError as exc:
        raise CommandError(
            code="artifact_version_not_found",
            message=str(exc),
            details={"artifact_version_id": str(artifact.get("artifact_version_id") or "")},
        ) from exc

def _require_projection_rows(raw_value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(raw_value, list):
        raise CommandError(
            code="invalid_payload",
            message=f"{label} projection must be a list",
            details={},
        )
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(raw_value):
        if not isinstance(row, Mapping):
            raise CommandError(
                code="invalid_payload",
                message=f"{label}[{index}] projection row must be an object",
                details={},
            )
        rows.append(dict(row))
    return rows

def _require_stage04_input_artifact(
    value: Mapping[str, Any] | None,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if value is None:
        raise CommandError(
            code="workpage_projection_unavailable",
            message=f"{field_name} artifact is required",
            details={"field_name": field_name},
        )
    return value

def _optional_stage04_input_artifact(
    value: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    return value if value is not None else None

def _metadata_string(
    metadata_json: Any,
    key: str,
    *,
    default: str,
) -> str:
    if isinstance(metadata_json, Mapping):
        value = metadata_json.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return default

def _canonical_eod_ui_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return canonical_eod_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )

def _canonical_schedule_ui_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return canonical_schedule_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )

def _canonical_route_demand_ui_route(*, workflow_run_id: str, artifact_version_id: str) -> str:
    return canonical_route_demand_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )

def _canonical_driver_preferences_ui_route(
    *,
    workflow_run_id: str,
    artifact_version_id: str,
) -> str:
    return canonical_driver_preferences_artifact_route(
        workflow_run_id=workflow_run_id,
        artifact_version_id=artifact_version_id,
    )

def _draft_file_name() -> str:
    return "dispatch_reporting_eod_v0_2026-03-16_qdci_dvc4_upd_draft.xlsx"

def _schedule_draft_file_name(base_artifact: Mapping[str, Any]) -> str:
    return _metadata_string(
        base_artifact.get("metadata_json"),
        "file_name",
        default=(
            f"weekly_schedule_stage04_{str(base_artifact.get('workflow_run_id') or 'draft')}_"
            "draft_workbook.json"
        ),
    )

def _route_demand_file_name(base_artifact: Mapping[str, Any]) -> str:
    return _metadata_string(
        base_artifact.get("metadata_json"),
        "file_name",
        default=(
            f"weekly_schedule_stage04_{str(base_artifact.get('workflow_run_id') or 'route-demand')}_"
            "route_demand_workbook.json"
        ),
    )

def _driver_preferences_file_name(base_artifact: Mapping[str, Any]) -> str:
    return _metadata_string(
        base_artifact.get("metadata_json"),
        "file_name",
        default=(
            f"weekly_schedule_stage04_{str(base_artifact.get('workflow_run_id') or 'driver-preferences')}_"
            "driver_preferences_workbook.json"
        ),
    )

def _schedule_companion_file_name(
    *,
    base_artifact: Mapping[str, Any],
    suffix: str,
) -> str:
    base_file_name = _schedule_draft_file_name(base_artifact)
    if base_file_name.endswith("draft_workbook.json"):
        return base_file_name.removesuffix("draft_workbook.json") + suffix
    return f"{base_file_name}.{suffix}"

def _xlsx_media_type() -> str:
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

def _artifact_links_for_workpage_subject(
    subject_link: Mapping[str, str] | None,
    *,
    relation_kind: str,
) -> list[dict[str, str]] | None:
    if subject_link is None:
        return None
    return [
        {
            "subject_kind": str(subject_link["subject_kind"]),
            "subject_id": str(subject_link["subject_id"]),
            "relation_kind": relation_kind,
        }
    ]
