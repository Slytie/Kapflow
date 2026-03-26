from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .bundle_builder import DriverCapability, DriverServiceDayState, WeeklyScheduleControlBundle
from .contract_minimization import assess_contract_minimization
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
    "coverage_pressure": 0.12,
    "availability_state_fit": 0.10,
    "preferred_shift_band_fit": 0.06,
    "preferred_route_slot_class_fit": 0.06,
    "previous_week_continuity": 0.05,
    "target_shift_gap": 0.18,
    "fairness_balance": 0.18,
    "on_call_coverage": 0.05,
    "lost_work_credit": 0.16,
    "seniority_preference_fit": 0.05,
    "reliability_score": 0.05,
    "rolling7_headroom": 0.03,
    "avoidable_assignment_score": 0.05,
    "template_state_preservation_fit": 0.07,
}


@dataclass(frozen=True)
class SoftScore:
    total: float
    fairness_balance: float
    on_call_coverage: float
    lost_work_credit: float
    coverage_pressure: float
    availability_fit: float
    availability_state: str
    availability_state_fit: float
    preferred_shift_band_fit: float
    preferred_route_slot_class_fit: float
    preference_fit: float
    previous_week_stability: float
    continuity_score: float
    target_shift_gap: float
    seniority_score: float
    seniority_preference_fit: float
    reliability_score: float
    avoidable_assignment_score: float
    baseline_template_state: str
    planned_driver_day_state: str
    new_agreement_required: bool
    new_agreement_trigger_reason: str
    template_state_preservation_fit: float
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
    planned_driver_day_state = _planned_driver_day_state_for_slot(route_slot)
    blocked_assessment = assess_contract_minimization(
        availability_state=hard_validation.driver_day_availability_state,
        planned_driver_day_state=planned_driver_day_state,
    )
    if hard_validation.status != "pass":
        return SoftScore(
            total=0.0,
            fairness_balance=0.0,
            on_call_coverage=0.0,
            lost_work_credit=0.0,
            coverage_pressure=0.0,
            availability_fit=0.0,
            availability_state=str(hard_validation.driver_day_availability_state or ""),
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
            baseline_template_state=blocked_assessment.baseline_template_state,
            planned_driver_day_state=blocked_assessment.planned_driver_day_state,
            new_agreement_required=blocked_assessment.new_agreement_required,
            new_agreement_trigger_reason=blocked_assessment.new_agreement_trigger_reason,
            template_state_preservation_fit=blocked_assessment.template_state_preservation_fit,
            current_week_shift_count=hard_validation.current_week_shift_count,
            projected_rolling7_minutes=hard_validation.projected_rolling7_minutes,
            remaining_rolling7_minutes=hard_validation.remaining_rolling7_minutes,
            bucket="blocked",
        )

    availability = bundle.availability_by_driver.get(driver.driver_id)
    policy_signal = bundle.policy_signals_by_driver.get(driver.driver_id)
    driver_day = _driver_day_record(availability=availability, service_date=route_slot.service_date)
    availability_state = _availability_state_label(
        driver_day=driver_day,
        fallback=hard_validation.driver_day_availability_state,
    )
    contract_assessment = assess_contract_minimization(
        availability_state=availability_state,
        planned_driver_day_state=planned_driver_day_state,
    )

    target_shifts = max(
        int(
            policy_signal.target_shifts_per_week
            if policy_signal is not None
            else getattr(availability, "target_shifts_per_week", 4)
        ),
        1,
    )
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
        availability_state=availability_state,
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
    availability_state_fit = _availability_state_fit(
        route_slot=route_slot,
        availability_state=availability_state,
        availability=availability,
    )
    preferred_shift_band_fit = _preferred_shift_band_fit(
        route_slot=route_slot,
        driver=driver,
        driver_day=driver_day,
    )
    preferred_route_slot_class_fit = _preferred_route_slot_class_fit(
        route_slot=route_slot,
        driver=driver,
        driver_day=driver_day,
    )
    avoidable_assignment_score = _avoidable_assignment_score(
        route_slot=route_slot,
        availability_state=availability_state,
        driver=driver,
        driver_day=driver_day,
    )
    preference_fit = _clamp01(
        (availability_state_fit * 0.32)
        + (preferred_shift_band_fit * 0.16)
        + (preferred_route_slot_class_fit * 0.16)
        + (avoidable_assignment_score * 0.16)
        + (contract_assessment.template_state_preservation_fit * 0.20)
    )
    continuity_score = _previous_week_continuity(
        route_slot=route_slot,
        driver=driver,
        availability=availability,
        driver_day=driver_day,
    )
    target_shift_gap = _clamp01((target_shifts - current_week_shift_count) / float(target_shifts))
    seniority_preference_fit = _seniority_preference_fit(
        bundle=bundle,
        driver=driver,
        availability=availability,
        preference_fit=preference_fit,
        continuity_score=continuity_score,
    )
    reliability_score = _reliability_score(
        driver=driver,
        availability=availability,
        driver_day=driver_day,
    )
    rolling7_limit = (
        policy_signal.max_minutes_rolling7
        if policy_signal is not None
        else max(expected_target_minutes, 1)
    )
    rolling7_headroom = _clamp01(
        hard_validation.remaining_rolling7_minutes / float(max(int(rolling7_limit), 1))
    )

    total = (
        (SOFT_SCORE_WEIGHTS["coverage_pressure"] * coverage_pressure)
        + (SOFT_SCORE_WEIGHTS["availability_state_fit"] * availability_state_fit)
        + (SOFT_SCORE_WEIGHTS["preferred_shift_band_fit"] * preferred_shift_band_fit)
        + (SOFT_SCORE_WEIGHTS["preferred_route_slot_class_fit"] * preferred_route_slot_class_fit)
        + (SOFT_SCORE_WEIGHTS["previous_week_continuity"] * continuity_score)
        + (SOFT_SCORE_WEIGHTS["target_shift_gap"] * target_shift_gap)
        + (SOFT_SCORE_WEIGHTS["fairness_balance"] * fairness_balance)
        + (SOFT_SCORE_WEIGHTS["on_call_coverage"] * on_call_coverage)
        + (SOFT_SCORE_WEIGHTS["lost_work_credit"] * lost_work_credit)
        + (SOFT_SCORE_WEIGHTS["seniority_preference_fit"] * seniority_preference_fit)
        + (SOFT_SCORE_WEIGHTS["reliability_score"] * reliability_score)
        + (SOFT_SCORE_WEIGHTS["rolling7_headroom"] * rolling7_headroom)
        + (SOFT_SCORE_WEIGHTS["avoidable_assignment_score"] * avoidable_assignment_score)
        + (
            SOFT_SCORE_WEIGHTS["template_state_preservation_fit"]
            * contract_assessment.template_state_preservation_fit
        )
    )
    bucket = _score_bucket_for_total(total)
    return SoftScore(
        total=round(total, 6),
        fairness_balance=round(fairness_balance, 6),
        on_call_coverage=round(on_call_coverage, 6),
        lost_work_credit=round(lost_work_credit, 6),
        coverage_pressure=round(coverage_pressure, 6),
        availability_fit=round(availability_state_fit, 6),
        availability_state=availability_state,
        availability_state_fit=round(availability_state_fit, 6),
        preferred_shift_band_fit=round(preferred_shift_band_fit, 6),
        preferred_route_slot_class_fit=round(preferred_route_slot_class_fit, 6),
        preference_fit=round(preference_fit, 6),
        previous_week_stability=round(continuity_score, 6),
        continuity_score=round(continuity_score, 6),
        target_shift_gap=round(target_shift_gap, 6),
        seniority_score=round(seniority_preference_fit, 6),
        seniority_preference_fit=round(seniority_preference_fit, 6),
        reliability_score=round(reliability_score, 6),
        avoidable_assignment_score=round(avoidable_assignment_score, 6),
        baseline_template_state=contract_assessment.baseline_template_state,
        planned_driver_day_state=contract_assessment.planned_driver_day_state,
        new_agreement_required=contract_assessment.new_agreement_required,
        new_agreement_trigger_reason=contract_assessment.new_agreement_trigger_reason,
        template_state_preservation_fit=round(
            contract_assessment.template_state_preservation_fit,
            6,
        ),
        current_week_shift_count=current_week_shift_count,
        projected_rolling7_minutes=hard_validation.projected_rolling7_minutes,
        remaining_rolling7_minutes=hard_validation.remaining_rolling7_minutes,
        bucket=bucket,
    )


def deterministic_rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(
        item: dict[str, Any],
    ) -> tuple[int, int, int, int, int, int, float, int, float, float, float, float, str]:
        hard_filter_status = str(item.get("hard_filter_status", "blocked")).strip().lower()
        score_bucket = str(item.get("score_bucket", "blocked")).strip().lower()
        candidate_driver_id = str(item.get("candidate_driver_id", ""))
        current_week_shift_count = int(item.get("current_week_shift_count") or 0)
        projected_week_shift_count = current_week_shift_count + (
            1 if hard_filter_status == "pass" else 0
        )
        return (
            _HARD_FILTER_ORDER.get(hard_filter_status, 99),
            _synthetic_demand_priority_rank(item),
            _work_distribution_priority_rank(
                current_week_shift_count=current_week_shift_count,
                projected_week_shift_count=projected_week_shift_count,
            ),
            _overtime_priority_rank(projected_week_shift_count=projected_week_shift_count),
            -_reaches_minimum_work(
                current_week_shift_count=current_week_shift_count,
                projected_week_shift_count=projected_week_shift_count,
            ),
            -_reaches_preferred_work(
                current_week_shift_count=current_week_shift_count,
                projected_week_shift_count=projected_week_shift_count,
            ),
            -float(item.get("fairness_balance") or 0.0),
            _SCORE_BUCKET_ORDER.get(score_bucket, 99),
            -float(item.get("soft_score_total") or 0.0),
            -float(item.get("target_shift_gap") or 0.0),
            -float(item.get("lost_work_credit") or 0.0),
            -float(item.get("template_state_preservation_fit") or 0.0),
            -float(item.get("preference_fit") or 0.0),
            -float(item.get("continuity_score") or item.get("previous_week_stability") or 0.0),
            -float(item.get("reliability_score") or 0.0),
            candidate_driver_id,
        )

    return sorted(candidates, key=sort_key)


def _synthetic_demand_priority_rank(item: dict[str, Any]) -> int:
    demand_kind = str(item.get("demand_kind") or "route").strip().lower()
    availability_state = str(item.get("availability_state") or "").strip().upper()
    baseline_template_state = str(item.get("baseline_template_state") or "").strip().lower()
    if demand_kind == "on_call":
        if availability_state == "ON_CALL_ONLY" or baseline_template_state == "on_call_template":
            return 0
        if availability_state == "AVAILABLE" or baseline_template_state == "white_template":
            return 1
        if (
            availability_state == "AVOID_IF_POSSIBLE"
            or baseline_template_state == "yellow_template"
        ):
            return 2
        return 9
    if demand_kind == "excess_capacity":
        if availability_state == "PREFERRED" or baseline_template_state == "assigned_template":
            return 0
        if availability_state == "AVAILABLE" or baseline_template_state == "white_template":
            return 1
        if (
            availability_state == "AVOID_IF_POSSIBLE"
            or baseline_template_state == "yellow_template"
        ):
            return 2
        return 9
    return 0


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
            "availability_state_fit": 0.0,
            "preferred_shift_band_fit": 0.0,
            "preferred_route_slot_class_fit": 0.0,
            "preference_fit": 0.0,
            "previous_week_stability": 0.0,
            "continuity_score": 0.0,
            "target_shift_gap": 0.0,
            "seniority_score": 0.0,
            "seniority_preference_fit": 0.0,
            "reliability_score": 0.0,
            "avoidable_assignment_score": 0.0,
            "template_state_preservation_fit": 0.0,
        }

    count = float(len(pass_candidates))
    totals: dict[str, float] = {}
    for key in (
        "fairness_balance",
        "on_call_coverage",
        "lost_work_credit",
        "coverage_pressure",
        "availability_fit",
        "availability_state_fit",
        "preferred_shift_band_fit",
        "preferred_route_slot_class_fit",
        "preference_fit",
        "previous_week_stability",
        "continuity_score",
        "target_shift_gap",
        "seniority_score",
        "seniority_preference_fit",
        "reliability_score",
        "avoidable_assignment_score",
        "template_state_preservation_fit",
    ):
        totals[key] = sum(float(item.get(key) or 0.0) for item in pass_candidates) / count
    return totals


def _score_bucket_for_total(total: float) -> str:
    if total >= 0.86:
        return "best"
    if total >= 0.72:
        return "good"
    if total >= 0.58:
        return "fair"
    if total >= 0.42:
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
    demand_kind = str(route_slot.demand_kind or "route").strip().lower()
    if route_slot.is_on_call_demand:
        planned_count = max(int(getattr(demand, "on_call_target", 0)), 1)
    elif route_slot.is_excess_capacity_demand:
        planned_count = max(int(getattr(demand, "excess_capacity_target", 0)), 1)
    else:
        planned_count = max(int(getattr(demand, "planned_route_count", 0)), 1)
    unresolved_for_day = planned_count
    if schedule_state is not None:
        unresolved_for_day = sum(
            1
            for item in schedule_state.remaining_route_slots()
            if item.service_date == route_slot.service_date
            and str(item.demand_kind or "route").strip().lower() == demand_kind
        )
        unresolved_for_day = max(unresolved_for_day, 1)
    pressure = unresolved_for_day / float(planned_count)
    if "rescue" in str(route_slot.route_slot_class or ""):
        pressure += 0.15
    elif "overflow" in str(route_slot.route_slot_class or ""):
        pressure += 0.10
    return _clamp01(pressure)


def _driver_day_record(*, availability: Any, service_date: str) -> DriverServiceDayState | None:
    if availability is None:
        return None
    for state in getattr(availability, "daily_states", ()):
        if state.service_date == service_date:
            return state
    return None


def _availability_state_label(*, driver_day: DriverServiceDayState | None, fallback: str = "") -> str:
    if driver_day is not None:
        state = str(getattr(driver_day, "state", "") or "").strip().upper()
        if state:
            return state
    token = str(fallback or "").strip().upper()
    if token:
        return token
    return "UNKNOWN"


def _availability_state_fit(
    *,
    route_slot: RouteSlotRequirement,
    availability_state: str,
    availability: Any,
) -> float:
    if availability_state == "PREFERRED":
        fit = 1.0
    elif availability_state == "AVAILABLE":
        fit = 0.84
    elif availability_state == "AVOID_IF_POSSIBLE":
        fit = 0.38
    elif availability_state == "ON_CALL_ONLY":
        fit = 0.62 if _is_flexible_slot(route_slot) else 0.18
    elif availability_state in {"CANNOT", "PATTERN_OFF"}:
        fit = 0.0
    else:
        fit = 0.6
    if availability is not None and bool(getattr(availability, "on_call_eligible", False)):
        if _is_flexible_slot(route_slot):
            fit += 0.08
    return _clamp01(fit)


def _preferred_shift_band_fit(
    *,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    driver_day: DriverServiceDayState | None,
) -> float:
    preferred_band = ""
    if driver_day is not None and str(driver_day.preferred_shift_band or "").strip():
        preferred_band = str(driver_day.preferred_shift_band or "").strip().lower()
    elif str(driver.preferred_shift_band or "").strip():
        preferred_band = str(driver.preferred_shift_band or "").strip().lower()

    route_band = str(route_slot.preferred_shift_band or "").strip().lower()
    if not preferred_band:
        return 0.72 if route_band else 0.7
    if not route_band:
        return 0.76
    if preferred_band == route_band:
        return 1.0
    if {preferred_band, route_band} <= {"rescue", "overflow"}:
        return 0.65
    return 0.18


def _preferred_route_slot_class_fit(
    *,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    driver_day: DriverServiceDayState | None,
) -> float:
    preferred = set(driver.preferred_route_slot_classes)
    avoided: set[str] = set()
    if driver_day is not None:
        preferred |= set(driver_day.preferred_route_slot_classes)
        avoided |= set(driver_day.avoid_route_slot_classes)
    route_slot_class = str(route_slot.route_slot_class or "")
    if route_slot_class in preferred:
        return 1.0
    if route_slot_class in avoided:
        return 0.08
    if preferred:
        return 0.55
    return 0.72


def _avoidable_assignment_score(
    *,
    route_slot: RouteSlotRequirement,
    availability_state: str,
    driver: DriverCapability,
    driver_day: DriverServiceDayState | None,
) -> float:
    if availability_state == "PREFERRED":
        score = 1.0
    elif availability_state == "AVAILABLE":
        score = 0.88
    elif availability_state == "AVOID_IF_POSSIBLE":
        score = 0.22
    elif availability_state == "ON_CALL_ONLY":
        score = 0.46 if _is_flexible_slot(route_slot) else 0.12
    else:
        score = 0.0
    route_slot_class = str(route_slot.route_slot_class or "")
    avoided = set(driver_day.avoid_route_slot_classes) if driver_day is not None else set()
    preferred = set(driver.preferred_route_slot_classes)
    if driver_day is not None:
        preferred |= set(driver_day.preferred_route_slot_classes)
    if route_slot_class in avoided:
        score = min(score, 0.12)
    if route_slot_class in preferred:
        score += 0.08
    return _clamp01(score)


def _on_call_coverage(
    *,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    availability: Any,
    availability_state: str,
) -> float:
    if _is_flexible_slot(route_slot):
        if availability_state == "ON_CALL_ONLY":
            return 1.0
        if availability is not None and bool(getattr(availability, "on_call_eligible", False)):
            return 0.95
        if "on_call" in set(driver.skills):
            return 0.9
        return 0.62
    if availability_state == "ON_CALL_ONLY":
        return 0.2
    if availability is not None and bool(getattr(availability, "on_call_eligible", False)):
        return 0.42
    return 0.78


def _previous_week_continuity(
    *,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    availability: Any,
    driver_day: DriverServiceDayState | None,
) -> float:
    if availability is None:
        return 0.35
    previous = _matching_previous_week_state(
        availability=availability,
        route_slot=route_slot,
        driver_day=driver_day,
    )
    if previous is None:
        base = 0.35
    else:
        raw_state = str(
            getattr(previous, "state", "")
            or getattr(previous, "previous_week_state", "")
            or getattr(previous, "normalized_state", "")
            or ""
        ).strip().upper()
        normalized_state = str(getattr(previous, "normalized_state", "") or "").strip()
        previous_route_id = str(getattr(previous, "route_id", "") or "").strip().upper()
        previous_slot_class = str(getattr(previous, "route_slot_class", "") or "").strip()
        route_id = str(route_slot.route_id or "").strip().upper()
        route_slot_class = str(route_slot.route_slot_class or "").strip()
        if raw_state == "WORKED" and previous_route_id and previous_route_id == route_id:
            base = 1.0
        elif raw_state == "WORKED" and previous_slot_class and previous_slot_class == route_slot_class:
            base = 0.86
        elif raw_state == "WORKED":
            base = 0.68
        elif raw_state == "DISPATCH":
            base = 0.58 if previous_slot_class == route_slot_class else 0.42
        elif raw_state == "ON_CALL":
            base = 0.42 if _is_flexible_slot(route_slot) else 0.26
        elif raw_state == "CANCELLED":
            base = 0.08
        elif raw_state == "SICK_CALL":
            base = 0.04
        elif raw_state == "NA":
            base = 0.08
        elif normalized_state == "worked":
            base = 0.64
        elif normalized_state == "available_not_assigned":
            base = 0.16
        elif normalized_state == "blocked_previous_week":
            base = 0.08
        else:
            base = 0.12
    tags = set(driver.policy_tags) | set(getattr(availability, "policy_tags", ()))
    if "stability_preferred" in tags and base > 0.0:
        base += 0.08
    if "anchor" in tags and base >= 0.6:
        base += 0.04
    if "stable_recent_history" in tags and base >= 0.4:
        base += 0.05
    return _clamp01(base)


def _matching_previous_week_state(
    *,
    availability: Any,
    route_slot: RouteSlotRequirement,
    driver_day: DriverServiceDayState | None,
) -> Any:
    previous_states = list(getattr(availability, "previous_week_states", ()))
    if driver_day is not None and str(driver_day.previous_week_state or "").strip():
        weekday = _weekday_token(route_slot.service_date)
        for item in previous_states:
            if _weekday_token(item.service_date) == weekday:
                return item
        return driver_day
    weekday = _weekday_token(route_slot.service_date)
    for item in previous_states:
        if _weekday_token(item.service_date) == weekday:
            return item
    return None


def _seniority_preference_fit(
    *,
    bundle: WeeklyScheduleControlBundle,
    driver: DriverCapability,
    availability: Any,
    preference_fit: float,
    continuity_score: float,
) -> float:
    rank = int(driver.seniority_rank or 0)
    ranked = sorted(item.seniority_rank for item in bundle.drivers if int(item.seniority_rank or 0) > 0)
    if rank > 0 and ranked:
        seniority_base = 1.0 - ((rank - 1) / float(max(ranked[-1] - 1, 1)))
    else:
        employment_type = str(
            driver.employment_type or getattr(availability, "employment_type", "") or ""
        ).strip()
        seniority_base = 0.82 if employment_type == "full_time" else 0.58
    desirability = max(preference_fit, continuity_score)
    score = 0.45 + (0.55 * seniority_base * desirability)
    tags = set(driver.policy_tags) | set(getattr(availability, "policy_tags", ()))
    if "anchor" in tags:
        score += 0.05
    return _clamp01(score)


def _reliability_score(
    *,
    driver: DriverCapability,
    availability: Any,
    driver_day: DriverServiceDayState | None,
) -> float:
    if driver.attendance_reliability_index > 0:
        base = float(driver.attendance_reliability_index)
    elif availability is None:
        base = 0.6
    else:
        previous_states = tuple(getattr(availability, "previous_week_states", ()))
        worked = sum(
            1
            for item in previous_states
            if str(getattr(item, "normalized_state", "") or item.state or "") == "worked"
        )
        active = sum(
            1
            for item in previous_states
            if str(getattr(item, "normalized_state", "") or item.state or "")
            in {"worked", "available_not_assigned", "blocked_previous_week"}
        )
        base = 0.6 if active == 0 else _clamp01(worked / float(active))
    penalty = (driver.recent_sick_calls_14d * 0.08) + (driver.recent_cancellations_14d * 0.06)
    raw_previous = str(driver_day.previous_week_state or "").strip().upper() if driver_day is not None else ""
    if raw_previous == "SICK_CALL":
        penalty += 0.04
    if raw_previous == "CANCELLED":
        penalty += 0.03
    tags = set(driver.policy_tags) | set(getattr(availability, "policy_tags", ()))
    if "attendance_clean" in tags:
        base += 0.05
    if "restricted_close" in tags:
        penalty += 0.02
    return _clamp01(base - penalty)


def _is_flexible_slot(route_slot: RouteSlotRequirement) -> bool:
    if route_slot.is_on_call_demand:
        return True
    route_slot_class = str(route_slot.route_slot_class or "").lower()
    route_band = str(route_slot.preferred_shift_band or "").lower()
    return "rescue" in route_slot_class or "overflow" in route_slot_class or route_band in {
        "rescue",
        "overflow",
    }


def _planned_driver_day_state_for_slot(route_slot: RouteSlotRequirement) -> str:
    return "on_call" if route_slot.is_on_call_demand else "assigned"


def _work_distribution_priority_rank(
    *,
    current_week_shift_count: int,
    projected_week_shift_count: int,
) -> int:
    if current_week_shift_count < 3 and projected_week_shift_count >= 3:
        return 0
    if current_week_shift_count < 4 and projected_week_shift_count >= 4:
        return 1
    if current_week_shift_count < 3:
        return 2
    if projected_week_shift_count <= 4:
        return 3
    return 4


def _overtime_priority_rank(*, projected_week_shift_count: int) -> int:
    return 1 if projected_week_shift_count >= 5 else 0


def _reaches_minimum_work(
    *,
    current_week_shift_count: int,
    projected_week_shift_count: int,
) -> int:
    return int(current_week_shift_count < 3 and projected_week_shift_count >= 3)


def _reaches_preferred_work(
    *,
    current_week_shift_count: int,
    projected_week_shift_count: int,
) -> int:
    return int(current_week_shift_count < 4 and projected_week_shift_count >= 4)


def _weekday_token(service_date: str) -> str:
    return date.fromisoformat(service_date).strftime("%a")
