from __future__ import annotations

from datetime import date, timedelta
import sqlite3
from typing import Any, Mapping

from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
    list_artifact_versions_for_scope_and_kind,
)

AVAILABILITY_REQUEST_WORKFLOW_ID = "availability_request.v1"
AVAILABILITY_APPROVED_PLAN_DATASET_KEY = "availability.approved_plan.workbook"
PLANNING_APPROVED_AVAILABILITY_DATASET_KEY = "planning.approved_availability.workbook"
SUPPORTED_AVAILABILITY_EXCEPTION_REASONS = frozenset(
    {"wedding", "vacation", "medical", "family", "appointment", "sick_no_show", "other"}
)


def driver_availability_exceptions_for_workflow_run(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
) -> dict[str, Any]:
    tenant_id = str(workflow_run.get("tenant_id") or "")
    domain_id = str(workflow_run.get("domain_id") or "")
    target_service_dates = _workflow_run_service_dates(
        connection,
        workflow_run=workflow_run,
    )
    artifacts = list_artifact_versions_for_scope_and_kind(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        artifact_kind=AVAILABILITY_APPROVED_PLAN_DATASET_KEY,
        workflow_id=AVAILABILITY_REQUEST_WORKFLOW_ID,
    )
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for artifact in artifacts:
        for item in availability_exception_items_from_approved_plan_artifact(artifact):
            exception_id = str(item.get("exception_id") or "").strip()
            if not exception_id or exception_id in seen:
                continue
            if target_service_dates:
                start_date = _optional_iso_date(item.get("start_date"))
                end_date = _optional_iso_date(item.get("end_date"))
                if start_date is None or end_date is None:
                    continue
                exception_service_dates = set(date_range_inclusive(start_date, end_date))
                if not exception_service_dates.intersection(target_service_dates):
                    continue
            else:
                lower_bound = _optional_iso_date(workflow_run.get("logical_date"))
                end_date = _optional_iso_date(item.get("end_date"))
                if lower_bound is not None and end_date is not None and end_date < lower_bound:
                    continue
            if exception_id in seen:
                continue
            seen.add(exception_id)
            items.append(item)
    items.sort(
        key=lambda item: (
            str(item.get("start_date") or ""),
            str(item.get("driver_name") or ""),
            str(item.get("exception_id") or ""),
        )
    )
    return {"items": items}


def availability_exception_items_from_approved_plan_artifact(
    artifact: Mapping[str, Any],
) -> list[dict[str, Any]]:
    metadata = artifact.get("metadata_json")
    if not isinstance(metadata, Mapping):
        return []

    raw_collection = metadata.get("driver_availability_exceptions")
    if isinstance(raw_collection, Mapping) and isinstance(raw_collection.get("items"), list):
        normalized_items = [
            _normalize_exception_item(
                raw_item,
                fallback_source_workflow_run_id=str(artifact.get("workflow_run_id") or ""),
                fallback_source_artifact_version_id=str(artifact.get("artifact_version_id") or ""),
            )
            for raw_item in raw_collection["items"]
        ]
        return [item for item in normalized_items if item is not None]

    columns, rows = table_rows_from_metadata(metadata)
    if not columns or not rows:
        return []
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        exception_id = str(
            row.get("exception_id") or row.get("request_id") or row.get("availability_request_id") or ""
        ).strip()
        if not exception_id:
            continue
        service_date = str(row.get("service_date") or "").strip()
        if not service_date:
            continue
        existing = grouped.setdefault(
            exception_id,
            {
                "exception_id": exception_id,
                "driver_id": str(row.get("driver_id") or "").strip(),
                "driver_name": str(row.get("driver_name") or "").strip(),
                "start_date": service_date,
                "end_date": service_date,
                "reason_code": str(row.get("reason_code") or "other").strip() or "other",
                "reason_note": str(row.get("reason_note") or row.get("notes") or "").strip(),
                "status": str(row.get("status") or "approved").strip() or "approved",
                "source_workflow_run_id": str(
                    row.get("source_workflow_run_id") or artifact.get("workflow_run_id") or ""
                ).strip(),
                "source_artifact_version_id": str(artifact.get("artifact_version_id") or "").strip(),
                "affected_planning_week_ids": [],
            },
        )
        existing["start_date"] = min(str(existing["start_date"]), service_date)
        existing["end_date"] = max(str(existing["end_date"]), service_date)
        raw_week_id = str(row.get("planning_week_id") or "").strip()
        if raw_week_id and raw_week_id not in existing["affected_planning_week_ids"]:
            existing["affected_planning_week_ids"].append(raw_week_id)

    metadata_week_ids = _string_list(metadata.get("affected_planning_week_ids"))
    for item in grouped.values():
        if metadata_week_ids:
            item["affected_planning_week_ids"] = metadata_week_ids
    items: list[dict[str, Any]] = []
    for item in grouped.values():
        normalized = _normalize_exception_item(
            item,
            fallback_source_workflow_run_id=str(artifact.get("workflow_run_id") or ""),
            fallback_source_artifact_version_id=str(artifact.get("artifact_version_id") or ""),
        )
        if normalized is not None:
            items.append(normalized)
    return items


def table_rows_from_metadata(metadata: Mapping[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    raw_columns = metadata.get("columns")
    raw_rows = metadata.get("rows")
    if not isinstance(raw_columns, list) or not isinstance(raw_rows, list):
        return [], []
    columns = [str(column) for column in raw_columns]
    rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        if isinstance(raw_row, Mapping):
            rows.append({str(key): value for key, value in raw_row.items()})
            continue
        if isinstance(raw_row, (list, tuple)):
            rows.append(
                {
                    column: raw_row[index] if index < len(raw_row) else ""
                    for index, column in enumerate(columns)
                }
            )
    return columns, rows


def date_range_inclusive(start_date: date, end_date: date) -> list[str]:
    days: list[str] = []
    cursor = start_date
    while cursor <= end_date:
        days.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return days


def parse_iso_service_date(value: Any, *, field_name: str) -> date:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date") from exc


def _normalize_exception_item(
    raw_item: Any,
    *,
    fallback_source_workflow_run_id: str,
    fallback_source_artifact_version_id: str,
) -> dict[str, Any] | None:
    if not isinstance(raw_item, Mapping):
        return None
    exception_id = str(raw_item.get("exception_id") or "").strip()
    driver_id = str(raw_item.get("driver_id") or "").strip()
    start_date = str(raw_item.get("start_date") or "").strip()
    end_date = str(raw_item.get("end_date") or "").strip()
    status = str(raw_item.get("status") or "approved").strip() or "approved"
    if not exception_id or not driver_id or not start_date or not end_date:
        return None
    if status != "approved":
        return None
    reason_code = str(raw_item.get("reason_code") or "other").strip() or "other"
    return {
        "exception_id": exception_id,
        "driver_id": driver_id,
        "driver_name": str(raw_item.get("driver_name") or "").strip(),
        "start_date": start_date,
        "end_date": end_date,
        "reason_code": reason_code,
        "reason_note": str(raw_item.get("reason_note") or "").strip(),
        "status": "approved",
        "source_workflow_run_id": str(
            raw_item.get("source_workflow_run_id") or fallback_source_workflow_run_id
        ).strip(),
        "source_artifact_version_id": str(
            raw_item.get("source_artifact_version_id") or fallback_source_artifact_version_id
        ).strip(),
        "affected_planning_week_ids": _string_list(
            raw_item.get("affected_planning_week_ids")
        ),
    }


def _optional_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _workflow_run_service_dates(
    connection: sqlite3.Connection,
    *,
    workflow_run: Mapping[str, Any],
) -> set[str]:
    workflow_run_id = str(workflow_run.get("workflow_run_id") or "").strip()
    if workflow_run_id:
        artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        approved_availability = _latest_artifact_for_kind(
            artifacts,
            PLANNING_APPROVED_AVAILABILITY_DATASET_KEY,
        )
        approved_availability_dates = _service_dates_from_artifact_rows(approved_availability)
        if approved_availability_dates:
            return approved_availability_dates
        route_demand = _latest_artifact_for_kind(
            artifacts,
            "planning.route_slot_requirements.workbook",
        )
        route_demand_dates = _service_dates_from_route_demand_artifact(route_demand)
        if route_demand_dates:
            return route_demand_dates
    logical_date = _optional_iso_date(workflow_run.get("logical_date"))
    if logical_date is None:
        return set()
    return {(logical_date + timedelta(days=offset)).isoformat() for offset in range(7)}


def _service_dates_from_artifact_rows(artifact: Mapping[str, Any] | None) -> set[str]:
    if artifact is None:
        return set()
    metadata = artifact.get("metadata_json")
    if not isinstance(metadata, Mapping):
        return set()
    _columns, rows = table_rows_from_metadata(metadata)
    return {
        str(row.get("service_date") or "").strip()
        for row in rows
        if str(row.get("service_date") or "").strip()
    }


def _service_dates_from_route_demand_artifact(artifact: Mapping[str, Any] | None) -> set[str]:
    if artifact is None:
        return set()
    metadata = artifact.get("metadata_json")
    if not isinstance(metadata, Mapping):
        return set()
    explicit_scope_dates = _service_dates_from_explicit_scope(metadata)
    if explicit_scope_dates:
        return explicit_scope_dates
    _columns, rows = table_rows_from_metadata(metadata)
    row_dates = {
        str(row.get("service_date") or "").strip()
        for row in rows
        if str(row.get("service_date") or "").strip()
    }
    if row_dates:
        return row_dates
    raw_daily_rows = metadata.get("daily_demand_rows")
    if not isinstance(raw_daily_rows, list):
        return set()
    dates: list[str] = []
    for row in raw_daily_rows:
        service_date = ""
        if isinstance(row, Mapping):
            service_date = str(row.get("service_date") or "").strip()
        elif isinstance(row, list) and row:
            service_date = str(row[0] or "").strip()
        if not service_date:
            continue
        dates.append(service_date)
        if len(dates) == 7:
            break
    return set(dates)


def _service_dates_from_explicit_scope(metadata: Mapping[str, Any]) -> set[str]:
    scope_start = _optional_iso_date(metadata.get("scope_start"))
    scope_end_exclusive = _optional_iso_date(metadata.get("scope_end_exclusive"))
    if scope_start is None or scope_end_exclusive is None or scope_end_exclusive <= scope_start:
        return set()
    dates: set[str] = set()
    cursor = scope_start
    while cursor < scope_end_exclusive:
        dates.add(cursor.isoformat())
        cursor += timedelta(days=1)
    return dates


def _latest_artifact_for_kind(
    artifacts: list[Mapping[str, Any]],
    artifact_kind: str,
) -> Mapping[str, Any] | None:
    matches = [
        artifact
        for artifact in artifacts
        if str(artifact.get("artifact_kind") or "") == artifact_kind
    ]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda artifact: (
            str(artifact.get("created_at") or ""),
            str(artifact.get("artifact_version_id") or ""),
        ),
    )[-1]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
