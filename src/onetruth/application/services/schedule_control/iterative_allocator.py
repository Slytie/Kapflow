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
    batch_id: str
    pressure_group_id: str
    pressure_service_date: str
    pressure_station_code: str
    pressure_service_area: str
    candidate_evaluations: tuple[CandidateEvaluation, ...]
    applied_decisions: tuple[ScheduledAssignment, ...]
    repair_moves: tuple[RepairMove, ...]
    summary: IterationSummary
    coverage_summary: dict[str, Any]


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
    if not schedule_state.remaining_route_slots():
        return None

    iteration_index = len(schedule_state.iteration_summaries) + 1
    batch_slots, pressure_group = _select_batch(bundle=bundle, schedule_state=schedule_state)
    batch_id = f"{bundle.bundle_id}:iter-{iteration_index:02d}"
    candidate_start = len(candidate_matrix)

    uncovered_slots = _allocate_batch(
        bundle=bundle,
        batch_slots=batch_slots,
        schedule_state=schedule_state,
        candidate_matrix=candidate_matrix,
        iteration_index=iteration_index,
        batch_id=batch_id,
        pressure_group_id=pressure_group["pressure_group_id"],
    )
    repair_count_before = len(schedule_state.repair_moves)
    if uncovered_slots:
        _attempt_repairs(
            bundle=bundle,
            uncovered_slots=uncovered_slots,
            schedule_state=schedule_state,
            candidate_matrix=candidate_matrix,
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group["pressure_group_id"],
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
            )
        )

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
    summary = IterationSummary(
        iteration_index=iteration_index,
        batch_id=batch_id,
        pressure_group_id=pressure_group["pressure_group_id"],
        pressure_service_date=pressure_group["service_date"],
        pressure_station_code=pressure_group["station_code"],
        pressure_service_area=pressure_group["service_area"],
        batch_size=len(batch_slots),
        route_slot_ids=batch_route_slot_ids,
        assigned_route_slot_ids=assigned_route_slot_ids,
        uncovered_route_slot_ids=uncovered_route_slot_ids,
        repair_move_count=len(schedule_state.repair_moves) - repair_count_before,
        covered_route_slot_count_after_iteration=schedule_state.assigned_count(),
        uncovered_route_slot_count_after_iteration=len(schedule_state.uncovered_route_slot_ids()),
        candidate_evaluation_count=len(candidate_matrix) - candidate_start,
    )
    schedule_state.record_iteration(summary)

    coverage_summary = _coverage_summary(schedule_state)
    return IterationExecutionResult(
        iteration_index=iteration_index,
        batch_id=batch_id,
        pressure_group_id=pressure_group["pressure_group_id"],
        pressure_service_date=pressure_group["service_date"],
        pressure_station_code=pressure_group["station_code"],
        pressure_service_area=pressure_group["service_area"],
        candidate_evaluations=tuple(candidate_matrix[candidate_start:]),
        applied_decisions=tuple(
            item for item in schedule_state.final_decisions() if item.iteration_index == iteration_index
        ),
        repair_moves=tuple(schedule_state.repair_moves[repair_count_before:]),
        summary=summary,
        coverage_summary=coverage_summary,
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
) -> None:
    for uncovered_slot in uncovered_slots:
        if schedule_state.has_decision(uncovered_slot.route_slot_id):
            continue
        repairs_used = sum(
            1 for item in schedule_state.repair_moves if item.iteration_index == iteration_index
        )
        if repairs_used >= MAX_REPAIR_MOVES_PER_ITERATION:
            return
        repair_candidate = _best_repair_candidate(
            bundle=bundle,
            uncovered_slot=uncovered_slot,
            schedule_state=schedule_state,
            candidate_matrix=candidate_matrix,
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
        )
        if repair_candidate is None:
            continue
        replacement_decision, filled_decision, repair_move = repair_candidate
        schedule_state.record_assignment(replacement_decision)
        schedule_state.record_assignment(filled_decision)
        schedule_state.record_repair_move(repair_move)


def _best_repair_candidate(
    *,
    bundle: WeeklyScheduleControlBundle,
    uncovered_slot: RouteSlotRequirement,
    schedule_state: PartialWeeklyScheduleState,
    candidate_matrix: list[CandidateEvaluation],
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
) -> tuple[ScheduledAssignment, ScheduledAssignment, RepairMove] | None:
    local_assignments = _local_repair_assignments(
        uncovered_slot=uncovered_slot,
        schedule_state=schedule_state,
        batch_id=batch_id,
    )
    best_candidate: tuple[float, str, ScheduledAssignment, ScheduledAssignment, RepairMove] | None = None

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

        objective = (
            10.0
            + fill_evaluation.soft_score_total
            + replacement_evaluation.soft_score_total
            - assignment.soft_score_total
        )
        if assignment.iteration_index < iteration_index:
            objective -= 0.2
        if fill_evaluation.previous_week_stability >= 0.9:
            objective += 0.15
        replacement_decision = _decision_from_candidate(
            replacement_evaluation,
            assignment_action="assign",
            delta_kind="repair",
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
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
            repair_depth=1,
            displaced_route_slot_id=assignment.route_slot_id,
            displaced_driver_id=assignment.candidate_driver_id,
        )
        repair_move = RepairMove(
            iteration_index=iteration_index,
            batch_id=batch_id,
            pressure_group_id=pressure_group_id,
            filled_route_slot_id=uncovered_slot.route_slot_id,
            filled_driver_id=assignment.candidate_driver_id,
            reassigned_route_slot_id=assignment.route_slot_id,
            previous_driver_id=assignment.candidate_driver_id,
            replacement_driver_id=replacement_evaluation.candidate_driver_id,
            score_gain=round(
                fill_evaluation.soft_score_total
                + replacement_evaluation.soft_score_total
                - assignment.soft_score_total,
                6,
            ),
            repair_reason=(
                "local_stability_repair"
                if fill_evaluation.previous_week_stability >= 0.9
                else "local_coverage_repair"
            ),
        )
        tie_breaker = "|".join(
            [
                assignment.route_slot_id,
                replacement_evaluation.candidate_driver_id,
                uncovered_slot.route_slot_id,
            ]
        )
        if best_candidate is None or (objective, tie_breaker) > (
            best_candidate[0],
            best_candidate[1],
        ):
            best_candidate = (
                objective,
                tie_breaker,
                replacement_decision,
                filled_decision,
                repair_move,
            )

    if best_candidate is None:
        return None
    return (
        best_candidate[2],
        best_candidate[3],
        best_candidate[4],
    )


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
    if "rescue" in route_slot_class:
        priority = 0
    elif "overflow" in route_slot_class:
        priority = 1
    else:
        priority = 2
    return (priority, route_slot.shift_start, route_slot.route_slot_id)


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
            item.iteration_index,
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
        previous_week_stability=candidate.previous_week_stability,
        target_shift_gap=candidate.target_shift_gap,
        seniority_score=candidate.seniority_score,
        reliability_score=candidate.reliability_score,
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
        repair_depth=repair_depth,
        previous_assignment_driver_id=previous_assignment_driver_id,
        displaced_route_slot_id=displaced_route_slot_id,
        displaced_driver_id=displaced_driver_id,
        warnings=_decision_warnings(candidate),
    )


def _unassigned_decision(
    *,
    route_slot: RouteSlotRequirement,
    iteration_index: int,
    batch_id: str,
    pressure_group_id: str,
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
        previous_week_stability=0.0,
        target_shift_gap=0.0,
        seniority_score=0.0,
        reliability_score=0.0,
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
        for route_slot_id in (move.filled_route_slot_id, move.reassigned_route_slot_id)
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
        "repaired_route_slot_count": len(repaired_route_slot_ids),
        "local_repair_posture": "bounded_local_repair",
    }


def _decision_rationale_code(
    *,
    candidate: CandidateEvaluation,
    delta_kind: str,
) -> str:
    if candidate.hard_filter_status != "pass":
        reason = next(iter(candidate.hard_filter_reasons), "blocked")
        return f"hard_filter_{reason}"
    if delta_kind == "repair" and candidate.previous_week_stability >= 0.9:
        return "repair_preserves_previous_week_stability"
    if delta_kind == "repair":
        return "repair_restores_local_coverage"
    if candidate.previous_week_stability >= 0.9:
        return "hard_rules_pass_stability_preserved"
    if candidate.coverage_pressure >= 0.9:
        return "hard_rules_pass_pressure_relief"
    return "hard_rules_pass_iterative_rank"


def _decision_warnings(candidate: CandidateEvaluation) -> tuple[str, ...]:
    warnings: list[str] = []
    if candidate.score_bucket in {"ok", "poor"}:
        warnings.append("low_soft_score")
    if candidate.previous_week_stability < 0.4:
        warnings.append("weak_previous_week_stability")
    return tuple(warnings)


def _pressure_group_id(group_key: tuple[str, str, str]) -> str:
    return "|".join(group_key)
