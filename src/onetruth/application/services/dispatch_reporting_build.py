from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
