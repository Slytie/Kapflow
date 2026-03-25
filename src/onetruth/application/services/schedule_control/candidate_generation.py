from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bundle_builder import WeeklyScheduleControlBundle
from .planning_state import PartialWeeklyScheduleState
from .route_slot_requirements import expand_route_slot_requirements
from .scoring import deterministic_rank_candidates, score_candidate
from .validation import evaluate_hard_constraints


@dataclass(frozen=True)
class CandidateEvaluation:
    route_slot_id: str
    route_id: str
    demand_kind: str
    service_date: str
    route_slot_class: str
    station_code: str
    service_area: str
    candidate_driver_id: str
    hard_filter_status: str
    hard_filter_reasons: tuple[str, ...]
    soft_score_total: float
    score_bucket: str
    projected_minutes: int
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
    iteration_index: int = 0
    evaluation_kind: str = "allocate"

    def to_row(self) -> dict[str, Any]:
        return {
            "route_slot_id": self.route_slot_id,
            "route_id": self.route_id,
            "demand_kind": self.demand_kind,
            "service_date": self.service_date,
            "route_slot_class": self.route_slot_class,
            "station_code": self.station_code,
            "service_area": self.service_area,
            "candidate_driver_id": self.candidate_driver_id,
            "hard_filter_status": self.hard_filter_status,
            "hard_filter_reasons": list(self.hard_filter_reasons),
            "soft_score_total": self.soft_score_total,
            "score_bucket": self.score_bucket,
            "projected_minutes": self.projected_minutes,
            "fairness_balance": self.fairness_balance,
            "on_call_coverage": self.on_call_coverage,
            "lost_work_credit": self.lost_work_credit,
            "coverage_pressure": self.coverage_pressure,
            "availability_fit": self.availability_fit,
            "availability_state": self.availability_state,
            "availability_state_fit": self.availability_state_fit,
            "preferred_shift_band_fit": self.preferred_shift_band_fit,
            "preferred_route_slot_class_fit": self.preferred_route_slot_class_fit,
            "preference_fit": self.preference_fit,
            "previous_week_stability": self.previous_week_stability,
            "continuity_score": self.continuity_score,
            "target_shift_gap": self.target_shift_gap,
            "seniority_score": self.seniority_score,
            "seniority_preference_fit": self.seniority_preference_fit,
            "reliability_score": self.reliability_score,
            "avoidable_assignment_score": self.avoidable_assignment_score,
            "baseline_template_state": self.baseline_template_state,
            "planned_driver_day_state": self.planned_driver_day_state,
            "new_agreement_required": self.new_agreement_required,
            "new_agreement_trigger_reason": self.new_agreement_trigger_reason,
            "template_state_preservation_fit": self.template_state_preservation_fit,
            "current_week_shift_count": self.current_week_shift_count,
            "projected_rolling7_minutes": self.projected_rolling7_minutes,
            "remaining_rolling7_minutes": self.remaining_rolling7_minutes,
            "iteration_index": self.iteration_index,
            "evaluation_kind": self.evaluation_kind,
        }


def generate_weekly_candidate_matrix(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slots: tuple[Any, ...] | None = None,
    schedule_state: PartialWeeklyScheduleState | None = None,
    iteration_index: int = 0,
    evaluation_kind: str = "allocate",
    exclude_route_slot_ids: set[str] | None = None,
) -> list[CandidateEvaluation]:
    candidates: list[CandidateEvaluation] = []
    expanded_slots = (
        expand_route_slot_requirements(bundle.route_slots)
        if route_slots is None
        else tuple(route_slots)
    )
    for route_slot in expanded_slots:
        for driver in bundle.drivers:
            hard_validation = evaluate_hard_constraints(
                bundle=bundle,
                route_slot=route_slot,
                driver=driver,
                schedule_state=schedule_state,
                exclude_route_slot_ids=exclude_route_slot_ids,
            )
            soft_score = score_candidate(
                bundle=bundle,
                route_slot=route_slot,
                driver=driver,
                hard_validation=hard_validation,
                schedule_state=schedule_state,
            )
            candidates.append(
                CandidateEvaluation(
                    route_slot_id=route_slot.route_slot_id,
                    route_id=route_slot.route_id,
                    demand_kind=str(route_slot.demand_kind or "route"),
                    service_date=route_slot.service_date,
                    route_slot_class=route_slot.route_slot_class,
                    station_code=route_slot.station_code,
                    service_area=route_slot.service_area,
                    candidate_driver_id=driver.driver_id,
                    hard_filter_status=hard_validation.status,
                    hard_filter_reasons=hard_validation.reasons,
                    soft_score_total=soft_score.total,
                    score_bucket=soft_score.bucket,
                    projected_minutes=route_slot.projected_minutes,
                    fairness_balance=soft_score.fairness_balance,
                    on_call_coverage=soft_score.on_call_coverage,
                    lost_work_credit=soft_score.lost_work_credit,
                    coverage_pressure=soft_score.coverage_pressure,
                    availability_fit=soft_score.availability_fit,
                    availability_state=soft_score.availability_state,
                    availability_state_fit=soft_score.availability_state_fit,
                    preferred_shift_band_fit=soft_score.preferred_shift_band_fit,
                    preferred_route_slot_class_fit=soft_score.preferred_route_slot_class_fit,
                    preference_fit=soft_score.preference_fit,
                    previous_week_stability=soft_score.previous_week_stability,
                    continuity_score=soft_score.continuity_score,
                    target_shift_gap=soft_score.target_shift_gap,
                    seniority_score=soft_score.seniority_score,
                    seniority_preference_fit=soft_score.seniority_preference_fit,
                    reliability_score=soft_score.reliability_score,
                    avoidable_assignment_score=soft_score.avoidable_assignment_score,
                    baseline_template_state=soft_score.baseline_template_state,
                    planned_driver_day_state=soft_score.planned_driver_day_state,
                    new_agreement_required=soft_score.new_agreement_required,
                    new_agreement_trigger_reason=soft_score.new_agreement_trigger_reason,
                    template_state_preservation_fit=soft_score.template_state_preservation_fit,
                    current_week_shift_count=soft_score.current_week_shift_count,
                    projected_rolling7_minutes=soft_score.projected_rolling7_minutes,
                    remaining_rolling7_minutes=soft_score.remaining_rolling7_minutes,
                    iteration_index=iteration_index,
                    evaluation_kind=evaluation_kind,
                )
            )
    return sorted(
        candidates,
        key=lambda item: (
            item.service_date,
            item.station_code,
            item.service_area,
            item.route_slot_id,
            item.candidate_driver_id,
        ),
    )


def select_weekly_candidates(candidate_matrix: list[CandidateEvaluation]) -> list[dict[str, Any]]:
    candidates_by_slot: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for candidate in candidate_matrix:
        key = (candidate.service_date, candidate.route_slot_id)
        candidates_by_slot.setdefault(key, []).append(candidate.to_row())

    selected_rows: list[dict[str, Any]] = []
    for key in sorted(candidates_by_slot.keys()):
        ranked_rows = deterministic_rank_candidates(candidates_by_slot[key])
        selected = ranked_rows[0]
        assignment_action = (
            "assign"
            if str(selected.get("hard_filter_status") or "") == "pass"
            else "unassigned"
        )
        selected_rows.append(
            {
                "service_date": selected["service_date"],
                "route_slot_id": selected["route_slot_id"],
                "route_id": selected["route_id"],
                "demand_kind": str(selected.get("demand_kind") or "route"),
                "candidate_driver_id": selected["candidate_driver_id"],
                "hard_filter_status": selected["hard_filter_status"],
                "hard_filter_reasons": list(selected.get("hard_filter_reasons") or []),
                "score_bucket": selected["score_bucket"],
                "soft_score_total": float(selected.get("soft_score_total") or 0.0),
                "projected_minutes": int(selected.get("projected_minutes") or 0),
                "fairness_balance": float(selected.get("fairness_balance") or 0.0),
                "on_call_coverage": float(selected.get("on_call_coverage") or 0.0),
                "lost_work_credit": float(selected.get("lost_work_credit") or 0.0),
                "coverage_pressure": float(selected.get("coverage_pressure") or 0.0),
                "availability_fit": float(selected.get("availability_fit") or 0.0),
                "availability_state": str(selected.get("availability_state") or ""),
                "availability_state_fit": float(selected.get("availability_state_fit") or 0.0),
                "preferred_shift_band_fit": float(
                    selected.get("preferred_shift_band_fit") or 0.0
                ),
                "preferred_route_slot_class_fit": float(
                    selected.get("preferred_route_slot_class_fit") or 0.0
                ),
                "preference_fit": float(selected.get("preference_fit") or 0.0),
                "previous_week_stability": float(
                    selected.get("previous_week_stability") or 0.0
                ),
                "continuity_score": float(selected.get("continuity_score") or 0.0),
                "target_shift_gap": float(selected.get("target_shift_gap") or 0.0),
                "seniority_score": float(selected.get("seniority_score") or 0.0),
                "seniority_preference_fit": float(
                    selected.get("seniority_preference_fit") or 0.0
                ),
                "reliability_score": float(selected.get("reliability_score") or 0.0),
                "avoidable_assignment_score": float(
                    selected.get("avoidable_assignment_score") or 0.0
                ),
                "baseline_template_state": str(selected.get("baseline_template_state") or ""),
                "planned_driver_day_state": (
                    (
                        str(selected.get("planned_driver_day_state") or "assigned")
                        if assignment_action == "assign"
                        else "unassigned"
                    )
                ),
                "new_agreement_required": (
                    bool(selected.get("new_agreement_required"))
                    if assignment_action == "assign"
                    else False
                ),
                "new_agreement_trigger_reason": (
                    str(selected.get("new_agreement_trigger_reason") or "")
                    if assignment_action == "assign"
                    else ""
                ),
                "template_state_preservation_fit": float(
                    selected.get("template_state_preservation_fit") or 0.0
                ),
                "current_week_shift_count": int(selected.get("current_week_shift_count") or 0),
                "projected_rolling7_minutes": int(
                    selected.get("projected_rolling7_minutes") or 0
                ),
                "remaining_rolling7_minutes": int(
                    selected.get("remaining_rolling7_minutes") or 0
                ),
                "assignment_action": assignment_action,
                "rationale_code": _rationale_code(selected),
            }
        )
    return selected_rows


def _rationale_code(candidate_row: dict[str, Any]) -> str:
    status = str(candidate_row.get("hard_filter_status") or "")
    if status != "pass":
        reason = next(iter(candidate_row.get("hard_filter_reasons") or []), "blocked")
        return f"hard_filter_{reason}"

    if float(candidate_row.get("previous_week_stability") or 0.0) >= 0.95:
        return "hard_rules_pass_stability_preserved"
    if float(candidate_row.get("coverage_pressure") or 0.0) >= 0.9:
        return "hard_rules_pass_pressure_relief"

    bucket = str(candidate_row.get("score_bucket") or "")
    if bucket == "best":
        return "hard_rules_pass_soft_rank_best"
    if bucket == "good":
        return "hard_rules_pass_soft_rank_good"
    if bucket == "fair":
        return "hard_rules_pass_soft_rank_fair"
    if bucket == "ok":
        return "hard_rules_pass_soft_rank_ok"
    return "hard_rules_pass_soft_rank_poor"
