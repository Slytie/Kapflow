from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .bundle_builder import DriverCapability, WeeklyScheduleControlBundle
from .planning_state import PartialWeeklyScheduleState
from .route_slot_requirements import RouteSlotRequirement
from .validation import HardValidationResult


_SCORE_BUCKET_ORDER = {
    "best": 0,
    "good": 1,
    "fair": 2,
    "ok": 3,
    "poor": 4,
    "blocked": 5,
    "n/a": 5,
}

_HARD_FILTER_ORDER = {
    "pass": 0,
    "blocked": 1,
    "fail": 2,
}

SOFT_SCORE_WEIGHTS: dict[str, float] = {
    "coverage_pressure": 0.18,
    "availability_fit": 0.14,
    "previous_week_stability": 0.18,
    "target_shift_gap": 0.14,
    "fairness_balance": 0.08,
    "on_call_coverage": 0.08,
    "lost_work_credit": 0.08,
    "seniority_score": 0.06,
    "reliability_score": 0.06,
    "rolling7_headroom": 0.10,
}


@dataclass(frozen=True)
class SoftScore:
    total: float
    fairness_balance: float
    on_call_coverage: float
    lost_work_credit: float
    coverage_pressure: float
    availability_fit: float
    previous_week_stability: float
    target_shift_gap: float
    seniority_score: float
    reliability_score: float
    current_week_shift_count: int
    projected_rolling7_minutes: int
    remaining_rolling7_minutes: int
    bucket: str


def score_candidate(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    hard_validation: HardValidationResult,
    schedule_state: PartialWeeklyScheduleState | None = None,
) -> SoftScore:
    if hard_validation.status != "pass":
        return SoftScore(
            total=0.0,
            fairness_balance=0.0,
            on_call_coverage=0.0,
            lost_work_credit=0.0,
            coverage_pressure=0.0,
            availability_fit=0.0,
            previous_week_stability=0.0,
            target_shift_gap=0.0,
            seniority_score=0.0,
            reliability_score=0.0,
            current_week_shift_count=hard_validation.current_week_shift_count,
            projected_rolling7_minutes=hard_validation.projected_rolling7_minutes,
            remaining_rolling7_minutes=hard_validation.remaining_rolling7_minutes,
            bucket="blocked",
        )

    availability = bundle.availability_by_driver.get(driver.driver_id)
    target_shifts = max(int(getattr(availability, "target_shifts_per_week", 4)), 1)
    expected_target_minutes = target_shifts * 480
    observed_minutes = int(bundle.actual_minutes_by_driver.get(driver.driver_id, 0))
    current_week_shift_count = hard_validation.current_week_shift_count
    if schedule_state is not None:
        observed_minutes += schedule_state.projected_minutes_for_driver(driver.driver_id)

    fairness_balance = _clamp01(
        (expected_target_minutes - observed_minutes) / float(max(expected_target_minutes, 1))
    )
    on_call_coverage = _on_call_coverage(
        route_slot=route_slot,
        driver=driver,
        availability=availability,
    )
    lost_work_credit = _clamp01(
        (
            expected_target_minutes
            - observed_minutes
            + route_slot.projected_minutes
            + (120 if "lost_work_credit" in set(driver.policy_tags) else 0)
        )
        / float(max(expected_target_minutes, 1))
    )
    coverage_pressure = _coverage_pressure(
        bundle=bundle,
        route_slot=route_slot,
        schedule_state=schedule_state,
    )
    availability_fit = _availability_fit(
        route_slot=route_slot,
        driver=driver,
        availability=availability,
        hard_validation=hard_validation,
    )
    previous_week_stability = _previous_week_stability(
        route_slot=route_slot,
        driver=driver,
        availability=availability,
    )
    target_shift_gap = _clamp01((target_shifts - current_week_shift_count) / float(target_shifts))
    seniority_score = _seniority_score(driver=driver, availability=availability)
    reliability_score = _reliability_score(driver=driver, availability=availability)
    rolling7_limit = (
        bundle.policy_signals_by_driver.get(driver.driver_id).max_minutes_rolling7
        if driver.driver_id in bundle.policy_signals_by_driver
        else max(expected_target_minutes, 1)
    )
    rolling7_headroom = _clamp01(
        hard_validation.remaining_rolling7_minutes / float(max(int(rolling7_limit), 1))
    )

    total = (
        (SOFT_SCORE_WEIGHTS["coverage_pressure"] * coverage_pressure)
        + (SOFT_SCORE_WEIGHTS["availability_fit"] * availability_fit)
        + (SOFT_SCORE_WEIGHTS["previous_week_stability"] * previous_week_stability)
        + (SOFT_SCORE_WEIGHTS["target_shift_gap"] * target_shift_gap)
        + (SOFT_SCORE_WEIGHTS["fairness_balance"] * fairness_balance)
        + (SOFT_SCORE_WEIGHTS["on_call_coverage"] * on_call_coverage)
        + (SOFT_SCORE_WEIGHTS["lost_work_credit"] * lost_work_credit)
        + (SOFT_SCORE_WEIGHTS["seniority_score"] * seniority_score)
        + (SOFT_SCORE_WEIGHTS["reliability_score"] * reliability_score)
        + (SOFT_SCORE_WEIGHTS["rolling7_headroom"] * rolling7_headroom)
    )
    bucket = _score_bucket_for_total(total)
    return SoftScore(
        total=round(total, 6),
        fairness_balance=round(fairness_balance, 6),
        on_call_coverage=round(on_call_coverage, 6),
        lost_work_credit=round(lost_work_credit, 6),
        coverage_pressure=round(coverage_pressure, 6),
        availability_fit=round(availability_fit, 6),
        previous_week_stability=round(previous_week_stability, 6),
        target_shift_gap=round(target_shift_gap, 6),
        seniority_score=round(seniority_score, 6),
        reliability_score=round(reliability_score, 6),
        current_week_shift_count=current_week_shift_count,
        projected_rolling7_minutes=hard_validation.projected_rolling7_minutes,
        remaining_rolling7_minutes=hard_validation.remaining_rolling7_minutes,
        bucket=bucket,
    )


def deterministic_rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[int, int, float, float, float, str]:
        hard_filter_status = str(item.get("hard_filter_status", "blocked")).strip().lower()
        score_bucket = str(item.get("score_bucket", "blocked")).strip().lower()
        candidate_driver_id = str(item.get("candidate_driver_id", ""))
        return (
            _HARD_FILTER_ORDER.get(hard_filter_status, 99),
            _SCORE_BUCKET_ORDER.get(score_bucket, 99),
            -float(item.get("soft_score_total") or 0.0),
            -float(item.get("previous_week_stability") or 0.0),
            -float(item.get("coverage_pressure") or 0.0),
            candidate_driver_id,
        )

    return sorted(candidates, key=sort_key)


def summarize_soft_scores(selected_candidates: list[dict[str, Any]]) -> dict[str, float]:
    pass_candidates = [
        item
        for item in selected_candidates
        if str(item.get("hard_filter_status") or "") == "pass"
    ]
    if not pass_candidates:
        return {
            "fairness_balance": 0.0,
            "on_call_coverage": 0.0,
            "lost_work_credit": 0.0,
            "coverage_pressure": 0.0,
            "availability_fit": 0.0,
            "previous_week_stability": 0.0,
            "target_shift_gap": 0.0,
            "seniority_score": 0.0,
            "reliability_score": 0.0,
        }

    count = float(len(pass_candidates))
    return {
        "fairness_balance": sum(float(item.get("fairness_balance") or 0.0) for item in pass_candidates)
        / count,
        "on_call_coverage": sum(float(item.get("on_call_coverage") or 0.0) for item in pass_candidates)
        / count,
        "lost_work_credit": sum(float(item.get("lost_work_credit") or 0.0) for item in pass_candidates)
        / count,
        "coverage_pressure": sum(float(item.get("coverage_pressure") or 0.0) for item in pass_candidates)
        / count,
        "availability_fit": sum(float(item.get("availability_fit") or 0.0) for item in pass_candidates)
        / count,
        "previous_week_stability": sum(
            float(item.get("previous_week_stability") or 0.0) for item in pass_candidates
        )
        / count,
        "target_shift_gap": sum(float(item.get("target_shift_gap") or 0.0) for item in pass_candidates)
        / count,
        "seniority_score": sum(float(item.get("seniority_score") or 0.0) for item in pass_candidates)
        / count,
        "reliability_score": sum(float(item.get("reliability_score") or 0.0) for item in pass_candidates)
        / count,
    }


def _score_bucket_for_total(total: float) -> str:
    if total >= 0.85:
        return "best"
    if total >= 0.70:
        return "good"
    if total >= 0.55:
        return "fair"
    if total >= 0.40:
        return "ok"
    return "poor"


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return float(value)


def _coverage_pressure(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slot: RouteSlotRequirement,
    schedule_state: PartialWeeklyScheduleState | None,
) -> float:
    demand = bundle.daily_demand_by_service_date.get(route_slot.service_date)
    planned_route_count = max(int(getattr(demand, "planned_route_count", 0)), 1)
    unresolved_for_day = planned_route_count
    if schedule_state is not None:
        unresolved_for_day = sum(
            1 for item in schedule_state.remaining_route_slots() if item.service_date == route_slot.service_date
        )
        unresolved_for_day = max(unresolved_for_day, 1)
    pressure = unresolved_for_day / float(planned_route_count)
    if "rescue" in str(route_slot.route_slot_class or ""):
        pressure += 0.2
    elif "overflow" in str(route_slot.route_slot_class or ""):
        pressure += 0.12
    return _clamp01(pressure)


def _availability_fit(
    *,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    availability: Any,
    hard_validation: HardValidationResult,
) -> float:
    state = str(hard_validation.driver_day_state or "unknown")
    if state == "available":
        fit = 1.0
    elif state == "emergency_only" and "rescue" in str(route_slot.route_slot_class or ""):
        fit = 0.75
    elif state == "unknown":
        fit = 0.6
    else:
        fit = 0.0
    if availability is not None and bool(getattr(availability, "on_call_eligible", False)):
        if "rescue" in str(route_slot.route_slot_class or "") or "overflow" in str(route_slot.route_slot_class or ""):
            fit += 0.1
    if "weekend_ok" in set(driver.policy_tags) and _weekday_token(route_slot.service_date) in {"Sat", "Sun"}:
        fit += 0.1
    return _clamp01(fit)


def _on_call_coverage(
    *,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    availability: Any,
) -> float:
    if "rescue" in str(route_slot.route_slot_class or "") or "overflow" in str(route_slot.route_slot_class or ""):
        if availability is not None and bool(getattr(availability, "on_call_eligible", False)):
            return 1.0
        if "on_call" in set(driver.skills):
            return 0.9
        return 0.55
    if availability is not None and bool(getattr(availability, "on_call_eligible", False)):
        return 0.75
    return 0.6


def _previous_week_stability(
    *,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    availability: Any,
) -> float:
    if availability is None:
        return 0.35
    weekday = _weekday_token(route_slot.service_date)
    previous_states = [
        item
        for item in getattr(availability, "previous_week_states", ())
        if _weekday_token(item.service_date) == weekday
    ]
    if not previous_states:
        base = 0.35
    else:
        previous = previous_states[0]
        if previous.state == "worked" and previous.route_id and previous.route_id == route_slot.route_id:
            base = 1.0
        elif previous.state == "worked":
            base = 0.65
        elif previous.state == "available_not_assigned":
            base = 0.5
        elif previous.state == "blocked_previous_week":
            base = 0.2
        else:
            base = 0.1
    tags = set(driver.policy_tags) | set(getattr(availability, "policy_tags", ()))
    if "stability_preferred" in tags and base > 0.0:
        base += 0.1
    if "anchor" in tags and base >= 0.65:
        base += 0.05
    return _clamp01(base)


def _seniority_score(*, driver: DriverCapability, availability: Any) -> float:
    employment_type = str(
        driver.employment_type or getattr(availability, "employment_type", "") or ""
    ).strip()
    score = 0.8 if employment_type == "full_time" else 0.55
    tags = set(driver.policy_tags) | set(getattr(availability, "policy_tags", ()))
    if "anchor" in tags:
        score += 0.15
    if "can_rescue" in tags:
        score += 0.05
    return _clamp01(score)


def _reliability_score(*, driver: DriverCapability, availability: Any) -> float:
    if availability is None:
        return 0.55
    previous_states = tuple(getattr(availability, "previous_week_states", ()))
    worked = sum(1 for item in previous_states if item.state == "worked")
    active = sum(
        1
        for item in previous_states
        if item.state in {"worked", "available_not_assigned", "blocked_previous_week"}
    )
    base = 0.6 if active == 0 else _clamp01(worked / float(active))
    tags = set(driver.policy_tags) | set(getattr(availability, "policy_tags", ()))
    if "anchor" in tags:
        base += 0.15
    if "on_call_priority" in tags:
        base += 0.1
    if "restricted_close" in tags:
        base -= 0.05
    return _clamp01(base)


def _weekday_token(service_date: str) -> str:
    return date.fromisoformat(service_date).strftime("%a")
