from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
from typing import Any, Iterable, Mapping

from onetruth.infrastructure.artifacts.storage import ArtifactStorageError, read_blob

from .route_slot_requirements import RouteSlotRequirement, parse_route_slot_requirements


@dataclass(frozen=True)
class DriverCapability:
    driver_id: str
    skills: tuple[str, ...]
    vehicle_certifications: tuple[str, ...]
    eligible_route_slot_classes: tuple[str, ...]
    approved_restrictions: tuple[str, ...]
    notes: str
    driver_name: str = ""
    employment_type: str = ""
    home_station: str = ""
    policy_tags: tuple[str, ...] = ()
    seniority_rank: int = 0
    attendance_reliability_index: float = 0.0
    recent_sick_calls_14d: int = 0
    recent_cancellations_14d: int = 0
    preferred_route_slot_classes: tuple[str, ...] = ()
    preferred_shift_band: str = ""
    external_driver_ref: str = ""


@dataclass(frozen=True)
class DriverServiceDayState:
    service_date: str
    state: str
    blocked_reasons: tuple[str, ...]
    actual_minutes: int
    route_id: str
    source_ref: str
    normalized_state: str = ""
    route_slot_class: str = ""
    preferred_route_slot_classes: tuple[str, ...] = ()
    avoid_route_slot_classes: tuple[str, ...] = ()
    preferred_shift_band: str = ""
    previous_week_state: str = ""
    locked_by_manager: bool = False
    call_in_sick_flag: bool = False
    cancellation_flag: bool = False
    non_working_day_flag: bool = False
    reason_code: str = ""
    reason_note: str = ""


@dataclass(frozen=True)
class DriverAvailability:
    driver_id: str
    target_shifts_per_week: int
    on_call_eligible: bool
    approved_unavailable_dates: tuple[str, ...]
    regular_pattern: tuple[str, ...]
    driver_name: str = ""
    employment_type: str = ""
    emergency_only: bool = False
    policy_tags: tuple[str, ...] = ()
    notes: str = ""
    daily_states: tuple[DriverServiceDayState, ...] = ()
    previous_week_states: tuple[DriverServiceDayState, ...] = ()


@dataclass(frozen=True)
class ActualHoursEntry:
    service_date: str
    driver_id: str
    actual_minutes: int
    route_id: str
    driver_name: str
    source_ref: str
    historical_state: str = ""
    normalized_state: str = ""
    route_slot_class: str = ""
    call_in_sick_flag: bool = False
    cancellation_flag: bool = False
    non_working_day_flag: bool = False


@dataclass(frozen=True)
class Rolling7ComplianceSnapshot:
    driver_id: str
    window_start: str
    window_end_exclusive: str
    total_minutes: int
    days_worked: int
    limit_minutes: int
    remaining_minutes: int
    status: str


@dataclass(frozen=True)
class DriverPolicySignal:
    driver_id: str
    target_shifts_per_week: int
    source_target_shifts_per_week: int
    minimum_desired_shifts_per_week: int
    avoid_overtime_after_shifts_per_week: int
    max_shifts_per_week: int
    hard_max_shifts_per_week: int | None
    max_minutes_rolling7: int
    hard_max_minutes_rolling7: int | None
    on_call_eligible: bool
    emergency_only: bool
    target_shifts_per_week_is_heuristic: bool
    max_shifts_per_week_is_heuristic: bool
    max_minutes_rolling7_is_heuristic: bool
    tags: tuple[str, ...]


@dataclass(frozen=True)
class BufferTargetRange:
    min_count: int
    preferred_count: int
    max_count: int


@dataclass(frozen=True)
class WeeklyPlanningPolicy:
    minimum_desired_shifts_per_week: int = 3
    preferred_target_shifts_per_week: int = 4
    avoid_overtime_after_shifts_per_week: int = 4
    heuristic_weekly_targets_are_soft: bool = False
    heuristic_weekly_caps_are_soft: bool = False
    heuristic_rolling7_caps_are_soft: bool = False


@dataclass(frozen=True)
class DailyDemandSummary:
    service_date: str
    planned_route_count: int
    on_call_target: int
    excess_capacity_target: int
    on_call_target_range: BufferTargetRange
    excess_capacity_target_range: BufferTargetRange
    standard_slot_count: int
    standard_early_slot_count: int
    standard_late_slot_count: int
    rescue_slot_count: int
    overflow_slot_count: int
    source_message_ids: tuple[str, ...]
    source_kind: str
    change_kind: str


@dataclass(frozen=True)
class WeeklyScheduleControlBundle:
    bundle_id: str
    workflow_run_id: str
    planning_week_id: str
    trigger_type: str
    scope_start: str
    scope_end_exclusive: str
    planning_policy: WeeklyPlanningPolicy
    route_slots: tuple[RouteSlotRequirement, ...]
    drivers: tuple[DriverCapability, ...]
    availability_by_driver: dict[str, DriverAvailability]
    actual_minutes_by_driver: dict[str, int]
    actual_entries_by_driver: dict[str, tuple[ActualHoursEntry, ...]]
    daily_demand_by_service_date: dict[str, DailyDemandSummary]
    rolling_7_compliance_by_driver: dict[str, Rolling7ComplianceSnapshot]
    policy_signals_by_driver: dict[str, DriverPolicySignal]
    referenced_artifacts: tuple[dict[str, str], ...]
    planner_notes: tuple[str, ...]
    external_evidence_refs: tuple[str, ...]


def build_weekly_schedule_control_bundle(
    *,
    workflow_run: Mapping[str, Any],
    route_slot_requirements_artifact: Mapping[str, Any],
    driver_capabilities_artifact: Mapping[str, Any],
    approved_availability_artifact: Mapping[str, Any] | None = None,
    actual_hours_artifact: Mapping[str, Any] | None = None,
    route_horizon_artifact: Mapping[str, Any] | None = None,
    trigger_type: str = "weekly_build",
) -> WeeklyScheduleControlBundle:
    planning_week_id = str(workflow_run.get("partition_key") or "")
    workflow_run_id = str(workflow_run.get("workflow_run_id") or "")
    if not workflow_run_id:
        raise ValueError("workflow_run_id is required for weekly schedule-control bundle")
    if not planning_week_id.startswith("PW-"):
        raise ValueError(
            "weekly schedule-control bundle requires PlanningWeekID partition key "
            f"(got {planning_week_id!r})"
        )

    scope_start_date, scope_end_exclusive_date = _resolve_weekly_scope_bounds(
        planning_week_id=planning_week_id,
        artifacts=(
            route_slot_requirements_artifact,
            driver_capabilities_artifact,
            approved_availability_artifact,
            actual_hours_artifact,
            route_horizon_artifact,
        ),
    )

    route_slots = _parse_route_slots(route_slot_requirements_artifact)
    if not route_slots:
        raise ValueError("route_slot_requirements artifact does not contain any route slots")
    _validate_route_slot_service_dates(
        route_slots=route_slots,
        scope_start=scope_start_date,
        scope_end_exclusive=scope_end_exclusive_date,
        artifact_label=_artifact_label(route_slot_requirements_artifact),
    )

    drivers = _parse_driver_capabilities(driver_capabilities_artifact)
    if not drivers:
        raise ValueError("driver_capabilities artifact does not contain any drivers")

    actual_entries_by_driver, actual_minutes_by_driver = _parse_actual_hours(actual_hours_artifact)
    availability_by_driver = _parse_approved_availability(
        approved_availability_artifact,
        planning_week_start=scope_start_date,
        planning_week_end_exclusive=scope_end_exclusive_date,
        actual_entries_by_driver=actual_entries_by_driver,
    )
    daily_demand_by_service_date = _parse_daily_demand_summary(
        route_slot_requirements_artifact=route_slot_requirements_artifact,
        route_slots=route_slots,
        scope_start=scope_start_date,
        scope_end_exclusive=scope_end_exclusive_date,
    )
    planning_policy = _parse_planning_policy(route_slot_requirements_artifact)
    policy_signals_by_driver = _build_policy_signals(
        drivers=drivers,
        availability_by_driver=availability_by_driver,
        planning_policy=planning_policy,
    )
    rolling_7_compliance_by_driver = _build_rolling_7_snapshots(
        planning_week_start=scope_start_date,
        actual_entries_by_driver=actual_entries_by_driver,
        policy_signals_by_driver=policy_signals_by_driver,
    )

    referenced_artifacts = _referenced_artifacts(
        route_horizon_artifact=route_horizon_artifact,
        approved_availability_artifact=approved_availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
        route_slot_requirements_artifact=route_slot_requirements_artifact,
        driver_capabilities_artifact=driver_capabilities_artifact,
    )

    bundle_id = _stable_bundle_id(
        planning_week_id=planning_week_id,
        route_slot_requirements_artifact_version_id=str(
            route_slot_requirements_artifact.get("artifact_version_id") or ""
        ),
        driver_capabilities_artifact_version_id=str(
            driver_capabilities_artifact.get("artifact_version_id") or ""
        ),
        approved_availability_artifact_version_id=(
            str(approved_availability_artifact.get("artifact_version_id") or "")
            if approved_availability_artifact is not None
            else ""
        ),
        actual_hours_artifact_version_id=(
            str(actual_hours_artifact.get("artifact_version_id") or "")
            if actual_hours_artifact is not None
            else ""
        ),
    )

    planner_notes, external_evidence_refs = _bundle_notes(
        route_horizon_artifact=route_horizon_artifact,
        approved_availability_artifact=approved_availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
    )

    return WeeklyScheduleControlBundle(
        bundle_id=bundle_id,
        workflow_run_id=workflow_run_id,
        planning_week_id=planning_week_id,
        trigger_type=str(trigger_type),
        scope_start=scope_start_date.isoformat(),
        scope_end_exclusive=scope_end_exclusive_date.isoformat(),
        planning_policy=planning_policy,
        route_slots=route_slots,
        drivers=drivers,
        availability_by_driver=availability_by_driver,
        actual_minutes_by_driver=actual_minutes_by_driver,
        actual_entries_by_driver=actual_entries_by_driver,
        daily_demand_by_service_date=daily_demand_by_service_date,
        rolling_7_compliance_by_driver=rolling_7_compliance_by_driver,
        policy_signals_by_driver=policy_signals_by_driver,
        referenced_artifacts=referenced_artifacts,
        planner_notes=planner_notes,
        external_evidence_refs=external_evidence_refs,
    )


def _parse_route_slots(artifact: Mapping[str, Any]) -> tuple[RouteSlotRequirement, ...]:
    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    return parse_route_slot_requirements(columns=columns, rows=rows)


def _parse_driver_capabilities(artifact: Mapping[str, Any]) -> tuple[DriverCapability, ...]:
    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    parsed: list[DriverCapability] = []
    for row in _rows_to_dicts(columns=columns, rows=rows):
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue
        parsed.append(
            DriverCapability(
                driver_id=driver_id,
                skills=_csv_tokens(row.get("skills")),
                vehicle_certifications=_csv_tokens(row.get("vehicle_certifications")),
                eligible_route_slot_classes=_csv_tokens(row.get("eligible_route_slot_classes")),
                approved_restrictions=_csv_tokens(row.get("approved_restrictions")),
                notes=str(row.get("notes") or "").strip(),
                driver_name=str(row.get("driver_name") or "").strip(),
                employment_type=str(row.get("employment_type") or "").strip(),
                home_station=str(row.get("home_station") or "").strip(),
                policy_tags=_csv_tokens(row.get("policy_tags")),
                seniority_rank=_coerce_int(row.get("seniority_rank"), default=0),
                attendance_reliability_index=_coerce_float(
                    row.get("attendance_reliability_index"),
                    default=0.0,
                ),
                recent_sick_calls_14d=_coerce_int(row.get("recent_sick_calls_14d"), default=0),
                recent_cancellations_14d=_coerce_int(
                    row.get("recent_cancellations_14d"),
                    default=0,
                ),
                preferred_route_slot_classes=_csv_tokens(row.get("preferred_route_slot_classes")),
                preferred_shift_band=str(row.get("preferred_shift_band") or "").strip(),
                external_driver_ref=str(row.get("external_driver_ref") or "").strip(),
            )
        )

    return tuple(sorted(parsed, key=lambda item: item.driver_id))


def _parse_approved_availability(
    artifact: Mapping[str, Any] | None,
    *,
    planning_week_start: date,
    planning_week_end_exclusive: date,
    actual_entries_by_driver: Mapping[str, tuple[ActualHoursEntry, ...]],
) -> dict[str, DriverAvailability]:
    if artifact is None:
        return {}

    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    row_dicts = _rows_to_dicts(columns=columns, rows=rows)
    if "service_date" in set(columns) and "availability_state" in set(columns):
        return _parse_explicit_driver_day_availability(
            rows=row_dicts,
            planning_week_start=planning_week_start,
            planning_week_end_exclusive=planning_week_end_exclusive,
            actual_entries_by_driver=actual_entries_by_driver,
            artifact_label=_artifact_label(artifact),
        )

    parsed: dict[str, DriverAvailability] = {}
    for row in row_dicts:
        driver_id = str(row.get("driver_id") or "").strip()
        if not driver_id:
            continue

        target_shifts_per_week = _coerce_int(row.get("target_shifts_per_week"), default=4)
        on_call_eligible = _coerce_bool(row.get("on_call_eligible"))
        emergency_only = _coerce_bool(row.get("emergency_only"))
        approved_unavailable_dates = _csv_tokens(row.get("approved_unavailable_dates"))
        regular_pattern = _csv_tokens(row.get("regular_pattern"))
        previous_week_blocked_dates = _csv_tokens(row.get("previous_week_blocked_dates"))

        parsed[driver_id] = DriverAvailability(
            driver_id=driver_id,
            target_shifts_per_week=max(target_shifts_per_week, 1),
            on_call_eligible=on_call_eligible,
            approved_unavailable_dates=approved_unavailable_dates,
            regular_pattern=regular_pattern,
            driver_name=str(row.get("driver_name") or "").strip(),
            employment_type=str(row.get("employment_type") or "").strip(),
            emergency_only=emergency_only,
            policy_tags=_csv_tokens(row.get("policy_tags")),
            notes=str(row.get("notes") or "").strip(),
            daily_states=_derive_planning_week_states(
                driver_id=driver_id,
                planning_week_start=planning_week_start,
                planning_week_end_exclusive=planning_week_end_exclusive,
                regular_pattern=regular_pattern,
                approved_unavailable_dates=approved_unavailable_dates,
                emergency_only=emergency_only,
            ),
            previous_week_states=_derive_previous_week_states(
                driver_id=driver_id,
                planning_week_start=planning_week_start,
                regular_pattern=regular_pattern,
                previous_week_blocked_dates=previous_week_blocked_dates,
                actual_entries=actual_entries_by_driver.get(driver_id, ()),
            ),
        )
    return parsed


def _parse_explicit_driver_day_availability(
    *,
    rows: list[dict[str, Any]],
    planning_week_start: date,
    planning_week_end_exclusive: date,
    actual_entries_by_driver: Mapping[str, tuple[ActualHoursEntry, ...]],
    artifact_label: str,
) -> dict[str, DriverAvailability]:
    _validate_explicit_service_date_rows(
        rows=rows,
        scope_start=planning_week_start,
        scope_end_exclusive=planning_week_end_exclusive,
        artifact_label=artifact_label,
    )
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        driver_id = str(row.get("driver_id") or "").strip()
        service_date = str(row.get("service_date") or "").strip()
        if not driver_id or not service_date:
            continue
        raw_state = str(row.get("availability_state") or "").strip().upper()
        normalized_state = _normalized_availability_state(raw_state)
        source_exception_id = str(row.get("source_exception_id") or "").strip()
        record = grouped.setdefault(
            driver_id,
            {
                "driver_id": driver_id,
                "driver_name": str(row.get("driver_name") or "").strip(),
                "employment_type": str(row.get("employment_type") or "").strip(),
                "target_shifts_per_week": _coerce_int(row.get("target_shifts_per_week"), default=4),
                "on_call_eligible": _coerce_bool(row.get("on_call_eligible")),
                "approved_unavailable_dates": [],
                "regular_pattern": [],
                "emergency_only": False,
                "policy_tags": [],
                "notes": str(row.get("notes") or "").strip(),
                "daily_states": [],
            },
        )

        if normalized_state == "approved_unavailable" and not source_exception_id:
            record["approved_unavailable_dates"].append(service_date)
        elif normalized_state != "pattern_off":
            record["regular_pattern"].append(_weekday_token(date.fromisoformat(service_date)))
        if normalized_state == "emergency_only":
            record["emergency_only"] = True

        if not record["driver_name"] and str(row.get("driver_name") or "").strip():
            record["driver_name"] = str(row.get("driver_name") or "").strip()
        if not record["employment_type"] and str(row.get("employment_type") or "").strip():
            record["employment_type"] = str(row.get("employment_type") or "").strip()
        if str(row.get("notes") or "").strip():
            record["notes"] = str(row.get("notes") or "").strip()

        record["daily_states"].append(
            DriverServiceDayState(
                service_date=service_date,
                state=raw_state,
                normalized_state=normalized_state,
                blocked_reasons=_blocked_reasons_for_normalized_state(normalized_state),
                actual_minutes=0,
                route_id="",
                source_ref=(
                    f"availability_exception:{source_exception_id}"
                    if source_exception_id
                    else f"availability:{driver_id}:{service_date}"
                ),
                preferred_route_slot_classes=_csv_tokens(row.get("preferred_route_slot_classes")),
                avoid_route_slot_classes=_csv_tokens(row.get("avoid_route_slot_classes")),
                preferred_shift_band=str(row.get("preferred_shift_band") or "").strip(),
                previous_week_state=_normalized_previous_week_state_label(
                    row.get("previous_week_state") or row.get("previous_week_same_day_state")
                ),
                locked_by_manager=_coerce_bool(row.get("locked_by_manager")),
                reason_code=str(row.get("reason_code") or "").strip(),
                reason_note=str(row.get("reason_note") or "").strip(),
            )
        )

    parsed: dict[str, DriverAvailability] = {}
    for driver_id, record in grouped.items():
        daily_states = tuple(
            sorted(
                record["daily_states"],
                key=lambda item: item.service_date,
            )
        )
        parsed[driver_id] = DriverAvailability(
            driver_id=driver_id,
            target_shifts_per_week=max(int(record["target_shifts_per_week"]), 1),
            on_call_eligible=bool(record["on_call_eligible"]),
            approved_unavailable_dates=tuple(sorted(dict.fromkeys(record["approved_unavailable_dates"]))),
            regular_pattern=tuple(dict.fromkeys(record["regular_pattern"])),
            driver_name=str(record["driver_name"]),
            employment_type=str(record["employment_type"]),
            emergency_only=bool(record["emergency_only"]),
            policy_tags=tuple(dict.fromkeys(record["policy_tags"])),
            notes=str(record["notes"]),
            daily_states=daily_states,
            previous_week_states=_derive_previous_week_states(
                driver_id=driver_id,
                planning_week_start=planning_week_start,
                regular_pattern=tuple(dict.fromkeys(record["regular_pattern"])),
                previous_week_blocked_dates=(),
                actual_entries=actual_entries_by_driver.get(driver_id, ()),
                planning_week_daily_states=daily_states,
            ),
        )

    return parsed


def _parse_actual_hours(
    artifact: Mapping[str, Any] | None,
) -> tuple[dict[str, tuple[ActualHoursEntry, ...]], dict[str, int]]:
    if artifact is None:
        return {}, {}

    metadata = _metadata_json(artifact)
    columns, rows = _extract_table(columns_key="columns", rows_key="rows", metadata=metadata)
    parsed: dict[str, list[ActualHoursEntry]] = {}
    totals: dict[str, int] = {}
    for row in _rows_to_dicts(columns=columns, rows=rows):
        driver_id = str(row.get("driver_id") or "").strip()
        service_date = str(row.get("service_date") or "").strip()
        if not driver_id or not service_date:
            continue

        actual_minutes = max(_coerce_int(row.get("actual_minutes"), default=0), 0)
        historical_state = _normalized_previous_week_state_label(row.get("historical_state"))
        entry = ActualHoursEntry(
            service_date=service_date,
            driver_id=driver_id,
            actual_minutes=actual_minutes,
            route_id=str(row.get("route_id") or "").strip(),
            driver_name=str(row.get("driver_name") or "").strip(),
            source_ref=str(
                row.get("source_snapshot_row_ref")
                or row.get("source")
                or f"actual-hours:{driver_id}:{service_date}"
            ).strip(),
            historical_state=historical_state,
            normalized_state=_normalized_previous_week_state(
                raw_state=historical_state,
                actual_minutes=actual_minutes,
                call_in_sick_flag=_coerce_bool(row.get("call_in_sick_flag")),
                cancellation_flag=_coerce_bool(row.get("cancellation_flag")),
                non_working_day_flag=_coerce_bool(row.get("non_working_day_flag")),
            ),
            route_slot_class=str(row.get("route_slot_class") or "").strip(),
            call_in_sick_flag=_coerce_bool(row.get("call_in_sick_flag")),
            cancellation_flag=_coerce_bool(row.get("cancellation_flag")),
            non_working_day_flag=_coerce_bool(row.get("non_working_day_flag")),
        )
        parsed.setdefault(driver_id, []).append(entry)
        totals[driver_id] = totals.get(driver_id, 0) + actual_minutes

    ordered = {
        driver_id: tuple(sorted(entries, key=lambda item: (item.service_date, item.route_id)))
        for driver_id, entries in parsed.items()
    }
    return ordered, totals


def _derive_planning_week_states(
    *,
    driver_id: str,
    planning_week_start: date,
    planning_week_end_exclusive: date,
    regular_pattern: tuple[str, ...],
    approved_unavailable_dates: tuple[str, ...],
    emergency_only: bool,
) -> tuple[DriverServiceDayState, ...]:
    states: list[DriverServiceDayState] = []
    unavailable_dates = set(approved_unavailable_dates)
    regular_days = set(regular_pattern)
    for current in _date_span(planning_week_start, planning_week_end_exclusive):
        current_text = current.isoformat()
        weekday = _weekday_token(current)
        if current_text in unavailable_dates:
            state = "approved_unavailable"
            blocked_reasons = ("approved_unavailable",)
        elif weekday not in regular_days:
            state = "pattern_off"
            blocked_reasons = ("pattern_off",)
        elif emergency_only:
            state = "emergency_only"
            blocked_reasons = ("emergency_only",)
        else:
            state = "available"
            blocked_reasons = ()
        states.append(
            DriverServiceDayState(
                service_date=current_text,
                state=state,
                blocked_reasons=blocked_reasons,
                actual_minutes=0,
                route_id="",
                source_ref=f"availability:{driver_id}:{current_text}",
                normalized_state=state,
            )
        )
    return tuple(states)


def _derive_previous_week_states(
    *,
    driver_id: str,
    planning_week_start: date,
    regular_pattern: tuple[str, ...],
    previous_week_blocked_dates: tuple[str, ...],
    actual_entries: tuple[ActualHoursEntry, ...],
    planning_week_daily_states: tuple[DriverServiceDayState, ...] = (),
) -> tuple[DriverServiceDayState, ...]:
    previous_week_start = planning_week_start - timedelta(days=7)
    blocked_dates = set(previous_week_blocked_dates)
    regular_days = set(regular_pattern)
    entries_by_date = {entry.service_date: entry for entry in actual_entries}
    explicit_state_by_service_date = {
        (
            date.fromisoformat(item.service_date) - timedelta(days=7)
        ).isoformat(): item.previous_week_state
        for item in planning_week_daily_states
        if item.previous_week_state
    }
    states: list[DriverServiceDayState] = []
    for current in _date_span(previous_week_start, planning_week_start):
        current_text = current.isoformat()
        entry = entries_by_date.get(current_text)
        weekday = _weekday_token(current)
        explicit_source_state = explicit_state_by_service_date.get(current_text)
        if entry is not None and (
            entry.historical_state
            or entry.route_slot_class
            or entry.call_in_sick_flag
            or entry.cancellation_flag
            or entry.non_working_day_flag
        ):
            historical_state = entry.historical_state
            if historical_state == "NA" and entry.actual_minutes > 0:
                historical_state = "WORKED"
            state = historical_state or explicit_source_state or (
                "WORKED" if entry.actual_minutes > 0 else "NA"
            )
            normalized_state = entry.normalized_state or _normalized_previous_week_state(
                raw_state=state,
                actual_minutes=entry.actual_minutes,
                call_in_sick_flag=entry.call_in_sick_flag,
                cancellation_flag=entry.cancellation_flag,
                non_working_day_flag=entry.non_working_day_flag,
            )
            blocked_reasons = _blocked_reasons_for_normalized_state(normalized_state)
            actual_minutes = entry.actual_minutes
            route_id = entry.route_id
            source_ref = entry.source_ref
            route_slot_class = entry.route_slot_class
            call_in_sick_flag = entry.call_in_sick_flag
            cancellation_flag = entry.cancellation_flag
            non_working_day_flag = entry.non_working_day_flag
        elif explicit_source_state:
            state = explicit_source_state
            normalized_state = _normalized_previous_week_state(
                raw_state=state,
                actual_minutes=0,
                call_in_sick_flag=False,
                cancellation_flag=False,
                non_working_day_flag=state == "NA",
            )
            blocked_reasons = _blocked_reasons_for_normalized_state(normalized_state)
            actual_minutes = 0
            route_id = ""
            source_ref = f"previous-week:{driver_id}:{current_text}"
            route_slot_class = ""
            call_in_sick_flag = False
            cancellation_flag = False
            non_working_day_flag = state == "NA"
        elif entry is not None:
            state = "worked"
            normalized_state = "worked"
            blocked_reasons = ()
            actual_minutes = entry.actual_minutes
            route_id = entry.route_id
            source_ref = entry.source_ref
            route_slot_class = ""
            call_in_sick_flag = False
            cancellation_flag = False
            non_working_day_flag = False
        elif current_text in blocked_dates:
            state = "blocked_previous_week"
            normalized_state = state
            blocked_reasons = ("previous_week_blocked",)
            actual_minutes = 0
            route_id = ""
            source_ref = f"previous-week:{driver_id}:{current_text}"
            route_slot_class = ""
            call_in_sick_flag = False
            cancellation_flag = False
            non_working_day_flag = False
        elif weekday in regular_days:
            state = "available_not_assigned"
            normalized_state = state
            blocked_reasons = ()
            actual_minutes = 0
            route_id = ""
            source_ref = f"previous-week:{driver_id}:{current_text}"
            route_slot_class = ""
            call_in_sick_flag = False
            cancellation_flag = False
            non_working_day_flag = False
        else:
            state = "pattern_off"
            normalized_state = state
            blocked_reasons = ("pattern_off",)
            actual_minutes = 0
            route_id = ""
            source_ref = f"previous-week:{driver_id}:{current_text}"
            route_slot_class = ""
            call_in_sick_flag = False
            cancellation_flag = False
            non_working_day_flag = True

        states.append(
            DriverServiceDayState(
                service_date=current_text,
                state=state,
                normalized_state=normalized_state,
                blocked_reasons=blocked_reasons,
                actual_minutes=actual_minutes,
                route_id=route_id,
                source_ref=source_ref,
                route_slot_class=route_slot_class,
                call_in_sick_flag=call_in_sick_flag,
                cancellation_flag=cancellation_flag,
                non_working_day_flag=non_working_day_flag,
            )
        )
    return tuple(states)


def _parse_daily_demand_summary(
    *,
    route_slot_requirements_artifact: Mapping[str, Any],
    route_slots: tuple[RouteSlotRequirement, ...],
    scope_start: date,
    scope_end_exclusive: date,
) -> dict[str, DailyDemandSummary]:
    metadata = _metadata_json(route_slot_requirements_artifact)
    columns, rows = _extract_table(
        columns_key="daily_demand_columns",
        rows_key="daily_demand_rows",
        metadata=metadata,
    )
    parsed: dict[str, DailyDemandSummary] = {}
    for row in _rows_to_dicts(columns=columns, rows=rows):
        service_date = str(row.get("service_date") or "").strip()
        if not service_date:
            continue
        if not _service_date_in_scope(
            service_date,
            scope_start=scope_start,
            scope_end_exclusive=scope_end_exclusive,
        ):
            continue
        source_message_ids = _csv_tokens(row.get("source_message_id"))
        if not source_message_ids and str(row.get("source_message_id") or "").strip():
            source_message_ids = (str(row.get("source_message_id") or "").strip(),)
        parsed[service_date] = DailyDemandSummary(
            service_date=service_date,
            planned_route_count=max(_coerce_int(row.get("planned_route_count"), default=0), 0),
            on_call_target=_buffer_target_range(
                row=row,
                min_key="on_call_min_target",
                preferred_key="on_call_preferred_target",
                max_key="on_call_max_target",
                fallback_key="on_call_target",
            ).preferred_count,
            excess_capacity_target=_buffer_target_range(
                row=row,
                min_key="excess_capacity_min_target",
                preferred_key="excess_capacity_preferred_target",
                max_key="excess_capacity_max_target",
                fallback_key="excess_capacity_target",
            ).preferred_count,
            on_call_target_range=_buffer_target_range(
                row=row,
                min_key="on_call_min_target",
                preferred_key="on_call_preferred_target",
                max_key="on_call_max_target",
                fallback_key="on_call_target",
            ),
            excess_capacity_target_range=_buffer_target_range(
                row=row,
                min_key="excess_capacity_min_target",
                preferred_key="excess_capacity_preferred_target",
                max_key="excess_capacity_max_target",
                fallback_key="excess_capacity_target",
            ),
            standard_slot_count=max(
                _coerce_int(
                    row.get("standard_slot_count"),
                    default=(
                        _coerce_int(row.get("standard_early_slot_count"), default=0)
                        + _coerce_int(row.get("standard_late_slot_count"), default=0)
                    ),
                ),
                0,
            ),
            standard_early_slot_count=max(
                _coerce_int(row.get("standard_early_slot_count"), default=0),
                0,
            ),
            standard_late_slot_count=max(
                _coerce_int(row.get("standard_late_slot_count"), default=0),
                0,
            ),
            rescue_slot_count=max(_coerce_int(row.get("rescue_slot_count"), default=0), 0),
            overflow_slot_count=max(_coerce_int(row.get("overflow_slot_count"), default=0), 0),
            source_message_ids=source_message_ids,
            source_kind=str(row.get("source_kind") or "").strip(),
            change_kind=str(row.get("change_kind") or "").strip(),
        )

    if parsed:
        return parsed

    derived: dict[str, dict[str, Any]] = {}
    for slot in route_slots:
        entry = derived.setdefault(
            slot.service_date,
            {
                "service_date": slot.service_date,
                "planned_route_count": 0,
                "on_call_target": 0,
                "excess_capacity_target": 0,
                "on_call_target_range": BufferTargetRange(0, 0, 0),
                "excess_capacity_target_range": BufferTargetRange(0, 0, 0),
                "standard_slot_count": 0,
                "standard_early_slot_count": 0,
                "standard_late_slot_count": 0,
                "rescue_slot_count": 0,
                "overflow_slot_count": 0,
                "source_message_ids": [],
                "source_kind": slot.source_kind,
                "change_kind": "",
            },
        )
        entry["planned_route_count"] += max(int(slot.required_count), 1)
        route_slot_class = str(slot.route_slot_class or "")
        if "rescue" in route_slot_class:
            entry["rescue_slot_count"] += max(int(slot.required_count), 1)
        elif "overflow" in route_slot_class:
            entry["overflow_slot_count"] += max(int(slot.required_count), 1)
        else:
            entry["standard_slot_count"] += max(int(slot.required_count), 1)
            if str(slot.preferred_shift_band or "").lower() == "early":
                entry["standard_early_slot_count"] += max(int(slot.required_count), 1)
            elif str(slot.preferred_shift_band or "").lower() == "late":
                entry["standard_late_slot_count"] += max(int(slot.required_count), 1)
        if slot.source_message_id:
            entry["source_message_ids"].append(slot.source_message_id)

    return {
        service_date: DailyDemandSummary(
            service_date=service_date,
            planned_route_count=int(values["planned_route_count"]),
            on_call_target=int(values["on_call_target"]),
            excess_capacity_target=int(values["excess_capacity_target"]),
            on_call_target_range=values["on_call_target_range"],
            excess_capacity_target_range=values["excess_capacity_target_range"],
            standard_slot_count=int(values["standard_slot_count"]),
            standard_early_slot_count=int(values["standard_early_slot_count"]),
            standard_late_slot_count=int(values["standard_late_slot_count"]),
            rescue_slot_count=int(values["rescue_slot_count"]),
            overflow_slot_count=int(values["overflow_slot_count"]),
            source_message_ids=tuple(dict.fromkeys(values["source_message_ids"])),
            source_kind=str(values["source_kind"] or ""),
            change_kind=str(values["change_kind"] or ""),
        )
        for service_date, values in sorted(derived.items())
    }


def _build_policy_signals(
    *,
    drivers: tuple[DriverCapability, ...],
    availability_by_driver: Mapping[str, DriverAvailability],
    planning_policy: WeeklyPlanningPolicy,
) -> dict[str, DriverPolicySignal]:
    signals: dict[str, DriverPolicySignal] = {}
    availability_driver_ids = set(availability_by_driver.keys())
    capability_by_driver = {driver.driver_id: driver for driver in drivers}
    for driver_id in sorted(set(capability_by_driver.keys()) | availability_driver_ids):
        capability = capability_by_driver.get(driver_id)
        availability = availability_by_driver.get(driver_id)
        source_target_shifts_per_week = (
            availability.target_shifts_per_week if availability is not None else 4
        )
        target_shifts_per_week = (
            planning_policy.preferred_target_shifts_per_week
            if planning_policy.heuristic_weekly_targets_are_soft
            else source_target_shifts_per_week
        )
        restriction_set = set(capability.approved_restrictions if capability is not None else ())
        source_max_shifts_per_week = _restriction_prefixed_int(
            restriction_set,
            prefix="max_shifts_per_week=",
        ) or source_target_shifts_per_week
        max_shifts_per_week = max(source_max_shifts_per_week, 1)
        hard_max_shifts_per_week = (
            None
            if planning_policy.heuristic_weekly_caps_are_soft
            else max_shifts_per_week
        )
        source_max_minutes_rolling7 = _restriction_prefixed_int(
            restriction_set,
            prefix="max_minutes_rolling7=",
        ) or (max(max_shifts_per_week, source_target_shifts_per_week) * 600)
        max_minutes_rolling7 = max(source_max_minutes_rolling7, 1)
        hard_max_minutes_rolling7 = (
            None
            if planning_policy.heuristic_rolling7_caps_are_soft
            else max_minutes_rolling7
        )
        tags = _unique_tokens(
            [
                *(capability.policy_tags if capability is not None else ()),
                *(availability.policy_tags if availability is not None else ()),
            ]
        )
        signals[driver_id] = DriverPolicySignal(
            driver_id=driver_id,
            target_shifts_per_week=target_shifts_per_week,
            source_target_shifts_per_week=source_target_shifts_per_week,
            minimum_desired_shifts_per_week=planning_policy.minimum_desired_shifts_per_week,
            avoid_overtime_after_shifts_per_week=planning_policy.avoid_overtime_after_shifts_per_week,
            max_shifts_per_week=max(max_shifts_per_week, 1),
            hard_max_shifts_per_week=hard_max_shifts_per_week,
            max_minutes_rolling7=max(max_minutes_rolling7, 1),
            hard_max_minutes_rolling7=hard_max_minutes_rolling7,
            on_call_eligible=bool(availability.on_call_eligible) if availability is not None else False,
            emergency_only=bool(availability.emergency_only) if availability is not None else False,
            target_shifts_per_week_is_heuristic=planning_policy.heuristic_weekly_targets_are_soft,
            max_shifts_per_week_is_heuristic=planning_policy.heuristic_weekly_caps_are_soft,
            max_minutes_rolling7_is_heuristic=planning_policy.heuristic_rolling7_caps_are_soft,
            tags=tags,
        )
    return signals


def _parse_planning_policy(artifact: Mapping[str, Any]) -> WeeklyPlanningPolicy:
    metadata = _metadata_json(artifact)
    raw = metadata.get("planning_policy")
    if not isinstance(raw, Mapping):
        return WeeklyPlanningPolicy()
    work_distribution = raw.get("work_distribution")
    if not isinstance(work_distribution, Mapping):
        work_distribution = {}
    return WeeklyPlanningPolicy(
        minimum_desired_shifts_per_week=max(
            _coerce_int(work_distribution.get("minimum_desired_shifts_per_week"), default=3),
            1,
        ),
        preferred_target_shifts_per_week=max(
            _coerce_int(work_distribution.get("preferred_target_shifts_per_week"), default=4),
            1,
        ),
        avoid_overtime_after_shifts_per_week=max(
            _coerce_int(work_distribution.get("avoid_overtime_after_shifts_per_week"), default=4),
            1,
        ),
        heuristic_weekly_targets_are_soft=_coerce_bool(
            raw.get("heuristic_weekly_targets_are_soft")
        ),
        heuristic_weekly_caps_are_soft=_coerce_bool(raw.get("heuristic_weekly_caps_are_soft")),
        heuristic_rolling7_caps_are_soft=_coerce_bool(
            raw.get("heuristic_rolling7_caps_are_soft")
        ),
    )


def _buffer_target_range(
    *,
    row: Mapping[str, Any],
    min_key: str,
    preferred_key: str,
    max_key: str,
    fallback_key: str,
) -> BufferTargetRange:
    fallback = max(_coerce_int(row.get(fallback_key), default=0), 0)
    preferred = max(_coerce_int(row.get(preferred_key), default=fallback), 0)
    minimum = max(_coerce_int(row.get(min_key), default=preferred), 0)
    maximum = max(_coerce_int(row.get(max_key), default=preferred), 0)
    if maximum < minimum:
        maximum = minimum
    preferred = min(max(preferred, minimum), maximum)
    return BufferTargetRange(
        min_count=minimum,
        preferred_count=preferred,
        max_count=maximum,
    )


def _build_rolling_7_snapshots(
    *,
    planning_week_start: date,
    actual_entries_by_driver: Mapping[str, tuple[ActualHoursEntry, ...]],
    policy_signals_by_driver: Mapping[str, DriverPolicySignal],
) -> dict[str, Rolling7ComplianceSnapshot]:
    window_start = planning_week_start - timedelta(days=7)
    window_start_text = window_start.isoformat()
    window_end_text = planning_week_start.isoformat()
    snapshots: dict[str, Rolling7ComplianceSnapshot] = {}

    for driver_id in sorted(policy_signals_by_driver.keys()):
        entries = [
            entry
            for entry in actual_entries_by_driver.get(driver_id, ())
            if window_start_text <= entry.service_date < window_end_text
        ]
        total_minutes = sum(entry.actual_minutes for entry in entries)
        days_worked = len({entry.service_date for entry in entries if entry.actual_minutes > 0})
        limit_minutes = int(policy_signals_by_driver[driver_id].max_minutes_rolling7)
        remaining_minutes = max(limit_minutes - total_minutes, 0)
        if total_minutes >= limit_minutes:
            status = "blocked"
        elif total_minutes + 480 > limit_minutes:
            status = "at_risk"
        else:
            status = "ok"

        snapshots[driver_id] = Rolling7ComplianceSnapshot(
            driver_id=driver_id,
            window_start=window_start_text,
            window_end_exclusive=window_end_text,
            total_minutes=total_minutes,
            days_worked=days_worked,
            limit_minutes=limit_minutes,
            remaining_minutes=remaining_minutes,
            status=status,
        )
    return snapshots


def _bundle_notes(
    *,
    route_horizon_artifact: Mapping[str, Any] | None,
    approved_availability_artifact: Mapping[str, Any] | None,
    actual_hours_artifact: Mapping[str, Any] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    evidence_refs: list[str] = []
    notes: list[str] = []
    for artifact in (
        route_horizon_artifact,
        approved_availability_artifact,
        actual_hours_artifact,
    ):
        if artifact is None:
            continue
        metadata = _metadata_json(artifact)
        external_refs = metadata.get("external_evidence_refs")
        if isinstance(external_refs, list):
            evidence_refs.extend(str(item) for item in external_refs if str(item).strip())
        planner_notes = metadata.get("planner_notes")
        if isinstance(planner_notes, list):
            notes.extend(str(item) for item in planner_notes if str(item).strip())

    if not notes:
        notes = [
            "Deterministic Stage04 build generated from canonical route-slot and driver-capability artifacts."
        ]
    return tuple(dict.fromkeys(notes)), tuple(dict.fromkeys(evidence_refs))


def _referenced_artifacts(
    *,
    route_horizon_artifact: Mapping[str, Any] | None,
    approved_availability_artifact: Mapping[str, Any] | None,
    actual_hours_artifact: Mapping[str, Any] | None,
    route_slot_requirements_artifact: Mapping[str, Any],
    driver_capabilities_artifact: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    ordered = [
        route_horizon_artifact,
        approved_availability_artifact,
        actual_hours_artifact,
        route_slot_requirements_artifact,
        driver_capabilities_artifact,
    ]
    refs: list[dict[str, str]] = []
    for artifact in ordered:
        if artifact is None:
            continue
        artifact_version_id = str(artifact.get("artifact_version_id") or "").strip()
        if not artifact_version_id:
            continue
        dataset_key = str(
            artifact.get("dataset_key")
            or artifact.get("artifact_kind")
            or ""
        ).strip()
        if not dataset_key:
            continue
        refs.append(
            {
                "dataset_key": dataset_key,
                "artifact_version_id": artifact_version_id,
            }
        )
    return tuple(refs)


def _stable_bundle_id(
    *,
    planning_week_id: str,
    route_slot_requirements_artifact_version_id: str,
    driver_capabilities_artifact_version_id: str,
    approved_availability_artifact_version_id: str,
    actual_hours_artifact_version_id: str,
) -> str:
    digest = hashlib.sha256(
        "|".join(
            [
                "weekly_stage04_bundle",
                planning_week_id,
                route_slot_requirements_artifact_version_id,
                driver_capabilities_artifact_version_id,
                approved_availability_artifact_version_id,
                actual_hours_artifact_version_id,
            ]
        ).encode("utf-8")
    ).hexdigest()[:10]
    return f"bundle-{planning_week_id.lower()}-stage04-{digest}"


def _planning_week_bounds(planning_week_id: str) -> tuple[date, date]:
    week_token = planning_week_id.removeprefix("PW-")
    year_text, week_text = week_token.split("-W", maxsplit=1)
    start = date.fromisocalendar(int(year_text), int(week_text), 1)
    end_exclusive = start + timedelta(days=7)
    return start, end_exclusive


def _resolve_weekly_scope_bounds(
    *,
    planning_week_id: str,
    artifacts: Iterable[Mapping[str, Any] | None],
) -> tuple[date, date]:
    explicit_bounds: dict[str, tuple[date, date]] = {}
    for artifact in artifacts:
        if artifact is None:
            continue
        bounds = _explicit_scope_bounds(artifact)
        if bounds is None:
            continue
        explicit_bounds[_artifact_label(artifact)] = bounds

    if not explicit_bounds:
        return _planning_week_bounds(planning_week_id)

    unique_bounds = {bounds for bounds in explicit_bounds.values()}
    if len(unique_bounds) != 1:
        details = ", ".join(
            f"{label}={bounds[0].isoformat()}..{bounds[1].isoformat()}"
            for label, bounds in sorted(explicit_bounds.items())
        )
        raise ValueError(
            "weekly Stage04 input artifacts declare conflicting explicit scope bounds: "
            f"{details}"
        )
    return next(iter(unique_bounds))


def _explicit_scope_bounds(artifact: Mapping[str, Any]) -> tuple[date, date] | None:
    metadata = _metadata_json(artifact)
    scope_start_text = str(metadata.get("scope_start") or "").strip()
    scope_end_text = str(metadata.get("scope_end_exclusive") or "").strip()
    if not scope_start_text and not scope_end_text:
        return None
    if not scope_start_text or not scope_end_text:
        raise ValueError(
            f"{_artifact_label(artifact)} must declare both scope_start and "
            "scope_end_exclusive when either explicit scope bound is present"
        )
    scope_start = _parse_service_date(scope_start_text, context=f"{_artifact_label(artifact)} scope_start")
    scope_end_exclusive = _parse_service_date(
        scope_end_text,
        context=f"{_artifact_label(artifact)} scope_end_exclusive",
    )
    if scope_end_exclusive <= scope_start:
        raise ValueError(
            f"{_artifact_label(artifact)} must declare scope_end_exclusive after scope_start "
            f"(got {scope_start_text}..{scope_end_text})"
        )
    return scope_start, scope_end_exclusive


def _validate_route_slot_service_dates(
    *,
    route_slots: tuple[RouteSlotRequirement, ...],
    scope_start: date,
    scope_end_exclusive: date,
    artifact_label: str,
) -> None:
    out_of_scope_dates = sorted(
        {
            route_slot.service_date
            for route_slot in route_slots
            if not _service_date_in_scope(
                route_slot.service_date,
                scope_start=scope_start,
                scope_end_exclusive=scope_end_exclusive,
            )
        }
    )
    if out_of_scope_dates:
        raise ValueError(
            f"{artifact_label} contains route-slot service_date values outside resolved weekly "
            f"scope {scope_start.isoformat()}..{scope_end_exclusive.isoformat()}: "
            f"{out_of_scope_dates}"
        )


def _validate_explicit_service_date_rows(
    *,
    rows: list[dict[str, Any]],
    scope_start: date,
    scope_end_exclusive: date,
    artifact_label: str,
) -> None:
    out_of_scope_dates = sorted(
        {
            service_date
            for row in rows
            for service_date in [str(row.get("service_date") or "").strip()]
            if service_date
            and not _service_date_in_scope(
                service_date,
                scope_start=scope_start,
                scope_end_exclusive=scope_end_exclusive,
            )
        }
    )
    if out_of_scope_dates:
        raise ValueError(
            f"{artifact_label} contains explicit availability service_date values outside "
            f"resolved weekly scope {scope_start.isoformat()}..{scope_end_exclusive.isoformat()}: "
            f"{out_of_scope_dates}"
        )


def _service_date_in_scope(
    service_date_text: str,
    *,
    scope_start: date,
    scope_end_exclusive: date,
) -> bool:
    service_date = _parse_service_date(service_date_text, context="service_date")
    return scope_start <= service_date < scope_end_exclusive


def _parse_service_date(value: str, *, context: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{context} must be an ISO date (got {value!r})") from exc


def _artifact_label(artifact: Mapping[str, Any]) -> str:
    return str(
        artifact.get("dataset_key")
        or artifact.get("artifact_kind")
        or artifact.get("artifact_version_id")
        or "artifact"
    ).strip()


def _metadata_json(artifact: Mapping[str, Any]) -> dict[str, Any]:
    metadata = artifact.get("metadata_json")
    if isinstance(metadata, dict):
        if _is_generic_frontend_upload_metadata(metadata):
            parsed = _parsed_json_blob_metadata(artifact)
            if parsed is not None:
                return parsed
        return metadata
    parsed = _parsed_json_blob_metadata(artifact)
    if parsed is not None:
        return parsed
    raise ValueError(
        "artifact metadata_json must be a JSON object "
        f"(artifact_version_id={artifact.get('artifact_version_id')})"
    )


def _is_generic_frontend_upload_metadata(metadata: Mapping[str, Any]) -> bool:
    generic_keys = {
        "original_file_name",
        "uploaded_via",
        "subject_kind",
        "subject_id",
        "ingress_file_name",
        "ingress_media_type",
        "ingress_kind",
    }
    metadata_keys = {str(key) for key in metadata.keys()}
    if not metadata_keys:
        return True
    return metadata_keys.issubset(generic_keys)


def _parsed_json_blob_metadata(artifact: Mapping[str, Any]) -> dict[str, Any] | None:
    storage_uri = str(artifact.get("storage_uri") or "").strip()
    if not storage_uri:
        return None
    try:
        blob = read_blob(storage_uri)
    except ArtifactStorageError:
        return None
    try:
        parsed = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_table(
    *,
    columns_key: str,
    rows_key: str,
    metadata: Mapping[str, Any],
) -> tuple[list[str], list[Any]]:
    columns = metadata.get(columns_key)
    rows = metadata.get(rows_key)

    if isinstance(columns, list) and isinstance(rows, list):
        return [str(item) for item in columns], list(rows)

    nested_bundle = metadata.get("bundle")
    if isinstance(nested_bundle, Mapping):
        columns = nested_bundle.get(columns_key)
        rows = nested_bundle.get(rows_key)
        if isinstance(columns, list) and isinstance(rows, list):
            return [str(item) for item in columns], list(rows)

    return [], []


def _rows_to_dicts(*, columns: list[str], rows: Iterable[Any]) -> list[dict[str, Any]]:
    normalized_columns = [str(column).strip() for column in columns]
    result: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            item = {str(key).strip(): value for key, value in row.items()}
        elif isinstance(row, (list, tuple)):
            item = {
                normalized_columns[index]: value
                for index, value in enumerate(row)
                if index < len(normalized_columns)
            }
        else:
            continue
        result.append(item)
    return result


def _csv_tokens(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    else:
        tokens = [part.strip() for part in str(value).split(",") if part.strip()]
    return tuple(tokens)


def _unique_tokens(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in values if str(item).strip()))


def _coerce_int(value: Any, *, default: int) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_float(value: Any, *, default: float) -> float:
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _normalized_previous_week_state_label(value: Any) -> str:
    token = str(value or "").strip().upper()
    if not token or token == "BLANK":
        return "NA"
    return token


def _normalized_availability_state(value: str) -> str:
    token = str(value or "").strip().upper()
    if token == "PREFERRED":
        return "available"
    if token == "AVAILABLE":
        return "available"
    if token == "AVOID_IF_POSSIBLE":
        return "available"
    if token == "ON_CALL_ONLY":
        return "available"
    if token == "CANNOT":
        return "approved_unavailable"
    return token.lower() if token else "unknown"


def _normalized_previous_week_state(
    *,
    raw_state: str,
    actual_minutes: int,
    call_in_sick_flag: bool,
    cancellation_flag: bool,
    non_working_day_flag: bool,
) -> str:
    token = _normalized_previous_week_state_label(raw_state)
    if token == "WORKED":
        return "worked"
    if token in {"ON_CALL", "DISPATCH"}:
        return "worked" if actual_minutes > 0 else "available_not_assigned"
    if token in {"SICK_CALL", "CANCELLED"} or call_in_sick_flag or cancellation_flag:
        return "blocked_previous_week"
    if actual_minutes > 0:
        return "worked"
    if token == "NA" or non_working_day_flag:
        return "pattern_off"
    return "available_not_assigned"


def _blocked_reasons_for_normalized_state(normalized_state: str) -> tuple[str, ...]:
    if normalized_state == "approved_unavailable":
        return ("approved_unavailable",)
    if normalized_state == "pattern_off":
        return ("pattern_off",)
    if normalized_state == "emergency_only":
        return ("emergency_only",)
    if normalized_state == "blocked_previous_week":
        return ("previous_week_blocked",)
    return ()


def _restriction_prefixed_int(restrictions: set[str], *, prefix: str) -> int | None:
    for restriction in restrictions:
        if not restriction.startswith(prefix):
            continue
        try:
            return int(restriction.removeprefix(prefix))
        except ValueError:
            return None
    return None


def _date_span(start: date, end_exclusive: date) -> list[date]:
    cursor = start
    values: list[date] = []
    while cursor < end_exclusive:
        values.append(cursor)
        cursor += timedelta(days=1)
    return values


def _weekday_token(current: date) -> str:
    return current.strftime("%a")
