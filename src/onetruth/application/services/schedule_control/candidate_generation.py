from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bundle_builder import WeeklyScheduleControlBundle
from .route_slot_requirements import expand_route_slot_requirements
from .scoring import deterministic_rank_candidates, score_candidate
from .validation import evaluate_hard_constraints


@dataclass(frozen=True)
class CandidateEvaluation:
    route_slot_id: str
    service_date: str
    candidate_driver_id: str
    hard_filter_status: str
    hard_filter_reasons: tuple[str, ...]
    soft_score_total: float
    score_bucket: str
    projected_minutes: int
    fairness_balance: float
    on_call_coverage: float
    lost_work_credit: float

    def to_row(self) -> dict[str, Any]:
        return {
            "route_slot_id": self.route_slot_id,
            "service_date": self.service_date,
            "candidate_driver_id": self.candidate_driver_id,
            "hard_filter_status": self.hard_filter_status,
            "hard_filter_reasons": list(self.hard_filter_reasons),
            "soft_score_total": self.soft_score_total,
            "score_bucket": self.score_bucket,
            "projected_minutes": self.projected_minutes,
            "fairness_balance": self.fairness_balance,
            "on_call_coverage": self.on_call_coverage,
            "lost_work_credit": self.lost_work_credit,
        }


def generate_weekly_candidate_matrix(
    *,
    bundle: WeeklyScheduleControlBundle,
) -> list[CandidateEvaluation]:
    candidates: list[CandidateEvaluation] = []
    expanded_slots = expand_route_slot_requirements(bundle.route_slots)
    for route_slot in expanded_slots:
        for driver in bundle.drivers:
            hard_validation = evaluate_hard_constraints(
                bundle=bundle,
                route_slot=route_slot,
                driver=driver,
            )
            soft_score = score_candidate(
                bundle=bundle,
                route_slot=route_slot,
                driver=driver,
                hard_validation=hard_validation,
            )
            candidates.append(
                CandidateEvaluation(
                    route_slot_id=route_slot.route_slot_id,
                    service_date=route_slot.service_date,
                    candidate_driver_id=driver.driver_id,
                    hard_filter_status=hard_validation.status,
                    hard_filter_reasons=hard_validation.reasons,
                    soft_score_total=soft_score.total,
                    score_bucket=soft_score.bucket,
                    projected_minutes=route_slot.projected_minutes,
                    fairness_balance=soft_score.fairness_balance,
                    on_call_coverage=soft_score.on_call_coverage,
                    lost_work_credit=soft_score.lost_work_credit,
                )
            )
    return sorted(
        candidates,
        key=lambda item: (
            item.service_date,
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
        selected_rows.append(
            {
                "service_date": selected["service_date"],
                "route_slot_id": selected["route_slot_id"],
                "candidate_driver_id": selected["candidate_driver_id"],
                "hard_filter_status": selected["hard_filter_status"],
                "hard_filter_reasons": list(selected.get("hard_filter_reasons") or []),
                "score_bucket": selected["score_bucket"],
                "soft_score_total": float(selected.get("soft_score_total") or 0.0),
                "projected_minutes": int(selected.get("projected_minutes") or 0),
                "fairness_balance": float(selected.get("fairness_balance") or 0.0),
                "on_call_coverage": float(selected.get("on_call_coverage") or 0.0),
                "lost_work_credit": float(selected.get("lost_work_credit") or 0.0),
                "assignment_action": (
                    "assign"
                    if str(selected.get("hard_filter_status") or "") == "pass"
                    else "unassigned"
                ),
                "rationale_code": _rationale_code(selected),
            }
        )
    return selected_rows


def _rationale_code(candidate_row: dict[str, Any]) -> str:
    status = str(candidate_row.get("hard_filter_status") or "")
    if status != "pass":
        reason = next(iter(candidate_row.get("hard_filter_reasons") or []), "blocked")
        return f"hard_filter_{reason}"

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
