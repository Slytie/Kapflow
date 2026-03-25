from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)
from onetruth.application.services.schedule_control import (
    WeeklyScheduleControlBundle,
    build_weekly_schedule_control_bundle,
)
from onetruth.infrastructure.events.event_store import utc_now_iso


REPO_ROOT = Path(__file__).resolve().parents[4]
_ACTUAL_OPS_SOURCE_MATERIAL_PATH = (
    REPO_ROOT / "fixtures" / "logistics" / "weekly_stage04_actual_ops_lab_source_material_v2.yaml"
)

SCHEDULE_DEMO_WORKPAGE_ID = "schedule-v0"
EOD_DEMO_WORKPAGE_ID = "eod-v0"
_SCHEDULE_WORKFLOW_ID = "weekly_schedule_planning.v1"
_EOD_WORKFLOW_ID = "dispatch_reporting.v1"
_PREVIEW_SERVICE_DATE = "2026-03-24"
_PLANNER_NOTE = (
    "Holdout schedule contributed route totals only; staffing cells were intentionally "
    "excluded from the normalized example package."
)
_SELECTED_DAY_OPEN_QUESTION = (
    "Confirm late requests and final on-call posture before day-of handoff."
)
_EOD_SERVICE_DATE = "2026-03-16"
_EOD_STATION_CODE = "DVC4"
_EOD_DSP_NAME = "QDCI"
_EOD_SOURCE_VERSION = "dispatch_reporting_2026_03_16_qdci_dvc4_partial_v1"
_EOD_WARNING_NOTE = (
    "This backend demo query is built from an intentionally partial 2026-03-16 "
    "QDCI / DVC4 reporting example family. Row-level actuals remain the primary truth "
    "because the source workbook summary tabs contained broken formulas."
)
_EOD_NOTE_PANEL_BODY = (
    "This backend demo query uses intentionally partial repo examples. Source workbook "
    "summary tabs showed formula failures, so row-level actuals remain the primary truth "
    "and v0 surfaces a warning instead of reproducing broken formulas."
)

_ROUTE_SLOT_DATASET_KEY = "planning.route_slot_requirements.workbook"
_APPROVED_AVAILABILITY_DATASET_KEY = "planning.approved_availability.workbook"
_DRIVER_CAPABILITIES_DATASET_KEY = "planning.driver_capabilities.workbook"
_ACTUAL_HOURS_DATASET_KEY = "planning.actual_hours_snapshot.workbook"
_INPUT_BUNDLE_DATASET_KEY = "planning.input_bundle.doc"
_EOD_RAW_DATASET_KEY = "reporting.eos_raw.workbook"
_EOD_NORMALIZED_DATASET_KEY = "reporting.actuals_normalized.workbook"
_EOD_DRAFT_DATASET_KEY = "reporting.upd_draft.workbook"

_SOURCE_DATASETS: tuple[tuple[str, str], ...] = (
    ("route_slot_requirements", _ROUTE_SLOT_DATASET_KEY),
    ("approved_availability", _APPROVED_AVAILABILITY_DATASET_KEY),
    ("driver_capabilities", _DRIVER_CAPABILITIES_DATASET_KEY),
    ("actual_hours_snapshot", _ACTUAL_HOURS_DATASET_KEY),
    ("stage04_input_bundle", _INPUT_BUNDLE_DATASET_KEY),
)

_SOURCE_ARTIFACT_KEYS = {
    "route_slot_requirements": "route_slot_requirements",
    "approved_availability": "approved_availability",
    "driver_capabilities": "driver_capabilities",
    "actual_hours_snapshot": "actual_hours",
    "stage04_input_bundle": "input_bundle_manifest",
}

_EOD_SOURCE_DATASETS: tuple[tuple[str, str], ...] = (
    ("eos_route_rows", _EOD_RAW_DATASET_KEY),
    ("normalized_actuals", _EOD_NORMALIZED_DATASET_KEY),
    ("upd_candidates", _EOD_DRAFT_DATASET_KEY),
)

_EOD_SOURCE_EXAMPLES = {
    "eos_route_rows": (
        "docs/workflows/dispatch_reporting/v1/examples/"
        "eos_route_rows_2026_03_16_qdci_partial_example.yaml"
    ),
    "normalized_actuals": (
        "docs/workflows/dispatch_reporting/v1/examples/"
        "normalized_actuals_2026_03_16_qdci_partial_example.yaml"
    ),
    "upd_candidates": (
        "docs/workflows/dispatch_reporting/v1/examples/"
        "upd_candidate_2026_03_16_qdci_partial_example.yaml"
    ),
}

_ROSTER_TARGET_NAMES = (
    "Parampreet Singh",
    "Balwinder Singh",
    "Navjot Singh",
)

_FORM_ON_CALL_OPTIONS = (
    "Parampreet Singh",
    "Brahmvir Singh",
    "Sachin Goyal",
)


class DemoWorkpageNotFoundError(LookupError):
    def __init__(self, workpage_id: str) -> None:
        super().__init__(f"demo workpage not found: {workpage_id}")
        self.workpage_id = workpage_id


def build_demo_workpage_contract(workpage_id: str) -> dict[str, Any]:
    if workpage_id == SCHEDULE_DEMO_WORKPAGE_ID:
        return build_schedule_demo_workpage_contract()
    if workpage_id == EOD_DEMO_WORKPAGE_ID:
        return build_eod_demo_workpage_contract()
    raise DemoWorkpageNotFoundError(workpage_id)


def build_schedule_demo_workpage_contract() -> dict[str, Any]:
    source_material = _load_actual_ops_source_material()
    source_examples = _source_examples(source_material)
    bundle = _schedule_demo_bundle()

    source_refs = [
        source_examples["route_slot_requirements"],
        source_examples["approved_availability"],
        source_examples["driver_capabilities"],
        source_examples["actual_hours_snapshot"],
        source_examples["stage04_input_bundle"],
    ]
    primary_demand = _sorted_daily_demand(bundle)[0]

    return {
        "workpage": {
            "workpage_id": SCHEDULE_DEMO_WORKPAGE_ID,
            "version": 2,
            "title": "Weekly schedule review",
            "mode": "example",
            "workflow_id": _SCHEDULE_WORKFLOW_ID,
            "dataset_key": _INPUT_BUNDLE_DATASET_KEY,
            "source_artifact_version_id": None,
            "source_examples": source_examples,
            "summary": {
                "planning_week_id": bundle.planning_week_id,
                "operational_week_start": bundle.scope_start,
                "service_area": _first_non_empty(slot.service_area for slot in bundle.route_slots),
                "station_code": _first_non_empty(slot.station_code for slot in bundle.route_slots),
                "total_routes_required": sum(
                    item.planned_route_count for item in bundle.daily_demand_by_service_date.values()
                ),
                "drivers_in_scope": len(bundle.drivers),
                "on_call_target_per_day": primary_demand.on_call_target,
                "excess_capacity_target_per_day": primary_demand.excess_capacity_target,
                "planner_note": _PLANNER_NOTE,
            },
            "sections": [
                {
                    "kind": "summary_cards",
                    "title": "Week summary",
                    "cards": [
                        {
                            "key": "planning_week",
                            "label": "Planning week",
                            "value": bundle.planning_week_id,
                        },
                        {
                            "key": "total_routes",
                            "label": "Required routes",
                            "value": sum(
                                item.planned_route_count
                                for item in bundle.daily_demand_by_service_date.values()
                            ),
                        },
                        {
                            "key": "drivers",
                            "label": "Drivers in scope",
                            "value": len(bundle.drivers),
                        },
                        {
                            "key": "on_call_target",
                            "label": "Daily on-call target",
                            "value": primary_demand.on_call_target,
                        },
                        {
                            "key": "excess_capacity_target",
                            "label": "Daily excess-capacity target",
                            "value": primary_demand.excess_capacity_target,
                        },
                    ],
                },
                {
                    "kind": "table",
                    "title": "Daily demand and coverage posture",
                    "table_id": "day_demand",
                    "columns": [
                        {"key": "service_date", "label": "Service date"},
                        {"key": "planned_route_count", "label": "Planned routes"},
                        {"key": "on_call_target", "label": "On-call target"},
                        {"key": "excess_capacity_target", "label": "Excess-capacity target"},
                        {"key": "note", "label": "Note"},
                    ],
                    "rows": _day_demand_rows(bundle),
                },
                {
                    "kind": "table",
                    "title": "Selected-day preview",
                    "table_id": "selected_day_preview",
                    "columns": [
                        {"key": "service_date", "label": "Selected day"},
                        {"key": "routes_required", "label": "Routes required"},
                        {"key": "drivers_available", "label": "Drivers available"},
                        {"key": "projected_on_call_needed", "label": "On-call needed"},
                        {"key": "open_questions", "label": "Open questions"},
                    ],
                    "rows": [_selected_day_preview_row(bundle)],
                },
                {
                    "kind": "table",
                    "title": "Driver roster excerpt",
                    "table_id": "driver_roster",
                    "columns": [
                        {"key": "driver_name", "label": "Driver"},
                        {"key": "employment_type", "label": "Employment"},
                        {
                            "key": "preferred_route_slot_classes",
                            "label": "Preferred slot",
                        },
                        {"key": "target_shifts_per_week", "label": "Target shifts"},
                        {"key": "on_call_eligible", "label": "On-call eligible"},
                        {"key": "previous_week_minutes", "label": "Previous-week minutes"},
                        {"key": "availability_summary", "label": "Availability summary"},
                    ],
                    "rows": _driver_roster_rows(bundle),
                },
                {
                    "kind": "note_panel",
                    "title": "Boundary note",
                    "body": (
                        "This page is a weekly-planning review surface. Any selected-day "
                        "controls below are local what-if inputs for the prototype and do "
                        "not replace live_dispatch.v1 day-of truth."
                    ),
                },
                {
                    "kind": "form",
                    "title": "Selected-day what-if inputs",
                    "form_id": "selected_day_what_if",
                    "fields": [
                        {
                            "key": "scenario_sick_calls",
                            "label": "Scenario sick calls",
                            "input": "multi_select",
                            "options": _multi_select_options(bundle),
                            "value": [],
                        },
                        {
                            "key": "scenario_on_call_assignments",
                            "label": "Scenario on-call assignments",
                            "input": "multi_select",
                            "options": [
                                name
                                for name in _FORM_ON_CALL_OPTIONS
                                if name in _available_driver_names(bundle)
                            ],
                            "value": [],
                        },
                        {
                            "key": "scenario_added_routes",
                            "label": "Scenario added routes",
                            "input": "integer",
                            "value": 0,
                        },
                        {
                            "key": "scenario_dropped_routes",
                            "label": "Scenario dropped routes",
                            "input": "integer",
                            "value": 0,
                        },
                        {
                            "key": "scenario_note",
                            "label": "Planner note",
                            "input": "textarea",
                            "value": "",
                        },
                    ],
                },
                {
                    "kind": "history_stub",
                    "title": "History",
                    "entries": [
                        {
                            "label": "Previous week actual-hours snapshot",
                            "value": "available for comparison",
                        },
                        {
                            "label": "Rescue / fairness trend",
                            "value": "future slice",
                        },
                    ],
                },
            ],
            "validation": {
                "status": "informational",
                "warnings": [
                    "This server-owned demo query is built from repo-native weekly planning example sources.",
                    "Selected-day controls are local what-if inputs only and do not claim ownership of live dispatch truth.",
                ],
            },
        },
        "source": {
            "mode": "demo",
            "primary_dataset_key": None,
            "source_dataset_keys": [dataset_key for _, dataset_key in _SOURCE_DATASETS],
            "source_artifact_version_id": None,
            "source_refs": source_refs,
        },
        "freshness": {
            "generated_at": utc_now_iso(),
            "source_kind": "repo_example_bundle",
            "source_version": _require_text(source_material.get("fixture_contract")),
        },
    }


def build_eod_demo_workpage_contract() -> dict[str, Any]:
    source_examples = dict(_EOD_SOURCE_EXAMPLES)
    route_rows = _load_eod_route_rows()
    normalized_rows = _load_eod_normalized_actuals()
    upd_rows = _load_eod_upd_candidates()
    source_refs = [
        source_examples["eos_route_rows"],
        source_examples["normalized_actuals"],
        source_examples["upd_candidates"],
    ]

    return {
        "workpage": {
            "workpage_id": EOD_DEMO_WORKPAGE_ID,
            "version": 2,
            "title": "End-of-day report",
            "mode": "example",
            "workflow_id": _EOD_WORKFLOW_ID,
            "dataset_key": _EOD_DRAFT_DATASET_KEY,
            "source_artifact_version_id": None,
            "source_examples": source_examples,
            "summary": _eod_summary(route_rows, normalized_rows),
            "sections": [
                {
                    "kind": "summary_cards",
                    "title": "Daily summary",
                    "cards": _eod_summary_cards(route_rows, normalized_rows),
                },
                {
                    "kind": "note_panel",
                    "title": "Formula-integrity warning",
                    "body": _EOD_NOTE_PANEL_BODY,
                },
                {
                    "kind": "table",
                    "title": "Route actuals",
                    "table_id": "route_actuals",
                    "columns": [
                        {"key": "route_id", "label": "Route"},
                        {"key": "driver_name", "label": "Driver"},
                        {"key": "packages_dispatched", "label": "Dispatched"},
                        {"key": "packages_delivered", "label": "Delivered"},
                        {"key": "planned_window", "label": "Planned"},
                        {"key": "actual_window", "label": "Actual"},
                        {"key": "actual_minutes", "label": "Minutes"},
                        {"key": "returns", "label": "Returns"},
                        {"key": "return_reasons", "label": "Return reasons"},
                        {"key": "upd_candidate", "label": "UPD?"},
                    ],
                    "rows": _eod_route_actual_rows(route_rows, normalized_rows),
                },
                {
                    "kind": "form",
                    "title": "Manual closeout",
                    "form_id": "closeout_details",
                    "fields": _eod_form_fields(route_rows),
                },
                {
                    "kind": "checklist",
                    "title": "UPD candidate review",
                    "checklist_id": "upd_candidates",
                    "items": _eod_checklist_items(upd_rows),
                },
                {
                    "kind": "history_stub",
                    "title": "History",
                    "entries": [
                        {"label": "Previous daily reports", "value": "future slice"},
                        {"label": "Weekly / monthly summaries", "value": "future slice"},
                    ],
                },
            ],
            "validation": {
                "status": "informational",
                "warnings": [
                    "This server-owned demo query is built from an intentionally partial 2026-03-16 dispatch-reporting example family.",
                    "Workbook summary formulas were broken in the source material, so row-level actuals remain the primary truth for this projection.",
                    "Manual closeout inputs remain local-only in v0; no submit/materialize contract exists yet.",
                ],
            },
        },
        "source": {
            "mode": "demo",
            "primary_dataset_key": _EOD_DRAFT_DATASET_KEY,
            "source_dataset_keys": [dataset_key for _, dataset_key in _EOD_SOURCE_DATASETS],
            "source_artifact_version_id": None,
            "source_refs": source_refs,
        },
        "freshness": {
            "generated_at": utc_now_iso(),
            "source_kind": "repo_example_bundle",
            "source_version": _EOD_SOURCE_VERSION,
        },
    }


@lru_cache(maxsize=1)
def _load_actual_ops_source_material() -> dict[str, Any]:
    loaded = yaml.safe_load(_ACTUAL_OPS_SOURCE_MATERIAL_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(
            "weekly Stage04 actual-ops source material must decode to an object"
        )
    return loaded


@lru_cache(maxsize=1)
def _schedule_demo_bundle() -> WeeklyScheduleControlBundle:
    source_material = _load_actual_ops_source_material()
    fixture_payloads = build_actual_ops_weekly_stage04_fixture_payloads()
    planning_week_id = _require_text(source_material.get("planning_week_id"))
    return build_weekly_schedule_control_bundle(
        workflow_run={
            "workflow_run_id": "wr-demo-schedule-v0",
            "partition_key": planning_week_id,
        },
        route_slot_requirements_artifact={
            "artifact_version_id": "av-demo-schedule-v0-routes",
            "artifact_kind": _ROUTE_SLOT_DATASET_KEY,
            "dataset_key": _ROUTE_SLOT_DATASET_KEY,
            "metadata_json": fixture_payloads["route_slot_requirements"],
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-demo-schedule-v0-drivers",
            "artifact_kind": _DRIVER_CAPABILITIES_DATASET_KEY,
            "dataset_key": _DRIVER_CAPABILITIES_DATASET_KEY,
            "metadata_json": fixture_payloads["driver_capabilities"],
        },
        approved_availability_artifact={
            "artifact_version_id": "av-demo-schedule-v0-availability",
            "artifact_kind": _APPROVED_AVAILABILITY_DATASET_KEY,
            "dataset_key": _APPROVED_AVAILABILITY_DATASET_KEY,
            "metadata_json": fixture_payloads["approved_availability"],
        },
        actual_hours_artifact={
            "artifact_version_id": "av-demo-schedule-v0-hours",
            "artifact_kind": _ACTUAL_HOURS_DATASET_KEY,
            "dataset_key": _ACTUAL_HOURS_DATASET_KEY,
            "metadata_json": fixture_payloads["actual_hours"],
        },
    )


def _source_examples(source_material: dict[str, Any]) -> dict[str, str]:
    source_artifacts = source_material.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        raise ValueError("weekly Stage04 source material must declare source_artifacts")
    return {
        label: _require_text(source_artifacts.get(_SOURCE_ARTIFACT_KEYS[label]))
        for label, _dataset_key in _SOURCE_DATASETS
    }


def _sorted_daily_demand(bundle: WeeklyScheduleControlBundle) -> list[Any]:
    return sorted(
        bundle.daily_demand_by_service_date.values(),
        key=lambda item: item.service_date,
    )


def _day_demand_rows(bundle: WeeklyScheduleControlBundle) -> list[dict[str, Any]]:
    daily_demand = _sorted_daily_demand(bundle)
    max_demand = max((item.planned_route_count for item in daily_demand), default=0)
    rows: list[dict[str, Any]] = []
    for item in daily_demand:
        notes = ["Holdout route total override"]
        if item.planned_route_count == max_demand and max_demand > 0:
            notes.append("Highest-demand day in the example week")
        if item.service_date == _PREVIEW_SERVICE_DATE:
            notes.append("Selected-day preview default")
        rows.append(
            {
                "service_date": item.service_date,
                "planned_route_count": item.planned_route_count,
                "on_call_target": item.on_call_target,
                "excess_capacity_target": item.excess_capacity_target,
                "note": "; ".join(notes),
            }
        )
    return rows


@lru_cache(maxsize=1)
def _load_eod_route_rows() -> tuple[dict[str, Any], ...]:
    return _load_tabular_example_rows(_EOD_SOURCE_EXAMPLES["eos_route_rows"])


@lru_cache(maxsize=1)
def _load_eod_normalized_actuals() -> tuple[dict[str, Any], ...]:
    return _load_tabular_example_rows(_EOD_SOURCE_EXAMPLES["normalized_actuals"])


@lru_cache(maxsize=1)
def _load_eod_upd_candidates() -> tuple[dict[str, Any], ...]:
    return _load_tabular_example_rows(_EOD_SOURCE_EXAMPLES["upd_candidates"])


def _load_tabular_example_rows(relative_path: str) -> tuple[dict[str, Any], ...]:
    loaded = yaml.safe_load((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"tabular example must decode to an object: {relative_path}")

    columns = loaded.get("columns")
    rows = loaded.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list):
        raise ValueError(f"tabular example must define columns and rows: {relative_path}")

    column_names = [_require_text(column) for column in columns]
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != len(column_names):
            raise ValueError(f"tabular example row shape mismatch: {relative_path}")
        normalized_rows.append(dict(zip(column_names, row)))
    return tuple(normalized_rows)


def _eod_summary(
    route_rows: tuple[dict[str, Any], ...],
    normalized_rows: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    packages_dispatched = sum(_require_int(row.get("packages_dispatched")) for row in route_rows)
    packages_delivered = sum(_require_int(row.get("packages_delivered")) for row in route_rows)
    packages_returned = sum(_require_int(row.get("returned_packages")) for row in normalized_rows)
    actual_minutes = [_require_int(row.get("actual_minutes")) for row in normalized_rows]
    formula_warning = any(str(row.get("formula_integrity_warning") or "").strip() for row in normalized_rows)

    return {
        "service_date": _EOD_SERVICE_DATE,
        "station_code": _EOD_STATION_CODE,
        "dsp_name": _EOD_DSP_NAME,
        "total_routes_actual": len(route_rows),
        "packages_dispatched": packages_dispatched,
        "actual_dispatched": packages_dispatched,
        "packages_delivered": packages_delivered,
        "packages_returned": packages_returned,
        "delivered_pct": _percent(packages_delivered, packages_dispatched),
        "return_pct": _percent(packages_returned, packages_dispatched),
        "average_route_time": _format_average_minutes(actual_minutes),
        "formula_integrity_warning": formula_warning,
        "warning_note": _EOD_WARNING_NOTE,
    }


def _eod_summary_cards(
    route_rows: tuple[dict[str, Any], ...],
    normalized_rows: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    summary = _eod_summary(route_rows, normalized_rows)
    return [
        {
            "key": "total_routes",
            "label": "Total routes actual",
            "value": summary["total_routes_actual"],
        },
        {
            "key": "packages_dispatched",
            "label": "Packages dispatched",
            "value": summary["packages_dispatched"],
        },
        {
            "key": "packages_delivered",
            "label": "Packages delivered",
            "value": summary["packages_delivered"],
        },
        {
            "key": "packages_returned",
            "label": "Packages returned",
            "value": summary["packages_returned"],
        },
        {
            "key": "delivered_pct",
            "label": "Delivered %",
            "value": f"{summary['delivered_pct']:.2f}%",
        },
        {
            "key": "average_route_time",
            "label": "Average route time",
            "value": summary["average_route_time"],
        },
    ]


def _eod_route_actual_rows(
    route_rows: tuple[dict[str, Any], ...],
    normalized_rows: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    normalized_by_key = {
        _eod_row_identity(row): row for row in normalized_rows
    }
    rows: list[dict[str, Any]] = []
    for route_row in route_rows:
        identity = _eod_row_identity(route_row)
        normalized_row = normalized_by_key.get(identity)
        if normalized_row is None:
            raise ValueError(f"normalized actuals missing for EOD route row: {identity}")
        rows.append(
            {
                "route_id": _require_text(route_row.get("route_id")),
                "driver_name": _require_text(route_row.get("driver_name")),
                "packages_dispatched": _require_int(route_row.get("packages_dispatched")),
                "packages_delivered": _require_int(route_row.get("packages_delivered")),
                "planned_window": _time_window(
                    route_row.get("planned_start"),
                    route_row.get("planned_finish"),
                ),
                "actual_window": _time_window(
                    route_row.get("actual_start"),
                    route_row.get("actual_finish"),
                ),
                "actual_minutes": _require_int(normalized_row.get("actual_minutes")),
                "returns": _require_int(normalized_row.get("returned_packages")),
                "return_reasons": str(normalized_row.get("return_reasons") or ""),
                "upd_candidate": bool(normalized_row.get("upd_candidate")),
            }
        )
    return rows


def _eod_form_fields(route_rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    driver_options = _unique_driver_names(route_rows)
    last_clockout = max(_require_text(row.get("actual_finish")) for row in route_rows)
    return [
        {
            "key": "sick_calls",
            "label": "Sick calls",
            "input": "multi_select",
            "options": driver_options,
            "value": [],
        },
        {
            "key": "unavailable_drivers",
            "label": "Not available",
            "input": "multi_select",
            "options": driver_options,
            "value": [],
        },
        {
            "key": "working_devices",
            "label": "Working devices / rabbits",
            "input": "text",
            "value": "",
        },
        {
            "key": "rescues",
            "label": "Rescues",
            "input": "repeater",
            "value": [],
        },
        {
            "key": "incidents",
            "label": "Incidents",
            "input": "repeater",
            "value": [],
        },
        {
            "key": "last_driver_clockout",
            "label": "Last driver clock-out",
            "input": "time",
            "value": last_clockout,
        },
        {
            "key": "dispatcher_comment",
            "label": "Dispatcher comment",
            "input": "textarea",
            "value": "",
        },
        {
            "key": "manager_note",
            "label": "Manager note",
            "input": "textarea",
            "value": "",
        },
    ]


def _eod_checklist_items(upd_rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in upd_rows:
        route_id = _require_text(row.get("route_id"))
        items.append(
            {
                "item_id": f"upd-candidate-{route_id.lower()}",
                "title": f"{_require_text(row.get('driver_name'))} · {route_id}",
                "detail": _require_text(row.get("reason")),
                "selected": False,
                "note": "",
                "tags": [f"{_require_int(row.get('actual_minutes'))} minutes"],
            }
        )
    return items


def _eod_row_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _require_text(row.get("service_date")),
        _require_text(row.get("route_id")),
        _require_text(row.get("driver_name")),
    )


def _unique_driver_names(route_rows: tuple[dict[str, Any], ...]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in route_rows:
        name = _require_text(row.get("driver_name"))
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def _time_window(start: Any, finish: Any) -> str:
    return f"{_require_text(start)} - {_require_text(finish)}"


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _format_average_minutes(minutes: list[int]) -> str:
    if not minutes:
        return "0:00:00"
    average_minutes = round(sum(minutes) / len(minutes))
    hours, minute_remainder = divmod(average_minutes, 60)
    return f"{hours}:{minute_remainder:02d}:00"


def _selected_day_preview_row(bundle: WeeklyScheduleControlBundle) -> dict[str, Any]:
    demand = bundle.daily_demand_by_service_date.get(_PREVIEW_SERVICE_DATE)
    if demand is None:
        raise ValueError(
            f"selected-day preview date is missing from schedule demo source: {_PREVIEW_SERVICE_DATE}"
        )
    return {
        "service_date": _PREVIEW_SERVICE_DATE,
        "routes_required": demand.planned_route_count,
        "drivers_available": demand.planned_route_count + demand.on_call_target,
        "projected_on_call_needed": demand.on_call_target,
        "open_questions": _SELECTED_DAY_OPEN_QUESTION,
    }


def _driver_roster_rows(bundle: WeeklyScheduleControlBundle) -> list[dict[str, Any]]:
    capabilities_by_name = {
        capability.driver_name: capability
        for capability in bundle.drivers
        if capability.driver_name
    }
    selected_names = [name for name in _ROSTER_TARGET_NAMES if name in capabilities_by_name]
    remaining_names = sorted(
        name for name in capabilities_by_name if name not in selected_names
    )
    for name in remaining_names:
        if len(selected_names) >= len(_ROSTER_TARGET_NAMES):
            break
        selected_names.append(name)

    rows: list[dict[str, Any]] = []
    for name in selected_names:
        capability = capabilities_by_name[name]
        availability = bundle.availability_by_driver.get(capability.driver_id)
        rows.append(
            {
                "driver_name": name,
                "employment_type": (
                    capability.employment_type
                    or (availability.employment_type if availability is not None else "")
                ),
                "preferred_route_slot_classes": ", ".join(
                    capability.preferred_route_slot_classes
                ),
                "target_shifts_per_week": (
                    availability.target_shifts_per_week if availability is not None else 0
                ),
                "on_call_eligible": (
                    bool(availability.on_call_eligible)
                    if availability is not None
                    else False
                ),
                "previous_week_minutes": bundle.actual_minutes_by_driver.get(
                    capability.driver_id,
                    0,
                ),
                "availability_summary": _availability_summary(availability),
            }
        )
    return rows


def _availability_summary(availability: Any) -> str:
    if availability is None or not availability.daily_states:
        return "no planning-week availability recorded"
    counts = Counter(str(item.state or "").upper() for item in availability.daily_states)
    labels = (
        ("PREFERRED", "preferred"),
        ("AVAILABLE", "available"),
        ("ON_CALL_ONLY", "on-call-only"),
        ("AVOID_IF_POSSIBLE", "avoid-if-possible"),
        ("CANNOT", "cannot"),
    )
    parts = [
        f"{label} {count} {'day' if count == 1 else 'days'}"
        for key, label in labels
        for count in [counts.get(key, 0)]
        if count > 0
    ]
    return "; ".join(parts) if parts else "no planning-week availability recorded"


def _multi_select_options(bundle: WeeklyScheduleControlBundle) -> list[str]:
    available_names = _available_driver_names(bundle)
    return [name for name in _ROSTER_TARGET_NAMES if name in available_names]


def _available_driver_names(bundle: WeeklyScheduleControlBundle) -> set[str]:
    return {
        capability.driver_name
        for capability in bundle.drivers
        if capability.driver_name
    }


def _first_non_empty(values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _require_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("expected non-empty text value")
    return text


def _require_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("expected integer value")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("expected integer value") from exc
