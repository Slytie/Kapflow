from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from onetruth.application.handlers._shared.artifact_effects import (
    persist_generated_artifact_effects,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
    command_transaction,
)
from onetruth.application.services.execution_evidence import resolve_execution_artifact_root
from onetruth.application.services.schedule_control import (
    build_weekly_schedule_control_bundle,
    run_weekly_stage04_deterministic_build,
)
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.artifact_provenance import create_artifact_provenance_edge
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run


WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"

STAGE04_OUTPUT_SPECS: tuple[tuple[str, str], ...] = (
    ("planning.input_bundle.doc", "official_input"),
    ("planning.candidate_schedule_delta.workbook", "official_input"),
    ("planning.draft_weekly_schedule.workbook", "official_input"),
    ("planning.validation_summary.doc", "evidence"),
    ("planning.draft_weekly_schedule.doc", "evidence"),
    ("planning.schedule_calculation_snapshot.json", "evidence"),
)


def build_weekly_schedule_control_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
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

    receipt = _prepare_command_receipt(
        command_name="schedule-control.build-weekly",
        payload=payload,
        fingerprint_payload=payload,
        tenant_id=str(workflow_run.get("tenant_id") or ""),
        domain_id=str(workflow_run.get("domain_id") or ""),
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )

    def _operation() -> dict[str, Any]:
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

        output_payloads = {
            "planning.input_bundle.doc": deterministic_build.input_bundle_payload,
            "planning.candidate_schedule_delta.workbook": deterministic_build.candidate_delta_payload,
            "planning.draft_weekly_schedule.workbook": deterministic_build.draft_workbook_payload,
            "planning.validation_summary.doc": deterministic_build.validation_summary_payload,
            "planning.draft_weekly_schedule.doc": deterministic_build.draft_doc_payload,
            "planning.schedule_calculation_snapshot.json": (
                deterministic_build.calculation_snapshot_payload
            ),
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
            event_idempotency_base=_receipt_event_idempotency_key(
                receipt,
                "stage04-outputs",
            ),
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
                "draft_workbook": created_outputs["planning.draft_weekly_schedule.workbook"],
                "validation_summary": created_outputs["planning.validation_summary.doc"],
                "draft_doc": created_outputs["planning.draft_weekly_schedule.doc"],
                "calculation_snapshot": created_outputs["planning.schedule_calculation_snapshot.json"],
            },
            "artifact_payloads": output_payloads,
        }

    raw_result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )
    return _command_receipt_payload(
        raw_result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def persist_weekly_stage04_output_payloads(
    connection: sqlite3.Connection,
    *,
    workflow_run: dict[str, Any],
    bundle_id: str,
    output_payloads: dict[str, dict[str, Any]],
    source_input_ids: list[str],
    event_idempotency_base: str | None = None,
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
    draft_artifact_version_id = _stable_output_artifact_id(
        workflow_run_id=workflow_run_id,
        artifact_kind="planning.draft_weekly_schedule.workbook",
        bundle_id=bundle_id,
        candidate_delta_id=candidate_delta_id,
    )
    storage_root = resolve_execution_artifact_root()
    with command_transaction(connection):
        for artifact_kind, artifact_role in STAGE04_OUTPUT_SPECS:
            artifact_id = _stable_output_artifact_id(
                workflow_run_id=workflow_run_id,
                artifact_kind=artifact_kind,
                bundle_id=bundle_id,
                candidate_delta_id=candidate_delta_id,
            )
            created_result = persist_generated_artifact_effects(
                connection,
                storage_root=storage_root,
                workflow_run_id=workflow_run_id,
                artifact_version_id=artifact_id,
                artifact_kind=artifact_kind,
                artifact_role=artifact_role,
                media_type="application/json",
                file_name=_stage04_output_file_name(artifact_kind),
                payload=output_payloads[artifact_kind],
                metadata_json=output_payloads[artifact_kind],
                parent_artifact_version_id=(
                    draft_artifact_version_id
                    if artifact_kind in {
                        "planning.validation_summary.doc",
                        "planning.draft_weekly_schedule.doc",
                        "planning.schedule_calculation_snapshot.json",
                    }
                    else None
                ),
                supersedes_artifact_version_id=None,
                lineage_note="stage04_deterministic_schedule_control",
                actor_id="system:schedule-control",
                actor_type="system",
                canonical_partition_kind="PlanningWeekID",
                canonical_partition_key=planning_week_id,
                event_idempotency=_stage04_output_event_idempotency_key(
                    event_idempotency_base=event_idempotency_base,
                    artifact_kind=artifact_kind,
                    artifact_version_id=artifact_id,
                ),
            )
            created = dict(created_result["artifact_version"])
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
    return created_outputs


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if payload.get(field) is None]
    if missing:
        raise CommandError(
            code="missing_required_fields",
            message="required fields are missing",
            details={"missing_fields": missing},
        )


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


def _stage04_output_file_name(artifact_kind: str) -> str:
    return f"stage04_{artifact_kind.replace('.', '_')}.json"


def _stage04_output_event_idempotency_key(
    *,
    event_idempotency_base: str | None,
    artifact_kind: str,
    artifact_version_id: str,
) -> str:
    safe_kind = artifact_kind.replace(".", "-")
    if event_idempotency_base is not None:
        return f"{event_idempotency_base}:{safe_kind}:artifact.version.created"
    return f"stage04-output:{artifact_version_id}:artifact.version.created"


def _stable_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
