from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bundle_builder import WeeklyScheduleControlBundle
from .candidate_generation import CandidateEvaluation, generate_weekly_candidate_matrix
from .planning_state import (
    IterationSummary,
    PartialWeeklyScheduleState,
    RepairMove,
    ScheduledAssignment,
)
from .route_slot_requirements import RouteSlotRequirement, expand_route_slot_requirements
from .scoring import deterministic_rank_candidates


MIN_ALLOCATION_BATCH_SIZE = 5
MAX_ALLOCATION_BATCH_SIZE = 10
MAX_REPAIR_MOVES_PER_ITERATION = 2
MAX_LOCAL_REPAIR_CANDIDATES = 6
MAX_IMPROVEMENT_MOVES_PER_ITERATION = 2
MAX_IMPROVEMENT_FOCUS_ASSIGNMENTS = 16
MAX_IMPROVEMENT_SWAP_PARTNERS = 3
UNCOVERED_ROUTE_SLOT_PENALTY = 2.5
MIN_MEANINGFUL_SOFT_DELTA = 0.015


@dataclass(frozen=True)
class IterativeAllocationResult:
    candidate_matrix: list[CandidateEvaluation]
    selected_candidates: list[dict[str, Any]]
    iteration_summaries: list[IterationSummary]
    repair_moves: list[RepairMove]
    coverage_summary: dict[str, Any]


@dataclass(frozen=True)
class IterationExecutionResult:
    iteration_index: int
    phase: str
    batch_id: str
    pressure_group_id: str
    pressure_service_date: str
    pressure_station_code: str
    pressure_service_area: str
    candidate_evaluations: tuple[CandidateEvaluation, ...]
    applied_decisions: tuple[ScheduledAssignment, ...]
    repair_moves: tuple[RepairMove, ...]
    rejected_move_reasons: tuple[str, ...]
    summary: IterationSummary
    coverage_summary: dict[str, Any]


@dataclass(frozen=True)
class ScheduleQualitySnapshot:
    assigned_route_slots: int
    uncovered_route_slots: int
    soft_objective_total: float
    stability_total: float
    target_shift_gap_total: float
    preference_fit_total: float


@dataclass(frozen=True)
class MoveProposal:
    assignments: tuple[ScheduledAssignment, ...]
    move: RepairMove
    quality_after: ScheduleQualitySnapshot
    tie_breaker: str


def run_iterative_weekly_allocation(
    *,
    bundle: WeeklyScheduleControlBundle,
) -> IterativeAllocationResult:
    expanded_slots = expand_route_slot_requirements(bundle.route_slots)
    schedule_state = PartialWeeklyScheduleState.from_route_slots(expanded_slots)
    candidate_matrix: list[CandidateEvaluation] = []

    while execute_next_weekly_allocation_iteration(
        bundle=bundle,
        schedule_state=schedule_state,
        candidate_matrix=candidate_matrix,
    ) is not None:
        pass

    coverage_summary = _coverage_summary(schedule_state)
    return IterativeAllocationResult(
        candidate_matrix=candidate_matrix,
        selected_candidates=[item.to_row() for item in schedule_state.final_decisions()],
        iteration_summaries=list(schedule_state.iteration_summaries),
        repair_moves=list(schedule_state.repair_moves),
        coverage_summary=coverage_summary,
    )


def execute_next_weekly_allocation_iteration(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
) -> IterationExecutionResult | None:
    if schedule_state.remaining_route_slots():
        return _execute_baseline_iteration(
            bundle=bundle,
            schedule_state=schedule_state,
            candidate_matrix=candidate_matrix,
        )

    improvement_iterations_completed = sum(
        1 for item in schedule_state.iteration_summaries if item.phase == "improvement"
    )
    if improvement_iterations_completed >= _improvement_iteration_budget(schedule_state):
        return None
    return _execute_improvement_iteration(
        bundle=bundle,
        schedule_state=schedule_state,
        candidate_matrix=candidate_matrix,
    )


def _execute_baseline_iteration(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
) -> IterationExecutionResult:
    iteration_index = len(schedule_state.iteration_summaries) + 1
    batch_slots, pressure_group = _select_batch(bundle=bundle, schedule_state=schedule_state)
    batch_slots = tuple(
        sorted(
            batch_slots,
            key=lambda slot: _baseline_slot_priority(
                bundle=bundle,
                schedule_state=schedule_state,
                route_slot=slot,
            ),
        )
    )
    batch_id = f"{bundle.bundle_id}:iter-{iteration_index:02d}"
    candidate_start = len(candidate_matrix)
    coverage_before = _coverage_summary(schedule_state)
    quality_before = _schedule_quality_snapshot(schedule_state)

    uncovered_slots = _allocate_batch(
        bundle=bundle,
        batch_slots=batch_slots,
        schedule_state=schedule_state,
        candidate_matrix=candidate_matrix,
        iteration_index=iteration_index,
        batch_id=batch_id,
        pressure_group_id=pressure_group["pressure_group_id"],
        phase="baseline",
    )
    repair_count_before = len(schedule_state.repair_moves)
    rejected_reasons: list[str] = []
    if uncovered_slots:
        rejected_reasons.extend(
            _attempt_repairs(
                bundle=bundle,
                uncovered_slots=uncovered_slots,
                schedule_state=schedule_state,
                candidate_matrix=candidate_matrix,
                iteration_index=iteration_index,
                batch_id=batch_id,
                pressure_group_id=pressure_group["pressure_group_id"],
                phase="baseline",
                max_moves=MAX_REPAIR_MOVES_PER_ITERATION,
            )
        )

    for slot in batch_slots:
        if schedule_state.has_decision(slot.route_slot_id):
            continue
        schedule_state.record_unassigned(
            _unassigned_decision(
                route_slot=slot,
                iteration_index=iteration_index,
                batch_id=batch_id,
                pressure_group_id=pressure_group["pressure_group_id"],
                phase="baseline",
            )
        )

    coverage_after = _coverage_summary(schedule_state)
    quality_after = _schedule_quality_snapshot(schedule_state)
    quality_delta = _quality_delta(before=quality_before, after=quality_after)
    batch_route_slot_ids = tuple(slot.route_slot_id for slot in batch_slots)
    assigned_route_slot_ids = tuple(
        route_slot_id
        for route_slot_id in batch_route_slot_ids
        if schedule_state.decisions_by_slot[route_slot_id].assignment_action != "unassigned"
    )
    uncovered_route_slot_ids = tuple(
        route_slot_id
        for route_slot_id in batch_route_slot_ids
        if schedule_state.decisions_by_slot[route_slot_id].assignment_action == "unassigned"
    )
    new_moves = schedule_state.repair_moves[repair_count_before:]
    coverage_after = _coverage_summary_with_pending_iteration(
        schedule_state=schedule_state,
        phase="baseline",
        batch_size=len(batch_slots),
    )
    summary = IterationSummary(
        iteration_index=iteration_index,
        phase="baseline",
        batch_id=batch_id,
        pressure_group_id=pressure_group["pressure_group_id"],
        pressure_service_date=pressure_group["service_date"],
        pressure_station_code=pressure_group["station_code"],
        pressure_service_area=pressure_group["service_area"],
        batch_size=len(batch_slots),
        route_slot_ids=batch_route_slot_ids,
        assigned_route_slot_ids=assigned_route_slot_ids,
        uncovered_route_slot_ids=uncovered_route_slot_ids,
        repair_move_count=len(new_moves),
        covered_route_slot_count_after_iteration=schedule_state.assigned_count(),
        uncovered_route_slot_count_after_iteration=len(schedule_state.uncovered_route_slot_ids()),
        candidate_evaluation_count=len(candidate_matrix) - candidate_start,
        moved_route_slot_ids=tuple(
            sorted(
                {
                    route_slot_id
                    for move in new_moves
                    for route_slot_id in move.affected_route_slot_ids
                }
            )
        ),
        coverage_before=coverage_before,
        coverage_after=coverage_after,
        soft_objective_before=quality_before.soft_objective_total,
        soft_objective_after=quality_after.soft_objective_total,
        soft_objective_delta=quality_delta["soft_objective_delta"],
        stability_delta=quality_delta["stability_delta"],
        target_shift_gap_delta=quality_delta["target_shift_gap_delta"],
        preference_fit_delta=quality_delta["preference_fit_delta"],
        accepted_move_reasons=tuple(
            move.accepted_reason for move in new_moves if move.accepted_reason
        ),
        rejected_move_reasons=tuple(rejected_reasons),
    )
    schedule_state.record_iteration(summary)

    return IterationExecutionResult(
        iteration_index=iteration_index,
        phase="baseline",
        batch_id=batch_id,
        pressure_group_id=pressure_group["pressure_group_id"],
        pressure_service_date=pressure_group["service_date"],
        pressure_station_code=pressure_group["station_code"],
        pressure_service_area=pressure_group["service_area"],
        candidate_evaluations=tuple(candidate_matrix[candidate_start:]),
        applied_decisions=tuple(
            item for item in schedule_state.final_decisions() if item.iteration_index == iteration_index
        ),
        repair_moves=tuple(new_moves),
        rejected_move_reasons=tuple(rejected_reasons),
        summary=summary,
        coverage_summary=coverage_after,
    )


def _execute_improvement_iteration(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
) -> IterationExecutionResult | None:
    iteration_index = len(schedule_state.iteration_summaries) + 1
    focus_slot = _primary_improvement_focus(schedule_state)
    if focus_slot is None:
        return None
    batch_id = f"{bundle.bundle_id}:iter-{iteration_index:02d}"
    pressure_group_id = _pressure_group_id(
        (focus_slot.service_date, focus_slot.station_code, focus_slot.service_area)
    )
    candidate_start = len(candidate_matrix)
    repair_count_before = len(schedule_state.repair_moves)
    coverage_before = _coverage_summary(schedule_state)
    quality_before = _schedule_quality_snapshot(schedule_state)
    rejected_reasons: list[str] = []
    blocked_route_slot_ids: set[str] = set()
    if schedule_state.iteration_summaries:
        previous = schedule_state.iteration_summaries[-1]
        if previous.phase == "improvement":
            blocked_route_slot_ids.update(previous.moved_route_slot_ids)

    accepted_moves = 0
    uncovered_slots = [
        schedule_state.route_slot(route_slot_id)
        for route_slot_id in schedule_state.uncovered_route_slot_ids()
    ]
    if uncovered_slots:
        rejected_reasons.extend(
            _attempt_repairs(
                bundle=bundle,
                uncovered_slots=uncovered_slots,
                schedule_state=schedule_state,
                candidate_matrix=candidate_matrix,
                iteration_index=iteration_index,
                batch_id=batch_id,
                pressure_group_id=pressure_group_id,
                phase="improvement",
                max_moves=MAX_IMPROVEMENT_MOVES_PER_ITERATION,
            )
        )
        accepted_moves = len(schedule_state.repair_moves) - repair_count_before

    while accepted_moves < MAX_IMPROVEMENT_MOVES_PER_ITERATION:
        proposal, proposal_rejections = _best_improvement_move(
            bundle=bundle,
            schedule_state=schedule_state,
            candidate_matrix=candidate_matrix,
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            blocked_route_slot_ids=blocked_route_slot_ids,
        )
        rejected_reasons.extend(proposal_rejections)
        if proposal is None:
            break
        for assignment in proposal.assignments:
            schedule_state.record_assignment(assignment)
        schedule_state.record_repair_move(proposal.move)
        blocked_route_slot_ids.update(proposal.move.affected_route_slot_ids)
        accepted_moves += 1

    if len(schedule_state.repair_moves) == repair_count_before:
        return None

    new_moves = schedule_state.repair_moves[repair_count_before:]
    affected_route_slot_ids = tuple(
        sorted(
            {
                route_slot_id
                for move in new_moves
                for route_slot_id in move.affected_route_slot_ids
            }
        )
    )
    assigned_route_slot_ids = tuple(
        sorted(
            route_slot_id
            for route_slot_id in affected_route_slot_ids
            if schedule_state.decisions_by_slot[route_slot_id].assignment_action != "unassigned"
        )
    )
    uncovered_route_slot_ids = tuple(
        sorted(
            route_slot_id
            for route_slot_id in affected_route_slot_ids
            if schedule_state.decisions_by_slot[route_slot_id].assignment_action == "unassigned"
        )
    )
    coverage_after = _coverage_summary_with_pending_iteration(
        schedule_state=schedule_state,
        phase="improvement",
        batch_size=len(affected_route_slot_ids),
    )
    quality_after = _schedule_quality_snapshot(schedule_state)
    quality_delta = _quality_delta(before=quality_before, after=quality_after)
    summary = IterationSummary(
        iteration_index=iteration_index,
        phase="improvement",
        batch_id=batch_id,
        pressure_group_id=pressure_group_id,
        pressure_service_date=focus_slot.service_date,
        pressure_station_code=focus_slot.station_code,
        pressure_service_area=focus_slot.service_area,
        batch_size=len(affected_route_slot_ids),
        route_slot_ids=affected_route_slot_ids,
        assigned_route_slot_ids=assigned_route_slot_ids,
        uncovered_route_slot_ids=uncovered_route_slot_ids,
        repair_move_count=len(new_moves),
        covered_route_slot_count_after_iteration=schedule_state.assigned_count(),
        uncovered_route_slot_count_after_iteration=len(schedule_state.uncovered_route_slot_ids()),
        candidate_evaluation_count=len(candidate_matrix) - candidate_start,
        moved_route_slot_ids=affected_route_slot_ids,
        coverage_before=coverage_before,
        coverage_after=coverage_after,
        soft_objective_before=quality_before.soft_objective_total,
        soft_objective_after=quality_after.soft_objective_total,
        soft_objective_delta=quality_delta["soft_objective_delta"],
        stability_delta=quality_delta["stability_delta"],
        target_shift_gap_delta=quality_delta["target_shift_gap_delta"],
        preference_fit_delta=quality_delta["preference_fit_delta"],
        accepted_move_reasons=tuple(
            move.accepted_reason for move in new_moves if move.accepted_reason
        ),
        rejected_move_reasons=tuple(rejected_reasons),
    )
    schedule_state.record_iteration(summary)

    return IterationExecutionResult(
        iteration_index=iteration_index,
        phase="improvement",
        batch_id=batch_id,
        pressure_group_id=pressure_group_id,
        pressure_service_date=focus_slot.service_date,
        pressure_station_code=focus_slot.station_code,
        pressure_service_area=focus_slot.service_area,
        candidate_evaluations=tuple(candidate_matrix[candidate_start:]),
        applied_decisions=tuple(
            item for item in schedule_state.final_decisions() if item.iteration_index == iteration_index
        ),
        repair_moves=tuple(new_moves),
        rejected_move_reasons=tuple(rejected_reasons),
        summary=summary,
        coverage_summary=coverage_after,
    )


def _allocate_batch(
    *,
    bundle: WeeklyScheduleControlBundle,
    batch_slots: tuple[RouteSlotRequirement, ...],
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    phase: str,
) -> list[RouteSlotRequirement]:
    uncovered_slots: list[RouteSlotRequirement] = []
    for route_slot in batch_slots:
        slot_candidates = generate_weekly_candidate_matrix(
            bundle=bundle,
            route_slots=(route_slot,),
            schedule_state=schedule_state,
            iteration_index=iteration_index,
            evaluation_kind="allocate",
        )
        candidate_matrix.extend(slot_candidates)
        selected = _select_best_candidate(slot_candidates)
        if selected is None or selected.hard_filter_status != "pass":
            uncovered_slots.append(route_slot)
            continue
        schedule_state.record_assignment(
            _decision_from_candidate(
                selected,
                assignment_action="assign",
                delta_kind="allocation",
                iteration_index=iteration_index,
                batch_id=batch_id,
                pressure_group_id=pressure_group_id,
                phase=phase,
            )
        )
    return uncovered_slots


def _attempt_repairs(
    *,
    bundle: WeeklyScheduleControlBundle,
    uncovered_slots: list[RouteSlotRequirement],
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    phase: str,
    max_moves: int,
) -> list[str]:
    rejected_reasons: list[str] = []
    for uncovered_slot in uncovered_slots:
        if schedule_state.has_decision(uncovered_slot.route_slot_id):
            decision = schedule_state.decisions_by_slot[uncovered_slot.route_slot_id]
            if decision.assignment_action != "unassigned":
                continue
        repairs_used = sum(
            1 for item in schedule_state.repair_moves if item.iteration_index == iteration_index
        )
        if repairs_used >= max_moves:
            return rejected_reasons
        proposal = _best_repair_candidate(
            bundle=bundle,
            uncovered_slot=uncovered_slot,
            schedule_state=schedule_state,
            candidate_matrix=candidate_matrix,
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            phase=phase,
        )
        if proposal is None:
            rejected_reasons.append(f"{uncovered_slot.route_slot_id}: no_compliant_local_repair_found")
            continue
        for assignment in proposal.assignments:
            schedule_state.record_assignment(assignment)
        schedule_state.record_repair_move(proposal.move)
    return rejected_reasons


def _best_repair_candidate(
    *,
    bundle: WeeklyScheduleControlBundle,
    uncovered_slot: RouteSlotRequirement,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    phase: str,
) -> MoveProposal | None:
    local_assignments = _local_repair_assignments(
        uncovered_slot=uncovered_slot,
        schedule_state=schedule_state,
        batch_id=batch_id,
    )
    best_candidate: MoveProposal | None = None
    quality_before = _schedule_quality_snapshot(schedule_state)

    for assignment in local_assignments[:MAX_LOCAL_REPAIR_CANDIDATES]:
        exclusion = {assignment.route_slot_id}
        fill_candidates = generate_weekly_candidate_matrix(
            bundle=bundle,
            route_slots=(uncovered_slot,),
            schedule_state=schedule_state,
            iteration_index=iteration_index,
            evaluation_kind="repair",
            exclude_route_slot_ids=exclusion,
        )
        candidate_matrix.extend(fill_candidates)
        fill_evaluation = next(
            (
                item
                for item in fill_candidates
                if item.candidate_driver_id == assignment.candidate_driver_id
            ),
            None,
        )
        if fill_evaluation is None or fill_evaluation.hard_filter_status != "pass":
            continue

        reassigned_slot = schedule_state.route_slot(assignment.route_slot_id)
        replacement_candidates = generate_weekly_candidate_matrix(
            bundle=bundle,
            route_slots=(reassigned_slot,),
            schedule_state=schedule_state,
            iteration_index=iteration_index,
            evaluation_kind="repair",
            exclude_route_slot_ids=exclusion,
        )
        candidate_matrix.extend(replacement_candidates)
        replacement_evaluation = _select_best_candidate(
            [
                item
                for item in replacement_candidates
                if item.candidate_driver_id != assignment.candidate_driver_id
            ]
        )
        if replacement_evaluation is None or replacement_evaluation.hard_filter_status != "pass":
            continue

        replacement_decision = _decision_from_candidate(
            replacement_evaluation,
            assignment_action="assign",
            delta_kind="repair",
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            phase=phase,
            repair_depth=assignment.repair_depth + 1,
            previous_assignment_driver_id=assignment.candidate_driver_id,
            displaced_route_slot_id=uncovered_slot.route_slot_id,
            displaced_driver_id=assignment.candidate_driver_id,
        )
        filled_decision = _decision_from_candidate(
            fill_evaluation,
            assignment_action="assign",
            delta_kind="repair",
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            phase=phase,
            repair_depth=1,
            previous_assignment_driver_id=assignment.candidate_driver_id,
            displaced_route_slot_id=assignment.route_slot_id,
            displaced_driver_id=assignment.candidate_driver_id,
        )
        temp_state = schedule_state.clone()
        temp_state.record_assignment(replacement_decision)
        temp_state.record_assignment(filled_decision)
        quality_after = _schedule_quality_snapshot(temp_state)
        delta = _quality_delta(before=quality_before, after=quality_after)
        if not _meaningful_improvement(delta):
            continue

        accepted_reason = "coverage_repair_restored_route_slot"
        if delta["preference_fit_delta"] >= MIN_MEANINGFUL_SOFT_DELTA:
            accepted_reason = "coverage_repair_improved_preference_fit"
        elif fill_evaluation.previous_week_stability >= 0.9:
            accepted_reason = "coverage_repair_preserved_previous_week_continuity"

        move = RepairMove(
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            filled_route_slot_id=uncovered_slot.route_slot_id,
            filled_driver_id=assignment.candidate_driver_id,
            reassigned_route_slot_id=assignment.route_slot_id,
            previous_driver_id=assignment.candidate_driver_id,
            replacement_driver_id=replacement_evaluation.candidate_driver_id,
            score_gain=round(delta["soft_objective_delta"], 6),
            repair_reason="coverage_repair",
            move_kind="repair",
            affected_route_slot_ids=tuple(
                sorted({uncovered_slot.route_slot_id, assignment.route_slot_id})
            ),
            soft_objective_delta=delta["soft_objective_delta"],
            stability_delta=delta["stability_delta"],
            target_shift_gap_delta=delta["target_shift_gap_delta"],
            preference_fit_delta=delta["preference_fit_delta"],
            coverage_delta=delta["coverage_delta"],
            accepted_reason=accepted_reason,
        )
        proposal = MoveProposal(
            assignments=(replacement_decision, filled_decision),
            move=move,
            quality_after=quality_after,
            tie_breaker="|".join(
                [
                    uncovered_slot.route_slot_id,
                    assignment.route_slot_id,
                    replacement_evaluation.candidate_driver_id,
                ]
            ),
        )
        if best_candidate is None or _proposal_sort_key(proposal) > _proposal_sort_key(best_candidate):
            best_candidate = proposal

    return best_candidate


def _best_improvement_move(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    blocked_route_slot_ids: set[str],
) -> tuple[MoveProposal | None, list[str]]:
    quality_before = _schedule_quality_snapshot(schedule_state)
    assignments = _improvement_focus_assignments(
        schedule_state=schedule_state,
        blocked_route_slot_ids=blocked_route_slot_ids,
    )
    best_candidate: MoveProposal | None = None
    rejected_reasons: list[str] = []

    for index, assignment in enumerate(assignments):
        direct = _best_direct_reassignment(
            bundle=bundle,
            schedule_state=schedule_state,
            candidate_matrix=candidate_matrix,
            assignment=assignment,
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            quality_before=quality_before,
            blocked_route_slot_ids=blocked_route_slot_ids,
        )
        if direct is not None and (
            best_candidate is None or _proposal_sort_key(direct) > _proposal_sort_key(best_candidate)
        ):
            best_candidate = direct
        elif direct is None:
            rejected_reasons.append(f"{assignment.route_slot_id}: no_positive_reassignment_delta")

        swap = _best_swap_reassignment(
            bundle=bundle,
            schedule_state=schedule_state,
            candidate_matrix=candidate_matrix,
            assignment=assignment,
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            quality_before=quality_before,
            blocked_route_slot_ids=blocked_route_slot_ids,
        )
        if swap is not None and (
            best_candidate is None or _proposal_sort_key(swap) > _proposal_sort_key(best_candidate)
        ):
            best_candidate = swap
        elif swap is None:
            rejected_reasons.append(f"{assignment.route_slot_id}: no_positive_swap_delta")

    return best_candidate, rejected_reasons[:12]


def _best_direct_reassignment(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
    assignment: ScheduledAssignment,
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    quality_before: ScheduleQualitySnapshot,
    blocked_route_slot_ids: set[str],
) -> MoveProposal | None:
    if assignment.route_slot_id in blocked_route_slot_ids:
        return None
    route_slot = schedule_state.route_slot(assignment.route_slot_id)
    exclusion = {assignment.route_slot_id}
    candidates = generate_weekly_candidate_matrix(
        bundle=bundle,
        route_slots=(route_slot,),
        schedule_state=schedule_state,
        iteration_index=iteration_index,
        evaluation_kind="improve",
        exclude_route_slot_ids=exclusion,
    )
    candidate_matrix.extend(candidates)
    ranked = deterministic_rank_candidates([item.to_row() for item in candidates])
    for row in ranked:
        candidate_driver_id = str(row.get("candidate_driver_id") or "")
        if str(row.get("hard_filter_status") or "") != "pass":
            continue
        if candidate_driver_id == assignment.candidate_driver_id:
            continue
        candidate = next(
            (
                item
                for item in candidates
                if item.route_slot_id == assignment.route_slot_id
                and item.candidate_driver_id == candidate_driver_id
            ),
            None,
        )
        if candidate is None:
            continue
        decision = _decision_from_candidate(
            candidate,
            assignment_action="assign",
            delta_kind="improvement",
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            phase="improvement",
            previous_assignment_driver_id=assignment.candidate_driver_id,
            displaced_driver_id=assignment.candidate_driver_id,
        )
        temp_state = schedule_state.clone()
        temp_state.record_assignment(decision)
        quality_after = _schedule_quality_snapshot(temp_state)
        delta = _quality_delta(before=quality_before, after=quality_after)
        if delta["soft_objective_delta"] < MIN_MEANINGFUL_SOFT_DELTA:
            continue
        move = RepairMove(
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            filled_route_slot_id=assignment.route_slot_id,
            filled_driver_id=decision.candidate_driver_id,
            reassigned_route_slot_id=assignment.route_slot_id,
            previous_driver_id=assignment.candidate_driver_id,
            replacement_driver_id=decision.candidate_driver_id,
            score_gain=round(delta["soft_objective_delta"], 6),
            repair_reason="soft_improvement_reassignment",
            move_kind="reassignment",
            affected_route_slot_ids=(assignment.route_slot_id,),
            soft_objective_delta=delta["soft_objective_delta"],
            stability_delta=delta["stability_delta"],
            target_shift_gap_delta=delta["target_shift_gap_delta"],
            preference_fit_delta=delta["preference_fit_delta"],
            coverage_delta=delta["coverage_delta"],
            accepted_reason="soft_objective_improved_without_breaking_compliance",
        )
        return MoveProposal(
            assignments=(decision,),
            move=move,
            quality_after=quality_after,
            tie_breaker=f"reassign|{assignment.route_slot_id}|{decision.candidate_driver_id}",
        )
    return None


def _best_swap_reassignment(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
    assignment: ScheduledAssignment,
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    quality_before: ScheduleQualitySnapshot,
    blocked_route_slot_ids: set[str],
) -> MoveProposal | None:
    if assignment.route_slot_id in blocked_route_slot_ids:
        return None
    partners = _swap_partner_assignments(assignment=assignment, schedule_state=schedule_state)
    best_candidate: MoveProposal | None = None
    for partner in partners[:MAX_IMPROVEMENT_SWAP_PARTNERS]:
        if partner.route_slot_id in blocked_route_slot_ids:
            continue
        exclusion = {assignment.route_slot_id, partner.route_slot_id}
        left_slot = schedule_state.route_slot(assignment.route_slot_id)
        right_slot = schedule_state.route_slot(partner.route_slot_id)
        left_candidates = generate_weekly_candidate_matrix(
            bundle=bundle,
            route_slots=(left_slot,),
            schedule_state=schedule_state,
            iteration_index=iteration_index,
            evaluation_kind="improve",
            exclude_route_slot_ids=exclusion,
        )
        candidate_matrix.extend(left_candidates)
        left_evaluation = next(
            (
                item
                for item in left_candidates
                if item.candidate_driver_id == partner.candidate_driver_id
                and item.hard_filter_status == "pass"
            ),
            None,
        )
        if left_evaluation is None:
            continue

        right_candidates = generate_weekly_candidate_matrix(
            bundle=bundle,
            route_slots=(right_slot,),
            schedule_state=schedule_state,
            iteration_index=iteration_index,
            evaluation_kind="improve",
            exclude_route_slot_ids=exclusion,
        )
        candidate_matrix.extend(right_candidates)
        right_evaluation = next(
            (
                item
                for item in right_candidates
                if item.candidate_driver_id == assignment.candidate_driver_id
                and item.hard_filter_status == "pass"
            ),
            None,
        )
        if right_evaluation is None:
            continue

        left_decision = _decision_from_candidate(
            left_evaluation,
            assignment_action="assign",
            delta_kind="improvement",
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            phase="improvement",
            previous_assignment_driver_id=assignment.candidate_driver_id,
            displaced_route_slot_id=partner.route_slot_id,
            displaced_driver_id=assignment.candidate_driver_id,
        )
        right_decision = _decision_from_candidate(
            right_evaluation,
            assignment_action="assign",
            delta_kind="improvement",
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            phase="improvement",
            previous_assignment_driver_id=partner.candidate_driver_id,
            displaced_route_slot_id=assignment.route_slot_id,
            displaced_driver_id=partner.candidate_driver_id,
        )
        temp_state = schedule_state.clone()
        temp_state.record_assignment(left_decision)
        temp_state.record_assignment(right_decision)
        quality_after = _schedule_quality_snapshot(temp_state)
        delta = _quality_delta(before=quality_before, after=quality_after)
        if delta["soft_objective_delta"] < MIN_MEANINGFUL_SOFT_DELTA:
            continue
        move = RepairMove(
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            filled_route_slot_id=assignment.route_slot_id,
            filled_driver_id=partner.candidate_driver_id,
            reassigned_route_slot_id=partner.route_slot_id,
            previous_driver_id=assignment.candidate_driver_id,
            replacement_driver_id=assignment.candidate_driver_id,
            score_gain=round(delta["soft_objective_delta"], 6),
            repair_reason="soft_improvement_swap",
            move_kind="swap",
            affected_route_slot_ids=tuple(
                sorted({assignment.route_slot_id, partner.route_slot_id})
            ),
            soft_objective_delta=delta["soft_objective_delta"],
            stability_delta=delta["stability_delta"],
            target_shift_gap_delta=delta["target_shift_gap_delta"],
            preference_fit_delta=delta["preference_fit_delta"],
            coverage_delta=delta["coverage_delta"],
            accepted_reason="soft_objective_swap_improved_preference_fit",
        )
        proposal = MoveProposal(
            assignments=(left_decision, right_decision),
            move=move,
            quality_after=quality_after,
            tie_breaker=f"swap|{assignment.route_slot_id}|{partner.route_slot_id}",
        )
        if best_candidate is None or _proposal_sort_key(proposal) > _proposal_sort_key(best_candidate):
            best_candidate = proposal
    return best_candidate


def _select_batch(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
) -> tuple[tuple[RouteSlotRequirement, ...], dict[str, str]]:
    remaining_slots = schedule_state.remaining_route_slots()
    grouped: dict[tuple[str, str, str], list[RouteSlotRequirement]] = {}
    for slot in remaining_slots:
        key = (slot.service_date, slot.station_code, slot.service_area)
        grouped.setdefault(key, []).append(slot)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: _pressure_sort_key(bundle, schedule_state, item[0], item[1]),
    )
    primary_key, primary_slots = ranked_groups[0]
    target_batch_size = _adaptive_batch_size(
        remaining_count=len(remaining_slots),
        group_slots=primary_slots,
        bundle=bundle,
    )

    selected: list[RouteSlotRequirement] = []
    for group_key, slots in ranked_groups:
        for slot in sorted(slots, key=_route_slot_priority):
            selected.append(slot)
            if len(selected) >= target_batch_size:
                break
        if len(selected) >= target_batch_size:
            break

    return (
        tuple(selected),
        {
            "pressure_group_id": _pressure_group_id(primary_key),
            "service_date": primary_key[0],
            "station_code": primary_key[1],
            "service_area": primary_key[2],
        },
    )


def _pressure_sort_key(
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    group_key: tuple[str, str, str],
    slots: list[RouteSlotRequirement],
) -> tuple[float, str, str, str]:
    service_date, station_code, service_area = group_key
    demand = bundle.daily_demand_by_service_date.get(service_date)
    demand_count = max(int(getattr(demand, "planned_route_count", 0)), len(slots), 1)
    assigned_for_day = sum(
        1
        for item in schedule_state.assignments_by_slot.values()
        if item.service_date == service_date
    )
    rescue_count = sum(1 for slot in slots if "rescue" in str(slot.route_slot_class or ""))
    overflow_count = sum(1 for slot in slots if "overflow" in str(slot.route_slot_class or ""))
    pressure = (
        len(slots) * 3
        + max(demand_count - assigned_for_day, 0)
        + (rescue_count * 2)
        + overflow_count
    )
    return (-float(pressure), service_date, station_code, service_area)


def _adaptive_batch_size(
    *,
    remaining_count: int,
    group_slots: list[RouteSlotRequirement],
    bundle: WeeklyScheduleControlBundle,
) -> int:
    if remaining_count <= MAX_ALLOCATION_BATCH_SIZE:
        return max(remaining_count, 1)
    if remaining_count <= MIN_ALLOCATION_BATCH_SIZE:
        return max(remaining_count, 1)
    service_date = group_slots[0].service_date
    demand = bundle.daily_demand_by_service_date.get(service_date)
    pressure_score = len(group_slots)
    pressure_score += max(int(getattr(demand, "rescue_slot_count", 0)), 0)
    pressure_score += max(int(getattr(demand, "overflow_slot_count", 0)), 0)
    if pressure_score >= 18:
        batch_size = 10
    elif pressure_score >= 12:
        batch_size = 8
    elif pressure_score >= 8:
        batch_size = 6
    else:
        batch_size = 5
    batch_size = max(
        min(batch_size, MAX_ALLOCATION_BATCH_SIZE, remaining_count),
        MIN_ALLOCATION_BATCH_SIZE,
    )
    remainder = remaining_count - batch_size
    if 0 < remainder < MIN_ALLOCATION_BATCH_SIZE:
        batch_size = remaining_count - MIN_ALLOCATION_BATCH_SIZE
    return max(
        min(batch_size, MAX_ALLOCATION_BATCH_SIZE, remaining_count),
        MIN_ALLOCATION_BATCH_SIZE,
    )


def _route_slot_priority(route_slot: RouteSlotRequirement) -> tuple[int, str, str]:
    route_slot_class = str(route_slot.route_slot_class or "")
    route_band = str(route_slot.preferred_shift_band or "").lower()
    if "rescue" in route_slot_class:
        priority = 0
    elif "overflow" in route_slot_class:
        priority = 1
    elif route_band == "late" or "late" in route_slot_class:
        priority = 2
    elif route_band == "early" or "early" in route_slot_class:
        priority = 3
    else:
        priority = 4
    return (priority, route_slot.shift_start, route_slot.route_slot_id)


def _baseline_slot_priority(
    *,
    bundle: WeeklyScheduleControlBundle,
    schedule_state: PartialWeeklyScheduleState,
    route_slot: RouteSlotRequirement,
) -> tuple[int, int, str, str]:
    feasible_count = _pass_candidate_count(
        bundle=bundle,
        route_slot=route_slot,
        schedule_state=schedule_state,
    )
    route_priority, shift_start, route_slot_id = _route_slot_priority(route_slot)
    return (feasible_count, route_priority, shift_start, route_slot_id)


def _pass_candidate_count(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slot: RouteSlotRequirement,
    schedule_state: PartialWeeklyScheduleState,
) -> int:
    candidates = generate_weekly_candidate_matrix(
        bundle=bundle,
        route_slots=(route_slot,),
        schedule_state=schedule_state,
        iteration_index=0,
        evaluation_kind="pressure_probe",
    )
    return sum(1 for item in candidates if item.hard_filter_status == "pass")


def _local_repair_assignments(
    *,
    uncovered_slot: RouteSlotRequirement,
    schedule_state: PartialWeeklyScheduleState,
    batch_id: str,
) -> list[ScheduledAssignment]:
    return sorted(
        schedule_state.assignments_by_slot.values(),
        key=lambda item: (
            item.batch_id != batch_id,
            item.service_date != uncovered_slot.service_date,
            item.service_area != uncovered_slot.service_area,
            item.station_code != uncovered_slot.station_code,
            item.preference_fit,
            item.soft_score_total,
            item.iteration_index,
            item.route_slot_id,
        ),
    )


def _swap_partner_assignments(
    *,
    assignment: ScheduledAssignment,
    schedule_state: PartialWeeklyScheduleState,
) -> list[ScheduledAssignment]:
    focus_slot_group = _route_slot_group_token(assignment.route_slot_class)
    return sorted(
        (
            item
            for item in schedule_state.assignments_by_slot.values()
            if item.route_slot_id != assignment.route_slot_id
            and item.candidate_driver_id != assignment.candidate_driver_id
            and item.service_date == assignment.service_date
            and item.station_code == assignment.station_code
            and item.service_area == assignment.service_area
        ),
        key=lambda item: (
            _route_slot_group_token(item.route_slot_class) == focus_slot_group,
            item.preference_fit,
            item.soft_score_total,
            item.route_slot_id,
        ),
    )


def _select_best_candidate(
    candidates: list[CandidateEvaluation],
) -> CandidateEvaluation | None:
    if not candidates:
        return None
    ranked_rows = deterministic_rank_candidates([item.to_row() for item in candidates])
    if not ranked_rows:
        return None
    selected_row = next(
        (item for item in ranked_rows if str(item.get("hard_filter_status") or "") == "pass"),
        ranked_rows[0],
    )
    for candidate in candidates:
        if (
            candidate.route_slot_id == str(selected_row.get("route_slot_id") or "")
            and candidate.candidate_driver_id == str(selected_row.get("candidate_driver_id") or "")
        ):
            return candidate
    return None


def _decision_from_candidate(
    candidate: CandidateEvaluation,
    *,
    assignment_action: str,
    delta_kind: str,
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    phase: str,
    repair_depth: int = 0,
    previous_assignment_driver_id: str = "",
    displaced_route_slot_id: str = "",
    displaced_driver_id: str = "",
) -> ScheduledAssignment:
    return ScheduledAssignment(
        route_slot_id=candidate.route_slot_id,
        route_id=candidate.route_id,
        service_date=candidate.service_date,
        candidate_driver_id=candidate.candidate_driver_id,
        assignment_action=assignment_action,
        hard_filter_status=candidate.hard_filter_status,
        hard_filter_reasons=candidate.hard_filter_reasons,
        score_bucket=candidate.score_bucket,
        soft_score_total=candidate.soft_score_total,
        projected_minutes=candidate.projected_minutes,
        fairness_balance=candidate.fairness_balance,
        on_call_coverage=candidate.on_call_coverage,
        lost_work_credit=candidate.lost_work_credit,
        coverage_pressure=candidate.coverage_pressure,
        availability_fit=candidate.availability_fit,
        availability_state=candidate.availability_state,
        availability_state_fit=candidate.availability_state_fit,
        preferred_shift_band_fit=candidate.preferred_shift_band_fit,
        preferred_route_slot_class_fit=candidate.preferred_route_slot_class_fit,
        preference_fit=candidate.preference_fit,
        previous_week_stability=candidate.previous_week_stability,
        continuity_score=candidate.continuity_score,
        target_shift_gap=candidate.target_shift_gap,
        seniority_score=candidate.seniority_score,
        seniority_preference_fit=candidate.seniority_preference_fit,
        reliability_score=candidate.reliability_score,
        avoidable_assignment_score=candidate.avoidable_assignment_score,
        current_week_shift_count=candidate.current_week_shift_count,
        projected_rolling7_minutes=candidate.projected_rolling7_minutes,
        remaining_rolling7_minutes=candidate.remaining_rolling7_minutes,
        iteration_index=iteration_index,
        batch_id=batch_id,
        pressure_group_id=pressure_group_id,
        delta_kind=delta_kind,
        rationale_code=_decision_rationale_code(candidate=candidate, delta_kind=delta_kind),
        route_slot_class=candidate.route_slot_class,
        station_code=candidate.station_code,
        service_area=candidate.service_area,
        planning_phase=phase,
        repair_depth=repair_depth,
        previous_assignment_driver_id=previous_assignment_driver_id,
        displaced_route_slot_id=displaced_route_slot_id,
        displaced_driver_id=displaced_driver_id,
        baseline_template_state=candidate.baseline_template_state,
        planned_driver_day_state=(
            candidate.planned_driver_day_state
            if assignment_action == "assign"
            else "unassigned"
        ),
        new_agreement_required=(
            candidate.new_agreement_required if assignment_action == "assign" else False
        ),
        new_agreement_trigger_reason=(
            candidate.new_agreement_trigger_reason if assignment_action == "assign" else ""
        ),
        template_state_preservation_fit=(
            candidate.template_state_preservation_fit if assignment_action == "assign" else 0.0
        ),
        warnings=_decision_warnings(candidate),
    )


def _unassigned_decision(
    *,
    route_slot: RouteSlotRequirement,
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
    phase: str,
) -> ScheduledAssignment:
    return ScheduledAssignment(
        route_slot_id=route_slot.route_slot_id,
        route_id=route_slot.route_id,
        service_date=route_slot.service_date,
        candidate_driver_id="",
        assignment_action="unassigned",
        hard_filter_status="blocked",
        hard_filter_reasons=("no_valid_assignment_found",),
        score_bucket="blocked",
        soft_score_total=0.0,
        projected_minutes=route_slot.projected_minutes,
        fairness_balance=0.0,
        on_call_coverage=0.0,
        lost_work_credit=0.0,
        coverage_pressure=0.0,
        availability_fit=0.0,
        availability_state="",
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
        current_week_shift_count=0,
        projected_rolling7_minutes=0,
        remaining_rolling7_minutes=0,
        iteration_index=iteration_index,
        batch_id=batch_id,
        pressure_group_id=pressure_group_id,
        delta_kind="unassigned",
        rationale_code="hard_filter_no_valid_assignment_found",
        route_slot_class=route_slot.route_slot_class,
        station_code=route_slot.station_code,
        service_area=route_slot.service_area,
        planning_phase=phase,
        planned_driver_day_state="unassigned",
    )


def _coverage_summary(schedule_state: PartialWeeklyScheduleState) -> dict[str, Any]:
    final_decisions = schedule_state.final_decisions()
    pending_route_slot_ids = [
        item.route_slot_id for item in schedule_state.remaining_route_slots()
    ]
    uncovered_route_slot_ids = [
        *schedule_state.uncovered_route_slot_ids(),
        *pending_route_slot_ids,
    ]
    batch_sizes = [item.batch_size for item in schedule_state.iteration_summaries]
    repaired_route_slot_ids = {
        route_slot_id
        for move in schedule_state.repair_moves
        for route_slot_id in move.affected_route_slot_ids
    }
    return {
        "total_route_slots": len(schedule_state.ordered_route_slot_ids),
        "decided_route_slots": len(final_decisions),
        "pending_route_slots": len(pending_route_slot_ids),
        "pending_route_slot_ids": pending_route_slot_ids,
        "assigned_route_slots": schedule_state.assigned_count(),
        "uncovered_route_slots": len(uncovered_route_slot_ids),
        "uncovered_route_slot_ids": uncovered_route_slot_ids,
        "iteration_count": len(schedule_state.iteration_summaries),
        "batch_size_min": min(batch_sizes) if batch_sizes else 0,
        "batch_size_max": max(batch_sizes) if batch_sizes else 0,
        "repair_move_count": len(schedule_state.repair_moves),
        "reallocation_move_count": len(schedule_state.repair_moves),
        "repaired_route_slot_count": len(repaired_route_slot_ids),
        "local_repair_posture": "bounded_local_reallocation",
        "phase_counts": {
            "baseline": sum(1 for item in schedule_state.iteration_summaries if item.phase == "baseline"),
            "improvement": sum(
                1 for item in schedule_state.iteration_summaries if item.phase == "improvement"
            ),
        },
    }


def _coverage_summary_with_pending_iteration(
    *,
    schedule_state: PartialWeeklyScheduleState,
    phase: str,
    batch_size: int,
) -> dict[str, Any]:
    summary = _coverage_summary(schedule_state)
    batch_sizes = [item.batch_size for item in schedule_state.iteration_summaries]
    batch_sizes.append(batch_size)
    phase_counts = dict(summary.get("phase_counts") or {})
    phase_counts[phase] = phase_counts.get(phase, 0) + 1
    summary["iteration_count"] = len(schedule_state.iteration_summaries) + 1
    summary["batch_size_min"] = min(batch_sizes) if batch_sizes else 0
    summary["batch_size_max"] = max(batch_sizes) if batch_sizes else 0
    summary["phase_counts"] = phase_counts
    return summary


def _schedule_quality_snapshot(
    schedule_state: PartialWeeklyScheduleState,
) -> ScheduleQualitySnapshot:
    assigned = list(schedule_state.assignments_by_slot.values())
    uncovered = len(schedule_state.uncovered_route_slot_ids()) + len(schedule_state.remaining_route_slots())
    soft_total = sum(item.soft_score_total for item in assigned)
    return ScheduleQualitySnapshot(
        assigned_route_slots=len(assigned),
        uncovered_route_slots=uncovered,
        soft_objective_total=round(soft_total - (uncovered * UNCOVERED_ROUTE_SLOT_PENALTY), 6),
        stability_total=round(sum(item.continuity_score for item in assigned), 6),
        target_shift_gap_total=round(sum(item.target_shift_gap for item in assigned), 6),
        preference_fit_total=round(sum(item.preference_fit for item in assigned), 6),
    )


def _quality_delta(
    *,
    before: ScheduleQualitySnapshot,
    after: ScheduleQualitySnapshot,
) -> dict[str, float]:
    return {
        "coverage_delta": before.uncovered_route_slots - after.uncovered_route_slots,
        "soft_objective_delta": round(after.soft_objective_total - before.soft_objective_total, 6),
        "stability_delta": round(after.stability_total - before.stability_total, 6),
        "target_shift_gap_delta": round(after.target_shift_gap_total - before.target_shift_gap_total, 6),
        "preference_fit_delta": round(after.preference_fit_total - before.preference_fit_total, 6),
    }


def _meaningful_improvement(delta: dict[str, float]) -> bool:
    return bool(
        delta["coverage_delta"] > 0
        or delta["soft_objective_delta"] >= MIN_MEANINGFUL_SOFT_DELTA
        or delta["preference_fit_delta"] >= MIN_MEANINGFUL_SOFT_DELTA
        or delta["stability_delta"] >= MIN_MEANINGFUL_SOFT_DELTA
    )


def _proposal_sort_key(proposal: MoveProposal) -> tuple[float, float, float, str]:
    move = proposal.move
    return (
        move.soft_objective_delta,
        move.preference_fit_delta,
        move.stability_delta,
        proposal.tie_breaker,
    )


def _improvement_focus_assignments(
    *,
    schedule_state: PartialWeeklyScheduleState,
    blocked_route_slot_ids: set[str],
) -> list[ScheduledAssignment]:
    return sorted(
        (
            item
            for item in schedule_state.assignments_by_slot.values()
            if item.route_slot_id not in blocked_route_slot_ids
        ),
        key=lambda item: (
            item.template_state_preservation_fit,
            item.preference_fit,
            item.continuity_score,
            item.soft_score_total,
            item.route_slot_id,
        ),
    )[:MAX_IMPROVEMENT_FOCUS_ASSIGNMENTS]


def _primary_improvement_focus(schedule_state: PartialWeeklyScheduleState) -> RouteSlotRequirement | None:
    uncovered_ids = schedule_state.uncovered_route_slot_ids()
    if uncovered_ids:
        return schedule_state.route_slot(uncovered_ids[0])
    focus = _improvement_focus_assignments(
        schedule_state=schedule_state,
        blocked_route_slot_ids=set(),
    )
    if not focus:
        return None
    return schedule_state.route_slot(focus[0].route_slot_id)


def _improvement_iteration_budget(schedule_state: PartialWeeklyScheduleState) -> int:
    total_slots = len(schedule_state.ordered_route_slot_ids)
    return max(2, min(5, (total_slots // 48) + 2))


def _decision_rationale_code(
    *,
    candidate: CandidateEvaluation,
    delta_kind: str,
) -> str:
    if candidate.hard_filter_status != "pass":
        reason = next(iter(candidate.hard_filter_reasons), "blocked")
        return f"hard_filter_{reason}"
    if delta_kind == "repair" and candidate.previous_week_stability >= 0.9:
        return "repair_preserves_previous_week_continuity"
    if delta_kind == "repair":
        return "repair_restores_local_coverage"
    if delta_kind == "improvement" and candidate.preference_fit >= 0.85:
        return "improvement_preference_fit_upgrade"
    if delta_kind == "improvement":
        return "improvement_soft_objective_upgrade"
    if candidate.previous_week_stability >= 0.9:
        return "hard_rules_pass_continuity_preserved"
    if candidate.coverage_pressure >= 0.9:
        return "hard_rules_pass_pressure_relief"
    return "hard_rules_pass_iterative_rank"


def _decision_warnings(candidate: CandidateEvaluation) -> tuple[str, ...]:
    warnings: list[str] = []
    if candidate.score_bucket in {"ok", "poor"}:
        warnings.append("low_soft_score")
    if candidate.previous_week_stability < 0.4:
        warnings.append("weak_previous_week_continuity")
    if candidate.new_agreement_required:
        warnings.append("new_agreement_required")
    if candidate.baseline_template_state == "on_call_template":
        warnings.append("used_on_call_template_day")
    if candidate.availability_state == "AVOID_IF_POSSIBLE":
        warnings.append("avoidable_availability_state_used")
    return tuple(warnings)


def _pressure_group_id(group_key: tuple[str, str, str]) -> str:
    return "|".join(group_key)


def _route_slot_group_token(route_slot_class: str) -> str:
    token = str(route_slot_class or "").lower()
    if "rescue" in token:
        return "rescue"
    if "overflow" in token:
        return "overflow"
    if "late" in token:
        return "late"
    if "early" in token:
        return "early"
    return token
