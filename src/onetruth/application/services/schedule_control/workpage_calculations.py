from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

from onetruth.application.services.workpage_descriptors import (
    DRIVER_PREFERENCES_ARTIFACT_KIND,
)
from onetruth.application.services.schedule_control.driver_preferences_workbook import (
    annotate_driver_preferences_projection,
    driver_preference_value_for_service_date,
)

from .bundle_builder import DriverAvailability, WeeklyScheduleControlBundle
from .bundle_builder import build_weekly_schedule_control_bundle
from .planning_state import PartialWeeklyScheduleState, ScheduledAssignment
from .route_slot_requirements import RouteSlotRequirement
from .validation import evaluate_hard_constraints


SCHEDULE_CALCULATION_SNAPSHOT_DATASET_KEY = "planning.schedule_calculation_snapshot.json"
SCHEDULE_ROUTE_SLOT_REQUIREMENTS_DATASET_KEY = "planning.route_slot_requirements.workbook"
SCHEDULE_APPROVED_AVAILABILITY_DATASET_KEY = "planning.approved_availability.workbook"
SCHEDULE_DRIVER_CAPABILITIES_DATASET_KEY = "planning.driver_capabilities.workbook"
SCHEDULE_ACTUAL_HOURS_DATASET_KEY = "planning.actual_hours_snapshot.workbook"
SCHEDULE_SELECTED_DAY_FALLBACK = "2026-03-24"

_DEPENDENCY_SPECS: tuple[tuple[str, str, str], ...] = (
    ("route_slot_requirements", SCHEDULE_ROUTE_SLOT_REQUIREMENTS_DATASET_KEY, "hard"),
    ("approved_availability", SCHEDULE_APPROVED_AVAILABILITY_DATASET_KEY, "hard"),
    ("driver_capabilities", SCHEDULE_DRIVER_CAPABILITIES_DATASET_KEY, "hard"),
    ("actual_hours", SCHEDULE_ACTUAL_HOURS_DATASET_KEY, "hard"),
    ("driver_preferences", DRIVER_PREFERENCES_ARTIFACT_KIND, "soft"),
)
_HARD_DEPENDENCY_KEYS = frozenset(
    dependency_key
    for dependency_key, _artifact_kind, impact_class in _DEPENDENCY_SPECS
    if impact_class == "hard"
)
_BLOCKED_AVAILABILITY_STATES = frozenset(
    {"approved_unavailable", "pattern_off", "emergency_only"}
)
_PREFERENCE_WARNING_STATES = frozenset(
    {"prefer_not_to_work", "definitely_can_not_work"}
)


@dataclass(frozen=True)
class ScheduleDependencyProjection:
    dependency_state: str
    dependencies: list[dict[str, Any]]


def build_schedule_dependency_manifest_from_bundle(
    bundle: WeeklyScheduleControlBundle,
) -> list[dict[str, Any]]:
    referenced_by_dataset = {
        str(item.get("dataset_key") or "").strip(): str(item.get("artifact_version_id") or "").strip()
        for item in bundle.referenced_artifacts
        if str(item.get("dataset_key") or "").strip()
    }
    return [
        {
            "dependency_key": dependency_key,
            "artifact_kind": artifact_kind,
            "artifact_version_id": (
                referenced_by_dataset.get(artifact_kind) or None
            ),
            "impact_class": impact_class,
            "source_ref": _artifact_source_ref_by_id(referenced_by_dataset.get(artifact_kind)),
        }
        for dependency_key, artifact_kind, impact_class in _DEPENDENCY_SPECS
    ]


def normalize_schedule_dependency_manifest(raw_manifest: object) -> list[dict[str, Any]]:
    rows_by_key: dict[str, dict[str, Any]] = {}
    if isinstance(raw_manifest, list):
        for row in raw_manifest:
            if not isinstance(row, Mapping):
                continue
            dependency_key = _normalized_text(row.get("dependency_key"))
            if not dependency_key:
                continue
            rows_by_key[dependency_key] = dict(row)

    normalized: list[dict[str, Any]] = []
    for dependency_key, artifact_kind, impact_class in _DEPENDENCY_SPECS:
        source = rows_by_key.get(dependency_key, {})
        normalized.append(
            {
                "dependency_key": dependency_key,
                "artifact_kind": artifact_kind,
                "artifact_version_id": _optional_text(source.get("artifact_version_id")),
                "impact_class": impact_class,
                "source_ref": _optional_text(source.get("source_ref")),
            }
        )
    return normalized


def latest_schedule_dependency_artifacts(
    artifacts: list[dict[str, Any]],
) -> dict[str, dict[str, Any] | None]:
    by_key: dict[str, dict[str, Any] | None] = {
        dependency_key: None for dependency_key, _artifact_kind, _impact_class in _DEPENDENCY_SPECS
    }
    for artifact in artifacts:
        artifact_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "").strip()
        if not artifact_kind:
            continue
        for dependency_key, expected_kind, _impact_class in _DEPENDENCY_SPECS:
            if artifact_kind == expected_kind:
                by_key[dependency_key] = artifact
    return by_key


def resolve_schedule_dependency_artifacts(
    *,
    workflow_run_id: str,
    artifacts: list[dict[str, Any]],
    dependency_manifest: object,
) -> dict[str, dict[str, Any] | None]:
    manifest = normalize_schedule_dependency_manifest(dependency_manifest)
    artifacts_by_id = {
        str(item.get("artifact_version_id") or ""): item
        for item in artifacts
        if str(item.get("artifact_version_id") or "").strip()
    }
    resolved: dict[str, dict[str, Any] | None] = {}
    for row in manifest:
        dependency_key = str(row["dependency_key"])
        artifact_version_id = _optional_text(row.get("artifact_version_id"))
        artifact_kind = str(row["artifact_kind"])
        artifact = artifacts_by_id.get(artifact_version_id or "")
        if artifact is None:
            resolved[dependency_key] = None
            continue
        if str(artifact.get("workflow_run_id") or "") != workflow_run_id:
            resolved[dependency_key] = None
            continue
        resolved_kind = str(artifact.get("artifact_kind") or artifact.get("dataset_key") or "")
        if resolved_kind != artifact_kind:
            resolved[dependency_key] = None
            continue
        resolved[dependency_key] = artifact
    return resolved


def build_schedule_bundle_from_dependencies(
    *,
    workflow_run: Mapping[str, Any],
    dependency_artifacts_by_key: Mapping[str, Mapping[str, Any] | None],
) -> WeeklyScheduleControlBundle:
    route_slot_requirements_artifact = dependency_artifacts_by_key.get("route_slot_requirements")
    driver_capabilities_artifact = dependency_artifacts_by_key.get("driver_capabilities")
    if route_slot_requirements_artifact is None or driver_capabilities_artifact is None:
        raise ValueError("pinned schedule dependency manifest is missing required Stage04 artifacts")
    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=route_slot_requirements_artifact,
        driver_capabilities_artifact=driver_capabilities_artifact,
        approved_availability_artifact=dependency_artifacts_by_key.get("approved_availability"),
        actual_hours_artifact=dependency_artifacts_by_key.get("actual_hours"),
        route_horizon_artifact=None,
    )


def project_schedule_dependency_state(
    *,
    dependency_manifest: object,
    artifacts: list[dict[str, Any]],
) -> ScheduleDependencyProjection:
    manifest = normalize_schedule_dependency_manifest(dependency_manifest)
    latest_by_key = latest_schedule_dependency_artifacts(artifacts)
    artifacts_by_id = {
        str(item.get("artifact_version_id") or ""): item
        for item in artifacts
        if str(item.get("artifact_version_id") or "").strip()
    }
    rows: list[dict[str, Any]] = []
    for manifest_row in manifest:
        dependency_key = str(manifest_row["dependency_key"])
        artifact_kind = str(manifest_row["artifact_kind"])
        pinned_artifact_version_id = _optional_text(manifest_row.get("artifact_version_id"))
        pinned_artifact = artifacts_by_id.get(pinned_artifact_version_id or "")
        latest_artifact = latest_by_key.get(dependency_key)
        latest_artifact_version_id = _optional_text(
            latest_artifact.get("artifact_version_id") if latest_artifact is not None else None
        )
        if pinned_artifact_version_id:
            if pinned_artifact is None:
                state = "missing"
            elif latest_artifact_version_id and latest_artifact_version_id != pinned_artifact_version_id:
                state = "drifted"
            else:
                state = "aligned"
        elif latest_artifact_version_id:
            state = "not_pinned"
        else:
            state = "aligned"

        rows.append(
            {
                "dependency_key": dependency_key,
                "artifact_kind": artifact_kind,
                "artifact_version_id": pinned_artifact_version_id,
                "impact_class": str(manifest_row["impact_class"]),
                "state": state,
                "source_ref": (
                    _optional_text(manifest_row.get("source_ref"))
                    or _artifact_source_ref_by_id(pinned_artifact_version_id)
                ),
            }
        )
    return ScheduleDependencyProjection(
        dependency_state=schedule_dependency_state(rows),
        dependencies=rows,
    )


def schedule_dependency_state(dependencies: list[dict[str, Any]]) -> str:
    hard_states = [
        str(row.get("state") or "")
        for row in dependencies
        if str(row.get("impact_class") or "") == "hard"
    ]
    if any(state == "missing" for state in hard_states):
        return "missing"
    if any(state == "not_pinned" for state in hard_states):
        return "not_pinned"
    if any(state == "drifted" for state in hard_states):
        return "drifted"
    if any(str(row.get("state") or "") in {"missing", "not_pinned", "drifted"} for row in dependencies):
        return "drifted"
    return "aligned"


def schedule_preview_disabled_reason(dependencies: list[dict[str, Any]]) -> str | None:
    if _has_blocking_dependency_state(dependencies, blocked_states={"missing", "not_pinned"}):
        return "dependency_baseline_unavailable"
    return None


def schedule_save_disabled_reason(dependencies: list[dict[str, Any]]) -> str | None:
    if _has_blocking_dependency_state(dependencies, blocked_states={"missing", "not_pinned"}):
        return "dependency_baseline_unavailable"
    if _has_blocking_dependency_state(dependencies, blocked_states={"drifted"}):
        return "dependency_drift_detected"
    return None


def build_schedule_calculations(
    *,
    bundle: WeeklyScheduleControlBundle,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    driver_preferences_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    preferences_projection = annotate_driver_preferences_projection(driver_preferences_projection)
    selected_service_date = _selected_service_date(bundle)
    route_slots_by_id = {item.route_slot_id: item for item in bundle.route_slots}
    drivers_by_id = {item.driver_id: item for item in bundle.drivers}
    schedule_state = _schedule_state(
        bundle=bundle,
        assignment_rows=assignment_rows,
        route_slots_by_id=route_slots_by_id,
    )
    assigned_rows_by_date = _rows_by_service_date(assignment_rows)
    reserve_rows_by_date = _rows_by_service_date(reserve_rows)
    selected_day_available_ids = _available_driver_ids(
        bundle=bundle,
        service_date=selected_service_date,
        occupied_driver_ids=_occupied_driver_ids(
            assignment_rows=assigned_rows_by_date.get(selected_service_date, []),
            reserve_rows=reserve_rows_by_date.get(selected_service_date, []),
        ),
    )
    assignment_issues = _assignment_issues(
        bundle=bundle,
        route_slots_by_id=route_slots_by_id,
        drivers_by_id=drivers_by_id,
        schedule_state=schedule_state,
        assignment_rows=assignment_rows,
    )
    preference_conflict_driver_ids = _scheduled_preference_conflict_driver_ids(
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
        driver_preferences_projection=preferences_projection,
    )

    top_bar_days: list[dict[str, Any]] = []
    capacity_alert_dates: list[str] = []
    reserve_alert_dates: list[str] = []
    for service_date in sorted(bundle.daily_demand_by_service_date.keys()):
        demand = bundle.daily_demand_by_service_date[service_date]
        daily_assignment_rows = _assigned_rows(assigned_rows_by_date.get(service_date, []))
        daily_reserve_rows = _assigned_rows(reserve_rows_by_date.get(service_date, []))
        occupied_driver_ids = _occupied_driver_ids(
            assignment_rows=daily_assignment_rows,
            reserve_rows=daily_reserve_rows,
        )
        available_driver_ids = _available_driver_ids(
            bundle=bundle,
            service_date=service_date,
            occupied_driver_ids=occupied_driver_ids,
        )
        routes_scheduled = len(daily_assignment_rows)
        on_call_drivers = len(daily_reserve_rows)
        if routes_scheduled < int(demand.planned_route_count):
            capacity_alert_dates.append(service_date)
        if on_call_drivers < int(demand.on_call_target):
            reserve_alert_dates.append(service_date)
        top_bar_days.append(
            {
                "service_date": service_date,
                "weekday_label": _weekday_label(service_date),
                "routes_required": int(demand.planned_route_count),
                "routes_scheduled": routes_scheduled,
                "on_call_target": int(demand.on_call_target),
                "on_call_drivers": on_call_drivers,
                "total_staff": len(occupied_driver_ids),
                "excess_capacity": max(routes_scheduled + on_call_drivers - int(demand.planned_route_count), 0),
                "available_driver_count": len(available_driver_ids),
                "capacity_state": "warn" if routes_scheduled < int(demand.planned_route_count) else "pass",
            }
        )

    driver_metrics: list[dict[str, Any]] = []
    affected_driver_ids: set[str] = set()
    for driver in sorted(
        bundle.drivers,
        key=lambda item: (str(item.driver_name or item.driver_id).lower(), item.driver_id),
    ):
        route_rows = [
            row for row in assignment_rows
            if _normalized_text(row.get("assigned_driver_id")) == driver.driver_id
        ]
        on_call_rows = [
            row for row in reserve_rows
            if _normalized_text(row.get("assigned_driver_id")) == driver.driver_id
        ]
        scheduled_minutes = sum(_int_value(row.get("projected_minutes")) for row in route_rows + on_call_rows)
        issues = sorted(dict.fromkeys(assignment_issues.get(driver.driver_id, [])))
        policy_signal = bundle.policy_signals_by_driver.get(driver.driver_id)
        rolling_limit = (
            int(policy_signal.max_minutes_rolling7)
            if policy_signal is not None and int(policy_signal.max_minutes_rolling7) > 0
            else 0
        )
        projected_rolling7 = int(bundle.actual_minutes_by_driver.get(driver.driver_id, 0)) + scheduled_minutes
        if rolling_limit and projected_rolling7 > rolling_limit:
            issues.append("rolling_7_day_limit")
        if issues:
            affected_driver_ids.add(driver.driver_id)
        availability = bundle.availability_by_driver.get(driver.driver_id)
        availability_state = _availability_state(availability, selected_service_date)
        preference_state = _preference_state(
            driver_id=driver.driver_id,
            service_date=selected_service_date,
            driver_preferences_projection=preferences_projection,
        )
        driver_metrics.append(
            {
                "driver_id": driver.driver_id,
                "driver_name": driver.driver_name or driver.driver_id,
                "scheduled_hours": round(scheduled_minutes / 60.0, 2),
                "scheduled_routes": len(route_rows),
                "on_call_shifts": len(on_call_rows),
                "preference_state": preference_state,
                "availability_state": availability_state,
                "compliance_state": (
                    "fail" if issues else "pass"
                ),
                "issues": issues,
            }
        )

    checks = [
        {
            "check_id": "scheduled_capacity",
            "label": "Routes within scheduled capacity",
            "state": "warn" if capacity_alert_dates else "pass",
            "blocking": True,
            "affected_service_dates": capacity_alert_dates,
        },
        {
            "check_id": "on_call_buffer",
            "label": "On-call target coverage",
            "state": "warn" if reserve_alert_dates else "pass",
            "blocking": False,
            "affected_service_dates": reserve_alert_dates,
        },
        {
            "check_id": "hard_constraint_compliance",
            "label": "Hard assignment compliance",
            "state": "fail" if affected_driver_ids else "pass",
            "blocking": True,
            "affected_driver_ids": sorted(affected_driver_ids),
        },
        {
            "check_id": "driver_preferences_alignment",
            "label": "Driver preference alignment",
            "state": "warn" if preference_conflict_driver_ids else "pass",
            "blocking": False,
            "affected_driver_ids": sorted(preference_conflict_driver_ids),
        },
    ]

    selected_day_top_bar = next(
        (row for row in top_bar_days if row["service_date"] == selected_service_date),
        None,
    ) or {
        "service_date": selected_service_date,
        "routes_required": 0,
        "routes_scheduled": 0,
        "on_call_target": 0,
        "on_call_drivers": 0,
    }
    return {
        "top_bar": {"days": top_bar_days},
        "driver_metrics": driver_metrics,
        "checks": checks,
        "selected_day": {
            "service_date": selected_service_date,
            "routes_required": int(selected_day_top_bar.get("routes_required") or 0),
            "routes_scheduled": int(selected_day_top_bar.get("routes_scheduled") or 0),
            "on_call_target": int(selected_day_top_bar.get("on_call_target") or 0),
            "on_call_drivers": int(selected_day_top_bar.get("on_call_drivers") or 0),
            "available_driver_count": len(selected_day_available_ids),
            "available_driver_ids": selected_day_available_ids,
            "available_preference_buckets": _selected_day_available_preference_buckets(
                available_driver_ids=selected_day_available_ids,
                service_date=selected_service_date,
                driver_preferences_projection=preferences_projection,
            ),
        },
    }


def build_schedule_calculation_snapshot_payload(
    *,
    bundle: WeeklyScheduleControlBundle,
    dependency_state: str,
    dependencies: list[dict[str, Any]],
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    driver_preferences_projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "schedule_calculation_snapshot",
        "bundle_id": bundle.bundle_id,
        "dependency_state": dependency_state,
        "dependencies": [dict(item) for item in dependencies],
        "calculations": build_schedule_calculations(
            bundle=bundle,
            assignment_rows=assignment_rows,
            reserve_rows=reserve_rows,
            driver_preferences_projection=driver_preferences_projection,
        ),
    }


def build_schedule_manual_validation_summary_payload(
    *,
    bundle: WeeklyScheduleControlBundle,
    dependency_state: str,
    dependencies: list[dict[str, Any]],
    calculations: Mapping[str, Any],
) -> dict[str, Any]:
    top_bar_days = calculations.get("top_bar", {}).get("days", [])
    checks = calculations.get("checks", [])
    warnings = [
        check["label"]
        for check in checks
        if isinstance(check, Mapping) and str(check.get("state") or "") == "warn"
    ]
    violations = [
        check["label"]
        for check in checks
        if isinstance(check, Mapping) and str(check.get("state") or "") == "fail"
    ]
    return {
        "summary": {
            "bundle_id": bundle.bundle_id,
            "dependency_state": dependency_state,
            "warnings": warnings,
            "violations": violations,
            "hard_rule_result": "fail" if violations else ("warn" if warnings else "pass"),
            "coverage_summary": {
                "service_day_count": len(top_bar_days),
                "understaffed_service_dates": [
                    row["service_date"]
                    for row in top_bar_days
                    if int(row.get("routes_scheduled") or 0) < int(row.get("routes_required") or 0)
                ],
            },
            "dependencies": [dict(item) for item in dependencies],
        }
    }


def build_schedule_manual_draft_doc_payload(
    *,
    bundle: WeeklyScheduleControlBundle,
    dependency_state: str,
    calculations: Mapping[str, Any],
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "summary": {
            "bundle_id": bundle.bundle_id,
            "dependency_state": dependency_state,
            "selected_route_slot_count": len(_assigned_rows(assignment_rows)),
            "selected_on_call_count": len(_assigned_rows(reserve_rows)),
            "check_count": len(list(calculations.get("checks") or [])),
        },
        "selected_assignments": [
            {
                "service_date": _normalized_text(row.get("service_date")),
                "route_slot_id": _normalized_text(row.get("route_slot_id")),
                "assigned_driver_id": _normalized_text(row.get("assigned_driver_id")),
                "assignment_status": _normalized_text(row.get("assignment_status")),
                "projected_minutes": _int_value(row.get("projected_minutes")),
            }
            for row in _assigned_rows(assignment_rows)
        ],
        "selected_on_call_rows": [
            {
                "service_date": _normalized_text(row.get("service_date")),
                "route_slot_id": _normalized_text(row.get("route_slot_id")),
                "assigned_driver_id": _normalized_text(row.get("assigned_driver_id")),
                "assignment_status": _normalized_text(row.get("assignment_status")),
                "projected_minutes": _int_value(row.get("projected_minutes")),
            }
            for row in _assigned_rows(reserve_rows)
        ],
    }


def _has_blocking_dependency_state(
    dependencies: list[dict[str, Any]],
    *,
    blocked_states: set[str],
) -> bool:
    return any(
        str(row.get("impact_class") or "") == "hard"
        and str(row.get("state") or "") in blocked_states
        for row in dependencies
    )


def _artifact_source_ref_by_id(artifact_version_id: str | None) -> str | None:
    text = _optional_text(artifact_version_id)
    if not text:
        return None
    return f"/api/v1/artifacts/{text}"


def _selected_service_date(bundle: WeeklyScheduleControlBundle) -> str:
    if SCHEDULE_SELECTED_DAY_FALLBACK in bundle.daily_demand_by_service_date:
        return SCHEDULE_SELECTED_DAY_FALLBACK
    ordered_dates = sorted(bundle.daily_demand_by_service_date.keys())
    if not ordered_dates:
        raise ValueError("schedule bundle does not contain any service dates")
    return ordered_dates[min(2, len(ordered_dates) - 1)]


def _schedule_state(
    *,
    bundle: WeeklyScheduleControlBundle,
    assignment_rows: list[dict[str, Any]],
    route_slots_by_id: Mapping[str, RouteSlotRequirement],
) -> PartialWeeklyScheduleState:
    state = PartialWeeklyScheduleState.from_route_slots(bundle.route_slots)
    for row in assignment_rows:
        route_slot_id = _normalized_text(row.get("route_slot_id"))
        if not route_slot_id or route_slot_id not in route_slots_by_id:
            continue
        route_slot = route_slots_by_id[route_slot_id]
        assignment = ScheduledAssignment(
            route_slot_id=route_slot.route_slot_id,
            route_id=route_slot.route_id,
            service_date=route_slot.service_date,
            candidate_driver_id=_normalized_text(row.get("assigned_driver_id")),
            assignment_action="assign" if _normalized_text(row.get("assigned_driver_id")) else "unassigned",
            hard_filter_status=_normalized_text(row.get("assignment_status")) or "pass",
            hard_filter_reasons=(),
            score_bucket="manual",
            soft_score_total=0.0,
            projected_minutes=_int_value(row.get("projected_minutes")),
            fairness_balance=0.0,
            on_call_coverage=0.0,
            lost_work_credit=0.0,
            coverage_pressure=0.0,
            availability_fit=0.0,
            availability_state="",
            availability_state_fit=0.0,
            preferred_shift_band_fit=0.0,
            preferred_route_slot_class_fit=0.0,
            preference_fit=0.0,
            previous_week_stability=0.0,
            continuity_score=0.0,
            target_shift_gap=0.0,
            seniority_score=0.0,
            seniority_preference_fit=0.0,
            reliability_score=0.0,
            avoidable_assignment_score=0.0,
            current_week_shift_count=0,
            projected_rolling7_minutes=0,
            remaining_rolling7_minutes=0,
            iteration_index=_int_value(row.get("iteration_index")),
            batch_id="manual-save",
            pressure_group_id="manual-save",
            delta_kind=_normalized_text(row.get("delta_kind")) or "manual_edit",
            rationale_code="manual_edit",
            route_slot_class=route_slot.route_slot_class,
            station_code=route_slot.station_code,
            service_area=route_slot.service_area,
            planning_phase="manual_edit",
            baseline_template_state=_normalized_text(row.get("baseline_template_state")),
            planned_driver_day_state=_normalized_text(row.get("planned_driver_day_state")),
            new_agreement_required=bool(row.get("new_agreement_required")),
            new_agreement_trigger_reason=_normalized_text(row.get("new_agreement_trigger_reason")),
            template_state_preservation_fit=float(row.get("template_state_preservation_fit") or 0.0),
        )
        if assignment.assignment_action == "assign":
            state.record_assignment(assignment)
        else:
            state.record_unassigned(assignment)
    return state


def _assignment_issues(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slots_by_id: Mapping[str, RouteSlotRequirement],
    drivers_by_id: Mapping[str, Any],
    schedule_state: PartialWeeklyScheduleState,
    assignment_rows: list[dict[str, Any]],
) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = defaultdict(list)
    for row in assignment_rows:
        route_slot_id = _normalized_text(row.get("route_slot_id"))
        driver_id = _normalized_text(row.get("assigned_driver_id"))
        if not route_slot_id or not driver_id:
            continue
        route_slot = route_slots_by_id.get(route_slot_id)
        if route_slot is None:
            issues[driver_id].append("route_slot_not_in_pinned_baseline")
            continue
        driver = drivers_by_id.get(driver_id)
        if driver is None:
            issues[driver_id].append("driver_not_in_pinned_capabilities")
            continue
        validation = evaluate_hard_constraints(
            bundle=bundle,
            route_slot=route_slot,
            driver=driver,
            schedule_state=schedule_state,
            exclude_route_slot_ids={route_slot_id},
        )
        if validation.status != "pass":
            issues[driver_id].extend(validation.reasons)
    return issues


def _rows_by_service_date(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        service_date = _normalized_text(row.get("service_date"))
        if service_date:
            by_date[service_date].append(dict(row))
    return by_date


def _assigned_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if _normalized_text(row.get("assigned_driver_id"))
    ]


def _occupied_driver_ids(
    *,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
) -> set[str]:
    return {
        _normalized_text(row.get("assigned_driver_id"))
        for row in [*assignment_rows, *reserve_rows]
        if _normalized_text(row.get("assigned_driver_id"))
    }


def _available_driver_ids(
    *,
    bundle: WeeklyScheduleControlBundle,
    service_date: str,
    occupied_driver_ids: set[str],
) -> list[str]:
    available_ids: list[str] = []
    for driver in sorted(
        bundle.drivers,
        key=lambda item: (str(item.driver_name or item.driver_id).lower(), item.driver_id),
    ):
        if driver.driver_id in occupied_driver_ids:
            continue
        availability = bundle.availability_by_driver.get(driver.driver_id)
        state = _availability_state(availability, service_date)
        if state in _BLOCKED_AVAILABILITY_STATES:
            continue
        available_ids.append(driver.driver_id)
    return available_ids


def _availability_state(
    availability: DriverAvailability | None,
    service_date: str,
) -> str:
    if availability is None:
        return "unknown"
    for day_state in availability.daily_states:
        if day_state.service_date != service_date:
            continue
        return _normalized_text(day_state.normalized_state or day_state.state) or "available"
    return "available"


def _preference_state(
    *,
    driver_id: str,
    service_date: str,
    driver_preferences_projection: Mapping[str, Any] | None,
) -> str:
    return driver_preference_value_for_service_date(
        projection=driver_preferences_projection,
        driver_id=driver_id,
        service_date=service_date,
    )


def _selected_day_available_preference_buckets(
    *,
    available_driver_ids: list[str],
    service_date: str,
    driver_preferences_projection: Mapping[str, Any] | None,
) -> dict[str, list[str]]:
    buckets = {
        "open_to_work": [],
        "prefer_not_to_work": [],
        "definitely_can_not_work": [],
        "unset": [],
    }
    for driver_id in available_driver_ids:
        preference_state = _preference_state(
            driver_id=driver_id,
            service_date=service_date,
            driver_preferences_projection=driver_preferences_projection,
        )
        buckets.setdefault(preference_state, [])
        buckets[preference_state].append(driver_id)
    return buckets


def _scheduled_preference_conflict_driver_ids(
    *,
    assignment_rows: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]],
    driver_preferences_projection: Mapping[str, Any] | None,
) -> set[str]:
    if driver_preferences_projection is None:
        return set()
    conflicts: set[str] = set()
    for row in [*assignment_rows, *reserve_rows]:
        driver_id = _normalized_text(row.get("assigned_driver_id"))
        service_date = _normalized_text(row.get("service_date"))
        if not driver_id or not service_date:
            continue
        preference_state = _preference_state(
            driver_id=driver_id,
            service_date=service_date,
            driver_preferences_projection=driver_preferences_projection,
        )
        if preference_state in _PREFERENCE_WARNING_STATES:
            conflicts.add(driver_id)
    return conflicts


def _weekday_label(service_date: str) -> str:
    year, month, day = (int(part) for part in service_date.split("-"))
    # Zeller-free compact weekday mapping via datetime is overkill for this small helper.
    # The date strings here are canonical ISO values produced by schedule inputs.
    import datetime as _datetime

    return _datetime.date(year, month, day).strftime("%a")


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_text(value: Any) -> str | None:
    text = _normalized_text(value)
    return text or None


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()
