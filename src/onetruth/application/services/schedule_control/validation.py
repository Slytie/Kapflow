from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any

from .bundle_builder import DriverCapability, WeeklyScheduleControlBundle
from .route_slot_requirements import RouteSlotRequirement


@dataclass(frozen=True)
class HardValidationResult:
    status: str
    reasons: tuple[str, ...]


def evaluate_hard_constraints(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slot: RouteSlotRequirement,
    driver: DriverCapability,
) -> HardValidationResult:
    failed_reasons: list[str] = []
    blocked_reasons: list[str] = []

    if route_slot.required_skill and route_slot.required_skill not in set(driver.skills):
        failed_reasons.append("missing_required_skill")

    if route_slot.vehicle_type and route_slot.vehicle_type not in set(driver.vehicle_certifications):
        failed_reasons.append("vehicle_not_certified")

    if route_slot.route_slot_class and route_slot.route_slot_class not in set(
        driver.eligible_route_slot_classes
    ):
        blocked_reasons.append("route_slot_class_not_eligible")

    availability = bundle.availability_by_driver.get(driver.driver_id)
    if availability is not None and route_slot.service_date in set(availability.approved_unavailable_dates):
        blocked_reasons.append("driver_unavailable")

    restriction_set = set(driver.approved_restrictions)
    if "no_shift_after_21_30" in restriction_set:
        parsed_end = _parse_hhmm(route_slot.shift_end)
        if parsed_end is not None and parsed_end > time(hour=21, minute=30):
            blocked_reasons.append("restriction_no_shift_after_21_30")

    rolling_minutes_limit = _restriction_prefixed_int(
        restriction_set,
        prefix="max_minutes_rolling7=",
    )
    if rolling_minutes_limit is not None:
        observed_minutes = int(bundle.actual_minutes_by_driver.get(driver.driver_id, 0))
        if observed_minutes + route_slot.projected_minutes > rolling_minutes_limit:
            blocked_reasons.append("rolling_7_day_limit")

    if failed_reasons:
        return HardValidationResult(status="fail", reasons=tuple(sorted(dict.fromkeys(failed_reasons))))
    if blocked_reasons:
        return HardValidationResult(
            status="blocked",
            reasons=tuple(sorted(dict.fromkeys(blocked_reasons))),
        )
    return HardValidationResult(status="pass", reasons=())


def build_stage04_validation_summary(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    soft_score_totals: dict[str, float],
) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []

    for candidate in selected_candidates:
        route_slot_id = str(candidate.get("route_slot_id") or "")
        status = str(candidate.get("hard_filter_status") or "blocked")
        driver_id = str(candidate.get("candidate_driver_id") or "unassigned")
        if status != "pass":
            reason_text = ",".join(str(item) for item in candidate.get("hard_filter_reasons") or [])
            violations.append(
                f"{route_slot_id} unresolved ({driver_id})"
                + (f" [{reason_text}]" if reason_text else "")
            )
            continue
        if str(candidate.get("score_bucket") or "") in {"poor", "ok"}:
            warnings.append(
                f"{driver_id} selected for {route_slot_id} with {candidate.get('score_bucket')} soft score"
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
            "route_slot_coverage",
        ],
        "soft_score_totals": {
            "fairness_balance": round(float(soft_score_totals.get("fairness_balance", 0.0)), 4),
            "on_call_coverage": round(float(soft_score_totals.get("on_call_coverage", 0.0)), 4),
            "lost_work_credit": round(float(soft_score_totals.get("lost_work_credit", 0.0)), 4),
        },
        "violations": violations,
        "warnings": warnings,
        "recommended_action": recommendation,
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


def _validation_summary_id(bundle_id: str) -> str:
    compact = bundle_id.removeprefix("bundle-")
    return f"valsum-{compact}"
