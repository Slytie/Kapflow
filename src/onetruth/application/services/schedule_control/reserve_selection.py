from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .bundle_builder import WeeklyScheduleControlBundle
from .candidate_generation import generate_weekly_candidate_matrix
from .planning_state import PartialWeeklyScheduleState, ScheduledAssignment
from .route_slot_requirements import RouteSlotRequirement, expand_route_slot_requirements
from .scoring import deterministic_rank_candidates

ON_CALL_BUFFER_PROJECTED_MINUTES = 180
DEFAULT_EXCESS_CAPACITY_ESTIMATED_HOURS = 8.5
_ON_CALL_ROUTE_ID = "ON_CALL"
_EXCESS_CAPACITY_ROUTE_ID = "EXCESS_CAPACITY"


@dataclass(frozen=True)
class ReserveSelectionResult:
    reserve_rows: list[dict[str, Any]]
    reserve_summary: dict[str, Any]
    excess_capacity_rows: list[dict[str, Any]]
    excess_capacity_summary: dict[str, Any]


def select_on_call_reserve_rows(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    iteration_index: int,
    schedule_state: PartialWeeklyScheduleState | None = None,
) -> ReserveSelectionResult:
    resolved_schedule_state = (
        schedule_state.clone()
        if schedule_state is not None
        else _schedule_state_from_selected_routes(
            bundle=bundle,
            selected_candidates=selected_candidates,
        )
    )
    on_call_slots = _build_synthetic_slots(bundle=bundle, demand_kind="on_call")
    resolved_schedule_state.extend_route_slots(on_call_slots)
    reserve_rows, reserve_summary = _allocate_synthetic_capacity_rows(
        bundle=bundle,
        route_slots=on_call_slots,
        schedule_state=resolved_schedule_state,
        iteration_index=iteration_index,
        demand_kind="on_call",
    )

    excess_capacity_slots = _build_synthetic_slots(bundle=bundle, demand_kind="excess_capacity")
    resolved_schedule_state.extend_route_slots(excess_capacity_slots)
    excess_capacity_rows, excess_capacity_summary = _allocate_synthetic_capacity_rows(
        bundle=bundle,
        route_slots=excess_capacity_slots,
        schedule_state=resolved_schedule_state,
        iteration_index=iteration_index,
        demand_kind="excess_capacity",
    )
    return ReserveSelectionResult(
        reserve_rows=reserve_rows,
        reserve_summary=reserve_summary,
        excess_capacity_rows=excess_capacity_rows,
        excess_capacity_summary=excess_capacity_summary,
    )


def _schedule_state_from_selected_routes(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
) -> PartialWeeklyScheduleState:
    route_slots = expand_route_slot_requirements(bundle.route_slots)
    schedule_state = PartialWeeklyScheduleState.from_route_slots(route_slots)
    for row in selected_candidates:
        if str(row.get("assignment_action") or "") != "assign":
            continue
        if str(row.get("hard_filter_status") or "") != "pass":
            continue
        route_slot_id = str(row.get("route_slot_id") or "")
        if not route_slot_id or route_slot_id not in schedule_state.route_slots_by_id:
            continue
        schedule_state.record_assignment(
            _assignment_from_row(
                route_slot=schedule_state.route_slot(route_slot_id),
                row=row,
                assignment_action="assign",
                planning_phase=str(row.get("planning_phase") or row.get("phase") or "baseline"),
                delta_kind=str(row.get("delta_kind") or "allocation"),
                batch_id=str(row.get("batch_id") or ""),
                pressure_group_id=str(row.get("pressure_group_id") or ""),
            )
        )
    return schedule_state


def _build_synthetic_slots(
    *,
    bundle: WeeklyScheduleControlBundle,
    demand_kind: str,
) -> tuple[RouteSlotRequirement, ...]:
    templates_by_service_date: dict[str, RouteSlotRequirement] = {}
    for route_slot in bundle.route_slots:
        templates_by_service_date.setdefault(route_slot.service_date, route_slot)

    slots: list[RouteSlotRequirement] = []
    for service_date, demand in sorted(bundle.daily_demand_by_service_date.items()):
        target_count = max(
            int(_synthetic_target_range(demand=demand, demand_kind=demand_kind).max_count or 0),
            0,
        )
        if target_count <= 0:
            continue
        template = templates_by_service_date.get(service_date)
        compact_date = service_date.replace("-", "")
        for sequence in range(1, target_count + 1):
            slots.append(
                RouteSlotRequirement(
                    service_date=service_date,
                    route_slot_id=_synthetic_route_slot_id(
                        demand_kind=demand_kind,
                        compact_date=compact_date,
                        sequence=sequence,
                    ),
                    route_slot_class=str(template.route_slot_class if template else ""),
                    required_skill=str(template.required_skill if template else ""),
                    vehicle_type=str(template.vehicle_type if template else ""),
                    shift_start=str(template.shift_start if template else "11:30"),
                    shift_end=str(template.shift_end if template else "20:00"),
                    estimated_hours=_synthetic_estimated_hours(
                        demand_kind=demand_kind,
                        template=template,
                    ),
                    source_snapshot_row_ref=_synthetic_source_snapshot_row_ref(
                        demand_kind=demand_kind,
                        service_date=service_date,
                    ),
                    route_id=_synthetic_route_id(demand_kind),
                    source_message_id=(
                        template.source_message_id
                        if template is not None
                        else _synthetic_source_kind(demand_kind)
                    ),
                    station_code=str(template.station_code if template else ""),
                    service_area=str(template.service_area if template else ""),
                    source_kind=_synthetic_source_kind(demand_kind),
                    route_family=demand_kind,
                    preferred_shift_band=str(template.preferred_shift_band if template else ""),
                    demand_kind=demand_kind,
                )
            )
    return tuple(slots)

def _allocate_synthetic_capacity_rows(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slots: tuple[RouteSlotRequirement, ...],
    schedule_state: PartialWeeklyScheduleState,
    iteration_index: int,
    demand_kind: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected_by_service_date: Counter[str] = Counter()
    selected_rows: list[dict[str, Any]] = []
    target_range_by_service_date = _synthetic_target_ranges_by_service_date(
        bundle=bundle,
        demand_kind=demand_kind,
    )
    target_by_service_date: dict[str, int] = {}
    note_by_service_date: dict[str, str] = {}
    route_slots_by_service_date: dict[str, list[RouteSlotRequirement]] = {}
    for route_slot in route_slots:
        route_slots_by_service_date.setdefault(route_slot.service_date, []).append(route_slot)

    for service_date, target_range in sorted(target_range_by_service_date.items()):
        service_date_slots = route_slots_by_service_date.get(service_date, [])
        selected_count = 0
        selection_note = ""
        chosen_target = 0

        for slot_index, route_slot in enumerate(service_date_slots, start=1):
            selected_row, rejection_reason = _allocate_synthetic_slot(
                bundle=bundle,
                route_slot=route_slot,
                schedule_state=schedule_state,
                iteration_index=iteration_index,
                demand_kind=demand_kind,
                slot_index=slot_index,
                target_range=target_range,
            )
            if selected_row is None:
                chosen_target = (
                    target_range.min_count
                    if selected_count < target_range.min_count
                    else selected_count
                )
                selection_note = _synthetic_selection_note(
                    demand_kind=demand_kind,
                    target_range=target_range,
                    selected_count=selected_count,
                    rejection_reason=rejection_reason,
                )
                break
            selected_rows.append(selected_row)
            selected_by_service_date[service_date] += 1
            selected_count += 1
            chosen_target = selected_count

        if not selection_note and selected_count < target_range.min_count:
            chosen_target = target_range.min_count
            selection_note = _synthetic_selection_note(
                demand_kind=demand_kind,
                target_range=target_range,
                selected_count=selected_count,
                rejection_reason="minimum_range_shortfall",
            )
        elif not selection_note:
            chosen_target = max(chosen_target, selected_count)

        target_by_service_date[service_date] = chosen_target
        if selection_note:
            note_by_service_date[service_date] = selection_note

    filled_by_service_date = {
        service_date: int(selected_by_service_date.get(service_date, 0))
        for service_date in sorted(target_range_by_service_date)
    }
    unmet_by_service_date = {
        service_date: max(target_by_service_date[service_date] - filled_count, 0)
        for service_date, filled_count in filled_by_service_date.items()
    }
    configured_range_by_service_date = {
        service_date: {
            "min": target_range.min_count,
            "preferred": target_range.preferred_count,
            "max": target_range.max_count,
        }
        for service_date, target_range in sorted(target_range_by_service_date.items())
    }
    preferred_by_service_date = {
        service_date: target_range.preferred_count
        for service_date, target_range in sorted(target_range_by_service_date.items())
    }

    if demand_kind == "on_call":
        summary = {
            "configured_on_call_range_by_service_date": configured_range_by_service_date,
            "preferred_on_call_target_by_service_date": preferred_by_service_date,
            "on_call_target_by_service_date": target_by_service_date,
            "selected_on_call_by_service_date": filled_by_service_date,
            "unmet_on_call_target_by_service_date": unmet_by_service_date,
            "selection_note_by_service_date": note_by_service_date,
            "preferred_on_call_total": sum(preferred_by_service_date.values()),
            "target_on_call_total": sum(target_by_service_date.values()),
            "selected_on_call_total": sum(filled_by_service_date.values()),
            "unmet_on_call_target_total": sum(unmet_by_service_date.values()),
        }
    else:
        summary = {
            "configured_excess_capacity_range_by_service_date": configured_range_by_service_date,
            "preferred_excess_capacity_target_by_service_date": preferred_by_service_date,
            "excess_capacity_target_by_service_date": target_by_service_date,
            "selected_excess_capacity_by_service_date": filled_by_service_date,
            "unmet_excess_capacity_target_by_service_date": unmet_by_service_date,
            "selection_note_by_service_date": note_by_service_date,
            "preferred_excess_capacity_total": sum(preferred_by_service_date.values()),
            "target_excess_capacity_total": sum(target_by_service_date.values()),
            "selected_excess_capacity_total": sum(filled_by_service_date.values()),
            "unmet_excess_capacity_target_total": sum(unmet_by_service_date.values()),
        }
    return selected_rows, summary


def _allocate_synthetic_slot(
    *,
    bundle: WeeklyScheduleControlBundle,
    route_slot: RouteSlotRequirement,
    schedule_state: PartialWeeklyScheduleState,
    iteration_index: int,
    demand_kind: str,
    slot_index: int,
    target_range: Any,
) -> tuple[dict[str, Any] | None, str]:
    candidate_matrix = generate_weekly_candidate_matrix(
        bundle=bundle,
        route_slots=(route_slot,),
        schedule_state=schedule_state,
        iteration_index=iteration_index,
        evaluation_kind=("reserve" if demand_kind == "on_call" else demand_kind),
    )
    ranked_rows = deterministic_rank_candidates([item.to_row() for item in candidate_matrix])
    rejection_reason = "no_legal_candidate"
    for selected in ranked_rows:
        if str(selected.get("hard_filter_status") or "") != "pass":
            continue
        rejection_reason = _synthetic_candidate_rejection_reason(
            bundle=bundle,
            selected=selected,
            demand_kind=demand_kind,
            slot_index=slot_index,
            target_range=target_range,
        )
        if rejection_reason:
            continue

        assignment = _assignment_from_row(
            route_slot=route_slot,
            row=selected,
            assignment_action=("reserve" if demand_kind == "on_call" else "assign"),
            planning_phase=(
                "reserve_buffer" if demand_kind == "on_call" else "baseline_excess_capacity"
            ),
            delta_kind=("reserve" if demand_kind == "on_call" else "excess_capacity"),
            batch_id=(
                f"reserve-buffer:{route_slot.service_date}"
                if demand_kind == "on_call"
                else f"baseline-excess-capacity:{route_slot.service_date}"
            ),
            pressure_group_id=(
                f"{route_slot.service_date}|ON_CALL|reserve_buffer"
                if demand_kind == "on_call"
                else f"{route_slot.service_date}|EXCESS_CAPACITY|baseline_excess_capacity"
            ),
            increment_shift_count=True,
        )
        schedule_state.record_assignment(assignment)
        selected_row = assignment.to_row()
        if demand_kind == "on_call":
            selected_row["assignment_status"] = "reserve"
            selected_row["phase"] = "reserve_buffer"
        return selected_row, ""
    return None, rejection_reason


def _assignment_from_row(
    *,
    route_slot: RouteSlotRequirement,
    row: dict[str, Any],
    assignment_action: str,
    planning_phase: str,
    delta_kind: str,
    batch_id: str,
    pressure_group_id: str,
    increment_shift_count: bool = False,
) -> ScheduledAssignment:
    baseline_template_state = str(row.get("baseline_template_state") or "")
    rationale_code = str(row.get("rationale_code") or "")
    if assignment_action == "reserve":
        rationale_code = {
            "on_call_template": "reserve_fill_on_call_template",
            "white_template": "reserve_fill_white_template",
            "yellow_template": "reserve_fill_yellow_template",
        }.get(baseline_template_state, "reserve_fill")
    elif route_slot.is_excess_capacity_demand:
        rationale_code = {
            "assigned_template": "excess_capacity_fill_assigned_template",
            "white_template": "excess_capacity_fill_white_template",
            "yellow_template": "excess_capacity_fill_yellow_template",
        }.get(baseline_template_state, "excess_capacity_fill")
    return ScheduledAssignment(
        route_slot_id=route_slot.route_slot_id,
        route_id=str(row.get("route_id") or route_slot.route_id),
        service_date=route_slot.service_date,
        candidate_driver_id=str(row.get("candidate_driver_id") or ""),
        assignment_action=assignment_action,
        hard_filter_status=str(row.get("hard_filter_status") or "pass"),
        hard_filter_reasons=tuple(str(item) for item in (row.get("hard_filter_reasons") or [])),
        score_bucket=str(row.get("score_bucket") or "good"),
        soft_score_total=round(float(row.get("soft_score_total") or 0.0), 6),
        projected_minutes=route_slot.projected_minutes,
        fairness_balance=round(float(row.get("fairness_balance") or 0.0), 6),
        on_call_coverage=round(float(row.get("on_call_coverage") or 0.0), 6),
        lost_work_credit=round(float(row.get("lost_work_credit") or 0.0), 6),
        coverage_pressure=round(float(row.get("coverage_pressure") or 0.0), 6),
        availability_fit=round(float(row.get("availability_fit") or 0.0), 6),
        availability_state=str(row.get("availability_state") or ""),
        availability_state_fit=round(float(row.get("availability_state_fit") or 0.0), 6),
        preferred_shift_band_fit=round(float(row.get("preferred_shift_band_fit") or 0.0), 6),
        preferred_route_slot_class_fit=round(
            float(row.get("preferred_route_slot_class_fit") or 0.0),
            6,
        ),
        preference_fit=round(float(row.get("preference_fit") or 0.0), 6),
        previous_week_stability=round(float(row.get("previous_week_stability") or 0.0), 6),
        continuity_score=round(float(row.get("continuity_score") or 0.0), 6),
        target_shift_gap=round(float(row.get("target_shift_gap") or 0.0), 6),
        seniority_score=round(float(row.get("seniority_score") or 0.0), 6),
        seniority_preference_fit=round(float(row.get("seniority_preference_fit") or 0.0), 6),
        reliability_score=round(float(row.get("reliability_score") or 0.0), 6),
        avoidable_assignment_score=round(float(row.get("avoidable_assignment_score") or 0.0), 6),
        current_week_shift_count=(
            int(row.get("current_week_shift_count") or 0) + (1 if increment_shift_count else 0)
        ),
        projected_rolling7_minutes=int(row.get("projected_rolling7_minutes") or 0),
        remaining_rolling7_minutes=int(row.get("remaining_rolling7_minutes") or 0),
        iteration_index=int(row.get("iteration_index") or 0),
        batch_id=batch_id,
        pressure_group_id=pressure_group_id,
        delta_kind=delta_kind,
        rationale_code=rationale_code,
        route_slot_class=route_slot.route_slot_class,
        station_code=route_slot.station_code,
        service_area=route_slot.service_area,
        planning_phase=planning_phase,
        baseline_template_state=baseline_template_state,
        planned_driver_day_state=str(row.get("planned_driver_day_state") or ""),
        new_agreement_required=bool(row.get("new_agreement_required")),
        new_agreement_trigger_reason=str(row.get("new_agreement_trigger_reason") or ""),
        template_state_preservation_fit=round(
            float(row.get("template_state_preservation_fit") or 0.0),
            6,
        ),
    )


def _synthetic_target_ranges_by_service_date(
    *,
    bundle: WeeklyScheduleControlBundle,
    demand_kind: str,
) -> dict[str, Any]:
    return {
        service_date: _synthetic_target_range(demand=demand, demand_kind=demand_kind)
        for service_date, demand in sorted(bundle.daily_demand_by_service_date.items())
    }


def _synthetic_target_range(*, demand: Any, demand_kind: str) -> Any:
    if demand_kind == "on_call":
        return getattr(demand, "on_call_target_range")
    return getattr(demand, "excess_capacity_target_range")


def _synthetic_candidate_rejection_reason(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected: dict[str, Any],
    demand_kind: str,
    slot_index: int,
    target_range: Any,
) -> str:
    current_week_shift_count = int(selected.get("current_week_shift_count") or 0)
    projected_week_shift_count = current_week_shift_count + 1
    if projected_week_shift_count > bundle.planning_policy.avoid_overtime_after_shifts_per_week:
        return "would_create_5th_placement_overtime"
    if slot_index > target_range.preferred_count:
        if current_week_shift_count >= bundle.planning_policy.minimum_desired_shifts_per_week:
            return "would_extend_buffer_above_preferred_without_low_work_recovery"
        if bool(selected.get("new_agreement_required")):
            return "would_extend_buffer_above_preferred_with_new_agreement_churn"
    return ""


def _synthetic_selection_note(
    *,
    demand_kind: str,
    target_range: Any,
    selected_count: int,
    rejection_reason: str,
) -> str:
    buffer_label = "on-call buffer" if demand_kind == "on_call" else "excess-capacity buffer"
    if selected_count < target_range.min_count:
        return (
            f"held at {selected_count} below minimum {target_range.min_count} because additional "
            f"{buffer_label} work would worsen work balance or create 5th-placement overtime"
        )
    if selected_count < target_range.preferred_count:
        return (
            f"held at {selected_count} below preferred {target_range.preferred_count} because "
            f"additional {buffer_label} work would worsen work balance or create 5th-placement overtime"
        )
    if (
        selected_count < target_range.max_count
        and rejection_reason == "would_extend_buffer_above_preferred_without_low_work_recovery"
    ):
        return (
            f"held at preferred {target_range.preferred_count} because additional {buffer_label} "
            "work would worsen work balance"
        )
    if (
        selected_count < target_range.max_count
        and rejection_reason == "would_create_5th_placement_overtime"
    ):
        return (
            f"held at preferred {target_range.preferred_count} because additional {buffer_label} "
            "work would create 5th-placement overtime"
        )
    if rejection_reason == "would_extend_buffer_above_preferred_with_new_agreement_churn":
        return (
            f"stopped at preferred {target_range.preferred_count} because additional {buffer_label} "
            "positions would add avoidable new-agreement churn"
        )
    return ""


def _synthetic_route_slot_id(*, demand_kind: str, compact_date: str, sequence: int) -> str:
    if demand_kind == "on_call":
        return f"oncall-{compact_date}#{sequence:02d}"
    return f"excess-{compact_date}#{sequence:02d}"


def _synthetic_estimated_hours(
    *,
    demand_kind: str,
    template: RouteSlotRequirement | None,
) -> float:
    if demand_kind == "on_call":
        return ON_CALL_BUFFER_PROJECTED_MINUTES / 60.0
    if template is not None and float(template.estimated_hours or 0.0) > 0.0:
        return float(template.estimated_hours)
    return DEFAULT_EXCESS_CAPACITY_ESTIMATED_HOURS


def _synthetic_source_snapshot_row_ref(*, demand_kind: str, service_date: str) -> str:
    if demand_kind == "on_call":
        return f"daily_on_call_target:{service_date}"
    return f"daily_excess_capacity_target:{service_date}"


def _synthetic_route_id(demand_kind: str) -> str:
    if demand_kind == "on_call":
        return _ON_CALL_ROUTE_ID
    return _EXCESS_CAPACITY_ROUTE_ID


def _synthetic_source_kind(demand_kind: str) -> str:
    if demand_kind == "on_call":
        return "daily_on_call_target"
    return "daily_excess_capacity_target"
