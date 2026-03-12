from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bundle_builder import DriverCapability, WeeklyScheduleControlBundle
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


@dataclass(frozen=True)
class SoftScore:
    total: float
    fairness_balance: float
    on_call_coverage: float
    lost_work_credit: float
    bucket: str


def score_candidate(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
    hard_validation: HardValidationResult,
) -> SoftScore:
    if hard_validation.status != "pass":
        return SoftScore(
            total=0.0,
            fairness_balance=0.0,
            on_call_coverage=0.0,
            lost_work_credit=0.0,
            bucket="blocked",
        )

    availability = bundle.availability_by_driver.get(driver.driver_id)
    target_shifts = max(int(getattr(availability, "target_shifts_per_week", 4)), 1)
    expected_target_minutes = target_shifts * 480
    observed_minutes = int(bundle.actual_minutes_by_driver.get(driver.driver_id, 0))

    fairness_balance = _clamp01((expected_target_minutes - observed_minutes) / float(expected_target_minutes))
    on_call_coverage = (
        1.0
        if availability is not None and bool(availability.on_call_eligible)
        else (0.8 if "on_call" in set(driver.skills) else 0.5)
    )
    lost_work_credit = _clamp01(
        (expected_target_minutes - observed_minutes + route_slot.projected_minutes)
        / float(expected_target_minutes)
    )

    total = (0.5 * fairness_balance) + (0.3 * on_call_coverage) + (0.2 * lost_work_credit)
    bucket = _score_bucket_for_total(total)
    return SoftScore(
        total=round(total, 6),
        fairness_balance=round(fairness_balance, 6),
        on_call_coverage=round(on_call_coverage, 6),
        lost_work_credit=round(lost_work_credit, 6),
        bucket=bucket,
    )


def deterministic_rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        hard_filter_status = str(item.get("hard_filter_status", "blocked")).strip().lower()
        score_bucket = str(item.get("score_bucket", "blocked")).strip().lower()
        candidate_driver_id = str(item.get("candidate_driver_id", ""))
        return (
            _HARD_FILTER_ORDER.get(hard_filter_status, 99),
            _SCORE_BUCKET_ORDER.get(score_bucket, 99),
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
        }

    count = float(len(pass_candidates))
    return {
        "fairness_balance": sum(float(item.get("fairness_balance") or 0.0) for item in pass_candidates)
        / count,
        "on_call_coverage": sum(float(item.get("on_call_coverage") or 0.0) for item in pass_candidates)
        / count,
        "lost_work_credit": sum(float(item.get("lost_work_credit") or 0.0) for item in pass_candidates)
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
