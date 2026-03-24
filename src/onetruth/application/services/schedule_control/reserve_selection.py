from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .bundle_builder import DriverAvailability, WeeklyScheduleControlBundle
from .contract_minimization import assess_contract_minimization

ON_CALL_BUFFER_PROJECTED_MINUTES = 180

_RESERVE_TEMPLATE_PRIORITY = {
    "on_call_template": 0,
    "white_template": 1,
    "yellow_template": 2,
}

_ELIGIBLE_RESERVE_TEMPLATE_STATES = frozenset(_RESERVE_TEMPLATE_PRIORITY)


@dataclass(frozen=True)
class ReserveSelectionResult:
    reserve_rows: list[dict[str, Any]]
    reserve_summary: dict[str, Any]


def select_on_call_reserve_rows(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    iteration_index: int,
) -> ReserveSelectionResult:
    route_rows = [
        row
        for row in selected_candidates
        if str(row.get("assignment_action") or "") == "assign"
        and str(row.get("hard_filter_status") or "") == "pass"
    ]
    route_assignments_by_driver = _rows_by_driver(route_rows)
    route_assignments_by_driver_date = {
        (str(row.get("candidate_driver_id") or ""), str(row.get("service_date") or ""))
        for row in route_rows
        if str(row.get("candidate_driver_id") or "").strip()
        and str(row.get("service_date") or "").strip()
    }
    selected_reserve_rows: list[dict[str, Any]] = []
    reserve_assignments_by_driver: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reserve_assignments_by_driver_date: set[tuple[str, str]] = set()
    on_call_targets_by_service_date: dict[str, int] = {}
    selected_on_call_by_service_date: Counter[str] = Counter()

    for service_date in sorted(bundle.daily_demand_by_service_date):
        demand = bundle.daily_demand_by_service_date[service_date]
        on_call_target = max(int(getattr(demand, "on_call_target", 0) or 0), 0)
        on_call_targets_by_service_date[service_date] = on_call_target
        if on_call_target <= 0:
            continue

        candidates = _reserve_candidates_for_date(
            bundle=bundle,
            service_date=service_date,
            route_assignments_by_driver=route_assignments_by_driver,
            route_assignments_by_driver_date=route_assignments_by_driver_date,
            reserve_assignments_by_driver=reserve_assignments_by_driver,
            reserve_assignments_by_driver_date=reserve_assignments_by_driver_date,
        )
        for sequence, candidate in enumerate(candidates, start=1):
            if selected_on_call_by_service_date[service_date] >= on_call_target:
                break
            reserve_row = _build_reserve_row(
                candidate=candidate,
                sequence=sequence,
                iteration_index=iteration_index,
            )
            selected_reserve_rows.append(reserve_row)
            reserve_assignments_by_driver[candidate["candidate_driver_id"]].append(reserve_row)
            reserve_assignments_by_driver_date.add(
                (candidate["candidate_driver_id"], service_date)
            )
            selected_on_call_by_service_date[service_date] += 1

    filled_on_call_by_service_date = {
        service_date: int(selected_on_call_by_service_date.get(service_date, 0))
        for service_date in sorted(on_call_targets_by_service_date)
    }
    unmet_on_call_target_by_service_date = {
        service_date: max(on_call_targets_by_service_date[service_date] - filled_count, 0)
        for service_date, filled_count in filled_on_call_by_service_date.items()
    }
    reserve_summary = {
        "on_call_target_by_service_date": on_call_targets_by_service_date,
        "selected_on_call_by_service_date": filled_on_call_by_service_date,
        "unmet_on_call_target_by_service_date": unmet_on_call_target_by_service_date,
        "target_on_call_total": sum(on_call_targets_by_service_date.values()),
        "selected_on_call_total": sum(filled_on_call_by_service_date.values()),
        "unmet_on_call_target_total": sum(unmet_on_call_target_by_service_date.values()),
    }
    return ReserveSelectionResult(
        reserve_rows=selected_reserve_rows,
        reserve_summary=reserve_summary,
    )


def _reserve_candidates_for_date(
    *,
    bundle: WeeklyScheduleControlBundle,
    service_date: str,
    route_assignments_by_driver: dict[str, list[dict[str, Any]]],
    route_assignments_by_driver_date: set[tuple[str, str]],
    reserve_assignments_by_driver: dict[str, list[dict[str, Any]]],
    reserve_assignments_by_driver_date: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for driver in bundle.drivers:
        driver_id = str(driver.driver_id)
        if (driver_id, service_date) in route_assignments_by_driver_date:
            continue
        if (driver_id, service_date) in reserve_assignments_by_driver_date:
            continue

        availability = bundle.availability_by_driver.get(driver_id)
        availability_state = _availability_state_for_date(
            availability=availability,
            service_date=service_date,
        )
        contract = assess_contract_minimization(
            availability_state=availability_state,
            planned_driver_day_state="on_call",
        )
        if contract.baseline_template_state not in _ELIGIBLE_RESERVE_TEMPLATE_STATES:
            continue

        current_week_shift_count = (
            len(route_assignments_by_driver.get(driver_id, ()))
            + len(reserve_assignments_by_driver.get(driver_id, ()))
        )
        max_shifts_per_week = _max_shifts_per_week(bundle=bundle, driver_id=driver_id)
        if current_week_shift_count + 1 > max_shifts_per_week:
            continue

        projected_rolling7_minutes = _projected_rolling7_minutes(
            bundle=bundle,
            driver_id=driver_id,
            service_date=service_date,
            route_assignments=route_assignments_by_driver.get(driver_id, ()),
            reserve_assignments=reserve_assignments_by_driver.get(driver_id, ()),
        )
        rolling7_limit = _rolling7_limit_minutes(bundle=bundle, driver_id=driver_id)
        if rolling7_limit > 0 and projected_rolling7_minutes > rolling7_limit:
            continue

        candidates.append(
            {
                "service_date": service_date,
                "candidate_driver_id": driver_id,
                "assigned_driver_id": driver_id,
                "availability_state": availability_state,
                "baseline_template_state": contract.baseline_template_state,
                "planned_driver_day_state": contract.planned_driver_day_state,
                "new_agreement_required": contract.new_agreement_required,
                "new_agreement_trigger_reason": contract.new_agreement_trigger_reason,
                "template_state_preservation_fit": contract.template_state_preservation_fit,
                "current_week_shift_count": current_week_shift_count,
                "projected_rolling7_minutes": projected_rolling7_minutes,
                "remaining_rolling7_minutes": max(rolling7_limit - projected_rolling7_minutes, 0),
                "on_call_eligible": bool(getattr(availability, "on_call_eligible", False)),
            }
        )

    return sorted(candidates, key=_reserve_candidate_sort_key)


def _reserve_candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, int, int, int, str]:
    return (
        _RESERVE_TEMPLATE_PRIORITY.get(
            str(candidate.get("baseline_template_state") or ""),
            len(_RESERVE_TEMPLATE_PRIORITY),
        ),
        0 if bool(candidate.get("on_call_eligible")) else 1,
        int(candidate.get("current_week_shift_count") or 0),
        int(candidate.get("projected_rolling7_minutes") or 0),
        str(candidate.get("candidate_driver_id") or ""),
    )


def _build_reserve_row(
    *,
    candidate: dict[str, Any],
    sequence: int,
    iteration_index: int,
) -> dict[str, Any]:
    service_date = str(candidate.get("service_date") or "")
    compact_date = service_date.replace("-", "")
    baseline_template_state = str(candidate.get("baseline_template_state") or "")
    rationale_code = {
        "on_call_template": "reserve_fill_on_call_template",
        "white_template": "reserve_fill_white_template",
        "yellow_template": "reserve_fill_yellow_template",
    }.get(baseline_template_state, "reserve_fill")
    return {
        "service_date": service_date,
        "route_slot_id": f"oncall-{compact_date}#{sequence:02d}",
        "route_id": "ON_CALL",
        "candidate_driver_id": str(candidate.get("candidate_driver_id") or ""),
        "assigned_driver_id": str(candidate.get("assigned_driver_id") or ""),
        "assignment_action": "reserve",
        "assignment_status": "reserve",
        "hard_filter_status": "pass",
        "hard_filter_reasons": [],
        "score_bucket": "good",
        "soft_score_total": round(float(candidate.get("template_state_preservation_fit") or 0.0), 6),
        "projected_minutes": ON_CALL_BUFFER_PROJECTED_MINUTES,
        "availability_state": str(candidate.get("availability_state") or ""),
        "baseline_template_state": baseline_template_state,
        "planned_driver_day_state": "on_call",
        "new_agreement_required": bool(candidate.get("new_agreement_required")),
        "new_agreement_trigger_reason": str(candidate.get("new_agreement_trigger_reason") or ""),
        "template_state_preservation_fit": round(
            float(candidate.get("template_state_preservation_fit") or 0.0),
            6,
        ),
        "current_week_shift_count": int(candidate.get("current_week_shift_count") or 0) + 1,
        "projected_rolling7_minutes": int(candidate.get("projected_rolling7_minutes") or 0),
        "remaining_rolling7_minutes": int(candidate.get("remaining_rolling7_minutes") or 0),
        "iteration_index": iteration_index,
        "phase": "reserve_buffer",
        "planning_phase": "reserve_buffer",
        "delta_kind": "reserve",
        "rationale_code": rationale_code,
    }


def _rows_by_driver(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_driver: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        driver_id = str(row.get("candidate_driver_id") or "")
        if not driver_id:
            continue
        by_driver[driver_id].append(row)
    return by_driver


def _availability_state_for_date(
    *,
    availability: DriverAvailability | None,
    service_date: str,
) -> str:
    if availability is None:
        return "UNKNOWN"
    for state in getattr(availability, "daily_states", ()):
        if state.service_date == service_date:
            token = str(getattr(state, "state", "") or "").strip().upper()
            if token:
                return token
            normalized = str(getattr(state, "normalized_state", "") or "").strip().lower()
            if normalized == "approved_unavailable":
                return "CANNOT"
            if normalized == "emergency_only":
                return "ON_CALL_ONLY"
            if normalized == "available":
                return "AVAILABLE"
            if normalized == "pattern_off":
                return "PATTERN_OFF"
    return "UNKNOWN"


def _max_shifts_per_week(*, bundle: WeeklyScheduleControlBundle, driver_id: str) -> int:
    policy_signal = bundle.policy_signals_by_driver.get(driver_id)
    if policy_signal is not None:
        return max(int(policy_signal.max_shifts_per_week), 1)
    availability = bundle.availability_by_driver.get(driver_id)
    return max(int(getattr(availability, "target_shifts_per_week", 4) or 4), 1)


def _rolling7_limit_minutes(*, bundle: WeeklyScheduleControlBundle, driver_id: str) -> int:
    policy_signal = bundle.policy_signals_by_driver.get(driver_id)
    if policy_signal is not None:
        return max(int(policy_signal.max_minutes_rolling7), 0)
    return 0


def _projected_rolling7_minutes(
    *,
    bundle: WeeklyScheduleControlBundle,
    driver_id: str,
    service_date: str,
    route_assignments: list[dict[str, Any]],
    reserve_assignments: list[dict[str, Any]],
) -> int:
    service_day = date.fromisoformat(service_date)
    window_start = service_day - timedelta(days=6)
    window_start_text = window_start.isoformat()
    actual_minutes = sum(
        int(entry.actual_minutes)
        for entry in bundle.actual_entries_by_driver.get(driver_id, ())
        if window_start_text <= entry.service_date <= service_date
    )
    planned_route_minutes = sum(
        int(row.get("projected_minutes") or 0)
        for row in route_assignments
        if window_start_text <= str(row.get("service_date") or "") <= service_date
    )
    planned_reserve_minutes = sum(
        int(row.get("projected_minutes") or 0)
        for row in reserve_assignments
        if window_start_text <= str(row.get("service_date") or "") <= service_date
    )
    return (
        actual_minutes
        + planned_route_minutes
        + planned_reserve_minutes
        + ON_CALL_BUFFER_PROJECTED_MINUTES
    )
