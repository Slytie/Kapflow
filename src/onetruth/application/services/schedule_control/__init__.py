from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bundle_builder import (
    ActualHoursEntry,
    DailyDemandSummary,
    DriverAvailability,
    DriverCapability,
    DriverPolicySignal,
    DriverServiceDayState,
    Rolling7ComplianceSnapshot,
    WeeklyScheduleControlBundle,
    build_weekly_schedule_control_bundle,
)
from .candidate_generation import (
    CandidateEvaluation,
    generate_weekly_candidate_matrix,
    select_weekly_candidates,
)
from .iterative_allocator import (
    IterationExecutionResult,
    IterativeAllocationResult,
    execute_next_weekly_allocation_iteration,
    run_iterative_weekly_allocation,
)
from .planning_state import IterationSummary, PartialWeeklyScheduleState, RepairMove, ScheduledAssignment
from .rendering import (
    render_stage04_candidate_delta,
    render_stage04_draft_weekly_schedule_doc,
    render_stage04_draft_weekly_schedule_workbook,
    render_stage04_input_bundle,
    render_stage04_validation_summary,
)
from .reserve_selection import ReserveSelectionResult, select_on_call_reserve_rows
from .route_slot_requirements import RouteSlotRequirement, expand_route_slot_requirements
from .scoring import deterministic_rank_candidates, score_candidate, summarize_soft_scores
from .validation import HardValidationResult, evaluate_hard_constraints


@dataclass(frozen=True)
class Stage04DeterministicBuildResult:
    bundle: WeeklyScheduleControlBundle
    candidate_matrix: list[CandidateEvaluation]
    selected_candidates: list[dict[str, Any]]
    reserve_rows: list[dict[str, Any]]
    reserve_summary: dict[str, Any]
    iteration_summaries: list[dict[str, Any]]
    repair_moves: list[dict[str, Any]]
    coverage_summary: dict[str, Any]
    input_bundle_payload: dict[str, Any]
    candidate_delta_payload: dict[str, Any]
    validation_summary_payload: dict[str, Any]
    draft_workbook_payload: dict[str, Any]
    draft_doc_payload: dict[str, Any]


def run_weekly_stage04_deterministic_build(
    *,
    bundle: WeeklyScheduleControlBundle,
) -> Stage04DeterministicBuildResult:
    allocation_result = run_iterative_weekly_allocation(bundle=bundle)
    reserve_result = select_on_call_reserve_rows(
        bundle=bundle,
        selected_candidates=allocation_result.selected_candidates,
        iteration_index=len(allocation_result.iteration_summaries) + 1,
    )
    return build_stage04_deterministic_outputs(
        bundle=bundle,
        candidate_matrix=allocation_result.candidate_matrix,
        selected_candidates=allocation_result.selected_candidates,
        reserve_rows=reserve_result.reserve_rows,
        reserve_summary=reserve_result.reserve_summary,
        iteration_summaries=allocation_result.iteration_summaries,
        repair_moves=allocation_result.repair_moves,
        coverage_summary=allocation_result.coverage_summary,
    )


def build_stage04_deterministic_outputs(
    *,
    bundle: WeeklyScheduleControlBundle,
    candidate_matrix: list[CandidateEvaluation],
    selected_candidates: list[dict[str, Any]],
    reserve_rows: list[dict[str, Any]] | None = None,
    reserve_summary: dict[str, Any] | None = None,
    iteration_summaries: list[IterationSummary],
    repair_moves: list[RepairMove],
    coverage_summary: dict[str, Any],
) -> Stage04DeterministicBuildResult:
    resolved_reserve_rows = list(reserve_rows or [])
    resolved_reserve_summary = dict(reserve_summary or {})
    input_bundle_payload = render_stage04_input_bundle(bundle=bundle)
    candidate_delta_payload = render_stage04_candidate_delta(
        bundle=bundle,
        selected_candidates=selected_candidates,
        reserve_rows=resolved_reserve_rows,
        iteration_summaries=iteration_summaries,
        repair_moves=repair_moves,
        coverage_summary=coverage_summary,
    )
    candidate_delta_id = str(candidate_delta_payload.get("candidate_delta_id") or "")
    validation_summary_payload = render_stage04_validation_summary(
        bundle=bundle,
        selected_candidates=selected_candidates,
        reserve_rows=resolved_reserve_rows,
        reserve_summary=resolved_reserve_summary,
        candidate_delta_id=candidate_delta_id,
        iteration_summaries=iteration_summaries,
        repair_moves=repair_moves,
        coverage_summary=coverage_summary,
    )
    draft_workbook_payload = render_stage04_draft_weekly_schedule_workbook(
        bundle=bundle,
        selected_candidates=selected_candidates,
        reserve_rows=resolved_reserve_rows,
        candidate_delta_id=candidate_delta_id,
        iteration_summaries=iteration_summaries,
    )
    draft_doc_payload = render_stage04_draft_weekly_schedule_doc(
        bundle=bundle,
        validation_summary=validation_summary_payload,
        selected_candidates=selected_candidates,
        reserve_rows=resolved_reserve_rows,
        reserve_summary=resolved_reserve_summary,
        iteration_summaries=iteration_summaries,
        coverage_summary=coverage_summary,
    )

    return Stage04DeterministicBuildResult(
        bundle=bundle,
        candidate_matrix=candidate_matrix,
        selected_candidates=selected_candidates,
        reserve_rows=resolved_reserve_rows,
        reserve_summary=resolved_reserve_summary,
        iteration_summaries=[item.to_payload() for item in iteration_summaries],
        repair_moves=[item.to_payload() for item in repair_moves],
        coverage_summary=coverage_summary,
        input_bundle_payload=input_bundle_payload,
        candidate_delta_payload=candidate_delta_payload,
        validation_summary_payload=validation_summary_payload,
        draft_workbook_payload=draft_workbook_payload,
        draft_doc_payload=draft_doc_payload,
    )


__all__ = [
    "CandidateEvaluation",
    "ActualHoursEntry",
    "DailyDemandSummary",
    "DriverAvailability",
    "DriverCapability",
    "DriverPolicySignal",
    "DriverServiceDayState",
    "HardValidationResult",
    "IterationSummary",
    "IterationExecutionResult",
    "IterativeAllocationResult",
    "PartialWeeklyScheduleState",
    "RepairMove",
    "ReserveSelectionResult",
    "RouteSlotRequirement",
    "ScheduledAssignment",
    "Rolling7ComplianceSnapshot",
    "Stage04DeterministicBuildResult",
    "WeeklyScheduleControlBundle",
    "build_weekly_schedule_control_bundle",
    "deterministic_rank_candidates",
    "evaluate_hard_constraints",
    "expand_route_slot_requirements",
    "execute_next_weekly_allocation_iteration",
    "generate_weekly_candidate_matrix",
    "build_stage04_deterministic_outputs",
    "run_iterative_weekly_allocation",
    "run_weekly_stage04_deterministic_build",
    "score_candidate",
    "select_on_call_reserve_rows",
    "select_weekly_candidates",
    "summarize_soft_scores",
]
