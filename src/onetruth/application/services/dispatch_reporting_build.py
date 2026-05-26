from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from onetruth.application.services.dispatch_reporting_raw_eos import (
    RAW_EOS_WORKBOOK_FAMILY,
    project_raw_eos_workbook,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    WorkbookRuntimeDependencyError,
    seed_upd_draft_workbook,
)


WORKFLOW_ID = "dispatch_reporting.v1"
EOS_RAW_ARTIFACT_KIND = "reporting.eos_raw.workbook"
NORMALIZED_ACTUALS_ARTIFACT_KIND = "reporting.actuals_normalized.workbook"
UPD_DRAFT_ARTIFACT_KIND = "reporting.upd_draft.workbook"
MANAGER_REVIEW_ARTIFACT_KIND = "reporting.manager_review.doc"
FINAL_PACKET_ARTIFACT_KIND = "reporting.final_packet.workbook"
FINAL_PACKET_POINTER_KEY = "official:reporting.final_packet.workbook"
REVIEW_TASK_KIND = "final_packet_review"
REVIEW_APPROVAL_ACTION = "confirm_dispatch_reporting_packet"
REVIEW_APPROVAL_SCOPE_REF = "Stage04"
REPORTING_TO_PLANNING_EDGE_ID = "reporting_actuals_to_future_planning"
SUPPORTED_SOURCE_WORKBOOK_FAMILY = RAW_EOS_WORKBOOK_FAMILY
DEFAULT_STATION_CODE = "DVC4"
DEFAULT_DSP_NAME = "QDCI"
PLANNING_ACTUAL_HOURS_ARTIFACT_KIND = "planning.actual_hours_snapshot.workbook"
PLANNING_ACTUAL_HOURS_COLUMNS: tuple[str, ...] = (
    "service_date",
    "driver_id",
    "driver_name",
    "historical_state",
    "actual_minutes",
    "route_id",
    "route_slot_class",
    "call_in_sick_flag",
    "cancellation_flag",
    "non_working_day_flag",
    "source_snapshot_row_ref",
)


class DispatchReportingBuildError(ValueError):
    pass


@dataclass(frozen=True)
class DispatchReportingBuildOutput:
    service_date: str
    station_code: str
    dsp_name: str
    formula_integrity_warning: bool
    normalized_payload: dict[str, Any]
    normalized_rows: list[dict[str, Any]]
    quality_warning_rows: list[dict[str, Any]]
    draft_route_actual_rows: list[dict[str, Any]]
    draft_upd_candidate_rows: list[dict[str, Any]]
    draft_manual_closeout_rows: list[dict[str, Any]]
    draft_workbook_bytes: bytes


def build_dispatch_reporting_artifacts(
    *,
    eos_workbook_bytes: bytes,
    draft_template_bytes: bytes,
    source_metadata_json: Mapping[str, Any] | None = None,
    source_file_name: str | None = None,
    fallback_service_date: str | None = None,
    built_at: str,
    actor_id: str,
) -> DispatchReportingBuildOutput:
    projection = _project_supported_source_workbook(
        eos_workbook_bytes,
        source_metadata_json=source_metadata_json,
        source_file_name=source_file_name,
        fallback_service_date=fallback_service_date,
    )
    route_rows = projection.route_rows
    quality_warning_rows = projection.quality_warning_rows
    manual_closeout_rows = _build_manual_closeout_rows(route_rows)

    service_date = projection.service_date
    station_code = projection.station_code
    dsp_name = projection.dsp_name

    formula_integrity_warning = bool(quality_warning_rows)
    warning_message = (
        "source workbook had broken summary formulas"
        if formula_integrity_warning
        else ""
    )

    normalized_rows: list[dict[str, Any]] = []
    draft_route_actual_rows: list[dict[str, Any]] = []
    draft_upd_candidate_rows: list[dict[str, Any]] = []
    for index, row in enumerate(route_rows):
        row_id = _resolve_text(
            row.get("row_id"),
            fallback=f"route-{index + 1:03d}",
        )
        route_id = _resolve_text(row.get("route_id"), fallback=row_id)
        actual_minutes = _coerce_int(
            row.get("actual_minutes"),
            field_name=f"route_actuals[{index}].actual_minutes",
        )
        returned_packages = _coerce_int(
            row.get("returns"),
            field_name=f"route_actuals[{index}].returns",
        )
        return_reasons = _resolve_text(row.get("return_reasons"), fallback="")
        upd_candidate = actual_minutes > 600

        normalized_rows.append(
            {
                "row_id": row_id,
                "service_date": _resolve_text(row.get("service_date"), fallback=service_date),
                "route_id": route_id,
                "driver_id": _resolve_text(row.get("driver_id"), fallback=""),
                "driver_name": _resolve_text(row.get("driver_name"), fallback=""),
                "actual_minutes": actual_minutes,
                "returned_packages": returned_packages,
                "return_reasons": return_reasons,
                "upd_candidate": upd_candidate,
                "formula_integrity_warning": warning_message if index == 0 else "",
            }
        )

        draft_route_actual_rows.append(
            {
                "row_id": row_id,
                "service_date": _resolve_text(row.get("service_date"), fallback=service_date),
                "route_id": route_id,
                "driver_name": _resolve_text(row.get("driver_name"), fallback=""),
                "packages_dispatched": _coerce_int(
                    row.get("packages_dispatched"),
                    field_name=f"route_actuals[{index}].packages_dispatched",
                ),
                "packages_delivered": _coerce_int(
                    row.get("packages_delivered"),
                    field_name=f"route_actuals[{index}].packages_delivered",
                ),
                "planned_start": _resolve_text(row.get("planned_start"), fallback=""),
                "planned_finish": _resolve_text(row.get("planned_finish"), fallback=""),
                "actual_start": _resolve_text(row.get("actual_start"), fallback=""),
                "actual_finish": _resolve_text(row.get("actual_finish"), fallback=""),
                "actual_minutes": actual_minutes,
                "returns": returned_packages,
                "return_reasons": return_reasons,
                "upd_candidate": upd_candidate,
            }
        )

        draft_upd_candidate_rows.append(
            {
                "row_id": f"upd-{route_id.lower()}",
                "service_date": _resolve_text(row.get("service_date"), fallback=service_date),
                "route_id": route_id,
                "driver_name": _resolve_text(row.get("driver_name"), fallback=""),
                "actual_minutes": actual_minutes,
                "selected": upd_candidate,
                "reason": (
                    ">600 minutes actual time" if upd_candidate else "Below 600 minutes"
                ),
                "manager_note": "",
            }
        )

    normalized_payload = {
        "schema_version": "1.0",
        "kind": "dispatch_reporting.actuals_normalized",
        "service_date": service_date,
        "station_code": station_code,
        "dsp_name": dsp_name,
        "source_workbook_family": SUPPORTED_SOURCE_WORKBOOK_FAMILY,
        "formula_integrity_warning": formula_integrity_warning,
        "quality_warnings": quality_warning_rows,
        "rows": normalized_rows,
        "break_tracker": {
            "sheet_present": projection.break_tracker_sheet_present,
            "rows": projection.break_tracker_rows,
        },
        "route_adherence": {
            "sheet_present": projection.route_adherence_sheet_present,
            "cycles": projection.route_adherence_cycles,
        },
        "totals": {
            "route_count": len(normalized_rows),
            "upd_candidate_count": sum(1 for row in normalized_rows if bool(row["upd_candidate"])),
        },
    }
    draft_manual_closeout_rows = manual_closeout_rows

    draft_workbook_bytes = seed_upd_draft_workbook(
        draft_template_bytes,
        {
            "route_actuals": draft_route_actual_rows,
            "upd_candidates": draft_upd_candidate_rows,
            "manual_closeout": draft_manual_closeout_rows,
            "quality_warnings": quality_warning_rows,
            "change_log_stage03_upd_draft": [
                {
                    "row_id": "build-generated",
                    "change_type": "build",
                    "actor_id": actor_id,
                    "changed_at": built_at,
                    "summary": "Draft auto-generated from EOS intake.",
                }
            ],
        },
    )

    return DispatchReportingBuildOutput(
        service_date=service_date,
        station_code=station_code,
        dsp_name=dsp_name,
        formula_integrity_warning=formula_integrity_warning,
        normalized_payload=normalized_payload,
        normalized_rows=normalized_rows,
        quality_warning_rows=quality_warning_rows,
        draft_route_actual_rows=draft_route_actual_rows,
        draft_upd_candidate_rows=draft_upd_candidate_rows,
        draft_manual_closeout_rows=draft_manual_closeout_rows,
        draft_workbook_bytes=draft_workbook_bytes,
    )


def build_planning_actual_hours_snapshot_payload(
    *,
    normalized_payload: Mapping[str, Any],
    source_artifact_version_id: str,
) -> dict[str, Any]:
    aggregated: dict[tuple[str, str], dict[str, Any]] = {}
    for index, row in enumerate(_normalized_route_rows(normalized_payload)):
        driver_id = _resolve_text(row.get("driver_id"), fallback="")
        service_date = _resolve_text(row.get("service_date"), fallback="")
        if not driver_id or not service_date:
            continue
        actual_minutes = max(
            _coerce_int(
                row.get("actual_minutes"),
                field_name=f"normalized_rows[{index}].actual_minutes",
            ),
            0,
        )
        route_id = _resolve_text(row.get("route_id"), fallback="")
        key = (service_date, driver_id)
        aggregate = aggregated.setdefault(
            key,
            {
                "service_date": service_date,
                "driver_id": driver_id,
                "driver_name": _resolve_text(row.get("driver_name"), fallback=driver_id),
                "actual_minutes": 0,
                "route_ids": set(),
            },
        )
        aggregate["actual_minutes"] += actual_minutes
        if route_id:
            aggregate["route_ids"].add(route_id)
        if not aggregate["driver_name"]:
            aggregate["driver_name"] = _resolve_text(row.get("driver_name"), fallback=driver_id)

    rows: list[list[Any]] = []
    for service_date, driver_id in sorted(aggregated.keys(), key=lambda item: (item[0], item[1])):
        aggregate = aggregated[(service_date, driver_id)]
        route_id = ",".join(sorted(str(item) for item in aggregate["route_ids"]))
        rows.append(
            [
                service_date,
                driver_id,
                str(aggregate["driver_name"]),
                "WORKED",
                int(aggregate["actual_minutes"]),
                route_id,
                "",
                0,
                0,
                0,
                _actual_hours_source_snapshot_row_ref(
                    source_artifact_version_id=source_artifact_version_id,
                    service_date=service_date,
                    driver_id=driver_id,
                    route_id=route_id,
                ),
            ]
        )

    return {
        "schema_version": "1.0",
        "artifact_kind": PLANNING_ACTUAL_HOURS_ARTIFACT_KIND,
        "shape": "previous_week_driver_day_history_rows",
        "columns": list(PLANNING_ACTUAL_HOURS_COLUMNS),
        "rows": rows,
        "source_reporting_artifact_version_id": source_artifact_version_id,
    }


def merge_planning_actual_hours_snapshot_payloads(
    *,
    current_payload: Mapping[str, Any] | None,
    incoming_payload: Mapping[str, Any],
) -> dict[str, Any]:
    merged_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in _planning_actual_hours_row_dicts(current_payload):
        key = (_resolve_text(row.get("service_date"), fallback=""), _resolve_text(row.get("driver_id"), fallback=""))
        if not key[0] or not key[1]:
            continue
        merged_by_key[key] = row
    for row in _planning_actual_hours_row_dicts(incoming_payload):
        key = (_resolve_text(row.get("service_date"), fallback=""), _resolve_text(row.get("driver_id"), fallback=""))
        if not key[0] or not key[1]:
            continue
        merged_by_key[key] = row

    rows = [
        [
            str(row.get("service_date") or ""),
            str(row.get("driver_id") or ""),
            str(row.get("driver_name") or ""),
            str(row.get("historical_state") or ""),
            _coerce_int(row.get("actual_minutes"), field_name="actual_hours.actual_minutes"),
            str(row.get("route_id") or ""),
            str(row.get("route_slot_class") or ""),
            1 if _coerce_bool(row.get("call_in_sick_flag")) else 0,
            1 if _coerce_bool(row.get("cancellation_flag")) else 0,
            1 if _coerce_bool(row.get("non_working_day_flag")) else 0,
            str(row.get("source_snapshot_row_ref") or ""),
        ]
        for _, row in sorted(
            merged_by_key.items(),
            key=lambda item: (
                str(item[1].get("service_date") or ""),
                str(item[1].get("driver_id") or ""),
                str(item[1].get("route_id") or ""),
            ),
        )
    ]

    merged_payload = dict(current_payload) if isinstance(current_payload, Mapping) else {}
    merged_payload.update(
        {
            "schema_version": "1.0",
            "artifact_kind": PLANNING_ACTUAL_HOURS_ARTIFACT_KIND,
            "shape": "previous_week_driver_day_history_rows",
            "columns": list(PLANNING_ACTUAL_HOURS_COLUMNS),
            "rows": rows,
        }
    )
    return merged_payload


def _project_supported_source_workbook(
    content: bytes,
    *,
    source_metadata_json: Mapping[str, Any] | None = None,
    source_file_name: str | None = None,
    fallback_service_date: str | None = None,
):
    try:
        projection = project_raw_eos_workbook(
            content,
            source_metadata_json=source_metadata_json,
            source_file_name=source_file_name,
            fallback_service_date=fallback_service_date,
            fallback_station_code=DEFAULT_STATION_CODE,
            fallback_dsp_name=DEFAULT_DSP_NAME,
        )
    except WorkbookRuntimeDependencyError:
        raise
    except Exception as exc:
        raise DispatchReportingBuildError(
            "EOS workbook must match the supported dispatch-reporting workbook family"
        ) from exc
    return projection


def _normalized_route_rows(normalized_payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = normalized_payload.get("rows")
    if not isinstance(rows, list):
        raise DispatchReportingBuildError("dispatch reporting normalized payload must contain rows")
    normalized_rows: list[Mapping[str, Any]] = []
    for row in rows:
        if isinstance(row, Mapping):
            normalized_rows.append(row)
    return normalized_rows


def _planning_actual_hours_row_dicts(
    payload: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    columns = payload.get("columns")
    rows = payload.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []
    column_names = [str(item) for item in columns]
    row_dicts: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        row_dicts.append(dict(zip(column_names, row)))
    return row_dicts


def _actual_hours_source_snapshot_row_ref(
    *,
    source_artifact_version_id: str,
    service_date: str,
    driver_id: str,
    route_id: str,
) -> str:
    route_token = route_id or "no-route"
    digest = json.dumps(
        {
            "source_artifact_version_id": source_artifact_version_id,
            "service_date": service_date,
            "driver_id": driver_id,
            "route_id": route_token,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"dispatch-reporting:{_stable_hash(digest)}"


def _stable_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _build_manual_closeout_rows(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_finish = max(
        (
            _resolve_text(row.get("actual_finish"), fallback="")
            for row in route_rows
            if _resolve_text(row.get("actual_finish"), fallback="")
        ),
        default="",
    )
    return [
        {
            "row_id": "manual-closeout",
            "sick_calls": "",
            "unavailable_drivers": "",
            "working_devices": "",
            "rescues": "",
            "incidents": "",
            "last_driver_clockout": latest_finish,
            "dispatcher_comment": "",
            "manager_note": "",
        }
    ]


def _resolve_text(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    return text or fallback


def _coerce_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise DispatchReportingBuildError(f"{field_name} must be numeric")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError as exc:
        raise DispatchReportingBuildError(f"{field_name} must be numeric") from exc


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}
