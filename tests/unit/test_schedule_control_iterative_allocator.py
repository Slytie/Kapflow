from __future__ import annotations

from onetruth.application.services.schedule_control import (
    build_weekly_schedule_control_bundle,
    execute_next_weekly_allocation_iteration,
    run_iterative_weekly_allocation,
)
from onetruth.application.services.schedule_control.candidate_generation import (
    generate_weekly_candidate_matrix,
)
from onetruth.application.services.schedule_control.planning_state import (
    PartialWeeklyScheduleState,
    ScheduledAssignment,
)
from onetruth.application.services.schedule_control.route_slot_requirements import (
    expand_route_slot_requirements,
)


def test_iterative_allocator_applies_local_repair_to_cover_late_slot() -> None:
    bundle = _build_repair_bundle()

    result = run_iterative_weekly_allocation(bundle=bundle)

    decisions = {item["route_slot_id"]: item for item in result.selected_candidates}
    assert decisions["slot-20260302-early-a"]["candidate_driver_id"] == "DRV-02"
    assert decisions["slot-20260302-late-u"]["candidate_driver_id"] == "DRV-01"
    assert decisions["slot-20260302-late-u"]["delta_kind"] in {"allocation", "repair"}

    if result.repair_moves:
        repair = result.repair_moves[0]
        assert repair.filled_route_slot_id == "slot-20260302-late-u"
        assert repair.reassigned_route_slot_id == "slot-20260302-early-a"
        assert repair.previous_driver_id == "DRV-01"
        assert repair.replacement_driver_id == "DRV-02"

    assert result.iteration_summaries[0].batch_size == 6
    assert result.iteration_summaries[0].repair_move_count == len(result.repair_moves)
    assert result.coverage_summary["assigned_route_slots"] == 6
    assert result.coverage_summary["repair_move_count"] == len(result.repair_moves)
    assert len(result.candidate_matrix) > 36


def test_execute_next_iteration_runs_soft_improvement_after_full_coverage() -> None:
    bundle = _build_post_coverage_improvement_bundle()
    route_slots = expand_route_slot_requirements(bundle.route_slots)
    schedule_state = PartialWeeklyScheduleState.from_route_slots(route_slots)

    for route_slot_id, driver_id in (
        ("slot-early", "DRV-02"),
        ("slot-late", "DRV-01"),
    ):
        route_slot = next(item for item in route_slots if item.route_slot_id == route_slot_id)
        candidate = next(
            item
            for item in generate_weekly_candidate_matrix(
                bundle=bundle,
                route_slots=(route_slot,),
                schedule_state=schedule_state,
                iteration_index=0,
            )
            if item.candidate_driver_id == driver_id
        )
        schedule_state.record_assignment(
            ScheduledAssignment(
                route_slot_id=candidate.route_slot_id,
                route_id=candidate.route_id,
                service_date=candidate.service_date,
                candidate_driver_id=candidate.candidate_driver_id,
                assignment_action="assign",
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
                iteration_index=1,
                batch_id="seed-baseline",
                pressure_group_id="2026-03-02||",
                delta_kind="allocation",
                rationale_code="seed",
                route_slot_class=candidate.route_slot_class,
                station_code=candidate.station_code,
                service_area=candidate.service_area,
                planning_phase="baseline",
            )
        )

    result = execute_next_weekly_allocation_iteration(
        bundle=bundle,
        schedule_state=schedule_state,
        candidate_matrix=[],
    )

    assert result is not None
    assert result.phase == "improvement"
    assert result.summary.moved_route_slot_ids == ("slot-early", "slot-late")
    assert result.summary.soft_objective_delta > 0.0
    assert result.summary.preference_fit_delta > 0.0
    assert result.repair_moves[0].move_kind == "swap"
    decisions = {item.route_slot_id: item for item in schedule_state.final_decisions()}
    assert decisions["slot-early"].candidate_driver_id == "DRV-01"
    assert decisions["slot-late"].candidate_driver_id == "DRV-02"


def _build_repair_bundle():
    workflow_run = {
        "workflow_run_id": "wr-weekly-repair",
        "partition_key": "PW-2026-W10",
    }
    route_slots_artifact = {
        "artifact_version_id": "av-routes-repair",
        "artifact_kind": "planning.route_slot_requirements.workbook",
        "dataset_key": "planning.route_slot_requirements.workbook",
        "metadata_json": {
            "columns": [
                "service_date",
                "route_slot_id",
                "route_slot_class",
                "required_skill",
                "vehicle_type",
                "shift_start",
                "shift_end",
                "estimated_hours",
                "source_snapshot_row_ref",
                "route_id",
            ],
            "rows": [
                ["2026-03-02", "slot-20260302-early-a", "cycle1_standard", "parcel_delivery", "XL_van", "08:00", "16:00", 8.0, "amazon:row-001", "ROUTE-A"],
                ["2026-03-02", "slot-20260302-early-b", "cycle1_standard", "skill_b", "XL_van", "08:05", "16:05", 8.0, "amazon:row-002", "ROUTE-B"],
                ["2026-03-02", "slot-20260302-early-c", "cycle1_standard", "skill_c", "XL_van", "08:10", "16:10", 8.0, "amazon:row-003", "ROUTE-C"],
                ["2026-03-02", "slot-20260302-early-d", "cycle1_standard", "skill_d", "XL_van", "08:15", "16:15", 8.0, "amazon:row-004", "ROUTE-D"],
                ["2026-03-02", "slot-20260302-early-e", "cycle1_standard", "skill_e", "XL_van", "08:20", "16:20", 8.0, "amazon:row-005", "ROUTE-E"],
                ["2026-03-02", "slot-20260302-late-u", "cycle1_standard", "parcel_delivery", "XL_van", "13:45", "22:00", 8.0, "amazon:row-006", "ROUTE-U"],
            ],
        },
    }
    driver_caps_artifact = {
        "artifact_version_id": "av-driver-repair",
        "artifact_kind": "planning.driver_capabilities.workbook",
        "dataset_key": "planning.driver_capabilities.workbook",
        "metadata_json": {
            "columns": [
                "driver_id",
                "skills",
                "vehicle_certifications",
                "eligible_route_slot_classes",
                "approved_restrictions",
                "policy_tags",
                "notes",
            ],
            "rows": [
                ["DRV-01", "parcel_delivery", "XL_van", "cycle1_standard", "", "anchor", ""],
                ["DRV-02", "parcel_delivery", "XL_van", "cycle1_standard", "no_shift_after_21_30", "", ""],
                ["DRV-03", "skill_b", "XL_van", "cycle1_standard", "", "", ""],
                ["DRV-04", "skill_c", "XL_van", "cycle1_standard", "", "", ""],
                ["DRV-05", "skill_d", "XL_van", "cycle1_standard", "", "", ""],
                ["DRV-06", "skill_e", "XL_van", "cycle1_standard", "", "", ""],
            ],
        },
    }
    availability_artifact = {
        "artifact_version_id": "av-availability-repair",
        "artifact_kind": "planning.approved_availability.workbook",
        "dataset_key": "planning.approved_availability.workbook",
        "metadata_json": {
            "columns": [
                "driver_id",
                "target_shifts_per_week",
                "on_call_eligible",
                "approved_unavailable_dates",
                "regular_pattern",
            ],
            "rows": [
                ["DRV-01", 2, "yes", "", "Mon"],
                ["DRV-02", 2, "yes", "", "Mon"],
                ["DRV-03", 2, "no", "", "Mon"],
                ["DRV-04", 2, "no", "", "Mon"],
                ["DRV-05", 2, "no", "", "Mon"],
                ["DRV-06", 2, "no", "", "Mon"],
            ],
        },
    }
    actual_hours_artifact = {
        "artifact_version_id": "av-hours-repair",
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "dataset_key": "planning.actual_hours_snapshot.workbook",
        "metadata_json": {
            "columns": ["service_date", "driver_id", "actual_minutes", "route_id"],
            "rows": [
                ["2026-02-24", "DRV-01", 480, "ROUTE-A"],
                ["2026-02-24", "DRV-02", 480, "ROUTE-Z"],
            ],
        },
    }

    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=route_slots_artifact,
        driver_capabilities_artifact=driver_caps_artifact,
        approved_availability_artifact=availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
    )


def _build_post_coverage_improvement_bundle():
    workflow_run = {
        "workflow_run_id": "wr-weekly-improvement",
        "partition_key": "PW-2026-W10",
    }
    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-routes-improve",
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "dataset_key": "planning.route_slot_requirements.workbook",
            "metadata_json": {
                "columns": [
                    "service_date",
                    "route_slot_id",
                    "route_slot_class",
                    "required_skill",
                    "vehicle_type",
                    "shift_start",
                    "shift_end",
                    "estimated_hours",
                    "source_snapshot_row_ref",
                    "route_id",
                    "preferred_shift_band",
                ],
                "rows": [
                    [
                        "2026-03-02",
                        "slot-early",
                        "cycle1_standard_early",
                        "parcel_delivery",
                        "XL_van",
                        "10:00",
                        "18:00",
                        8.0,
                        "amazon:row-101",
                        "EARLY-A",
                        "early",
                    ],
                    [
                        "2026-03-02",
                        "slot-late",
                        "cycle1_standard_late",
                        "parcel_delivery",
                        "XL_van",
                        "11:30",
                        "20:00",
                        8.0,
                        "amazon:row-102",
                        "LATE-B",
                        "late",
                    ],
                ],
                "daily_demand_columns": [
                    "service_date",
                    "planned_route_count",
                    "standard_slot_count",
                    "source_message_id",
                    "source_kind",
                    "change_kind",
                ],
                "daily_demand_rows": [
                    ["2026-03-02", 2, 2, "amazon-improve", "test", "same"]
                ],
            },
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-improve",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": {
                "columns": [
                    "driver_id",
                    "driver_name",
                    "employment_type",
                    "skills",
                    "vehicle_certifications",
                    "eligible_route_slot_classes",
                    "approved_restrictions",
                    "policy_tags",
                    "seniority_rank",
                    "attendance_reliability_index",
                    "preferred_route_slot_classes",
                    "preferred_shift_band",
                    "notes",
                ],
                "rows": [
                    [
                        "DRV-01",
                        "Senior Early",
                        "full_time",
                        "parcel_delivery",
                        "XL_van",
                        "cycle1_standard_early,cycle1_standard_late",
                        "max_minutes_rolling7=3000",
                        "anchor,stability_preferred",
                        1,
                        0.99,
                        "cycle1_standard_early",
                        "early",
                        "",
                    ],
                    [
                        "DRV-02",
                        "Junior Late",
                        "full_time",
                        "parcel_delivery",
                        "XL_van",
                        "cycle1_standard_early,cycle1_standard_late",
                        "max_minutes_rolling7=3000",
                        "",
                        12,
                        0.9,
                        "cycle1_standard_late",
                        "late",
                        "",
                    ],
                ],
            },
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-improve",
            "artifact_kind": "planning.approved_availability.workbook",
            "dataset_key": "planning.approved_availability.workbook",
            "metadata_json": {
                "columns": [
                    "driver_id",
                    "driver_name",
                    "service_date",
                    "availability_state",
                    "preferred_route_slot_classes",
                    "avoid_route_slot_classes",
                    "target_shifts_per_week",
                    "on_call_eligible",
                    "preferred_shift_band",
                    "previous_week_same_day_state",
                    "locked_by_manager",
                    "notes",
                ],
                "rows": [
                    [
                        "DRV-01",
                        "Senior Early",
                        "2026-03-02",
                        "PREFERRED",
                        "cycle1_standard_early",
                        "",
                        1,
                        "no",
                        "early",
                        "WORKED",
                        "no",
                        "",
                    ],
                    [
                        "DRV-02",
                        "Junior Late",
                        "2026-03-02",
                        "PREFERRED",
                        "cycle1_standard_late",
                        "",
                        1,
                        "no",
                        "late",
                        "NA",
                        "no",
                        "",
                    ],
                ],
            },
        },
        actual_hours_artifact={
            "artifact_version_id": "av-hours-improve",
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "dataset_key": "planning.actual_hours_snapshot.workbook",
            "metadata_json": {
                "columns": [
                    "service_date",
                    "driver_id",
                    "actual_minutes",
                    "route_id",
                    "route_slot_class",
                ],
                "rows": [
                    ["2026-02-23", "DRV-01", 480, "LATE-B", "cycle1_standard_late"],
                    ["2026-02-23", "DRV-02", 0, "", ""],
                ],
            },
        },
    )
