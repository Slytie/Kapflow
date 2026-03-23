from __future__ import annotations

import hashlib
from typing import Any

from .bundle_builder import (
    DriverServiceDayState,
    WeeklyScheduleControlBundle,
)
from .contract_minimization import summarize_contract_change_metrics
from .iterative_allocator import (
    MAX_ALLOCATION_BATCH_SIZE,
    MAX_REPAIR_MOVES_PER_ITERATION,
    MIN_ALLOCATION_BATCH_SIZE,
)
from .planning_state import IterationSummary, RepairMove
from .scoring import SOFT_SCORE_WEIGHTS
from .scoring import summarize_soft_scores
from .validation import build_stage04_validation_summary


def render_stage04_input_bundle(
    *,
    bundle: WeeklyScheduleControlBundle,
) -> dict[str, Any]:
    return {
        "bundle": {
            "bundle_id": bundle.bundle_id,
            "trigger_type": bundle.trigger_type,
            "planning_week_id": bundle.planning_week_id,
            "scope_dates": {
                "start": bundle.scope_start,
                "end_exclusive": bundle.scope_end_exclusive,
            },
            "publish_intent": "publish_weekly_base_schedule",
            "referenced_artifacts": list(bundle.referenced_artifacts),
            "external_evidence_refs": list(bundle.external_evidence_refs),
            "planner_notes": list(bundle.planner_notes),
            "demand_by_service_date": [
                {
                    "service_date": item.service_date,
                    "planned_route_count": item.planned_route_count,
                    "standard_slot_count": item.standard_slot_count,
                    "standard_early_slot_count": item.standard_early_slot_count,
                    "standard_late_slot_count": item.standard_late_slot_count,
                    "rescue_slot_count": item.rescue_slot_count,
                    "overflow_slot_count": item.overflow_slot_count,
                    "source_message_ids": list(item.source_message_ids),
                    "source_kind": item.source_kind,
                    "change_kind": item.change_kind,
                }
                for item in sorted(
                    bundle.daily_demand_by_service_date.values(),
                    key=lambda row: row.service_date,
                )
            ],
            "route_slots": [
                {
                    "service_date": item.service_date,
                    "route_slot_id": item.route_slot_id,
                    "route_id": item.route_id,
                    "route_family": item.route_family,
                    "route_slot_class": item.route_slot_class,
                    "required_skill": item.required_skill,
                    "vehicle_type": item.vehicle_type,
                    "shift_start": item.shift_start,
                    "shift_end": item.shift_end,
                    "preferred_shift_band": item.preferred_shift_band,
                    "projected_minutes": item.projected_minutes,
                    "required_count": item.required_count,
                    "station_code": item.station_code,
                    "service_area": item.service_area,
                    "source_message_id": item.source_message_id,
                    "source_kind": item.source_kind,
                    "source_snapshot_row_ref": item.source_snapshot_row_ref,
                }
                for item in bundle.route_slots
            ],
            "driver_profiles": [
                _driver_profile(bundle=bundle, driver_id=driver.driver_id)
                for driver in bundle.drivers
            ],
            "deterministic_iteration_model": {
                "planner_truth_owner": "deterministic_stage04_allocator",
                "planning_phases": [
                    "baseline_allocation",
                    "bounded_improvement_reallocation",
                ],
                "batch_size_range": {
                    "min": MIN_ALLOCATION_BATCH_SIZE,
                    "max": MAX_ALLOCATION_BATCH_SIZE,
                },
                "max_repair_moves_per_iteration": MAX_REPAIR_MOVES_PER_ITERATION,
                "repair_posture": "prefer_local_reallocation_over_broad_weekly_rewrites",
                "soft_score_weights": {
                    key: round(value, 4) for key, value in sorted(SOFT_SCORE_WEIGHTS.items())
                },
            },
        }
    }


def render_stage04_candidate_delta(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    iteration_summaries: list[IterationSummary],
    repair_moves: list[RepairMove],
    coverage_summary: dict[str, Any],
) -> dict[str, Any]:
    candidate_delta_id = stage04_candidate_delta_id(
        bundle_id=bundle.bundle_id,
        selected_candidates=selected_candidates,
        iteration_summaries=iteration_summaries,
        repair_moves=repair_moves,
    )
    contract_change_summary = summarize_contract_change_metrics(selected_candidates)
    columns = [
        "candidate_delta_id",
        "route_slot_id",
        "service_date",
        "route_id",
        "assigned_driver_id",
        "assignment_action",
        "rationale_code",
        "projected_minutes",
        "source_bundle_id",
        "iteration_index",
        "phase",
        "delta_kind",
        "pressure_group_id",
        "availability_state",
        "baseline_template_state",
        "planned_driver_day_state",
        "new_agreement_required",
        "new_agreement_trigger_reason",
        "template_state_preservation_fit",
        "preference_fit",
        "continuity_score",
        "preferred_shift_band_fit",
        "preferred_route_slot_class_fit",
        "seniority_preference_fit",
        "avoidable_assignment_score",
        "previous_week_stability",
        "coverage_pressure",
    ]
    rows: list[list[Any]] = []
    for selected in selected_candidates:
        route_slot_id = str(selected.get("route_slot_id") or "")
        rows.append(
            [
                candidate_delta_id,
                route_slot_id,
                str(selected.get("service_date") or ""),
                _route_id_from_slot(route_slot_id),
                str(selected.get("candidate_driver_id") or ""),
                str(selected.get("assignment_action") or "assign"),
                str(selected.get("rationale_code") or ""),
                int(selected.get("projected_minutes") or 0),
                bundle.bundle_id,
                int(selected.get("iteration_index") or 0),
                str(selected.get("planning_phase") or ""),
                str(selected.get("delta_kind") or "allocation"),
                str(selected.get("pressure_group_id") or ""),
                str(selected.get("availability_state") or ""),
                str(selected.get("baseline_template_state") or ""),
                str(selected.get("planned_driver_day_state") or ""),
                bool(selected.get("new_agreement_required")),
                str(selected.get("new_agreement_trigger_reason") or ""),
                round(float(selected.get("template_state_preservation_fit") or 0.0), 4),
                round(float(selected.get("preference_fit") or 0.0), 4),
                round(float(selected.get("continuity_score") or 0.0), 4),
                round(float(selected.get("preferred_shift_band_fit") or 0.0), 4),
                round(float(selected.get("preferred_route_slot_class_fit") or 0.0), 4),
                round(float(selected.get("seniority_preference_fit") or 0.0), 4),
                round(float(selected.get("avoidable_assignment_score") or 0.0), 4),
                round(float(selected.get("previous_week_stability") or 0.0), 4),
                round(float(selected.get("coverage_pressure") or 0.0), 4),
            ]
        )

    return {
        "columns": columns,
        "rows": rows,
        "candidate_delta_id": candidate_delta_id,
        "coverage_summary": coverage_summary,
        "contract_change_summary": contract_change_summary,
        "iteration_deltas": [item.to_payload() for item in iteration_summaries],
        "repair_moves": [item.to_payload() for item in repair_moves],
        "reallocation_moves": [item.to_payload() for item in repair_moves],
    }


def render_stage04_validation_summary(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    candidate_delta_id: str,
    iteration_summaries: list[IterationSummary],
    repair_moves: list[RepairMove],
    coverage_summary: dict[str, Any],
) -> dict[str, Any]:
    soft_totals = summarize_soft_scores(selected_candidates)
    summary = build_stage04_validation_summary(
        bundle=bundle,
        selected_candidates=selected_candidates,
        soft_score_totals=soft_totals,
        iteration_summaries=iteration_summaries,
        repair_moves=repair_moves,
    )
    summary["candidate_delta_id"] = candidate_delta_id
    summary["coverage_summary"] = coverage_summary
    return {"summary": summary}


def render_stage04_draft_weekly_schedule_workbook(
    *,
    bundle: WeeklyScheduleControlBundle,
    selected_candidates: list[dict[str, Any]],
    candidate_delta_id: str,
    iteration_summaries: list[IterationSummary],
) -> dict[str, Any]:
    columns = [
        "service_date",
        "route_slot_id",
        "assigned_driver_id",
        "assignment_status",
        "projected_minutes",
        "baseline_template_state",
        "planned_driver_day_state",
        "new_agreement_required",
        "new_agreement_trigger_reason",
        "template_state_preservation_fit",
        "candidate_delta_id",
        "source_bundle_id",
        "iteration_index",
        "delta_kind",
        "previous_week_stability",
    ]
    rows: list[list[Any]] = []
    for selected in selected_candidates:
        rows.append(
            [
                str(selected.get("service_date") or ""),
                str(selected.get("route_slot_id") or ""),
                str(selected.get("candidate_driver_id") or ""),
                str(selected.get("hard_filter_status") or "blocked"),
                int(selected.get("projected_minutes") or 0),
                str(selected.get("baseline_template_state") or ""),
                str(selected.get("planned_driver_day_state") or ""),
                bool(selected.get("new_agreement_required")),
                str(selected.get("new_agreement_trigger_reason") or ""),
                round(float(selected.get("template_state_preservation_fit") or 0.0), 4),
                candidate_delta_id,
                bundle.bundle_id,
                int(selected.get("iteration_index") or 0),
                str(selected.get("delta_kind") or "allocation"),
                round(float(selected.get("previous_week_stability") or 0.0), 4),
            ]
        )

    return {
        "columns": columns,
        "rows": rows,
        "iteration_deltas": [item.to_payload() for item in iteration_summaries],
    }


def render_stage04_draft_weekly_schedule_doc(
    *,
    bundle: WeeklyScheduleControlBundle,
    validation_summary: dict[str, Any],
    selected_candidates: list[dict[str, Any]],
    iteration_summaries: list[IterationSummary],
    coverage_summary: dict[str, Any],
) -> dict[str, Any]:
    summary = validation_summary.get("summary") if isinstance(validation_summary, dict) else {}
    contract_change_summary = summarize_contract_change_metrics(selected_candidates)
    return {
        "summary": {
            "bundle_id": bundle.bundle_id,
            "selected_route_slot_count": len(selected_candidates),
            "hard_rule_result": str(summary.get("hard_rule_result") or "unknown"),
            "recommended_action": str(summary.get("recommended_action") or "review_required"),
            "warnings": list(summary.get("warnings") or []),
            "violations": list(summary.get("violations") or []),
            "tradeoffs": list(summary.get("tradeoffs") or []),
            "iteration_count": len(iteration_summaries),
            "repair_move_count": int(
                ((summary.get("churn_summary") or {}).get("repair_move_count") or 0)
            ),
            "phase_counts": dict((coverage_summary.get("phase_counts") or {})),
            "coverage_summary": coverage_summary,
            **contract_change_summary,
        },
        "selected_assignments": [
            {
                "service_date": str(selected.get("service_date") or ""),
                "route_slot_id": str(selected.get("route_slot_id") or ""),
                "route_id": str(selected.get("route_id") or ""),
                "candidate_driver_id": str(selected.get("candidate_driver_id") or ""),
                "baseline_template_state": str(selected.get("baseline_template_state") or ""),
                "planned_driver_day_state": str(selected.get("planned_driver_day_state") or ""),
                "new_agreement_required": bool(selected.get("new_agreement_required")),
                "new_agreement_trigger_reason": str(
                    selected.get("new_agreement_trigger_reason") or ""
                ),
                "template_state_preservation_fit": round(
                    float(selected.get("template_state_preservation_fit") or 0.0),
                    4,
                ),
            }
            for selected in selected_candidates
            if str(selected.get("assignment_action") or "assign") == "assign"
        ],
        "contract_change_summary": {
            key: value for key, value in contract_change_summary.items()
        }
    }


def stage04_candidate_delta_id(
    *,
    bundle_id: str,
    selected_candidates: list[dict[str, Any]],
    iteration_summaries: list[IterationSummary] | None = None,
    repair_moves: list[RepairMove] | None = None,
) -> str:
    rows = [
        "|".join(
            [
                str(item.get("service_date") or ""),
                str(item.get("route_slot_id") or ""),
                str(item.get("candidate_driver_id") or ""),
                str(item.get("hard_filter_status") or ""),
                str(item.get("score_bucket") or ""),
                str(item.get("delta_kind") or ""),
            ]
        )
        for item in sorted(
            selected_candidates,
            key=lambda row: (
                str(row.get("service_date") or ""),
                str(row.get("route_slot_id") or ""),
            ),
        )
    ]
    iteration_rows = [
        "|".join(
            [
                str(item.iteration_index),
                item.batch_id,
                item.pressure_group_id,
                str(item.batch_size),
                ",".join(item.route_slot_ids),
                ",".join(item.assigned_route_slot_ids),
                ",".join(item.uncovered_route_slot_ids),
            ]
        )
        for item in (iteration_summaries or [])
    ]
    repair_rows = [
        "|".join(
            [
                str(item.iteration_index),
                item.filled_route_slot_id,
                item.reassigned_route_slot_id,
                item.replacement_driver_id,
            ]
        )
        for item in (repair_moves or [])
    ]
    digest = hashlib.sha256(
        (bundle_id + "\n" + "\n".join(rows + iteration_rows + repair_rows)).encode("utf-8")
    ).hexdigest()[:8]
    compact = bundle_id.removeprefix("bundle-")
    return f"cand-{compact}-{digest}"


def _route_id_from_slot(route_slot_id: str) -> str:
    compact = route_slot_id.split("#", maxsplit=1)[0]
    token = compact.rsplit("-", maxsplit=1)[-1]
    return token.upper()


def _driver_profile(
    *,
    bundle: WeeklyScheduleControlBundle,
    driver_id: str,
) -> dict[str, Any]:
    capability = next(driver for driver in bundle.drivers if driver.driver_id == driver_id)
    availability = bundle.availability_by_driver.get(driver_id)
    policy_signal = bundle.policy_signals_by_driver.get(driver_id)
    rolling_7 = bundle.rolling_7_compliance_by_driver.get(driver_id)

    return {
        "driver_id": driver_id,
        "driver_name": capability.driver_name or (availability.driver_name if availability else ""),
        "employment_type": capability.employment_type or (
            availability.employment_type if availability else ""
        ),
        "home_station": capability.home_station,
        "skills": list(capability.skills),
        "vehicle_certifications": list(capability.vehicle_certifications),
        "eligible_route_slot_classes": list(capability.eligible_route_slot_classes),
        "preferred_route_slot_classes": list(capability.preferred_route_slot_classes),
        "preferred_shift_band": capability.preferred_shift_band,
        "approved_restrictions": list(capability.approved_restrictions),
        "seniority_rank": capability.seniority_rank,
        "attendance_reliability_index": capability.attendance_reliability_index,
        "recent_sick_calls_14d": capability.recent_sick_calls_14d,
        "recent_cancellations_14d": capability.recent_cancellations_14d,
        "external_driver_ref": capability.external_driver_ref,
        "policy_tags": list(
            dict.fromkeys(
                [
                    *capability.policy_tags,
                    *(availability.policy_tags if availability is not None else ()),
                    *(policy_signal.tags if policy_signal is not None else ()),
                ]
            )
        ),
        "target_shifts_per_week": (
            availability.target_shifts_per_week if availability is not None else 4
        ),
        "on_call_eligible": bool(availability.on_call_eligible) if availability is not None else False,
        "emergency_only": bool(availability.emergency_only) if availability is not None else False,
        "approved_unavailable_dates": list(
            availability.approved_unavailable_dates if availability is not None else ()
        ),
        "regular_pattern": list(availability.regular_pattern if availability is not None else ()),
        "notes": availability.notes if availability is not None else capability.notes,
        "daily_states": [
            _service_day_state_payload(item)
            for item in (availability.daily_states if availability is not None else ())
        ],
        "previous_week_states": [
            _service_day_state_payload(item)
            for item in (availability.previous_week_states if availability is not None else ())
        ],
        "rolling_7_compliance": (
            {
                "window_start": rolling_7.window_start,
                "window_end_exclusive": rolling_7.window_end_exclusive,
                "total_minutes": rolling_7.total_minutes,
                "days_worked": rolling_7.days_worked,
                "limit_minutes": rolling_7.limit_minutes,
                "remaining_minutes": rolling_7.remaining_minutes,
                "status": rolling_7.status,
            }
            if rolling_7 is not None
            else None
        ),
        "policy_signal": (
            {
                "target_shifts_per_week": policy_signal.target_shifts_per_week,
                "max_shifts_per_week": policy_signal.max_shifts_per_week,
                "max_minutes_rolling7": policy_signal.max_minutes_rolling7,
                "on_call_eligible": policy_signal.on_call_eligible,
                "emergency_only": policy_signal.emergency_only,
                "tags": list(policy_signal.tags),
            }
            if policy_signal is not None
            else None
        ),
    }


def _service_day_state_payload(item: DriverServiceDayState) -> dict[str, Any]:
    return {
        "service_date": item.service_date,
        "state": item.state,
        "normalized_state": item.normalized_state,
        "blocked_reasons": list(item.blocked_reasons),
        "actual_minutes": item.actual_minutes,
        "route_id": item.route_id,
        "route_slot_class": item.route_slot_class,
        "preferred_route_slot_classes": list(item.preferred_route_slot_classes),
        "avoid_route_slot_classes": list(item.avoid_route_slot_classes),
        "preferred_shift_band": item.preferred_shift_band,
        "previous_week_state": item.previous_week_state,
        "locked_by_manager": item.locked_by_manager,
        "call_in_sick_flag": item.call_in_sick_flag,
        "cancellation_flag": item.cancellation_flag,
        "non_working_day_flag": item.non_working_day_flag,
        "source_ref": item.source_ref,
    }
