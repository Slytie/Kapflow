from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import CommandError
from onetruth.application.services.schedule_control import (
    build_weekly_schedule_control_bundle,
    run_weekly_stage04_deterministic_build,
)
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.artifact_provenance import create_artifact_provenance_edge
from onetruth.infrastructure.repositories.artifact_versions import (
    create_artifact_version,
    get_artifact_version,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run


WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"

STAGE04_OUTPUT_SPECS: tuple[tuple[str, str], ...] = (
    ("planning.input_bundle.doc", "official_input"),
    ("planning.candidate_schedule_delta.workbook", "official_input"),
    ("planning.validation_summary.doc", "evidence"),
    ("planning.draft_weekly_schedule.workbook", "official_input"),
    ("planning.draft_weekly_schedule.doc", "evidence"),
)


def build_weekly_schedule_control_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "route_slot_requirements_artifact_version_id",
            "driver_capabilities_artifact_version_id",
            "idempotency_key",
        ],
    )

    workflow_run_id = str(payload["workflow_run_id"])
    workflow_run = _require_workflow_run(connection, workflow_run_id)
    if str(workflow_run.get("workflow_id") or "") != WEEKLY_WORKFLOW_ID:
        raise CommandError(
            code="invalid_workflow_for_stage04_build",
            message="deterministic Stage04 weekly build requires weekly_schedule_planning.v1 workflow run",
            details={
                "workflow_run_id": workflow_run_id,
                "workflow_id": str(workflow_run.get("workflow_id") or ""),
            },
        )

    route_slot_artifact = _require_input_artifact(
        connection,
        artifact_version_id=str(payload["route_slot_requirements_artifact_version_id"]),
        workflow_run_id=workflow_run_id,
        expected_artifact_kind="planning.route_slot_requirements.workbook",
    )
    driver_capability_artifact = _require_input_artifact(
        connection,
        artifact_version_id=str(payload["driver_capabilities_artifact_version_id"]),
        workflow_run_id=workflow_run_id,
        expected_artifact_kind="planning.driver_capabilities.workbook",
    )

    approved_availability_artifact = _optional_input_artifact(
        connection,
        artifact_version_id=payload.get("approved_availability_artifact_version_id"),
        workflow_run_id=workflow_run_id,
        expected_artifact_kind="planning.approved_availability.workbook",
    )
    actual_hours_artifact = _optional_input_artifact(
        connection,
        artifact_version_id=payload.get("actual_hours_artifact_version_id"),
        workflow_run_id=workflow_run_id,
        expected_artifact_kind="planning.actual_hours_snapshot.workbook",
    )
    route_horizon_artifact = _optional_input_artifact(
        connection,
        artifact_version_id=payload.get("route_horizon_artifact_version_id"),
        workflow_run_id=workflow_run_id,
        expected_artifact_kind="planning.route_horizon.workbook",
    )

    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=route_slot_artifact,
        driver_capabilities_artifact=driver_capability_artifact,
        approved_availability_artifact=approved_availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
        route_horizon_artifact=route_horizon_artifact,
    )
    deterministic_build = run_weekly_stage04_deterministic_build(bundle=bundle)

    planning_week_id = str(workflow_run.get("partition_key") or "")
    output_payloads = {
        "planning.input_bundle.doc": deterministic_build.input_bundle_payload,
        "planning.candidate_schedule_delta.workbook": deterministic_build.candidate_delta_payload,
        "planning.validation_summary.doc": deterministic_build.validation_summary_payload,
        "planning.draft_weekly_schedule.workbook": deterministic_build.draft_workbook_payload,
        "planning.draft_weekly_schedule.doc": deterministic_build.draft_doc_payload,
    }

    source_inputs = [
        route_slot_artifact,
        driver_capability_artifact,
        approved_availability_artifact,
        actual_hours_artifact,
        route_horizon_artifact,
    ]
    source_input_ids = [
        str(item.get("artifact_version_id") or "")
        for item in source_inputs
        if item is not None and str(item.get("artifact_version_id") or "").strip()
    ]

    created_outputs = persist_weekly_stage04_output_payloads(
        connection,
        workflow_run=workflow_run,
        bundle_id=bundle.bundle_id,
        output_payloads=output_payloads,
        source_input_ids=source_input_ids,
    )

    return {
        "bundle_id": bundle.bundle_id,
        "workflow_run_id": workflow_run_id,
        "candidate_count": len(deterministic_build.candidate_matrix),
        "selected_candidate_count": len(deterministic_build.selected_candidates),
        "selected_candidates": deterministic_build.selected_candidates,
        "iteration_summaries": deterministic_build.iteration_summaries,
        "repair_moves": deterministic_build.repair_moves,
        "coverage_summary": deterministic_build.coverage_summary,
        "artifacts": {
            "input_bundle": created_outputs["planning.input_bundle.doc"],
            "candidate_delta": created_outputs["planning.candidate_schedule_delta.workbook"],
            "validation_summary": created_outputs["planning.validation_summary.doc"],
            "draft_workbook": created_outputs["planning.draft_weekly_schedule.workbook"],
            "draft_doc": created_outputs["planning.draft_weekly_schedule.doc"],
        },
        "artifact_payloads": output_payloads,
    }


def persist_weekly_stage04_output_payloads(
    connection: sqlite3.Connection,
    *,
    workflow_run: dict[str, Any],
    bundle_id: str,
    output_payloads: dict[str, dict[str, Any]],
    source_input_ids: list[str],
) -> dict[str, dict[str, Any]]:
    workflow_run_id = str(workflow_run.get("workflow_run_id") or "")
    planning_week_id = str(workflow_run.get("partition_key") or "")
    candidate_delta_id = str(
        (output_payloads.get("planning.candidate_schedule_delta.workbook") or {}).get(
            "candidate_delta_id"
        )
        or ""
    )
    created_outputs: dict[str, dict[str, Any]] = {}
    _begin_transaction(connection)
    try:
        for artifact_kind, artifact_role in STAGE04_OUTPUT_SPECS:
            artifact_id = _stable_output_artifact_id(
                workflow_run_id=workflow_run_id,
                artifact_kind=artifact_kind,
                bundle_id=bundle_id,
                candidate_delta_id=candidate_delta_id,
            )
            created = _create_or_load_artifact_version(
                connection,
                artifact_version_id=artifact_id,
                workflow_run_id=workflow_run_id,
                tenant_id=str(workflow_run.get("tenant_id") or ""),
                domain_id=str(workflow_run.get("domain_id") or ""),
                dataset_key=artifact_kind,
                partition_kind="PlanningWeekID",
                partition_key=planning_week_id,
                artifact_kind=artifact_kind,
                artifact_role=artifact_role,
                media_type="application/json",
                storage_uri=f"inmem://schedule-control/{workflow_run_id}/{artifact_kind}",
                content_digest=f"sha256:{_digest_payload(output_payloads[artifact_kind])}",
                metadata_json=output_payloads[artifact_kind],
                parent_artifact_version_id=None,
                supersedes_artifact_version_id=None,
                lineage_note="stage04_deterministic_schedule_control",
                created_at=utc_now_iso(),
            )
            created_outputs[artifact_kind] = created

        output_input_bundle_id = str(
            created_outputs["planning.input_bundle.doc"].get("artifact_version_id") or ""
        )
        for artifact_kind, output_artifact in created_outputs.items():
            output_id = str(output_artifact.get("artifact_version_id") or "")
            if not output_id:
                continue
            for source_input_id in source_input_ids:
                _create_or_ignore_provenance_edge(
                    connection,
                    output_artifact_version_id=output_id,
                    input_artifact_version_id=source_input_id,
                    workflow_run_id=workflow_run_id,
                    edge_id=f"ape-{_stable_hash('stage04-source', output_id, source_input_id)}",
                    edge_order=0,
                    created_at=utc_now_iso(),
                    edge_type="derives_from",
                    metadata_json={
                        "stage_id": "Stage04",
                        "lineage_class": "deterministic_weekly_build",
                    },
                )
            if artifact_kind == "planning.input_bundle.doc":
                continue
            _create_or_ignore_provenance_edge(
                connection,
                output_artifact_version_id=output_id,
                input_artifact_version_id=output_input_bundle_id,
                workflow_run_id=workflow_run_id,
                edge_id=f"ape-{_stable_hash('stage04-bundle', output_id, output_input_bundle_id)}",
                edge_order=1,
                created_at=utc_now_iso(),
                edge_type="derives_from",
                metadata_json={
                    "stage_id": "Stage04",
                    "lineage_class": "bundle_lowering",
                },
            )
    except Exception:
        connection.rollback()
        raise
    connection.commit()
    return created_outputs


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if payload.get(field) is None]
    if missing:
        raise CommandError(
            code="missing_required_fields",
            message="required fields are missing",
            details={"missing_fields": missing},
        )


def _begin_transaction(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN")


def _require_workflow_run(connection: sqlite3.Connection, workflow_run_id: str) -> dict[str, Any]:
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    return workflow_run


def _require_input_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    expected_artifact_kind: str,
) -> dict[str, Any]:
    artifact = _require_artifact(connection, artifact_version_id)
    if str(artifact.get("workflow_run_id") or "") != workflow_run_id:
        raise CommandError(
            code="cross_workflow_artifact_reference",
            message="artifact belongs to a different workflow run",
            details={
                "artifact_version_id": artifact_version_id,
                "artifact_workflow_run_id": str(artifact.get("workflow_run_id") or ""),
                "workflow_run_id": workflow_run_id,
            },
        )
    artifact_kind = str(artifact.get("artifact_kind") or "")
    if artifact_kind != expected_artifact_kind:
        raise CommandError(
            code="unexpected_artifact_kind",
            message="artifact kind does not match required Stage04 input",
            details={
                "artifact_version_id": artifact_version_id,
                "expected_artifact_kind": expected_artifact_kind,
                "artifact_kind": artifact_kind,
            },
        )
    return artifact


def _optional_input_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: Any,
    workflow_run_id: str,
    expected_artifact_kind: str,
) -> dict[str, Any] | None:
    if artifact_version_id is None:
        return None
    return _require_input_artifact(
        connection,
        artifact_version_id=str(artifact_version_id),
        workflow_run_id=workflow_run_id,
        expected_artifact_kind=expected_artifact_kind,
    )


def _require_artifact(connection: sqlite3.Connection, artifact_version_id: str) -> dict[str, Any]:
    artifact = get_artifact_version(connection, artifact_version_id)
    if artifact is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact


def _create_or_load_artifact_version(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    tenant_id: str,
    domain_id: str,
    dataset_key: str,
    partition_kind: str,
    partition_key: str,
    artifact_kind: str,
    artifact_role: str,
    media_type: str,
    storage_uri: str,
    content_digest: str,
    metadata_json: dict[str, Any],
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    lineage_note: str | None,
    created_at: str,
) -> dict[str, Any]:
    existing = get_artifact_version(connection, artifact_version_id)
    if existing is not None:
        return existing

    create_artifact_version(
        connection,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        dataset_key=dataset_key,
        partition_kind=partition_kind,
        partition_key=partition_key,
        task_run_id=None,
        artifact_kind=artifact_kind,
        artifact_role=artifact_role,
        media_type=media_type,
        storage_uri=storage_uri,
        content_digest=content_digest,
        byte_size=None,
        metadata_json=metadata_json,
        parent_artifact_version_id=parent_artifact_version_id,
        supersedes_artifact_version_id=supersedes_artifact_version_id,
        lineage_note=lineage_note,
        created_at=created_at,
    )

    created = get_artifact_version(connection, artifact_version_id)
    if created is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found after create",
            details={"artifact_version_id": artifact_version_id},
        )
    return created


def _create_or_ignore_provenance_edge(
    connection: sqlite3.Connection,
    *,
    output_artifact_version_id: str,
    input_artifact_version_id: str,
    workflow_run_id: str,
    edge_id: str,
    edge_order: int,
    created_at: str,
    edge_type: str,
    metadata_json: dict[str, Any],
) -> None:
    try:
        create_artifact_provenance_edge(
            connection,
            edge_id=edge_id,
            output_artifact_version_id=output_artifact_version_id,
            input_artifact_version_id=input_artifact_version_id,
            edge_type=edge_type,
            workflow_run_id=workflow_run_id,
            edge_order=edge_order,
            metadata_json=metadata_json,
            created_at=created_at,
        )
    except sqlite3.IntegrityError:
        return


def _stable_output_artifact_id(
    *,
    workflow_run_id: str,
    artifact_kind: str,
    bundle_id: str,
    candidate_delta_id: str,
) -> str:
    seed = "|".join(
        [
            "stage04_weekly_output",
            workflow_run_id,
            artifact_kind,
            bundle_id,
            candidate_delta_id,
        ]
    )
    return f"av-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:24]}"


def _digest_payload(payload: dict[str, Any]) -> str:
    body = repr(_stable_serialize(payload)).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _stable_serialize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable_serialize(value[key]) for key in sorted(value.keys(), key=str)}
    if isinstance(value, list):
        return [_stable_serialize(item) for item in value]
    return value


def _stable_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
