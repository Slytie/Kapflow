from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
from typing import Any, Iterable, Mapping

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


@dataclass(frozen=True)
class DriverServiceDayState:
    service_date: str
    state: str
    blocked_reasons: tuple[str, ...]
    actual_minutes: int
    route_id: str
    source_ref: str


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
    max_shifts_per_week: int
    max_minutes_rolling7: int
    on_call_eligible: bool
    emergency_only: bool
    tags: tuple[str, ...]


@dataclass(frozen=True)
class DailyDemandSummary:
    service_date: str
    planned_route_count: int
    standard_slot_count: int
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

    scope_start_date, scope_end_exclusive_date = _planning_week_bounds(planning_week_id)

    route_slots = _parse_route_slots(route_slot_requirements_artifact)
    if not route_slots:
        raise ValueError("route_slot_requirements artifact does not contain any route slots")

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
    )
    policy_signals_by_driver = _build_policy_signals(
        drivers=drivers,
        availability_by_driver=availability_by_driver,
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
    parsed: dict[str, DriverAvailability] = {}
    for row in _rows_to_dicts(columns=columns, rows=rows):
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
) -> tuple[DriverServiceDayState, ...]:
    previous_week_start = planning_week_start - timedelta(days=7)
    blocked_dates = set(previous_week_blocked_dates)
    regular_days = set(regular_pattern)
    entries_by_date = {entry.service_date: entry for entry in actual_entries}
    states: list[DriverServiceDayState] = []
    for current in _date_span(previous_week_start, planning_week_start):
        current_text = current.isoformat()
        entry = entries_by_date.get(current_text)
        weekday = _weekday_token(current)
        if entry is not None:
            state = "worked"
            blocked_reasons = ()
            actual_minutes = entry.actual_minutes
            route_id = entry.route_id
            source_ref = entry.source_ref
        elif current_text in blocked_dates:
            state = "blocked_previous_week"
            blocked_reasons = ("previous_week_blocked",)
            actual_minutes = 0
            route_id = ""
            source_ref = f"previous-week:{driver_id}:{current_text}"
        elif weekday in regular_days:
            state = "available_not_assigned"
            blocked_reasons = ()
            actual_minutes = 0
            route_id = ""
            source_ref = f"previous-week:{driver_id}:{current_text}"
        else:
            state = "pattern_off"
            blocked_reasons = ("pattern_off",)
            actual_minutes = 0
            route_id = ""
            source_ref = f"previous-week:{driver_id}:{current_text}"

        states.append(
            DriverServiceDayState(
                service_date=current_text,
                state=state,
                blocked_reasons=blocked_reasons,
                actual_minutes=actual_minutes,
                route_id=route_id,
                source_ref=source_ref,
            )
        )
    return tuple(states)


def _parse_daily_demand_summary(
    *,
    route_slot_requirements_artifact: Mapping[str, Any],
    route_slots: tuple[RouteSlotRequirement, ...],
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
        source_message_ids = _csv_tokens(row.get("source_message_id"))
        if not source_message_ids and str(row.get("source_message_id") or "").strip():
            source_message_ids = (str(row.get("source_message_id") or "").strip(),)
        parsed[service_date] = DailyDemandSummary(
            service_date=service_date,
            planned_route_count=max(_coerce_int(row.get("planned_route_count"), default=0), 0),
            standard_slot_count=max(_coerce_int(row.get("standard_slot_count"), default=0), 0),
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
                "standard_slot_count": 0,
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
        if slot.source_message_id:
            entry["source_message_ids"].append(slot.source_message_id)

    return {
        service_date: DailyDemandSummary(
            service_date=service_date,
            planned_route_count=int(values["planned_route_count"]),
            standard_slot_count=int(values["standard_slot_count"]),
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
) -> dict[str, DriverPolicySignal]:
    signals: dict[str, DriverPolicySignal] = {}
    availability_driver_ids = set(availability_by_driver.keys())
    capability_by_driver = {driver.driver_id: driver for driver in drivers}
    for driver_id in sorted(set(capability_by_driver.keys()) | availability_driver_ids):
        capability = capability_by_driver.get(driver_id)
        availability = availability_by_driver.get(driver_id)
        target_shifts_per_week = (
            availability.target_shifts_per_week if availability is not None else 4
        )
        restriction_set = set(capability.approved_restrictions if capability is not None else ())
        max_shifts_per_week = _restriction_prefixed_int(
            restriction_set,
            prefix="max_shifts_per_week=",
        ) or target_shifts_per_week
        max_minutes_rolling7 = _restriction_prefixed_int(
            restriction_set,
            prefix="max_minutes_rolling7=",
        ) or (max(max_shifts_per_week, target_shifts_per_week) * 600)
        tags = _unique_tokens(
            [
                *(capability.policy_tags if capability is not None else ()),
                *(availability.policy_tags if availability is not None else ()),
            ]
        )
        signals[driver_id] = DriverPolicySignal(
            driver_id=driver_id,
            target_shifts_per_week=target_shifts_per_week,
            max_shifts_per_week=max(max_shifts_per_week, 1),
            max_minutes_rolling7=max(max_minutes_rolling7, 1),
            on_call_eligible=bool(availability.on_call_eligible) if availability is not None else False,
            emergency_only=bool(availability.emergency_only) if availability is not None else False,
            tags=tags,
        )
    return signals


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


def _metadata_json(artifact: Mapping[str, Any]) -> dict[str, Any]:
    metadata = artifact.get("metadata_json")
    if isinstance(metadata, dict):
        return metadata
    raise ValueError(
        "artifact metadata_json must be a JSON object "
        f"(artifact_version_id={artifact.get('artifact_version_id')})"
    )


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


def _coerce_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


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
