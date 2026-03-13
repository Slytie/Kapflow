from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable

from .bundle_builder import WeeklyScheduleControlBundle
from .route_slot_requirements import RouteSlotRequirement


@dataclass(frozen=True)
class ScheduledAssignment:
    route_slot_id: str
    route_id: str
    service_date: str
    candidate_driver_id: str
    assignment_action: str
    hard_filter_status: str
    hard_filter_reasons: tuple[str, ...]
    score_bucket: str
    soft_score_total: float
    projected_minutes: int
    fairness_balance: float
    on_call_coverage: float
    lost_work_credit: float
    coverage_pressure: float
    availability_fit: float
    previous_week_stability: float
    target_shift_gap: float
    seniority_score: float
    reliability_score: float
    current_week_shift_count: int
    projected_rolling7_minutes: int
    remaining_rolling7_minutes: int
    iteration_index: int
    batch_id: str
    pressure_group_id: str
    delta_kind: str
    rationale_code: str
    route_slot_class: str = ""
    station_code: str = ""
    service_area: str = ""
    repair_depth: int = 0
    previous_assignment_driver_id: str = ""
    displaced_route_slot_id: str = ""
    displaced_driver_id: str = ""
    warnings: tuple[str, ...] = ()

    def to_row(self) -> dict[str, Any]:
        return {
            "route_slot_id": self.route_slot_id,
            "route_id": self.route_id,
            "service_date": self.service_date,
            "candidate_driver_id": self.candidate_driver_id,
            "assignment_action": self.assignment_action,
            "hard_filter_status": self.hard_filter_status,
            "hard_filter_reasons": list(self.hard_filter_reasons),
            "score_bucket": self.score_bucket,
            "soft_score_total": self.soft_score_total,
            "projected_minutes": self.projected_minutes,
            "fairness_balance": self.fairness_balance,
            "on_call_coverage": self.on_call_coverage,
            "lost_work_credit": self.lost_work_credit,
            "coverage_pressure": self.coverage_pressure,
            "availability_fit": self.availability_fit,
            "previous_week_stability": self.previous_week_stability,
            "target_shift_gap": self.target_shift_gap,
            "seniority_score": self.seniority_score,
            "reliability_score": self.reliability_score,
            "current_week_shift_count": self.current_week_shift_count,
            "projected_rolling7_minutes": self.projected_rolling7_minutes,
            "remaining_rolling7_minutes": self.remaining_rolling7_minutes,
            "iteration_index": self.iteration_index,
            "batch_id": self.batch_id,
            "pressure_group_id": self.pressure_group_id,
            "delta_kind": self.delta_kind,
            "rationale_code": self.rationale_code,
            "route_slot_class": self.route_slot_class,
            "station_code": self.station_code,
            "service_area": self.service_area,
            "repair_depth": self.repair_depth,
            "previous_assignment_driver_id": self.previous_assignment_driver_id,
            "displaced_route_slot_id": self.displaced_route_slot_id,
            "displaced_driver_id": self.displaced_driver_id,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class RepairMove:
    iteration_index: int
    batch_id: str
    pressure_group_id: str
    filled_route_slot_id: str
    filled_driver_id: str
    reassigned_route_slot_id: str
    previous_driver_id: str
    replacement_driver_id: str
    score_gain: float
    repair_reason: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "iteration_index": self.iteration_index,
            "batch_id": self.batch_id,
            "pressure_group_id": self.pressure_group_id,
            "filled_route_slot_id": self.filled_route_slot_id,
            "filled_driver_id": self.filled_driver_id,
            "reassigned_route_slot_id": self.reassigned_route_slot_id,
            "previous_driver_id": self.previous_driver_id,
            "replacement_driver_id": self.replacement_driver_id,
            "score_gain": round(self.score_gain, 6),
            "repair_reason": self.repair_reason,
        }


@dataclass(frozen=True)
class IterationSummary:
    iteration_index: int
    batch_id: str
    pressure_group_id: str
    pressure_service_date: str
    pressure_station_code: str
    pressure_service_area: str
    batch_size: int
    route_slot_ids: tuple[str, ...]
    assigned_route_slot_ids: tuple[str, ...]
    uncovered_route_slot_ids: tuple[str, ...]
    repair_move_count: int
    covered_route_slot_count_after_iteration: int
    uncovered_route_slot_count_after_iteration: int
    candidate_evaluation_count: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "iteration_index": self.iteration_index,
            "batch_id": self.batch_id,
            "pressure_group_id": self.pressure_group_id,
            "pressure_service_date": self.pressure_service_date,
            "pressure_station_code": self.pressure_station_code,
            "pressure_service_area": self.pressure_service_area,
            "batch_size": self.batch_size,
            "route_slot_ids": list(self.route_slot_ids),
            "assigned_route_slot_ids": list(self.assigned_route_slot_ids),
            "uncovered_route_slot_ids": list(self.uncovered_route_slot_ids),
            "repair_move_count": self.repair_move_count,
            "covered_route_slot_count_after_iteration": self.covered_route_slot_count_after_iteration,
            "uncovered_route_slot_count_after_iteration": self.uncovered_route_slot_count_after_iteration,
            "candidate_evaluation_count": self.candidate_evaluation_count,
        }


@dataclass
class PartialWeeklyScheduleState:
    ordered_route_slot_ids: tuple[str, ...]
    route_slots_by_id: dict[str, RouteSlotRequirement]
    decisions_by_slot: dict[str, ScheduledAssignment] = field(default_factory=dict)
    assignments_by_slot: dict[str, ScheduledAssignment] = field(default_factory=dict)
    iteration_summaries: list[IterationSummary] = field(default_factory=list)
    repair_moves: list[RepairMove] = field(default_factory=list)

    @classmethod
    def from_route_slots(
        cls,
        route_slots: Iterable[RouteSlotRequirement],
    ) -> PartialWeeklyScheduleState:
        ordered = tuple(
            sorted(
                route_slots,
                key=lambda item: (
                    item.service_date,
                    item.station_code,
                    item.service_area,
                    item.shift_start,
                    item.route_slot_id,
                ),
            )
        )
        return cls(
            ordered_route_slot_ids=tuple(item.route_slot_id for item in ordered),
            route_slots_by_id={item.route_slot_id: item for item in ordered},
        )

    def has_decision(self, route_slot_id: str) -> bool:
        return route_slot_id in self.decisions_by_slot

    def route_slot(self, route_slot_id: str) -> RouteSlotRequirement:
        return self.route_slots_by_id[route_slot_id]

    def remaining_route_slots(self) -> tuple[RouteSlotRequirement, ...]:
        return tuple(
            self.route_slots_by_id[route_slot_id]
            for route_slot_id in self.ordered_route_slot_ids
            if route_slot_id not in self.decisions_by_slot
        )

    def record_assignment(self, assignment: ScheduledAssignment) -> None:
        self.decisions_by_slot[assignment.route_slot_id] = assignment
        self.assignments_by_slot[assignment.route_slot_id] = assignment

    def record_unassigned(self, assignment: ScheduledAssignment) -> None:
        self.decisions_by_slot[assignment.route_slot_id] = assignment
        self.assignments_by_slot.pop(assignment.route_slot_id, None)

    def record_iteration(self, summary: IterationSummary) -> None:
        self.iteration_summaries.append(summary)

    def record_repair_move(self, move: RepairMove) -> None:
        self.repair_moves.append(move)

    def driver_assignments(
        self,
        driver_id: str,
        *,
        exclude_route_slot_ids: set[str] | None = None,
    ) -> tuple[ScheduledAssignment, ...]:
        exclude = exclude_route_slot_ids or set()
        return tuple(
            sorted(
                (
                    assignment
                    for assignment in self.assignments_by_slot.values()
                    if assignment.candidate_driver_id == driver_id
                    and assignment.route_slot_id not in exclude
                ),
                key=lambda item: (
                    item.service_date,
                    self.route_slots_by_id[item.route_slot_id].shift_start,
                    item.route_slot_id,
                ),
            )
        )

    def driver_assignments_on_date(
        self,
        driver_id: str,
        service_date: str,
        *,
        exclude_route_slot_ids: set[str] | None = None,
    ) -> tuple[ScheduledAssignment, ...]:
        return tuple(
            assignment
            for assignment in self.driver_assignments(
                driver_id,
                exclude_route_slot_ids=exclude_route_slot_ids,
            )
            if assignment.service_date == service_date
        )

    def current_week_shift_count(
        self,
        driver_id: str,
        *,
        exclude_route_slot_ids: set[str] | None = None,
    ) -> int:
        return len(
            self.driver_assignments(driver_id, exclude_route_slot_ids=exclude_route_slot_ids)
        )

    def projected_minutes_for_driver(
        self,
        driver_id: str,
        *,
        exclude_route_slot_ids: set[str] | None = None,
    ) -> int:
        return sum(
            assignment.projected_minutes
            for assignment in self.driver_assignments(
                driver_id,
                exclude_route_slot_ids=exclude_route_slot_ids,
            )
        )

    def projected_rolling7_state(
        self,
        *,
        bundle: WeeklyScheduleControlBundle,
        driver_id: str,
        service_date: str,
        candidate_minutes: int = 0,
        exclude_route_slot_ids: set[str] | None = None,
    ) -> tuple[int, int]:
        service_day = date.fromisoformat(service_date)
        window_start = service_day - timedelta(days=6)
        window_start_text = window_start.isoformat()
        service_date_text = service_day.isoformat()
        exclude = exclude_route_slot_ids or set()

        actual_minutes = 0
        actual_days: set[str] = set()
        for entry in bundle.actual_entries_by_driver.get(driver_id, ()):
            if window_start_text <= entry.service_date <= service_date_text:
                actual_minutes += int(entry.actual_minutes)
                if int(entry.actual_minutes) > 0:
                    actual_days.add(entry.service_date)

        planned_minutes = 0
        planned_days: set[str] = set()
        for assignment in self.driver_assignments(
            driver_id,
            exclude_route_slot_ids=exclude,
        ):
            if window_start_text <= assignment.service_date <= service_date_text:
                planned_minutes += int(assignment.projected_minutes)
                if int(assignment.projected_minutes) > 0:
                    planned_days.add(assignment.service_date)

        total_minutes = actual_minutes + planned_minutes + max(int(candidate_minutes), 0)
        total_days = len(actual_days | planned_days | ({service_date_text} if candidate_minutes > 0 else set()))
        return total_minutes, total_days

    def final_decisions(self) -> list[ScheduledAssignment]:
        return [
            self.decisions_by_slot[route_slot_id]
            for route_slot_id in self.ordered_route_slot_ids
            if route_slot_id in self.decisions_by_slot
        ]

    def assigned_count(self) -> int:
        return len(self.assignments_by_slot)

    def uncovered_route_slot_ids(self) -> list[str]:
        return [
            route_slot_id
            for route_slot_id in self.ordered_route_slot_ids
            if route_slot_id in self.decisions_by_slot
            and self.decisions_by_slot[route_slot_id].assignment_action == "unassigned"
        ]
