from __future__ import annotations

from onetruth.application.services.schedule_control import build_weekly_schedule_control_bundle
from onetruth.application.services.schedule_control.planning_state import (
    PartialWeeklyScheduleState,
    ScheduledAssignment,
)
from onetruth.application.services.schedule_control.validation import evaluate_hard_constraints


def test_evaluate_hard_constraints_fails_for_missing_skill() -> None:
    bundle = _build_bundle(
        route_required_skill="rescue_support",
        driver_skills="parcel_delivery",
        driver_restrictions="",
        shift_end="20:10",
        actual_minutes=1000,
        approved_unavailable_dates="",
    )

    result = evaluate_hard_constraints(
        bundle=bundle,
        route_slot=bundle.route_slots[0],
        driver=bundle.drivers[0],
    )

    assert result.status == "fail"
    assert "missing_required_skill" in result.reasons


def test_evaluate_hard_constraints_blocks_for_restrictions_and_rolling_limit() -> None:
    bundle = _build_bundle(
        route_required_skill="parcel_delivery",
        driver_skills="parcel_delivery",
        driver_restrictions="no_shift_after_21_30,max_minutes_rolling7=3300",
        shift_end="21:45",
        actual_minutes=3200,
        approved_unavailable_dates="",
    )

    result = evaluate_hard_constraints(
        bundle=bundle,
        route_slot=bundle.route_slots[0],
        driver=bundle.drivers[0],
    )

    assert result.status == "blocked"
    assert "restriction_no_shift_after_21_30" in result.reasons
    assert "rolling_7_day_limit" in result.reasons


def test_evaluate_hard_constraints_blocks_for_driver_day_unavailable() -> None:
    bundle = _build_bundle(
        route_required_skill="parcel_delivery",
        driver_skills="parcel_delivery",
        driver_restrictions="",
        shift_end="20:10",
        actual_minutes=800,
        approved_unavailable_dates="2026-03-02",
    )

    result = evaluate_hard_constraints(
        bundle=bundle,
        route_slot=bundle.route_slots[0],
        driver=bundle.drivers[0],
    )

    assert result.status == "blocked"
    assert "driver_unavailable" in result.reasons


def test_evaluate_hard_constraints_keeps_on_call_only_as_soft_state() -> None:
    workflow_run = {
        "workflow_run_id": "wr-weekly-on-call-soft",
        "partition_key": "PW-2026-W10",
    }
    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-routes-on-call-soft",
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
                ],
                "rows": [
                    [
                        "2026-03-02",
                        "slot-20260302-cx200",
                        "cycle1_standard_late",
                        "parcel_delivery",
                        "XL_van",
                        "11:30",
                        "20:00",
                        8.0,
                        "amazon:row-100",
                    ],
                ],
            },
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-on-call-soft",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": {
                "columns": [
                    "driver_id",
                    "skills",
                    "vehicle_certifications",
                    "eligible_route_slot_classes",
                    "approved_restrictions",
                    "notes",
                ],
                "rows": [["DRV-01", "parcel_delivery", "XL_van", "cycle1_standard_late", "", ""]],
            },
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-on-call-soft",
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
                        "On Call Only",
                        "2026-03-02",
                        "ON_CALL_ONLY",
                        "",
                        "",
                        1,
                        "yes",
                        "late",
                        "NA",
                        "no",
                        "",
                    ],
                ],
            },
        },
    )

    result = evaluate_hard_constraints(
        bundle=bundle,
        route_slot=bundle.route_slots[0],
        driver=bundle.drivers[0],
    )

    assert result.status == "pass"
    assert result.driver_day_availability_state == "ON_CALL_ONLY"


def test_evaluate_hard_constraints_blocks_for_same_day_overlap_when_state_is_present() -> None:
    workflow_run = {
        "workflow_run_id": "wr-weekly-overlap",
        "partition_key": "PW-2026-W10",
    }
    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-routes-overlap",
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
                ],
                "rows": [
                    [
                        "2026-03-02",
                        "slot-20260302-cx100",
                        "cycle1_standard",
                        "parcel_delivery",
                        "XL_van",
                        "10:00",
                        "18:00",
                        8.0,
                        "amazon:row-001",
                    ],
                    [
                        "2026-03-02",
                        "slot-20260302-cx101",
                        "cycle1_standard",
                        "parcel_delivery",
                        "XL_van",
                        "13:00",
                        "21:00",
                        8.0,
                        "amazon:row-002",
                    ],
                ],
            },
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-overlap",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": {
                "columns": [
                    "driver_id",
                    "skills",
                    "vehicle_certifications",
                    "eligible_route_slot_classes",
                    "approved_restrictions",
                    "notes",
                ],
                "rows": [["DRV-01", "parcel_delivery", "XL_van", "cycle1_standard", "", ""]],
            },
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-overlap",
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
                "rows": [["DRV-01", 4, "yes", "", "Mon,Tue,Wed,Thu"]],
            },
        },
    )
    schedule_state = PartialWeeklyScheduleState.from_route_slots(bundle.route_slots)
    schedule_state.record_assignment(
        ScheduledAssignment(
            route_slot_id=bundle.route_slots[0].route_slot_id,
            route_id=bundle.route_slots[0].route_id,
            service_date=bundle.route_slots[0].service_date,
            candidate_driver_id="DRV-01",
            assignment_action="assign",
            hard_filter_status="pass",
            hard_filter_reasons=(),
            score_bucket="best",
            soft_score_total=0.9,
            projected_minutes=bundle.route_slots[0].projected_minutes,
            fairness_balance=0.8,
            on_call_coverage=0.8,
            lost_work_credit=0.8,
            coverage_pressure=0.8,
            availability_fit=1.0,
            availability_state="AVAILABLE",
            availability_state_fit=1.0,
            preferred_shift_band_fit=0.8,
            preferred_route_slot_class_fit=0.8,
            preference_fit=0.8667,
            previous_week_stability=0.7,
            continuity_score=0.7,
            target_shift_gap=1.0,
            seniority_score=0.8,
            seniority_preference_fit=0.8,
            reliability_score=0.8,
            avoidable_assignment_score=0.9,
            current_week_shift_count=1,
            projected_rolling7_minutes=900,
            remaining_rolling7_minutes=1500,
            iteration_index=1,
            batch_id="iter-01",
            pressure_group_id="2026-03-02|DVC4|Pitt Meadows",
            delta_kind="allocation",
            rationale_code="seed",
        )
    )

    result = evaluate_hard_constraints(
        bundle=bundle,
        route_slot=bundle.route_slots[1],
        driver=bundle.drivers[0],
        schedule_state=schedule_state,
    )

    assert result.status == "blocked"
    assert "shift_overlap" in result.reasons


def _build_bundle(
    *,
    route_required_skill: str,
    driver_skills: str,
    driver_restrictions: str,
    shift_end: str,
    actual_minutes: int,
    approved_unavailable_dates: str,
):
    workflow_run = {
        "workflow_run_id": "wr-weekly-validate",
        "partition_key": "PW-2026-W10",
    }
    route_slots_artifact = {
        "artifact_version_id": "av-routes-validate",
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
            ],
            "rows": [
                [
                    "2026-03-02",
                    "slot-20260302-cx100",
                    "cycle1_standard",
                    route_required_skill,
                    "XL_van",
                    "11:40",
                    shift_end,
                    8.5,
                    "amazon:row-001",
                ],
            ],
        },
    }
    driver_caps_artifact = {
        "artifact_version_id": "av-driver-validate",
        "artifact_kind": "planning.driver_capabilities.workbook",
        "dataset_key": "planning.driver_capabilities.workbook",
        "metadata_json": {
            "columns": [
                "driver_id",
                "skills",
                "vehicle_certifications",
                "eligible_route_slot_classes",
                "approved_restrictions",
                "notes",
            ],
            "rows": [
                [
                    "DRV-01",
                    driver_skills,
                    "XL_van",
                    "cycle1_standard",
                    driver_restrictions,
                    "",
                ],
            ],
        },
    }
    availability_artifact = {
        "artifact_version_id": "av-availability-validate",
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
            "rows": [["DRV-01", 4, "yes", approved_unavailable_dates, "Mon,Tue,Wed,Thu"]],
        },
    }
    actual_hours_artifact = {
        "artifact_version_id": "av-hours-validate",
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "dataset_key": "planning.actual_hours_snapshot.workbook",
        "metadata_json": {
            "columns": ["service_date", "driver_id", "actual_minutes"],
            "rows": [["2026-02-26", "DRV-01", actual_minutes]],
        },
    }

    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=route_slots_artifact,
        driver_capabilities_artifact=driver_caps_artifact,
        approved_availability_artifact=availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
    )
