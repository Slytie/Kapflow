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
_SCHEDULE_WORKFLOW_ID = "weekly_schedule_planning.v1"
_PREVIEW_SERVICE_DATE = "2026-03-24"
_PLANNER_NOTE = (
    "Holdout schedule contributed route totals only; staffing cells were intentionally "
    "excluded from the normalized example package."
)
_SELECTED_DAY_OPEN_QUESTION = (
    "Confirm late requests and final on-call posture before day-of handoff."
)

_ROUTE_SLOT_DATASET_KEY = "planning.route_slot_requirements.workbook"
_APPROVED_AVAILABILITY_DATASET_KEY = "planning.approved_availability.workbook"
_DRIVER_CAPABILITIES_DATASET_KEY = "planning.driver_capabilities.workbook"
_ACTUAL_HOURS_DATASET_KEY = "planning.actual_hours_snapshot.workbook"
_INPUT_BUNDLE_DATASET_KEY = "planning.input_bundle.doc"

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
