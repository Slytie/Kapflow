from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

from .bundle_builder import DriverCapability, WeeklyScheduleControlBundle
from .contract_minimization import summarize_contract_change_metrics
from .planning_state import IterationSummary, PartialWeeklyScheduleState, RepairMove
from .route_slot_requirements import RouteSlotRequirement

MIN_REST_HOURS_BETWEEN_SHIFTS = 10


@dataclass(frozen=True)
class HardValidationResult:
    status: str
    reasons: tuple[str, ...]
    driver_day_state: str = ""
    driver_day_availability_state: str = ""
    current_week_shift_count: int = 0
    projected_rolling7_minutes: int = 0
    remaining_rolling7_minutes: int = 0


def evaluate_hard_constraints(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    schedule_state: PartialWeeklyScheduleState | None = None,
    exclude_route_slot_ids: set[str] | None = None,
) -> HardValidationResult:
    failed_reasons: list[str] = []
    blocked_reasons: list[str] = []
    exclude = exclude_route_slot_ids or set()

    if route_slot.required_skill and route_slot.required_skill not in set(driver.skills):
        failed_reasons.append("missing_required_skill")

    if route_slot.vehicle_type and route_slot.vehicle_type not in set(driver.vehicle_certifications):
        failed_reasons.append("vehicle_not_certified")

    if route_slot.route_slot_class and route_slot.route_slot_class not in set(
        driver.eligible_route_slot_classes
    ):
        blocked_reasons.append("route_slot_class_not_eligible")

    availability = bundle.availability_by_driver.get(driver.driver_id)
    driver_day_record = _driver_day_record(availability, route_slot.service_date)
    driver_day_state = _driver_day_state(availability, route_slot.service_date)
    driver_day_availability_state = _driver_day_availability_state(
        driver_day_record=driver_day_record,
        normalized_state=driver_day_state,
    )
    if driver_day_state == "approved_unavailable":
        blocked_reasons.append("driver_unavailable")
    elif driver_day_state == "pattern_off":
        blocked_reasons.append("driver_day_pattern_off")
    elif driver_day_state == "emergency_only" and not _is_emergency_eligible_slot(route_slot):
        blocked_reasons.append("driver_day_emergency_only")

    restriction_set = set(driver.approved_restrictions)
    if "no_shift_after_21_30" in restriction_set:
        parsed_end = _parse_hhmm(route_slot.shift_end)
        if parsed_end is not None and parsed_end > time(hour=21, minute=30):
            blocked_reasons.append("restriction_no_shift_after_21_30")

    locked_route_id = _restriction_prefixed_value(restriction_set, prefix="locked_route_id=")
    if locked_route_id and route_slot.route_id and route_slot.route_id != locked_route_id:
        blocked_reasons.append("locked_route_mismatch")
    locked_service_date = _restriction_prefixed_value(
        restriction_set,
        prefix="locked_service_date=",
    )
    if locked_service_date and route_slot.service_date != locked_service_date:
        blocked_reasons.append("locked_service_date_mismatch")

    policy_signal = bundle.policy_signals_by_driver.get(driver.driver_id)
    current_week_shift_count = (
        schedule_state.current_week_shift_count(
            driver.driver_id,
            exclude_route_slot_ids=exclude,
        )
        if schedule_state is not None
        else 0
    )
    max_shifts_per_week = (
        int(policy_signal.max_shifts_per_week)
        if policy_signal is not None
        else max(int(getattr(availability, "target_shifts_per_week", 4)), 1)
    )
    if current_week_shift_count + 1 > max_shifts_per_week:
        blocked_reasons.append("max_shifts_per_week")

    rolling_minutes_limit = (
        int(policy_signal.max_minutes_rolling7)
        if policy_signal is not None
        else (
            _restriction_prefixed_int(
                restriction_set,
                prefix="max_minutes_rolling7=",
            )
            or 0
        )
    )
    if schedule_state is not None:
        projected_rolling7_minutes, _ = schedule_state.projected_rolling7_state(
            bundle=bundle,
            driver_id=driver.driver_id,
            service_date=route_slot.service_date,
            candidate_minutes=route_slot.projected_minutes,
            exclude_route_slot_ids=exclude,
        )
    else:
        projected_rolling7_minutes = int(bundle.actual_minutes_by_driver.get(driver.driver_id, 0))
        projected_rolling7_minutes += route_slot.projected_minutes
    remaining_rolling7_minutes = max(rolling_minutes_limit - projected_rolling7_minutes, 0)
    if rolling_minutes_limit > 0 and projected_rolling7_minutes > rolling_minutes_limit:
        blocked_reasons.append("rolling_7_day_limit")

    if schedule_state is not None:
        same_day_assignments = schedule_state.driver_assignments_on_date(
            driver.driver_id,
            route_slot.service_date,
            exclude_route_slot_ids=exclude,
        )
        if any(
            _shift_windows_overlap(
                route_slot,
                schedule_state.route_slot(assignment.route_slot_id),
            )
            for assignment in same_day_assignments
        ):
            blocked_reasons.append("shift_overlap")

        min_rest_hours = max(
            _restriction_prefixed_int(restriction_set, prefix="min_rest_hours=")
            or MIN_REST_HOURS_BETWEEN_SHIFTS,
            MIN_REST_HOURS_BETWEEN_SHIFTS,
        )
        if any(
            _rest_window_violated(
                route_slot,
                schedule_state.route_slot(assignment.route_slot_id),
                min_rest_hours=min_rest_hours,
            )
            for assignment in schedule_state.driver_assignments(
                driver.driver_id,
                exclude_route_slot_ids=exclude,
            )
        ):
            blocked_reasons.append("rest_window")

    if failed_reasons:
        return HardValidationResult(
            status="fail",
            reasons=tuple(sorted(dict.fromkeys(failed_reasons))),
            driver_day_state=driver_day_state,
            driver_day_availability_state=driver_day_availability_state,
            current_week_shift_count=current_week_shift_count,
            projected_rolling7_minutes=projected_rolling7_minutes,
            remaining_rolling7_minutes=remaining_rolling7_minutes,
        )
    if blocked_reasons:
        return HardValidationResult(
            status="blocked",
            reasons=tuple(sorted(dict.fromkeys(blocked_reasons))),
            driver_day_state=driver_day_state,
            driver_day_availability_state=driver_day_availability_state,
            current_week_shift_count=current_week_shift_count,
            projected_rolling7_minutes=projected_rolling7_minutes,
            remaining_rolling7_minutes=remaining_rolling7_minutes,
        )
    return HardValidationResult(
        status="pass",
        reasons=(),
        driver_day_state=driver_day_state,
        driver_day_availability_state=driver_day_availability_state,
        current_week_shift_count=current_week_shift_count,
        projected_rolling7_minutes=projected_rolling7_minutes,
        remaining_rolling7_minutes=remaining_rolling7_minutes,
    )


def build_stage04_validation_summary(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    soft_score_totals: dict[str, float],
    iteration_summaries: list[IterationSummary] | None = None,
    repair_moves: list[RepairMove] | None = None,
) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []
    tradeoffs: list[str] = []
    uncovered_route_slot_ids: list[str] = []
    iterations = iteration_summaries or []
    repairs = repair_moves or []
    contract_change_summary = summarize_contract_change_metrics(selected_candidates)

    for candidate in selected_candidates:
        route_slot_id = str(candidate.get("route_slot_id") or "")
        status = str(candidate.get("hard_filter_status") or "blocked")
        driver_id = str(candidate.get("candidate_driver_id") or "unassigned")
        assignment_action = str(candidate.get("assignment_action") or "assign")
        if assignment_action == "unassigned" or status != "pass":
            reason_text = ",".join(str(item) for item in candidate.get("hard_filter_reasons") or [])
            uncovered_route_slot_ids.append(route_slot_id)
            violations.append(
                f"{route_slot_id} unresolved ({driver_id})"
                + (f" [{reason_text}]" if reason_text else "")
            )
            continue
        if str(candidate.get("score_bucket") or "") in {"poor", "ok"}:
            warnings.append(
                f"{driver_id} selected for {route_slot_id} with {candidate.get('score_bucket')} soft score"
            )
        availability_state = str(candidate.get("availability_state") or "")
        if bool(candidate.get("new_agreement_required")):
            trigger_reason = str(candidate.get("new_agreement_trigger_reason") or "")
            warnings.append(
                f"{driver_id} selected for {route_slot_id} requires new agreement"
                + (f" ({trigger_reason})" if trigger_reason else "")
            )
        elif str(candidate.get("baseline_template_state") or "") == "on_call_template":
            warnings.append(
                f"{driver_id} selected for {route_slot_id} using signed on-call template day"
            )
        elif availability_state == "AVOID_IF_POSSIBLE":
            warnings.append(
                f"{driver_id} selected for {route_slot_id} using {availability_state} availability state"
            )
        if float(candidate.get("previous_week_stability") or 0.0) < 0.4:
            warnings.append(
                f"{driver_id} selected for {route_slot_id} with weak previous-week stability"
            )
        if str(candidate.get("delta_kind") or "") == "repair":
            tradeoffs.append(
                f"{route_slot_id} re-assigned in iteration {candidate.get('iteration_index')} to preserve local coverage."
            )
        if str(candidate.get("delta_kind") or "") == "improvement":
            tradeoffs.append(
                f"{route_slot_id} re-assigned in iteration {candidate.get('iteration_index')} to improve preference fit while keeping hard rules satisfied."
            )
    hard_rule_result = "pass" if not violations else "fail"
    if hard_rule_result == "pass" and warnings:
        recommendation = "forward_to_stage05_manager_review_with_warnings"
    elif hard_rule_result == "pass":
        recommendation = "forward_to_stage05_manager_review"
    else:
        recommendation = "request_stage04_route_gap_review"

    return {
        "summary_id": _validation_summary_id(bundle.bundle_id),
        "bundle_id": bundle.bundle_id,
        "hard_rule_result": hard_rule_result,
        "hard_rule_checks": [
            "whc_limit",
            "rest_window",
            "skill_compatibility",
            "driver_day_availability",
            "rolling_7_day_limit",
            "max_shifts_per_week",
            "shift_overlap",
            "route_slot_class_eligibility",
            "route_slot_coverage",
        ],
        "soft_score_totals": {
            key: round(float(value), 4)
            for key, value in sorted(soft_score_totals.items())
        },
        "coverage_summary": {
            "total_route_slots": len(selected_candidates),
            "assigned_route_slots": len(selected_candidates) - len(uncovered_route_slot_ids),
            "uncovered_route_slots": len(uncovered_route_slot_ids),
            "uncovered_route_slot_ids": uncovered_route_slot_ids,
        },
        "iteration_summary": {
            "iteration_count": len(iterations),
            "batch_size_min": min((item.batch_size for item in iterations), default=0),
            "batch_size_max": max((item.batch_size for item in iterations), default=0),
            "candidate_evaluation_count": sum(
                item.candidate_evaluation_count for item in iterations
            ),
        },
        "churn_summary": {
            "repair_move_count": len(repairs),
            "reallocation_move_count": len(repairs),
            "repaired_route_slot_count": len(
                {
                    route_slot_id
                    for item in repairs
                    for route_slot_id in (
                        item.filled_route_slot_id,
                        item.reassigned_route_slot_id,
                    )
                }
            ),
            "local_repair_posture": "bounded_local_reallocation",
        },
        "violations": violations,
        "warnings": warnings,
        "tradeoffs": tradeoffs,
        "repair_moves": [item.to_payload() for item in repairs],
        "reallocation_moves": [item.to_payload() for item in repairs],
        "recommended_action": recommendation,
        **contract_change_summary,
    }


def _parse_hhmm(value: str) -> time | None:
    token = str(value or "").strip()
    if not token:
        return None
    try:
        hour_text, minute_text = token.split(":", maxsplit=1)
        return time(hour=int(hour_text), minute=int(minute_text))
    except (TypeError, ValueError):
        return None


def _restriction_prefixed_int(restrictions: set[str], *, prefix: str) -> int | None:
    for restriction in restrictions:
        if not restriction.startswith(prefix):
            continue
        value = restriction.removeprefix(prefix)
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _restriction_prefixed_value(restrictions: set[str], *, prefix: str) -> str:
    for restriction in restrictions:
        if restriction.startswith(prefix):
            return restriction.removeprefix(prefix).strip()
    return ""


def _driver_day_state(availability: Any, service_date: str) -> str:
    if availability is None:
        return "unknown"
    for state in getattr(availability, "daily_states", ()):
        if state.service_date == service_date:
            normalized = str(getattr(state, "normalized_state", "") or "").strip()
            if normalized:
                return normalized
            return str(state.state or "unknown")
    if service_date in set(getattr(availability, "approved_unavailable_dates", ())):
        return "approved_unavailable"
    return "unknown"


def _driver_day_record(availability: Any, service_date: str) -> Any | None:
    if availability is None:
        return None
    for state in getattr(availability, "daily_states", ()):
        if state.service_date == service_date:
            return state
    return None


def _driver_day_availability_state(*, driver_day_record: Any | None, normalized_state: str) -> str:
    if driver_day_record is not None:
        raw_state = str(getattr(driver_day_record, "state", "") or "").strip().upper()
        if raw_state:
            return raw_state
    token = str(normalized_state or "").strip().lower()
    if token == "approved_unavailable":
        return "CANNOT"
    if token == "pattern_off":
        return "PATTERN_OFF"
    if token == "emergency_only":
        return "ON_CALL_ONLY"
    if token == "available":
        return "AVAILABLE"
    if token:
        return token.upper()
    return "UNKNOWN"


def _is_emergency_eligible_slot(route_slot: RouteSlotRequirement) -> bool:
    route_slot_class = str(route_slot.route_slot_class or "")
    return "rescue" in route_slot_class or "overflow" in route_slot_class


def _shift_windows_overlap(left: RouteSlotRequirement, right: RouteSlotRequirement) -> bool:
    left_start, left_end = _slot_window(left)
    right_start, right_end = _slot_window(right)
    return left_start < right_end and right_start < left_end


def _rest_window_violated(
    candidate_slot: RouteSlotRequirement,
    existing_slot: RouteSlotRequirement,
    *,
    min_rest_hours: int,
) -> bool:
    candidate_start, candidate_end = _slot_window(candidate_slot)
    existing_start, existing_end = _slot_window(existing_slot)
    minimum_gap = timedelta(hours=max(min_rest_hours, 0))
    if candidate_start >= existing_end:
        return candidate_start - existing_end < minimum_gap
    if existing_start >= candidate_end:
        return existing_start - candidate_end < minimum_gap
    return False


def _slot_window(route_slot: RouteSlotRequirement) -> tuple[datetime, datetime]:
    start_time = _parse_hhmm(route_slot.shift_start) or time(hour=0, minute=0)
    end_time = _parse_hhmm(route_slot.shift_end) or start_time
    service_day = datetime.fromisoformat(route_slot.service_date)
    start = service_day.replace(hour=start_time.hour, minute=start_time.minute)
    end = service_day.replace(hour=end_time.hour, minute=end_time.minute)
    if end <= start:
        end = end + timedelta(days=1)
    return start, end


def _validation_summary_id(bundle_id: str) -> str:
    compact = bundle_id.removeprefix("bundle-")
    return f"valsum-{compact}"
