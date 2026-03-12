from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bundle_builder import (
    DriverAvailability,
    DriverCapability,
    WeeklyScheduleControlBundle,
    build_weekly_schedule_control_bundle,
)
from .candidate_generation import (
    CandidateEvaluation,
    generate_weekly_candidate_matrix,
    select_weekly_candidates,
)
from .rendering import (
    render_stage04_candidate_delta,
    render_stage04_draft_weekly_schedule_doc,
    render_stage04_draft_weekly_schedule_workbook,
    render_stage04_input_bundle,
    render_stage04_validation_summary,
)
from .route_slot_requirements import RouteSlotRequirement, expand_route_slot_requirements
from .scoring import deterministic_rank_candidates, score_candidate, summarize_soft_scores
from .validation import HardValidationResult, evaluate_hard_constraints


@dataclass(frozen=True)
class Stage04DeterministicBuildResult:
    bundle: WeeklyScheduleControlBundle
    candidate_matrix: list[CandidateEvaluation]
    selected_candidates: list[dict[str, Any]]
    input_bundle_payload: dict[str, Any]
    candidate_delta_payload: dict[str, Any]
    validation_summary_payload: dict[str, Any]
    draft_workbook_payload: dict[str, Any]
    draft_doc_payload: dict[str, Any]


def run_weekly_stage04_deterministic_build(
    *,
    bundle: WeeklyScheduleControlBundle,
) -> Stage04DeterministicBuildResult:
    candidate_matrix = generate_weekly_candidate_matrix(bundle=bundle)
    selected_candidates = select_weekly_candidates(candidate_matrix)

    input_bundle_payload = render_stage04_input_bundle(bundle=bundle)
    candidate_delta_payload = render_stage04_candidate_delta(
        bundle=bundle,
        selected_candidates=selected_candidates,
    )
    candidate_delta_id = str(candidate_delta_payload.get("candidate_delta_id") or "")
    validation_summary_payload = render_stage04_validation_summary(
        bundle=bundle,
        selected_candidates=selected_candidates,
        candidate_delta_id=candidate_delta_id,
    )
    draft_workbook_payload = render_stage04_draft_weekly_schedule_workbook(
        bundle=bundle,
        selected_candidates=selected_candidates,
        candidate_delta_id=candidate_delta_id,
    )
    draft_doc_payload = render_stage04_draft_weekly_schedule_doc(
        bundle=bundle,
        validation_summary=validation_summary_payload,
        selected_candidates=selected_candidates,
    )

    return Stage04DeterministicBuildResult(
        bundle=bundle,
        candidate_matrix=candidate_matrix,
        selected_candidates=selected_candidates,
        input_bundle_payload=input_bundle_payload,
        candidate_delta_payload=candidate_delta_payload,
        validation_summary_payload=validation_summary_payload,
        draft_workbook_payload=draft_workbook_payload,
        draft_doc_payload=draft_doc_payload,
    )


__all__ = [
    "CandidateEvaluation",
    "DriverAvailability",
    "DriverCapability",
    "HardValidationResult",
    "RouteSlotRequirement",
    "Stage04DeterministicBuildResult",
    "WeeklyScheduleControlBundle",
    "build_weekly_schedule_control_bundle",
    "deterministic_rank_candidates",
    "evaluate_hard_constraints",
    "expand_route_slot_requirements",
    "generate_weekly_candidate_matrix",
    "run_weekly_stage04_deterministic_build",
    "score_candidate",
    "select_weekly_candidates",
    "summarize_soft_scores",
]
