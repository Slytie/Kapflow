from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from typing import Any, Iterable, Mapping, Sequence

from . import (
    PartialWeeklyScheduleState,
    RouteSlotRequirement,
    ScheduledAssignment,
    WeeklyScheduleControlBundle,
    deterministic_rank_candidates,
    evaluate_hard_constraints,
    expand_route_slot_requirements,
    generate_weekly_candidate_matrix,
)

DEFAULT_MAX_ROUTE_DEMAND_COVERAGE_CANDIDATES = 8
MAX_ROUTE_DEMAND_COVERAGE_CANDIDATES = 20


def recommend_route_demand_coverage(
    *,
    old_bundle: WeeklyScheduleControlBundle,
    updated_bundle: WeeklyScheduleControlBundle,
    assignment_rows: Iterable[Mapping[str, Any]],
    reserve_rows: Iterable[Mapping[str, Any]],
    service_dates: Iterable[str] | None = None,
    max_candidates: int = DEFAULT_MAX_ROUTE_DEMAND_COVERAGE_CANDIDATES,
) -> dict[str, Any]:
    clamped_max_candidates = max(1, min(int(max_candidates), MAX_ROUTE_DEMAND_COVERAGE_CANDIDATES))
    expanded_old_slots = tuple(expand_route_slot_requirements(old_bundle.route_slots))
    expanded_updated_slots = tuple(expand_route_slot_requirements(updated_bundle.route_slots))
    route_slot_aliases = _build_route_slot_aliases(
        old_slots=expanded_old_slots,
        updated_slots=expanded_updated_slots,
    )
    schedule_state = _build_schedule_state(
        old_bundle=old_bundle,
        updated_bundle=updated_bundle,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
        route_slot_aliases=route_slot_aliases,
    )
    targets = _detect_added_route_slot_targets(
        old_slots=expanded_old_slots,
        updated_slots=expanded_updated_slots,
        service_dates=service_dates,
    )
    drivers_by_id = {
        str(driver.driver_id): driver
        for driver in updated_bundle.drivers
    }
    candidate_groups: list[dict[str, Any]] = []
    for target in targets:
        candidate_rows = [
            evaluation.to_row()
            for evaluation in generate_weekly_candidate_matrix(
                bundle=updated_bundle,
                route_slots=(target,),
                schedule_state=schedule_state,
                evaluation_kind="route_demand_coverage",
                exclude_route_slot_ids=_same_day_reserve_route_slot_ids(
                    reserve_rows=reserve_rows,
                    service_date=target.service_date,
                    driver_id=None,
                ),
            )
        ]
        ranked_candidates = deterministic_rank_candidates(candidate_rows)
        normalized_candidates: list[dict[str, Any]] = []
        for rank, candidate in enumerate(ranked_candidates[:clamped_max_candidates], start=1):
            normalized = _coverage_candidate_payload(
                candidate=candidate,
                target=target,
                drivers_by_id=drivers_by_id,
                reserve_rows=reserve_rows,
                recommendation_rank=rank,
            )
            normalized_candidates.append(normalized)
        candidate_groups.append(
            {
                "target": _coverage_target_payload(target),
                "candidate_count": len(normalized_candidates),
                "pass_candidate_count": sum(
                    1
                    for candidate in normalized_candidates
                    if candidate["hard_filter_status"] == "pass"
                ),
                "candidates": normalized_candidates,
            }
        )
    selected_defaults = _selected_route_demand_coverage_defaults(candidate_groups)
    result: dict[str, Any] = {
        "added_route_count": len(targets),
        "target_count": len(targets),
        "max_candidates": clamped_max_candidates,
        "targets": [_coverage_target_payload(target) for target in targets],
        "candidate_groups": candidate_groups,
        "selected_defaults": selected_defaults,
    }
    if not targets:
        result["diagnostic_reason"] = "no_uncovered_route_slots_detected"
    return result


def selected_route_demand_coverage_candidates(
    *,
    recommendations: Mapping[str, Any],
    selections: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    groups = list(recommendations.get("candidate_groups") or [])
    candidate_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        for candidate in list(group.get("candidates") or []):
            if not isinstance(candidate, Mapping):
                continue
            route_slot_id = str(candidate.get("route_slot_id") or "").strip()
            driver_id = str(candidate.get("driver_id") or "").strip()
            if not route_slot_id or not driver_id:
                continue
            candidate_by_key[(route_slot_id, driver_id)] = dict(candidate)
    selected: list[dict[str, Any]] = []
    for item in selections:
        if not isinstance(item, Mapping):
            continue
        route_slot_id = str(item.get("route_slot_id") or "").strip()
        driver_id = str(item.get("driver_id") or "").strip()
        if not route_slot_id or not driver_id:
            continue
        candidate = candidate_by_key.get((route_slot_id, driver_id))
        if candidate is not None:
            selected.append(candidate)
    return selected


def apply_route_demand_coverage_candidates(
    *,
    bundle: WeeklyScheduleControlBundle,
    assignment_rows: Iterable[Mapping[str, Any]],
    reserve_rows: Iterable[Mapping[str, Any]],
    selections: Sequence[Mapping[str, Any]],
    recommendations: Mapping[str, Any],
    route_demand_artifact_version_id: str,
) -> dict[str, Any]:
    route_slots = tuple(expand_route_slot_requirements(bundle.route_slots))
    route_slots_by_id = {route_slot.route_slot_id: route_slot for route_slot in route_slots}
    drivers_by_id = {
        str(driver.driver_id): driver
        for driver in bundle.drivers
    }
    schedule_state = _build_schedule_state_from_updated_slots(
        updated_slots=route_slots,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
    )
    candidate_groups = {
        str(group.get("target", {}).get("route_slot_id") or ""): dict(group)
        for group in list(recommendations.get("candidate_groups") or [])
        if isinstance(group, Mapping)
    }
    next_reserve_rows = [dict(row) for row in reserve_rows]
    selected_candidates: list[dict[str, Any]] = []
    appended_rows: list[dict[str, Any]] = []
    cleared_same_day_reserve_count = 0
    next_iteration_index = _next_iteration_index(assignment_rows=assignment_rows)
    seen_target_ids: set[str] = set()
    seen_service_date_driver_ids: set[tuple[str, str]] = set()
    for raw_selection in selections:
        route_slot_id = str(raw_selection.get("route_slot_id") or "").strip()
        driver_id = str(raw_selection.get("driver_id") or "").strip()
        row_kind = str(raw_selection.get("row_kind") or "").strip() or "assignment"
        if row_kind != "assignment" or not route_slot_id or not driver_id:
            continue
        if route_slot_id in seen_target_ids:
            continue
        seen_target_ids.add(route_slot_id)
        group = candidate_groups.get(route_slot_id)
        if group is None:
            raise ValueError(f"route-demand coverage candidate unavailable for route_slot_id={route_slot_id}")
        candidate = next(
            (
                dict(item)
                for item in list(group.get("candidates") or [])
                if str(item.get("route_slot_id") or "").strip() == route_slot_id
                and str(item.get("driver_id") or "").strip() == driver_id
            ),
            None,
        )
        if candidate is None:
            raise ValueError(f"route-demand coverage candidate unavailable for route_slot_id={route_slot_id}")
        if candidate.get("selection_state") != "selectable":
            raise RuntimeError(f"route-demand coverage candidate blocked for route_slot_id={route_slot_id}")
        if str(candidate.get("hard_filter_status") or "") != "pass":
            raise RuntimeError(f"route-demand coverage candidate blocked for route_slot_id={route_slot_id}")
        route_slot = route_slots_by_id.get(route_slot_id)
        driver = drivers_by_id.get(driver_id)
        if route_slot is None or driver is None:
            raise ValueError(f"route-demand coverage candidate unavailable for route_slot_id={route_slot_id}")
        service_date_driver_key = (route_slot.service_date, driver_id)
        if service_date_driver_key in seen_service_date_driver_ids:
            raise RuntimeError(f"route-demand coverage candidate blocked for route_slot_id={route_slot_id}")
        seen_service_date_driver_ids.add(service_date_driver_key)
        exclude_route_slot_ids = _same_day_reserve_route_slot_ids(
            reserve_rows=next_reserve_rows,
            service_date=route_slot.service_date,
            driver_id=driver_id,
        )
        validation = evaluate_hard_constraints(
            bundle=bundle,
            route_slot=route_slot,
            driver=driver,
            schedule_state=schedule_state,
            exclude_route_slot_ids=exclude_route_slot_ids,
        )
        if validation.status != "pass":
            raise RuntimeError(f"route-demand coverage candidate blocked for route_slot_id={route_slot_id}")
        reserve_clear_count = 0
        if bool(candidate.get("clear_same_day_on_call_reserve")):
            next_reserve_rows, reserve_clear_count = _clear_same_day_reserve_rows(
                reserve_rows=next_reserve_rows,
                driver_id=driver_id,
                service_date=route_slot.service_date,
            )
            cleared_same_day_reserve_count += reserve_clear_count
            for reserve_route_slot_id in exclude_route_slot_ids:
                if reserve_route_slot_id in schedule_state.route_slots_by_id:
                    schedule_state.record_unassigned(
                        _scheduled_assignment_for_unassigned_route_slot(
                            route_slot=schedule_state.route_slot(reserve_route_slot_id),
                            iteration_index=next_iteration_index,
                        )
                    )
        candidate["hard_filter_status"] = validation.status
        candidate["hard_filter_reasons"] = list(validation.reasons)
        appended_row = _appended_assignment_row(
            route_slot=route_slot,
            candidate=candidate,
            route_demand_artifact_version_id=route_demand_artifact_version_id,
            bundle=bundle,
            iteration_index=next_iteration_index,
        )
        appended_rows.append(appended_row)
        selected_candidates.append(candidate)
        schedule_state.record_assignment(
            _scheduled_assignment_from_payload(
                route_slot=route_slot,
                driver_id=driver_id,
                candidate=candidate,
                assignment_action="assign",
                iteration_index=next_iteration_index,
                delta_kind="route_demand_coverage",
            )
        )
    return {
        "appended_rows": appended_rows,
        "reserve_rows": next_reserve_rows,
        "selected": selected_candidates,
        "assigned_count": len(selected_candidates),
        "appended_assignment_count": len(appended_rows),
        "cleared_same_day_reserve_count": cleared_same_day_reserve_count,
    }


def _detect_added_route_slot_targets(
    *,
    old_slots: Sequence[RouteSlotRequirement],
    updated_slots: Sequence[RouteSlotRequirement],
    service_dates: Iterable[str] | None,
) -> list[RouteSlotRequirement]:
    allowed_service_dates = {
        str(service_date).strip()
        for service_date in service_dates or []
        if str(service_date).strip()
    }
    old_groups = _group_route_slots_by_family(old_slots)
    updated_groups = _group_route_slots_by_family(updated_slots)
    targets: list[RouteSlotRequirement] = []
    for family_key, updated_group in sorted(updated_groups.items(), key=lambda item: item[0]):
        if allowed_service_dates and family_key[0] not in allowed_service_dates:
            continue
        old_group = old_groups.get(family_key, ())
        delta = max(len(updated_group) - len(old_group), 0)
        if delta <= 0:
            continue
        old_ids = {route_slot.route_slot_id for route_slot in old_group}
        preferred_targets = [
            route_slot
            for route_slot in updated_group
            if route_slot.route_slot_id not in old_ids
        ]
        if len(preferred_targets) >= delta:
            targets.extend(preferred_targets[-delta:])
            continue
        targets.extend(updated_group[-delta:])
    return sorted(
        targets,
        key=lambda route_slot: (
            route_slot.service_date,
            route_slot.shift_start,
            route_slot.route_slot_id,
        ),
    )


def _build_route_slot_aliases(
    *,
    old_slots: Sequence[RouteSlotRequirement],
    updated_slots: Sequence[RouteSlotRequirement],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    old_groups = _group_route_slots_by_family(old_slots)
    updated_groups = _group_route_slots_by_family(updated_slots)
    for family_key, old_group in old_groups.items():
        updated_group = updated_groups.get(family_key, ())
        if not updated_group:
            continue
        for index, old_slot in enumerate(old_group):
            if old_slot.route_slot_id in {slot.route_slot_id for slot in updated_group}:
                aliases[old_slot.route_slot_id] = old_slot.route_slot_id
                continue
            target_index = min(index, len(updated_group) - 1)
            aliases[old_slot.route_slot_id] = updated_group[target_index].route_slot_id
    return aliases


def _build_schedule_state(
    *,
    old_bundle: WeeklyScheduleControlBundle,
    updated_bundle: WeeklyScheduleControlBundle,
    assignment_rows: Iterable[Mapping[str, Any]],
    reserve_rows: Iterable[Mapping[str, Any]],
    route_slot_aliases: Mapping[str, str],
) -> PartialWeeklyScheduleState:
    del old_bundle
    updated_slots = tuple(expand_route_slot_requirements(updated_bundle.route_slots))
    state = _build_schedule_state_from_updated_slots(
        updated_slots=updated_slots,
        assignment_rows=assignment_rows,
        reserve_rows=reserve_rows,
        route_slot_aliases=route_slot_aliases,
    )
    return state


def _build_schedule_state_from_updated_slots(
    *,
    updated_slots: Sequence[RouteSlotRequirement],
    assignment_rows: Iterable[Mapping[str, Any]],
    reserve_rows: Iterable[Mapping[str, Any]],
    route_slot_aliases: Mapping[str, str] | None = None,
) -> PartialWeeklyScheduleState:
    state = PartialWeeklyScheduleState.from_route_slots(updated_slots)
    updated_slots_by_id = {route_slot.route_slot_id: route_slot for route_slot in updated_slots}
    extra_route_slots: list[RouteSlotRequirement] = []
    reserve_assignments: list[ScheduledAssignment] = []
    for row in reserve_rows:
        route_slot_id = _normalized_text(row.get("route_slot_id"))
        if not route_slot_id:
            continue
        if route_slot_id not in updated_slots_by_id and route_slot_id not in state.route_slots_by_id:
            extra_route_slots.append(_synthetic_reserve_route_slot(row))
        assignment = _scheduled_assignment_from_row(
            row=row,
            route_slots_by_id=updated_slots_by_id,
            assignment_action=str(row.get("assignment_action") or "reserve").strip() or "reserve",
            default_delta_kind="manual_edit",
            route_slot_aliases=route_slot_aliases or {},
        )
        if assignment is not None:
            reserve_assignments.append(assignment)
    if extra_route_slots:
        state.extend_route_slots(extra_route_slots)
    for row in assignment_rows:
        assignment = _scheduled_assignment_from_row(
            row=row,
            route_slots_by_id=state.route_slots_by_id,
            assignment_action="assign",
            default_delta_kind="manual_edit",
            route_slot_aliases=route_slot_aliases or {},
        )
        if assignment is None:
            continue
        if assignment.assignment_action == "assign":
            state.record_assignment(assignment)
        else:
            state.record_unassigned(assignment)
    for assignment in reserve_assignments:
        if assignment.assignment_action == "reserve":
            state.record_assignment(assignment)
        else:
            state.record_unassigned(assignment)
    return state


def _group_route_slots_by_family(
    route_slots: Sequence[RouteSlotRequirement],
) -> dict[tuple[str, str, str, str, str, str, str, str, str, str], tuple[RouteSlotRequirement, ...]]:
    grouped: dict[
        tuple[str, str, str, str, str, str, str, str, str, str],
        list[RouteSlotRequirement],
    ] = defaultdict(list)
    for route_slot in sorted(
        route_slots,
        key=lambda item: (
            item.service_date,
            item.station_code,
            item.service_area,
            item.shift_start,
            item.route_slot_id,
        ),
    ):
        grouped[_route_slot_family_key(route_slot)].append(route_slot)
    return {
        key: tuple(value)
        for key, value in grouped.items()
    }


def _route_slot_family_key(
    route_slot: RouteSlotRequirement,
) -> tuple[str, str, str, str, str, str, str, str, str, str]:
    return (
        route_slot.service_date,
        route_slot.station_code,
        route_slot.service_area,
        route_slot.route_slot_class,
        route_slot.required_skill,
        route_slot.vehicle_type,
        route_slot.shift_start,
        route_slot.shift_end,
        route_slot.route_id,
        route_slot.demand_kind,
    )


def _coverage_target_payload(route_slot: RouteSlotRequirement) -> dict[str, Any]:
    return {
        "target_id": _target_id_for_route_slot(route_slot),
        "route_slot_id": route_slot.route_slot_id,
        "route_id": route_slot.route_id,
        "service_date": route_slot.service_date,
        "route_slot_class": route_slot.route_slot_class,
        "station_code": route_slot.station_code,
        "service_area": route_slot.service_area,
        "shift_start": route_slot.shift_start,
        "shift_end": route_slot.shift_end,
        "projected_minutes": route_slot.projected_minutes,
        "required_skill": route_slot.required_skill,
        "vehicle_type": route_slot.vehicle_type,
    }


def _coverage_candidate_payload(
    *,
    candidate: Mapping[str, Any],
    target: RouteSlotRequirement,
    drivers_by_id: Mapping[str, Any],
    reserve_rows: Iterable[Mapping[str, Any]],
    recommendation_rank: int,
) -> dict[str, Any]:
    driver_id = str(candidate.get("candidate_driver_id") or "").strip()
    reserve_row = _same_day_reserve_row(
        reserve_rows=reserve_rows,
        service_date=target.service_date,
        driver_id=driver_id,
    )
    driver = drivers_by_id.get(driver_id)
    driver_name = str(
        getattr(driver, "driver_name", "")
        or driver_id
    ).strip()
    hard_filter_status = str(candidate.get("hard_filter_status") or "blocked").strip() or "blocked"
    return {
        "recommendation_rank": recommendation_rank,
        "target_id": _target_id_for_route_slot(target),
        "route_slot_id": target.route_slot_id,
        "route_id": target.route_id,
        "row_kind": "assignment",
        "service_date": target.service_date,
        "driver_id": driver_id,
        "driver_name": driver_name,
        "selection_state": "selectable" if hard_filter_status == "pass" else "blocked",
        "hard_filter_status": hard_filter_status,
        "hard_filter_reasons": list(candidate.get("hard_filter_reasons") or []),
        "score_bucket": str(candidate.get("score_bucket") or ""),
        "soft_score_total": float(candidate.get("soft_score_total") or 0.0),
        "projected_minutes": int(candidate.get("projected_minutes") or target.projected_minutes),
        "availability_state": str(candidate.get("availability_state") or ""),
        "current_week_shift_count": int(candidate.get("current_week_shift_count") or 0),
        "projected_rolling7_minutes": int(candidate.get("projected_rolling7_minutes") or 0),
        "remaining_rolling7_minutes": int(candidate.get("remaining_rolling7_minutes") or 0),
        "fairness_balance": float(candidate.get("fairness_balance") or 0.0),
        "target_shift_gap": float(candidate.get("target_shift_gap") or 0.0),
        "preference_fit": float(candidate.get("preference_fit") or 0.0),
        "preferred_shift_band_fit": float(candidate.get("preferred_shift_band_fit") or 0.0),
        "preferred_route_slot_class_fit": float(
            candidate.get("preferred_route_slot_class_fit") or 0.0
        ),
        "seniority_preference_fit": float(candidate.get("seniority_preference_fit") or 0.0),
        "reliability_score": float(candidate.get("reliability_score") or 0.0),
        "previous_week_stability": float(candidate.get("previous_week_stability") or 0.0),
        "baseline_template_state": str(candidate.get("baseline_template_state") or ""),
        "planned_driver_day_state": str(candidate.get("planned_driver_day_state") or ""),
        "new_agreement_required": bool(candidate.get("new_agreement_required")),
        "new_agreement_trigger_reason": str(candidate.get("new_agreement_trigger_reason") or ""),
        "template_state_preservation_fit": float(
            candidate.get("template_state_preservation_fit") or 0.0
        ),
        "clear_same_day_on_call_reserve": reserve_row is not None,
        "reserve_route_slot_id": (
            str(reserve_row.get("route_slot_id") or "").strip()
            if reserve_row is not None
            else None
        ),
        "reserve_route_id": (
            str(reserve_row.get("route_id") or "").strip()
            if reserve_row is not None
            else None
        ),
        "assignment_action": "add_route_assignment",
        "evaluation_kind": str(candidate.get("evaluation_kind") or "route_demand_coverage"),
    }


def _selected_route_demand_coverage_defaults(
    candidate_groups: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    groups_by_service_date: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for group in candidate_groups:
        target = group.get("target") if isinstance(group, Mapping) else None
        if not isinstance(target, Mapping):
            continue
        service_date = str(target.get("service_date") or "").strip()
        if not service_date:
            continue
        groups_by_service_date[service_date].append(group)

    selected_defaults: list[dict[str, Any]] = []
    for service_date in sorted(groups_by_service_date):
        selected_defaults.extend(
            _best_distinct_service_date_defaults(groups_by_service_date[service_date])
        )
    return selected_defaults


def _best_distinct_service_date_defaults(
    candidate_groups: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selectable_options: list[list[tuple[int, Mapping[str, Any]]]] = []
    driver_masks: dict[str, int] = {}
    for group in candidate_groups:
        options: list[tuple[int, Mapping[str, Any]]] = []
        for candidate_index, candidate in enumerate(list(group.get("candidates") or [])):
            if not isinstance(candidate, Mapping):
                continue
            if not _candidate_is_selectable(candidate):
                continue
            driver_id = str(candidate.get("driver_id") or "").strip()
            if not driver_id:
                continue
            options.append((candidate_index, candidate))
            if driver_id not in driver_masks:
                driver_masks[driver_id] = 1 << len(driver_masks)
        selectable_options.append(options)

    skip_order_index = MAX_ROUTE_DEMAND_COVERAGE_CANDIDATES + 1

    @lru_cache(maxsize=None)
    def solve(
        group_index: int,
        used_driver_mask: int,
    ) -> tuple[int, float, int, tuple[int, ...], tuple[tuple[int, int], ...]]:
        if group_index >= len(candidate_groups):
            return (0, 0.0, 0, (), ())

        next_solution = solve(group_index + 1, used_driver_mask)
        best_solution = (
            next_solution[0],
            next_solution[1],
            next_solution[2],
            (skip_order_index,) + next_solution[3],
            next_solution[4],
        )

        for candidate_index, candidate in selectable_options[group_index]:
            driver_id = str(candidate.get("driver_id") or "").strip()
            driver_mask = driver_masks[driver_id]
            if used_driver_mask & driver_mask:
                continue
            child_solution = solve(group_index + 1, used_driver_mask | driver_mask)
            candidate_solution = (
                1 + child_solution[0],
                float(candidate.get("soft_score_total") or 0.0) + child_solution[1],
                int(candidate.get("recommendation_rank") or candidate_index + 1) + child_solution[2],
                (candidate_index,) + child_solution[3],
                ((group_index, candidate_index),) + child_solution[4],
            )
            if _route_demand_default_solution_better(candidate_solution, best_solution):
                best_solution = candidate_solution

        return best_solution

    solution = solve(0, 0)
    selected_defaults: list[dict[str, Any]] = []
    for group_index, candidate_index in solution[4]:
        group = candidate_groups[group_index]
        target = group.get("target") if isinstance(group, Mapping) else None
        if not isinstance(target, Mapping):
            continue
        candidate = list(group.get("candidates") or [])[candidate_index]
        if not isinstance(candidate, Mapping):
            continue
        selected_defaults.append(
            {
                "target_id": str(target.get("target_id") or "").strip(),
                "route_slot_id": str(target.get("route_slot_id") or "").strip(),
                "driver_id": str(candidate.get("driver_id") or "").strip(),
                "row_kind": "assignment",
            }
        )
    return selected_defaults


def _route_demand_default_solution_better(
    candidate_solution: tuple[int, float, int, tuple[int, ...], tuple[tuple[int, int], ...]],
    current_solution: tuple[int, float, int, tuple[int, ...], tuple[tuple[int, int], ...]],
) -> bool:
    if candidate_solution[0] != current_solution[0]:
        return candidate_solution[0] > current_solution[0]
    if candidate_solution[1] != current_solution[1]:
        return candidate_solution[1] > current_solution[1]
    if candidate_solution[2] != current_solution[2]:
        return candidate_solution[2] < current_solution[2]
    return candidate_solution[3] < current_solution[3]


def _candidate_is_selectable(candidate: Mapping[str, Any]) -> bool:
    return (
        str(candidate.get("selection_state") or "").strip() == "selectable"
        and str(candidate.get("hard_filter_status") or "").strip() == "pass"
    )


def _scheduled_assignment_from_row(
    *,
    row: Mapping[str, Any],
    route_slots_by_id: Mapping[str, RouteSlotRequirement],
    assignment_action: str,
    default_delta_kind: str,
    route_slot_aliases: Mapping[str, str],
) -> ScheduledAssignment | None:
    route_slot_id = _normalized_text(row.get("route_slot_id"))
    if not route_slot_id:
        return None
    resolved_route_slot_id = route_slot_id
    if resolved_route_slot_id not in route_slots_by_id:
        resolved_route_slot_id = route_slot_aliases.get(route_slot_id, route_slot_id)
    route_slot = route_slots_by_id.get(resolved_route_slot_id)
    if route_slot is None:
        return None
    driver_id = _normalized_text(row.get("assigned_driver_id"))
    effective_assignment_action = assignment_action if driver_id else "unassigned"
    hard_filter_status = _normalized_text(row.get("assignment_status")) or (
        "pass" if driver_id else "unassigned"
    )
    return _scheduled_assignment_from_payload(
        route_slot=route_slot,
        driver_id=driver_id,
        candidate={
            "hard_filter_status": hard_filter_status,
            "hard_filter_reasons": list(row.get("hard_filter_reasons") or []),
            "score_bucket": _normalized_text(row.get("score_bucket")) or "manual",
            "soft_score_total": float(row.get("soft_score_total") or 0.0),
            "projected_minutes": int(row.get("projected_minutes") or route_slot.projected_minutes),
            "fairness_balance": float(row.get("fairness_balance") or 0.0),
            "availability_state": _normalized_text(row.get("availability_state")),
            "preferred_shift_band_fit": float(row.get("preferred_shift_band_fit") or 0.0),
            "preferred_route_slot_class_fit": float(
                row.get("preferred_route_slot_class_fit") or 0.0
            ),
            "preference_fit": float(row.get("preference_fit") or 0.0),
            "previous_week_stability": float(row.get("previous_week_stability") or 0.0),
            "continuity_score": float(row.get("continuity_score") or row.get("previous_week_stability") or 0.0),
            "target_shift_gap": float(row.get("target_shift_gap") or 0.0),
            "seniority_preference_fit": float(row.get("seniority_preference_fit") or 0.0),
            "reliability_score": float(row.get("reliability_score") or 0.0),
            "current_week_shift_count": int(row.get("current_week_shift_count") or 0),
            "projected_rolling7_minutes": int(row.get("projected_rolling7_minutes") or 0),
            "remaining_rolling7_minutes": int(row.get("remaining_rolling7_minutes") or 0),
            "baseline_template_state": _normalized_text(row.get("baseline_template_state")),
            "planned_driver_day_state": _normalized_text(row.get("planned_driver_day_state")),
            "new_agreement_required": bool(row.get("new_agreement_required")),
            "new_agreement_trigger_reason": _normalized_text(row.get("new_agreement_trigger_reason")),
            "template_state_preservation_fit": float(row.get("template_state_preservation_fit") or 0.0),
        },
        assignment_action=effective_assignment_action,
        iteration_index=int(row.get("iteration_index") or 0),
        delta_kind=_normalized_text(row.get("delta_kind")) or default_delta_kind,
    )


def _scheduled_assignment_from_payload(
    *,
    route_slot: RouteSlotRequirement,
    driver_id: str,
    candidate: Mapping[str, Any],
    assignment_action: str,
    iteration_index: int,
    delta_kind: str,
) -> ScheduledAssignment:
    return ScheduledAssignment(
        route_slot_id=route_slot.route_slot_id,
        route_id=route_slot.route_id,
        service_date=route_slot.service_date,
        candidate_driver_id=driver_id,
        assignment_action=assignment_action,
        hard_filter_status=str(candidate.get("hard_filter_status") or "pass"),
        hard_filter_reasons=tuple(str(item) for item in candidate.get("hard_filter_reasons") or []),
        score_bucket=str(candidate.get("score_bucket") or "manual"),
        soft_score_total=float(candidate.get("soft_score_total") or 0.0),
        projected_minutes=int(candidate.get("projected_minutes") or route_slot.projected_minutes),
        fairness_balance=float(candidate.get("fairness_balance") or 0.0),
        on_call_coverage=float(candidate.get("on_call_coverage") or 0.0),
        lost_work_credit=float(candidate.get("lost_work_credit") or 0.0),
        coverage_pressure=float(candidate.get("coverage_pressure") or 0.0),
        availability_fit=float(candidate.get("availability_fit") or 0.0),
        availability_state=str(candidate.get("availability_state") or ""),
        availability_state_fit=float(candidate.get("availability_state_fit") or 0.0),
        preferred_shift_band_fit=float(candidate.get("preferred_shift_band_fit") or 0.0),
        preferred_route_slot_class_fit=float(candidate.get("preferred_route_slot_class_fit") or 0.0),
        preference_fit=float(candidate.get("preference_fit") or 0.0),
        previous_week_stability=float(candidate.get("previous_week_stability") or 0.0),
        continuity_score=float(
            candidate.get("continuity_score")
            or candidate.get("previous_week_stability")
            or 0.0
        ),
        target_shift_gap=float(candidate.get("target_shift_gap") or 0.0),
        seniority_score=float(candidate.get("seniority_score") or 0.0),
        seniority_preference_fit=float(candidate.get("seniority_preference_fit") or 0.0),
        reliability_score=float(candidate.get("reliability_score") or 0.0),
        avoidable_assignment_score=float(candidate.get("avoidable_assignment_score") or 0.0),
        current_week_shift_count=int(candidate.get("current_week_shift_count") or 0),
        projected_rolling7_minutes=int(candidate.get("projected_rolling7_minutes") or 0),
        remaining_rolling7_minutes=int(candidate.get("remaining_rolling7_minutes") or 0),
        iteration_index=max(iteration_index, 0),
        batch_id="route-demand-coverage",
        pressure_group_id=f"{route_slot.service_date}:{route_slot.station_code}:{route_slot.service_area}",
        delta_kind=delta_kind,
        rationale_code="route_demand_coverage",
        route_slot_class=route_slot.route_slot_class,
        station_code=route_slot.station_code,
        service_area=route_slot.service_area,
        planning_phase="manual_edit",
        baseline_template_state=str(candidate.get("baseline_template_state") or ""),
        planned_driver_day_state=str(candidate.get("planned_driver_day_state") or ""),
        new_agreement_required=bool(candidate.get("new_agreement_required")),
        new_agreement_trigger_reason=str(candidate.get("new_agreement_trigger_reason") or ""),
        template_state_preservation_fit=float(
            candidate.get("template_state_preservation_fit") or 0.0
        ),
    )


def _scheduled_assignment_for_unassigned_route_slot(
    *,
    route_slot: RouteSlotRequirement,
    iteration_index: int,
) -> ScheduledAssignment:
    return ScheduledAssignment(
        route_slot_id=route_slot.route_slot_id,
        route_id=route_slot.route_id,
        service_date=route_slot.service_date,
        candidate_driver_id="",
        assignment_action="unassigned",
        hard_filter_status="unassigned",
        hard_filter_reasons=(),
        score_bucket="manual",
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
        iteration_index=max(iteration_index, 0),
        batch_id="route-demand-coverage",
        pressure_group_id=f"{route_slot.service_date}:{route_slot.station_code}:{route_slot.service_area}",
        delta_kind="route_demand_coverage",
        rationale_code="route_demand_coverage",
        route_slot_class=route_slot.route_slot_class,
        station_code=route_slot.station_code,
        service_area=route_slot.service_area,
        planning_phase="manual_edit",
    )


def _synthetic_reserve_route_slot(row: Mapping[str, Any]) -> RouteSlotRequirement:
    service_date = _normalized_text(row.get("service_date"))
    route_slot_id = _normalized_text(row.get("route_slot_id"))
    projected_minutes = int(row.get("projected_minutes") or 0)
    return RouteSlotRequirement(
        service_date=service_date,
        route_slot_id=route_slot_id,
        route_slot_class=_normalized_text(row.get("route_slot_class")) or "on_call",
        required_skill="",
        vehicle_type="",
        shift_start=_normalized_text(row.get("shift_start")) or "00:00",
        shift_end=_normalized_text(row.get("shift_end")) or "23:59",
        estimated_hours=max(projected_minutes, 0) / 60.0,
        source_snapshot_row_ref="synthetic-reserve-row",
        required_count=1,
        route_id=_normalized_text(row.get("route_id")) or "ON_CALL",
        station_code=_normalized_text(row.get("station_code")),
        service_area=_normalized_text(row.get("service_area")),
        route_family="on_call",
        preferred_shift_band="",
        demand_kind="on_call",
    )


def _same_day_reserve_row(
    *,
    reserve_rows: Iterable[Mapping[str, Any]],
    service_date: str,
    driver_id: str,
) -> Mapping[str, Any] | None:
    for row in reserve_rows:
        if _normalized_text(row.get("service_date")) != service_date:
            continue
        if _normalized_text(row.get("assigned_driver_id")) != driver_id:
            continue
        return row
    return None


def _same_day_reserve_route_slot_ids(
    *,
    reserve_rows: Iterable[Mapping[str, Any]],
    service_date: str,
    driver_id: str | None,
) -> set[str]:
    route_slot_ids: set[str] = set()
    for row in reserve_rows:
        if _normalized_text(row.get("service_date")) != service_date:
            continue
        if driver_id is not None and _normalized_text(row.get("assigned_driver_id")) != driver_id:
            continue
        route_slot_id = _normalized_text(row.get("route_slot_id"))
        if route_slot_id:
            route_slot_ids.add(route_slot_id)
    return route_slot_ids


def _clear_same_day_reserve_rows(
    *,
    reserve_rows: Sequence[Mapping[str, Any]],
    driver_id: str,
    service_date: str,
) -> tuple[list[dict[str, Any]], int]:
    cleared_count = 0
    next_rows: list[dict[str, Any]] = []
    for row in reserve_rows:
        next_row = dict(row)
        if (
            _normalized_text(next_row.get("service_date")) == service_date
            and _normalized_text(next_row.get("assigned_driver_id")) == driver_id
        ):
            next_row["assigned_driver_id"] = ""
            next_row["assignment_status"] = "manual_override"
            cleared_count += 1
        next_rows.append(next_row)
    return next_rows, cleared_count


def _appended_assignment_row(
    *,
    route_slot: RouteSlotRequirement,
    candidate: Mapping[str, Any],
    route_demand_artifact_version_id: str,
    bundle: WeeklyScheduleControlBundle,
    iteration_index: int,
) -> dict[str, Any]:
    driver_id = str(candidate.get("driver_id") or "").strip()
    return {
        "service_date": route_slot.service_date,
        "route_slot_id": route_slot.route_slot_id,
        "assigned_driver_id": driver_id,
        "assignment_status": "manual_override",
        "projected_minutes": route_slot.projected_minutes,
        "baseline_template_state": str(candidate.get("baseline_template_state") or ""),
        "planned_driver_day_state": str(candidate.get("planned_driver_day_state") or ""),
        "new_agreement_required": bool(candidate.get("new_agreement_required")),
        "new_agreement_trigger_reason": str(candidate.get("new_agreement_trigger_reason") or ""),
        "template_state_preservation_fit": float(
            candidate.get("template_state_preservation_fit") or 0.0
        ),
        "candidate_delta_id": (
            f"midweek-route-demand:{route_demand_artifact_version_id}:{route_slot.route_slot_id}:{driver_id}"
        ),
        "source_bundle_id": bundle.bundle_id,
        "iteration_index": iteration_index,
        "delta_kind": "route_demand_coverage",
        "previous_week_stability": float(candidate.get("previous_week_stability") or 0.0),
    }


def _next_iteration_index(
    *,
    assignment_rows: Iterable[Mapping[str, Any]],
) -> int:
    max_iteration_index = 0
    for row in assignment_rows:
        try:
            max_iteration_index = max(max_iteration_index, int(row.get("iteration_index") or 0))
        except (TypeError, ValueError):
            continue
    return max_iteration_index + 1


def _target_id_for_route_slot(route_slot: RouteSlotRequirement) -> str:
    return f"{route_slot.service_date}:{route_slot.route_slot_id}"


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()
