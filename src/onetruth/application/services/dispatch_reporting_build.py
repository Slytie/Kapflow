from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from onetruth.application.services.dispatch_reporting_workbook import (
    WorkbookRuntimeDependencyError,
    project_upd_draft_workbook,
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
SUPPORTED_SOURCE_WORKBOOK_FAMILY = "dispatch_reporting.stage03.upd_draft.workbook"
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
    built_at: str,
    actor_id: str,
) -> DispatchReportingBuildOutput:
    projection = _project_supported_source_workbook(eos_workbook_bytes)
    route_rows = _normalize_route_actual_rows(projection.get("route_actuals"))
    quality_warning_rows = _normalize_quality_warning_rows(projection.get("quality_warnings"))
    manual_closeout_rows = _normalize_manual_closeout_rows(projection.get("manual_closeout"))

    metadata = dict(source_metadata_json) if isinstance(source_metadata_json, Mapping) else {}
    service_date = _resolve_service_date(route_rows, metadata)
    station_code = _resolve_text(metadata.get("station_code"), fallback=DEFAULT_STATION_CODE)
    dsp_name = _resolve_text(metadata.get("dsp_name"), fallback=DEFAULT_DSP_NAME)

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


def _project_supported_source_workbook(content: bytes) -> dict[str, Any]:
    try:
        projection = project_upd_draft_workbook(content)
    except WorkbookRuntimeDependencyError:
        raise
    except Exception as exc:
        raise DispatchReportingBuildError(
            "EOS workbook must match the supported dispatch-reporting workbook family"
        ) from exc
    if str(projection.get("workflow_id") or "") != WORKFLOW_ID:
        raise DispatchReportingBuildError(
            "EOS workbook must belong to the dispatch-reporting workbook family"
        )
    return projection


def _normalize_route_actual_rows(raw_rows: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, list):
        raise DispatchReportingBuildError("supported EOS workbook is missing route_actuals rows")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise DispatchReportingBuildError(
                f"route_actuals[{index}] must be an object in the supported EOS workbook"
            )
        normalized.append(dict(row))
    return normalized


def _normalize_quality_warning_rows(raw_rows: Any) -> list[dict[str, Any]]:
    if raw_rows is None:
        return []
    if not isinstance(raw_rows, list):
        raise DispatchReportingBuildError("quality_warnings must be a list in the supported EOS workbook")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping):
            raise DispatchReportingBuildError(
                f"quality_warnings[{index}] must be an object in the supported EOS workbook"
            )
        normalized.append(
            {
                "row_id": _resolve_text(row.get("row_id"), fallback=f"warning-{index + 1:03d}"),
                "warning_code": _resolve_text(row.get("warning_code"), fallback="formula_integrity_warning"),
                "severity": _resolve_text(row.get("severity"), fallback="warning"),
                "message": _resolve_text(
                    row.get("message"),
                    fallback="Source workbook had broken summary formulas.",
                ),
                "source_sheet": _resolve_text(row.get("source_sheet"), fallback="Summary"),
            }
        )
    return normalized


def _normalize_manual_closeout_rows(raw_rows: Any) -> list[dict[str, Any]]:
    if isinstance(raw_rows, list) and raw_rows:
        row = raw_rows[0]
        if not isinstance(row, Mapping):
            raise DispatchReportingBuildError(
                "manual_closeout must contain one object row in the supported EOS workbook"
            )
        return [
            {
                "row_id": _resolve_text(row.get("row_id"), fallback="manual-closeout"),
                "sick_calls": _resolve_text(row.get("sick_calls"), fallback=""),
                "unavailable_drivers": _resolve_text(row.get("unavailable_drivers"), fallback=""),
                "working_devices": _resolve_text(row.get("working_devices"), fallback=""),
                "rescues": _resolve_text(row.get("rescues"), fallback=""),
                "incidents": _resolve_text(row.get("incidents"), fallback=""),
                "last_driver_clockout": _resolve_text(row.get("last_driver_clockout"), fallback=""),
                "dispatcher_comment": _resolve_text(row.get("dispatcher_comment"), fallback=""),
                "manager_note": _resolve_text(row.get("manager_note"), fallback=""),
            }
        ]
    return [
        {
            "row_id": "manual-closeout",
            "sick_calls": "",
            "unavailable_drivers": "",
            "working_devices": "",
            "rescues": "",
            "incidents": "",
            "last_driver_clockout": "",
            "dispatcher_comment": "",
            "manager_note": "",
        }
    ]


def _resolve_service_date(
    route_rows: list[dict[str, Any]],
    metadata: Mapping[str, Any],
) -> str:
    for row in route_rows:
        candidate = _resolve_text(row.get("service_date"), fallback="")
        if candidate:
            return candidate
    return _resolve_text(metadata.get("service_date"), fallback="")


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
