from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _command_receipt_payload,
    _event_envelope,
    _execute_with_command_receipt,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
)
from onetruth.application.handlers.workpage_action_resolution import _require_non_empty_string
from onetruth.application.handlers.workpage_command_support import _create_workbook_artifact_version
from onetruth.application.services.availability_exceptions import (
    AVAILABILITY_APPROVED_PLAN_DATASET_KEY,
    AVAILABILITY_REQUEST_WORKFLOW_ID,
    PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
    SUPPORTED_AVAILABILITY_EXCEPTION_REASONS,
    date_range_inclusive,
    driver_availability_exceptions_for_workflow_run,
    parse_iso_service_date,
    table_rows_from_metadata,
)
from onetruth.application.services.schedule_control.draft_workbook import SCHEDULE_WORKFLOW_ID
from onetruth.application.services.workpage_descriptors import DRIVER_PREFERENCES_WORKPAGE_KIND
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.workflow_runs import (
    create_workflow_run,
    list_workflow_runs,
)

_ADD_EXCEPTION_ACTION_ID = "workpage.driver-preferences-v0.add_availability_exception"
_REQUEST_SUBMISSION_DATASET_KEY = "availability.request_submission.workbook"
_MANAGER_DECISION_DATASET_KEY = "availability.manager_decision.workbook"
_UPDATE_PACKET_DATASET_KEY = "availability.update_packet.doc"
_AVAILABILITY_OVERLAY_COLUMNS = (
    "source_exception_id",
    "source_workflow_run_id",
    "source_artifact_version_id",
    "reason_code",
    "reason_note",
    "exception_status",
)


def add_driver_availability_exception_command(
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
    driver_id = _require_non_empty_string(payload.get("driver_id"), field_name="driver_id")
    reason_code = str(payload.get("reason_code") or "").strip().lower()
    if reason_code not in SUPPORTED_AVAILABILITY_EXCEPTION_REASONS:
        raise CommandError(
            code="invalid_reason_code",
            message="unsupported driver availability exception reason_code",
            details={"allowed_reason_codes": sorted(SUPPORTED_AVAILABILITY_EXCEPTION_REASONS)},
        )
    try:
        start_date = parse_iso_service_date(payload.get("start_date"), field_name="start_date")
        end_date = parse_iso_service_date(payload.get("end_date"), field_name="end_date")
    except ValueError as exc:
        raise CommandError(code="invalid_payload", message=str(exc), details={}) from exc
    if end_date < start_date:
        raise CommandError(
            code="invalid_date_range",
            message="end_date must be on or after start_date",
            details={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        )
    action_ref = _normalize_add_exception_action_ref(
        payload.get("action_ref"),
        workflow_run_id=workflow_run_id,
    )
    reason_note = str(payload.get("reason_note") or "").strip()

    receipt = _prepare_command_receipt(
        command_name="workpages.driver-preferences.availability-exceptions.add",
        payload={
            **payload,
            "workflow_run_id": workflow_run_id,
            "workflow_id": SCHEDULE_WORKFLOW_ID,
            "workpage_id": DRIVER_PREFERENCES_WORKPAGE_KIND,
        },
        fingerprint_payload={
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "workflow_run_id": workflow_run_id,
            "workflow_id": SCHEDULE_WORKFLOW_ID,
            "workpage_id": DRIVER_PREFERENCES_WORKPAGE_KIND,
            "driver_id": driver_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "reason_code": reason_code,
            "reason_note": reason_note,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action_ref": action_ref,
        },
        tenant_id=tenant_id,
        domain_id=domain_id,
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )

    def _operation() -> dict[str, Any]:
        return create_approved_driver_availability_exception(
            connection,
            workflow_run=workflow_run,
            storage_root=storage_root,
            tenant_id=tenant_id,
            domain_id=domain_id,
            actor_id=actor_id,
            actor_type=actor_type,
            driver_id=driver_id,
            start_date=start_date,
            end_date=end_date,
            reason_code=reason_code,
            reason_note=reason_note,
            receipt=receipt,
            event_idempotency_prefix="availability-exception",
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


def create_approved_driver_availability_exception(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
    storage_root: Path,
    tenant_id: str,
    domain_id: str,
    actor_id: str,
    actor_type: str,
    driver_id: str,
    start_date: date,
    end_date: date,
    reason_code: str,
    reason_note: str,
    receipt: Any,
    event_idempotency_prefix: str,
) -> dict[str, Any]:
    workflow_run_id = _require_non_empty_string(
        workflow_run.get("workflow_run_id"),
        field_name="workflow_run_id",
    )
    workflow_artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    driver_details = _require_driver_details(
        workflow_artifacts,
        driver_id=driver_id,
    )
    service_dates = date_range_inclusive(start_date, end_date)
    affected_weekly_runs = _affected_weekly_runs(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        service_dates=service_dates,
    )
    affected_planning_week_ids = [
        str(row.get("partition_key") or "")
        for row in affected_weekly_runs
        if str(row.get("partition_key") or "").strip()
    ]
    exception_id = f"ae-{uuid4()}"
    availability_request_workflow_run_id = f"wr-{uuid4()}"
    availability_partition_key = _availability_request_partition_key(
        start_date=start_date,
        exception_id=exception_id,
    )
    _create_availability_request_run(
        connection,
        workflow_run_id=availability_request_workflow_run_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        partition_key=availability_partition_key,
        logical_date=start_date.isoformat(),
        activation_key=f"driver-availability-exception:{exception_id}",
        actor_id=actor_id,
        actor_type=actor_type,
        event_idempotency=_receipt_event_idempotency_key(
            receipt,
            f"{event_idempotency_prefix}.workflow.run.created",
        ),
    )

    base_exception_item = {
        "exception_id": exception_id,
        "driver_id": driver_id,
        "driver_name": driver_details["driver_name"],
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "reason_code": reason_code,
        "reason_note": reason_note,
        "status": "approved",
        "source_workflow_run_id": availability_request_workflow_run_id,
        "source_artifact_version_id": None,
        "affected_planning_week_ids": affected_planning_week_ids,
    }
    artifacts = _create_availability_request_artifacts(
        connection,
        storage_root=storage_root,
        availability_request_workflow_run_id=availability_request_workflow_run_id,
        source_weekly_workflow_run_id=workflow_run_id,
        exception_item=base_exception_item,
        driver_details=driver_details,
        service_dates=service_dates,
        actor_id=actor_id,
        actor_type=actor_type,
        event_idempotency_prefix=event_idempotency_prefix,
        receipt=receipt,
    )
    approved_plan_artifact_version_id = str(artifacts["approved_plan"]["artifact_version_id"])
    exception_item = {
        **base_exception_item,
        "source_artifact_version_id": approved_plan_artifact_version_id,
    }
    weekly_artifacts = _materialize_exception_for_weekly_runs(
        connection,
        storage_root=storage_root,
        weekly_runs=affected_weekly_runs,
        exception_items=[exception_item],
        actor_id=actor_id,
        actor_type=actor_type,
        receipt=receipt,
    )
    return {
        "created": {
            "exception": exception_item,
            "availability_request_workflow_run_id": availability_request_workflow_run_id,
            "source_artifact_version_id": approved_plan_artifact_version_id,
            "weekly_approved_availability_artifact_version_ids": [
                str(item["artifact_version_id"]) for item in weekly_artifacts
            ],
            "affected_planning_week_ids": affected_planning_week_ids,
            "affected_service_dates": service_dates,
        }
    }


def materialize_weekly_approved_availability_exceptions(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
    storage_root: Path,
    actor_id: str,
    actor_type: str,
    receipt_event_idempotency_base: str | None = None,
) -> list[dict[str, Any]]:
    exceptions = driver_availability_exceptions_for_workflow_run(
        connection,
        workflow_run=workflow_run,
    )["items"]
    if not exceptions:
        return []
    return _materialize_exception_for_weekly_runs(
        connection,
        storage_root=storage_root,
        weekly_runs=[workflow_run],
        exception_items=exceptions,
        actor_id=actor_id,
        actor_type=actor_type,
        receipt=None,
        receipt_event_idempotency_base=receipt_event_idempotency_base,
    )


def _create_availability_request_run(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    tenant_id: str,
    domain_id: str,
    partition_key: str,
    logical_date: str,
    activation_key: str,
    actor_id: str,
    actor_type: str,
    event_idempotency: str | None,
) -> None:
    now = utc_now_iso()
    create_workflow_run(
        connection,
        workflow_run_id=workflow_run_id,
        workflow_id=AVAILABILITY_REQUEST_WORKFLOW_ID,
        workflow_version="v1",
        tenant_id=tenant_id,
        domain_id=domain_id,
        partition_key=partition_key,
        logical_date=logical_date,
        activation_key=activation_key,
        state="COMPLETED",
        created_at=now,
    )
    append_event(
        connection,
        _event_envelope(
            event_type="workflow.run.created",
            tenant_id=tenant_id,
            domain_id=domain_id,
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {
                    "rel": "uses_definition",
                    "type": "workflow_contract_version",
                    "id": f"{AVAILABILITY_REQUEST_WORKFLOW_ID}@v1",
                },
                {
                    "rel": "uses_decisions",
                    "type": "decision_catalog_version",
                    "id": f"{AVAILABILITY_REQUEST_WORKFLOW_ID}@v1",
                },
                {
                    "rel": "uses_profile",
                    "type": "execution_profile_version",
                    "id": f"{AVAILABILITY_REQUEST_WORKFLOW_ID}@v1",
                },
            ],
            payload={
                "workflow_run_id": workflow_run_id,
                "workflow_id": AVAILABILITY_REQUEST_WORKFLOW_ID,
                "workflow_version": "v1",
                "partition_key": partition_key,
                "activation_key": activation_key,
                "state": "COMPLETED",
            },
            idempotency_key=event_idempotency,
        ),
    )


def _create_availability_request_artifacts(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    availability_request_workflow_run_id: str,
    source_weekly_workflow_run_id: str,
    exception_item: Mapping[str, Any],
    driver_details: Mapping[str, str],
    service_dates: list[str],
    actor_id: str,
    actor_type: str,
    event_idempotency_prefix: str,
    receipt: Any,
) -> dict[str, dict[str, Any]]:
    request_payload = _availability_request_payload(
        exception_item=exception_item,
        source_weekly_workflow_run_id=source_weekly_workflow_run_id,
    )
    decision_payload = {
        **request_payload,
        "artifact_kind": _MANAGER_DECISION_DATASET_KEY,
        "decision": {
            "status": "approved",
            "decision_kind": "operations_manager_internal_approval",
            "approved_by_actor_id": actor_id,
            "approved_by_actor_type": actor_type,
            "decided_at": utc_now_iso(),
        },
    }
    update_payload = {
        **request_payload,
        "artifact_kind": _UPDATE_PACKET_DATASET_KEY,
        "update_kind": "availability_exception_approved",
        "summary": "Operations-approved driver availability exception.",
    }
    approved_plan_payload = _availability_approved_plan_payload(
        exception_item=exception_item,
        driver_details=driver_details,
        service_dates=service_dates,
        source_weekly_workflow_run_id=source_weekly_workflow_run_id,
    )
    created: dict[str, dict[str, Any]] = {}
    for key, artifact_kind, artifact_role, payload in (
        ("request_submission", _REQUEST_SUBMISSION_DATASET_KEY, "official_input", request_payload),
        ("manager_decision", _MANAGER_DECISION_DATASET_KEY, "evidence", decision_payload),
        ("update_packet", _UPDATE_PACKET_DATASET_KEY, "evidence", update_payload),
        ("approved_plan", AVAILABILITY_APPROVED_PLAN_DATASET_KEY, "official_output", approved_plan_payload),
    ):
        artifact_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        created[key] = _create_workbook_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=availability_request_workflow_run_id,
            artifact_kind=artifact_kind,
            artifact_bytes=artifact_bytes,
            artifact_role=artifact_role,
            file_name=f"{exception_item['exception_id']}_{key}.json",
            media_type="application/json",
            metadata_json=payload,
            parent_artifact_version_id=(
                str(created["request_submission"]["artifact_version_id"])
                if key in {"manager_decision", "update_packet", "approved_plan"}
                else None
            ),
            supersedes_artifact_version_id=None,
            lineage_note=f"{event_idempotency_prefix}.{key}",
            actor_id=actor_id,
            actor_type=actor_type,
            event_idempotency=_receipt_event_idempotency_key(
                receipt,
                f"{event_idempotency_prefix}.{key}.artifact.version.created",
            ),
            links=None,
        )
    return created


def _availability_request_payload(
    *,
    exception_item: Mapping[str, Any],
    source_weekly_workflow_run_id: str,
) -> dict[str, Any]:
    return {
        "artifact_kind": _REQUEST_SUBMISSION_DATASET_KEY,
        "schema_version": "1.0",
        "request_kind": "driver_availability_exception",
        "operations_approved_lane": True,
        "source_weekly_workflow_run_id": source_weekly_workflow_run_id,
        "driver_availability_exceptions": {"items": [dict(exception_item)]},
    }


def _availability_approved_plan_payload(
    *,
    exception_item: Mapping[str, Any],
    driver_details: Mapping[str, str],
    service_dates: list[str],
    source_weekly_workflow_run_id: str,
) -> dict[str, Any]:
    columns = [
        "exception_id",
        "driver_id",
        "driver_name",
        "employment_type",
        "service_date",
        "availability_state",
        "locked_by_manager",
        "reason_code",
        "reason_note",
        "status",
        "source_weekly_workflow_run_id",
        "notes",
    ]
    rows = [
        [
            exception_item["exception_id"],
            exception_item["driver_id"],
            exception_item["driver_name"],
            driver_details.get("employment_type", ""),
            service_date,
            "CANNOT",
            "yes",
            exception_item["reason_code"],
            exception_item["reason_note"],
            "approved",
            source_weekly_workflow_run_id,
            _exception_note(exception_item),
        ]
        for service_date in service_dates
    ]
    return {
        "artifact_kind": AVAILABILITY_APPROVED_PLAN_DATASET_KEY,
        "schema_version": "1.0",
        "shape": "normalized_driver_day_rows",
        "columns": columns,
        "rows": rows,
        "driver_availability_exceptions": {"items": [dict(exception_item)]},
        "affected_planning_week_ids": list(exception_item.get("affected_planning_week_ids") or []),
    }


def _materialize_exception_for_weekly_runs(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    weekly_runs: list[Mapping[str, Any]],
    exception_items: list[Mapping[str, Any]],
    actor_id: str,
    actor_type: str,
    receipt: Any,
    receipt_event_idempotency_base: str | None = None,
) -> list[dict[str, Any]]:
    created: list[dict[str, Any]] = []
    for run_index, weekly_run in enumerate(weekly_runs):
        workflow_run_id = str(weekly_run.get("workflow_run_id") or "")
        artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        base_artifact = _latest_artifact_for_kind(
            artifacts,
            PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
        )
        if base_artifact is None:
            continue
        payload = _approved_availability_overlay_payload(
            base_artifact=base_artifact,
            weekly_run=weekly_run,
            exception_items=exception_items,
        )
        if payload is None:
            continue
        base_artifact_version_id = str(base_artifact["artifact_version_id"])
        artifact_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        event_idempotency = (
            _receipt_event_idempotency_key(
                receipt,
                f"weekly-approved-availability-overlay.{workflow_run_id}.{run_index}.artifact.version.created",
            )
            if receipt is not None
            else _event_idempotency_from_base(
                receipt_event_idempotency_base,
                f"weekly-approved-availability-overlay.{workflow_run_id}.{run_index}.artifact.version.created",
            )
        )
        created.append(
            _create_workbook_artifact_version(
                connection,
                storage_root=storage_root,
                workflow_run_id=workflow_run_id,
                artifact_kind=PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
                artifact_bytes=artifact_bytes,
                artifact_role=str(base_artifact.get("artifact_role") or "official_input"),
                file_name=_approved_availability_file_name(base_artifact),
                media_type=str(base_artifact.get("media_type") or "application/json"),
                metadata_json=payload,
                parent_artifact_version_id=base_artifact_version_id,
                supersedes_artifact_version_id=base_artifact_version_id,
                lineage_note="Applied approved driver availability exceptions.",
                actor_id=actor_id,
                actor_type=actor_type,
                event_idempotency=event_idempotency,
                links=None,
            )
        )
    return created


def _approved_availability_overlay_payload(
    *,
    base_artifact: Mapping[str, Any],
    weekly_run: Mapping[str, Any],
    exception_items: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    metadata = base_artifact.get("metadata_json")
    if not isinstance(metadata, Mapping):
        return None
    columns, rows = table_rows_from_metadata(metadata)
    if "service_date" not in set(columns) or "availability_state" not in set(columns):
        return None
    for column in _AVAILABILITY_OVERLAY_COLUMNS:
        if column not in columns:
            columns.append(column)
            for row in rows:
                row[column] = ""
    service_dates = {str(row.get("service_date") or "").strip() for row in rows}
    driver_rows = _driver_details_by_id_from_rows(rows)
    changed = False
    applied_exception_ids: set[str] = set()
    rows_by_driver_date: dict[tuple[str, str], dict[str, Any]] = {
        (str(row.get("driver_id") or "").strip(), str(row.get("service_date") or "").strip()): row
        for row in rows
        if str(row.get("driver_id") or "").strip() and str(row.get("service_date") or "").strip()
    }
    for exception_item in exception_items:
        driver_id = str(exception_item.get("driver_id") or "").strip()
        exception_dates = set(
            date_range_inclusive(
                parse_iso_service_date(exception_item.get("start_date"), field_name="start_date"),
                parse_iso_service_date(exception_item.get("end_date"), field_name="end_date"),
            )
        )
        for service_date in sorted(exception_dates.intersection(service_dates)):
            key = (driver_id, service_date)
            row = rows_by_driver_date.get(key)
            if row is None:
                row = _blank_availability_row(
                    columns=columns,
                    driver_id=driver_id,
                    driver_details=driver_rows.get(driver_id) or exception_item,
                    service_date=service_date,
                )
                rows.append(row)
                rows_by_driver_date[key] = row
                changed = True
            changed = _set_overlay_row_values(row, exception_item=exception_item) or changed
            applied_exception_ids.add(str(exception_item.get("exception_id") or ""))
    if not changed:
        return None
    payload = dict(metadata)
    payload["columns"] = columns
    payload["rows"] = [[row.get(column, "") for column in columns] for row in rows]
    overlay = dict(payload.get("availability_exception_overlay") or {})
    overlay["source"] = "driver_preferences_v0_availability_exceptions"
    overlay["applied_exception_ids"] = sorted(item for item in applied_exception_ids if item)
    overlay["base_artifact_version_id"] = str(base_artifact.get("artifact_version_id") or "")
    overlay["workflow_run_id"] = str(weekly_run.get("workflow_run_id") or "")
    payload["availability_exception_overlay"] = overlay
    return payload


def _set_overlay_row_values(
    row: dict[str, Any],
    *,
    exception_item: Mapping[str, Any],
) -> bool:
    desired = {
        "availability_state": "CANNOT",
        "locked_by_manager": "yes",
        "source_exception_id": str(exception_item.get("exception_id") or ""),
        "source_workflow_run_id": str(exception_item.get("source_workflow_run_id") or ""),
        "source_artifact_version_id": str(exception_item.get("source_artifact_version_id") or ""),
        "reason_code": str(exception_item.get("reason_code") or ""),
        "reason_note": str(exception_item.get("reason_note") or ""),
        "exception_status": "approved",
    }
    changed = False
    for key, value in desired.items():
        if str(row.get(key) or "") != value:
            row[key] = value
            changed = True
    note = _exception_note(exception_item)
    existing_note = str(row.get("notes") or "")
    if note and note not in existing_note:
        row["notes"] = f"{existing_note}; {note}" if existing_note else note
        changed = True
    return changed


def _affected_weekly_runs(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    service_dates: list[str],
) -> list[dict[str, Any]]:
    target_dates = set(service_dates)
    weekly_runs = list_workflow_runs(
        connection,
        workflow_id=SCHEDULE_WORKFLOW_ID,
        tenant_id=tenant_id,
        domain_id=domain_id,
    )
    affected: list[dict[str, Any]] = []
    for weekly_run in weekly_runs:
        artifacts = list_artifact_versions_for_workflow_run(
            connection,
            str(weekly_run.get("workflow_run_id") or ""),
        )
        run_service_dates = _weekly_run_service_dates(weekly_run, artifacts)
        if target_dates.intersection(run_service_dates):
            affected.append(weekly_run)
    return affected


def _weekly_run_service_dates(
    workflow_run: Mapping[str, Any],
    artifacts: list[Mapping[str, Any]],
) -> set[str]:
    approved_availability = _latest_artifact_for_kind(
        artifacts,
        PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
    )
    if approved_availability is not None:
        metadata = approved_availability.get("metadata_json")
        if isinstance(metadata, Mapping):
            _columns, rows = table_rows_from_metadata(metadata)
            dates = {str(row.get("service_date") or "").strip() for row in rows}
            dates = {item for item in dates if item}
            if dates:
                return dates
    try:
        logical_date = parse_iso_service_date(
            workflow_run.get("logical_date"),
            field_name="logical_date",
        )
    except ValueError:
        return set()
    return {(logical_date + timedelta(days=offset)).isoformat() for offset in range(7)}


def _require_driver_details(
    artifacts: list[Mapping[str, Any]],
    *,
    driver_id: str,
) -> dict[str, str]:
    details = _driver_details_by_id(artifacts).get(driver_id)
    if details is None:
        raise CommandError(
            code="invalid_driver_id",
            message="driver_id is not available in this weekly planning run",
            details={"driver_id": driver_id},
        )
    return details


def _driver_details_by_id(artifacts: list[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    details: dict[str, dict[str, str]] = {}
    for artifact_kind in (
        "planning.driver_capabilities.workbook",
        PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
    ):
        artifact = _latest_artifact_for_kind(artifacts, artifact_kind)
        if artifact is None:
            continue
        metadata = artifact.get("metadata_json")
        if not isinstance(metadata, Mapping):
            continue
        _columns, rows = table_rows_from_metadata(metadata)
        for row in rows:
            driver_id = str(row.get("driver_id") or "").strip()
            if not driver_id:
                continue
            current = details.setdefault(driver_id, {"driver_id": driver_id})
            for key in ("driver_name", "employment_type", "on_call_eligible"):
                value = str(row.get(key) or "").strip()
                if value and not current.get(key):
                    current[key] = value
    return details


def _driver_details_by_id_from_rows(rows: list[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    details: dict[str, dict[str, str]] = {}
    for row in rows:
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue
        current = details.setdefault(driver_id, {"driver_id": driver_id})
        for key in ("driver_name", "employment_type", "target_shifts_per_week", "on_call_eligible"):
            value = str(row.get(key) or "").strip()
            if value and not current.get(key):
                current[key] = value
    return details


def _blank_availability_row(
    *,
    columns: list[str],
    driver_id: str,
    driver_details: Mapping[str, Any],
    service_date: str,
) -> dict[str, Any]:
    row = {column: "" for column in columns}
    row["driver_id"] = driver_id
    row["driver_name"] = str(driver_details.get("driver_name") or "")
    row["employment_type"] = str(driver_details.get("employment_type") or "")
    row["service_date"] = service_date
    row["target_shifts_per_week"] = str(driver_details.get("target_shifts_per_week") or "")
    row["on_call_eligible"] = str(driver_details.get("on_call_eligible") or "")
    return row


def _latest_artifact_for_kind(
    artifacts: list[Mapping[str, Any]],
    artifact_kind: str,
) -> Mapping[str, Any] | None:
    matches = [
        artifact
        for artifact in artifacts
        if str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "") == artifact_kind
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


def _availability_request_partition_key(*, start_date: date, exception_id: str) -> str:
    suffix = int(hashlib.sha256(exception_id.encode("utf-8")).hexdigest()[:8], 16) % 10000
    return f"AR-{start_date.strftime('%Y%m%d')}-{suffix:04d}"


def _normalize_add_exception_action_ref(
    raw_action_ref: Any,
    *,
    workflow_run_id: str,
) -> dict[str, Any] | None:
    if raw_action_ref is None:
        return None
    if not isinstance(raw_action_ref, Mapping):
        raise CommandError(
            code="invalid_payload",
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
    if action_id != _ADD_EXCEPTION_ACTION_ID:
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref action_id does not match the add availability exception flow",
            details={"action_id": action_id, "expected_action_id": _ADD_EXCEPTION_ACTION_ID},
        )
    if action_workpage_kind != DRIVER_PREFERENCES_WORKPAGE_KIND:
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref workpage_kind does not match the add availability exception flow",
            details={"workpage_kind": action_workpage_kind},
        )
    if action_workflow_run_id != workflow_run_id:
        raise CommandError(
            code="invalid_workpage_action_ref",
            message="action_ref workflow_run_id does not match the requested workflow run",
            details={
                "workflow_run_id": workflow_run_id,
                "action_workflow_run_id": action_workflow_run_id,
            },
        )
    return {
        "action_id": action_id,
        "workpage_kind": action_workpage_kind,
        "workflow_run_id": action_workflow_run_id,
        "artifact_version_id": None,
        "subject": None,
    }


def _approved_availability_file_name(base_artifact: Mapping[str, Any]) -> str:
    metadata = base_artifact.get("metadata_json")
    if isinstance(metadata, Mapping):
        for key in ("file_name", "ingress_file_name"):
            value = str(metadata.get(key) or "").strip()
            if value:
                return value
    return "planning_approved_availability.json"


def _exception_note(exception_item: Mapping[str, Any]) -> str:
    reason_code = str(exception_item.get("reason_code") or "other").strip()
    reason_note = str(exception_item.get("reason_note") or "").strip()
    label = f"Approved exception: {reason_code}"
    return f"{label} - {reason_note}" if reason_note else label


def _event_idempotency_from_base(base: str | None, suffix: str) -> str | None:
    if base is None:
        return None
    return f"{base}:{suffix}"
