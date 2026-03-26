from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
)
from onetruth.application.services.schedule_control import (
    WeeklyScheduleControlBundle,
    build_weekly_schedule_control_bundle,
)
from onetruth.application.services.schedule_control.stage04_input_registry import (
    resolve_weekly_stage04_input_artifacts,
)
from onetruth.infrastructure.events.event_store import utc_now_iso


REPO_ROOT = Path(__file__).resolve().parents[4]
_ACTUAL_OPS_SOURCE_MATERIAL_PATH = (
    REPO_ROOT / "fixtures" / "logistics" / "weekly_stage04_actual_ops_lab_source_material_v3.yaml"
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


class WorkpageProjectionUnavailableError(RuntimeError):
    def __init__(
        self,
        *,
        workflow_run_id: str,
        workpage_id: str,
        message: str,
        missing_dataset_keys: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.workflow_run_id = workflow_run_id
        self.workpage_id = workpage_id
        self.missing_dataset_keys = list(missing_dataset_keys or [])


def build_demo_workpage_contract(workpage_id: str) -> dict[str, Any]:
    if workpage_id == SCHEDULE_DEMO_WORKPAGE_ID:
        return build_schedule_demo_workpage_contract()
    if workpage_id == EOD_DEMO_WORKPAGE_ID:
        return build_eod_demo_workpage_contract()
    raise DemoWorkpageNotFoundError(workpage_id)


def build_schedule_workflow_run_workpage_contract(
    *,
    workflow_run: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    workflow_run_id = _require_text(workflow_run.get("workflow_run_id"))
    try:
        resolved_inputs = resolve_weekly_stage04_input_artifacts(
            artifacts=artifacts,
            stage_spec={"required_evidence_keys": [_ROUTE_SLOT_DATASET_KEY, _DRIVER_CAPABILITIES_DATASET_KEY]},
        )
        bundle = build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=_require_mapping(
                resolved_inputs.get("route_slot_requirements"),
                field_name="route_slot_requirements",
            ),
            driver_capabilities_artifact=_require_mapping(
                resolved_inputs.get("driver_capabilities"),
                field_name="driver_capabilities",
            ),
            approved_availability_artifact=_optional_mapping(
                resolved_inputs.get("approved_availability")
            ),
            actual_hours_artifact=_optional_mapping(resolved_inputs.get("actual_hours")),
            route_horizon_artifact=None,
        )
    except CommandError as exc:
        if exc.code != "stage04_input_artifact_missing":
            raise
        missing_slots = exc.details.get("missing_slots", [])
        missing_dataset_keys = [
            _require_text(slot.get("dataset_key"))
            for slot in missing_slots
            if isinstance(slot, dict) and slot.get("dataset_key") is not None
        ]
        raise WorkpageProjectionUnavailableError(
            workflow_run_id=workflow_run_id,
            workpage_id=SCHEDULE_DEMO_WORKPAGE_ID,
            message="workflow-run-backed schedule workpage is unavailable until the weekly Stage04 inputs exist for this run",
            missing_dataset_keys=missing_dataset_keys,
        ) from exc
    except ValueError as exc:
        raise WorkpageProjectionUnavailableError(
            workflow_run_id=workflow_run_id,
            workpage_id=SCHEDULE_DEMO_WORKPAGE_ID,
            message=f"workflow-run-backed schedule workpage is unavailable: {exc}",
        ) from exc

    source_refs = _schedule_runtime_source_refs(
        resolved_inputs=resolved_inputs,
        input_bundle_artifact=_latest_artifact_for_dataset_key(
            artifacts,
            dataset_key=_INPUT_BUNDLE_DATASET_KEY,
        ),
    )
    return {
        **_build_schedule_workpage_contract(
            bundle=bundle,
            source_examples={},
            source_mode="run_projection",
            source_refs=source_refs,
            freshness_source_kind="workflow_run_projection",
            freshness_source_version=bundle.bundle_id,
            validation_warnings=[
                "This workflow-run-backed schedule projection is built from canonical weekly-planning input artifacts for the selected run.",
                "Selected-day controls are local what-if inputs only and do not claim ownership of live dispatch truth.",
            ],
        ),
        "run_context": _workflow_run_context(workflow_run),
        "draft_resolution": None,
    }


def build_schedule_demo_workpage_contract() -> dict[str, Any]:
    source_material = _load_actual_ops_source_material()
    source_examples = _source_examples(source_material)
    bundle = _schedule_demo_bundle()

    return _build_schedule_workpage_contract(
        bundle=bundle,
        source_examples=source_examples,
        source_mode="demo",
        source_refs=[
            source_examples["route_slot_requirements"],
            source_examples["approved_availability"],
            source_examples["driver_capabilities"],
            source_examples["actual_hours_snapshot"],
            source_examples["stage04_input_bundle"],
        ],
        freshness_source_kind="repo_example_bundle",
        freshness_source_version=_require_text(source_material.get("fixture_contract")),
        validation_warnings=[
            "This server-owned demo query is built from repo-native weekly planning example sources.",
            "Selected-day controls are local what-if inputs only and do not claim ownership of live dispatch truth.",
        ],
    )


def _build_schedule_workpage_contract(
    *,
    bundle: WeeklyScheduleControlBundle,
    source_examples: Mapping[str, str],
    source_mode: str,
    source_refs: list[str],
    freshness_source_kind: str,
    freshness_source_version: str,
    validation_warnings: list[str],
) -> dict[str, Any]:
    return {
        "workpage": _build_schedule_workpage_view_model(
            bundle=bundle,
            source_examples=source_examples,
            validation_warnings=validation_warnings,
        ),
        "source": {
            "mode": source_mode,
            "primary_dataset_key": None,
            "source_dataset_keys": [dataset_key for _, dataset_key in _SOURCE_DATASETS],
            "source_artifact_version_id": None,
            "source_refs": source_refs,
        },
        "freshness": {
            "generated_at": utc_now_iso(),
            "source_kind": freshness_source_kind,
            "source_version": freshness_source_version,
        },
    }


def _build_schedule_workpage_view_model(
    *,
    bundle: WeeklyScheduleControlBundle,
    source_examples: Mapping[str, str],
    validation_warnings: list[str],
) -> dict[str, Any]:
    primary_demand = _sorted_daily_demand(bundle)[0]
    return {
        "workpage_id": SCHEDULE_DEMO_WORKPAGE_ID,
        "version": 2,
        "title": "Weekly schedule review",
        "mode": "example",
        "workflow_id": _SCHEDULE_WORKFLOW_ID,
        "dataset_key": _INPUT_BUNDLE_DATASET_KEY,
        "source_artifact_version_id": None,
        "source_examples": dict(source_examples),
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
            "warnings": validation_warnings,
        },
    }


def _workflow_run_context(workflow_run: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "workflow_run_id": _require_text(workflow_run.get("workflow_run_id")),
        "workflow_id": _require_text(workflow_run.get("workflow_id")),
        "workflow_version": _require_text(workflow_run.get("workflow_version")),
        "partition_key": _require_text(workflow_run.get("partition_key")),
        "logical_date": _require_text(workflow_run.get("logical_date")),
        "activation_key": _require_text(workflow_run.get("activation_key")),
        "state": _require_text(workflow_run.get("state")),
    }


def _schedule_runtime_source_refs(
    *,
    resolved_inputs: Mapping[str, Mapping[str, Any] | None],
    input_bundle_artifact: Mapping[str, Any] | None,
) -> list[str]:
    refs: list[str] = []
    for slot_key in (
        "route_slot_requirements",
        "approved_availability",
        "driver_capabilities",
        "actual_hours",
    ):
        artifact = resolved_inputs.get(slot_key)
        if artifact is None:
            continue
        ref = _artifact_detail_ref(artifact)
        if ref not in refs:
            refs.append(ref)
    if input_bundle_artifact is not None:
        input_bundle_ref = _artifact_detail_ref(input_bundle_artifact)
        if input_bundle_ref not in refs:
            refs.append(input_bundle_ref)
    return refs


def _artifact_detail_ref(artifact: Mapping[str, Any]) -> str:
    return f"/api/v1/artifacts/{_require_text(artifact.get('artifact_version_id'))}"


def _latest_artifact_for_dataset_key(
    artifacts: list[dict[str, Any]],
    *,
    dataset_key: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in artifacts:
        if str(artifact.get("dataset_key") or artifact.get("artifact_kind") or "") != dataset_key:
            continue
        latest = artifact
    return latest


def _require_mapping(
    value: Mapping[str, Any] | None,
    *,
    field_name: str,
) -> Mapping[str, Any]:
    if value is None:
        raise ValueError(f"{field_name} artifact is required")
    return value


def _optional_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    return value


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


def build_eod_artifact_workpage_contract(
    *,
    artifact_version_id: str,
    workflow_run_id: str,
    supersedes_artifact_version_id: str | None,
    superseded_by_artifact_version_id: str | None,
    latest_in_chain_artifact_version_id: str,
    download_path: str,
    projection: Mapping[str, Any],
    source_refs: list[str],
    service_date: str = _EOD_SERVICE_DATE,
    station_code: str = _EOD_STATION_CODE,
    dsp_name: str = _EOD_DSP_NAME,
    generated_at: str | None = None,
) -> dict[str, Any]:
    route_rows = _projection_rows(projection, "route_actuals")
    manual_closeout_rows = _projection_rows(projection, "manual_closeout")
    checklist_rows = _projection_rows(projection, "upd_candidates")
    quality_warning_rows = _projection_rows(projection, "quality_warnings")

    summary = _artifact_eod_summary(
        route_rows=route_rows,
        quality_warning_rows=quality_warning_rows,
        service_date=service_date,
        station_code=station_code,
        dsp_name=dsp_name,
    )
    return {
        "workpage": {
            "workpage_id": EOD_DEMO_WORKPAGE_ID,
            "version": 2,
            "title": "End-of-day report",
            "mode": "example",
            "workflow_id": _EOD_WORKFLOW_ID,
            "dataset_key": _EOD_DRAFT_DATASET_KEY,
            "source_artifact_version_id": artifact_version_id,
            "source_examples": {},
            "summary": summary,
            "sections": [
                {
                    "kind": "summary_cards",
                    "title": "Daily summary",
                    "cards": _artifact_eod_summary_cards(summary),
                },
                {
                    "kind": "note_panel",
                    "title": "Artifact-backed projection note",
                    "body": _artifact_eod_note_body(quality_warning_rows),
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
                    "rows": _artifact_eod_route_actual_rows(route_rows),
                },
                {
                    "kind": "form",
                    "title": "Manual closeout",
                    "form_id": "closeout_details",
                    "fields": _artifact_eod_form_fields(
                        route_rows=route_rows,
                        manual_closeout_rows=manual_closeout_rows,
                    ),
                },
                {
                    "kind": "checklist",
                    "title": "UPD candidate review",
                    "checklist_id": "upd_candidates",
                    "items": _artifact_eod_checklist_items(checklist_rows),
                },
                {
                    "kind": "history_stub",
                    "title": "History",
                    "entries": [
                        {
                            "label": "Current artifact version",
                            "value": artifact_version_id,
                        },
                        {
                            "label": "Supersedes",
                            "value": supersedes_artifact_version_id or "Initial draft",
                        },
                        {
                            "label": "Latest draft in chain",
                            "value": latest_in_chain_artifact_version_id,
                        },
                    ],
                },
            ],
            "validation": {
                "status": "informational",
                "warnings": _artifact_eod_validation_warnings(quality_warning_rows),
            },
        },
        "source": {
            "mode": "artifact_projection",
            "primary_dataset_key": _EOD_DRAFT_DATASET_KEY,
            "source_dataset_keys": [_EOD_DRAFT_DATASET_KEY],
            "source_artifact_version_id": artifact_version_id,
            "source_refs": source_refs,
        },
        "freshness": {
            "generated_at": generated_at or utc_now_iso(),
            "source_kind": "artifact_version",
            "source_version": artifact_version_id,
        },
        "artifact_context": {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": workflow_run_id,
            "artifact_kind": _EOD_DRAFT_DATASET_KEY,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "superseded_by_artifact_version_id": superseded_by_artifact_version_id,
            "latest_in_chain_artifact_version_id": latest_in_chain_artifact_version_id,
            "download_path": download_path,
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


def _projection_rows(projection: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    raw_rows = projection.get(key)
    if not isinstance(raw_rows, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in raw_rows:
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return rows


def _artifact_eod_summary(
    *,
    route_rows: list[dict[str, Any]],
    quality_warning_rows: list[dict[str, Any]],
    service_date: str,
    station_code: str,
    dsp_name: str,
) -> dict[str, Any]:
    packages_dispatched = sum(_int_or_zero(row.get("packages_dispatched")) for row in route_rows)
    packages_delivered = sum(_int_or_zero(row.get("packages_delivered")) for row in route_rows)
    packages_returned = sum(_int_or_zero(row.get("returns")) for row in route_rows)
    actual_minutes = [_int_or_zero(row.get("actual_minutes")) for row in route_rows]
    formula_warning = len(quality_warning_rows) > 0

    return {
        "service_date": service_date,
        "station_code": station_code,
        "dsp_name": dsp_name,
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


def _artifact_eod_summary_cards(summary: dict[str, Any]) -> list[dict[str, Any]]:
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


def _artifact_eod_note_body(quality_warning_rows: list[dict[str, Any]]) -> str:
    if not quality_warning_rows:
        return (
            "This page is projected from an immutable Stage03 reporting workbook artifact. "
            "Quality warnings are surfaced from the workbook when present, and formulas are not recomputed."
        )

    warning_messages = [
        _require_text(row.get("message"))
        for row in quality_warning_rows
        if str(row.get("message") or "").strip()
    ]
    joined = "; ".join(warning_messages[:2])
    if joined:
        return (
            "This page is projected from an immutable Stage03 reporting workbook artifact. "
            f"Workbook warnings remain visible instead of being recomputed: {joined}"
        )
    return (
        "This page is projected from an immutable Stage03 reporting workbook artifact. "
        "Workbook warnings remain visible instead of being recomputed."
    )


def _artifact_eod_route_actual_rows(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in route_rows:
        rows.append(
            {
                "route_id": str(row.get("route_id") or ""),
                "driver_name": str(row.get("driver_name") or ""),
                "packages_dispatched": _int_or_zero(row.get("packages_dispatched")),
                "packages_delivered": _int_or_zero(row.get("packages_delivered")),
                "planned_window": _optional_time_window(
                    row.get("planned_start"),
                    row.get("planned_finish"),
                ),
                "actual_window": _optional_time_window(
                    row.get("actual_start"),
                    row.get("actual_finish"),
                ),
                "actual_minutes": _int_or_zero(row.get("actual_minutes")),
                "returns": _int_or_zero(row.get("returns")),
                "return_reasons": str(row.get("return_reasons") or ""),
                "upd_candidate": _truthy_bool(row.get("upd_candidate")),
            }
        )
    return rows


def _artifact_eod_form_fields(
    *,
    route_rows: list[dict[str, Any]],
    manual_closeout_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    driver_options = _unique_driver_names(tuple(route_rows))
    manual_closeout = manual_closeout_rows[0] if manual_closeout_rows else {}
    last_clockout = str(manual_closeout.get("last_driver_clockout") or "").strip()
    if not last_clockout:
        last_clockout = _artifact_last_clockout(route_rows)
    return [
        {
            "key": "sick_calls",
            "label": "Sick calls",
            "input": "multi_select",
            "options": driver_options,
            "value": _split_workbook_multivalue(manual_closeout.get("sick_calls")),
        },
        {
            "key": "unavailable_drivers",
            "label": "Not available",
            "input": "multi_select",
            "options": driver_options,
            "value": _split_workbook_multivalue(manual_closeout.get("unavailable_drivers")),
        },
        {
            "key": "working_devices",
            "label": "Working devices / rabbits",
            "input": "text",
            "value": str(manual_closeout.get("working_devices") or ""),
        },
        {
            "key": "rescues",
            "label": "Rescues",
            "input": "repeater",
            "value": _split_workbook_multivalue(manual_closeout.get("rescues")),
        },
        {
            "key": "incidents",
            "label": "Incidents",
            "input": "repeater",
            "value": _split_workbook_multivalue(manual_closeout.get("incidents")),
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
            "value": str(manual_closeout.get("dispatcher_comment") or ""),
        },
        {
            "key": "manager_note",
            "label": "Manager note",
            "input": "textarea",
            "value": str(manual_closeout.get("manager_note") or ""),
        },
    ]


def _artifact_eod_checklist_items(upd_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in upd_rows:
        item_id = str(row.get("row_id") or "").strip()
        if not item_id:
            continue
        route_id = str(row.get("route_id") or "").strip()
        actual_minutes = _int_or_zero(row.get("actual_minutes"))
        items.append(
            {
                "item_id": item_id,
                "title": f"{str(row.get('driver_name') or '').strip()} · {route_id}".strip(" ·"),
                "detail": str(row.get("reason") or "Needs review"),
                "selected": _truthy_bool(row.get("selected")),
                "note": str(row.get("manager_note") or ""),
                "tags": [f"{actual_minutes} minutes"] if actual_minutes > 0 else [],
            }
        )
    return items


def _artifact_eod_validation_warnings(
    quality_warning_rows: list[dict[str, Any]],
) -> list[str]:
    warnings = [
        "This workpage is derived from an immutable reporting workbook artifact; the workbook remains authoritative truth.",
        "Submit creates a new superseding workbook artifact version; no in-place workbook mutation occurs.",
    ]
    if quality_warning_rows:
        warnings.append(
            "Workbook quality warnings are surfaced from the artifact directly; formulas are not recomputed in the workpage projection."
        )
    return warnings


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


def _optional_time_window(start: Any, finish: Any) -> str:
    start_text = str(start or "").strip()
    finish_text = str(finish or "").strip()
    if not start_text and not finish_text:
        return ""
    return f"{start_text} - {finish_text}".strip()


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


def _truthy_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def _int_or_zero(value: Any) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    return _require_int(value)


def _split_workbook_multivalue(value: Any) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    return [part.strip() for part in text.split("\n") if part.strip()]


def _artifact_last_clockout(route_rows: list[dict[str, Any]]) -> str:
    finishes = [
        str(row.get("actual_finish") or "").strip()
        for row in route_rows
        if str(row.get("actual_finish") or "").strip()
    ]
    return max(finishes, default="")
