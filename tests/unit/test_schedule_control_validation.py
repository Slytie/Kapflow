from __future__ import annotations

from onetruth.application.services.schedule_control import build_weekly_schedule_control_bundle
from onetruth.application.services.schedule_control.validation import evaluate_hard_constraints


def test_evaluate_hard_constraints_fails_for_missing_skill() -> None:
    bundle = _build_bundle(
        route_required_skill="rescue_support",
        driver_skills="parcel_delivery",
        driver_restrictions="",
        shift_end="20:10",
        actual_minutes=1000,
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
    )

    result = evaluate_hard_constraints(
        bundle=bundle,
        route_slot=bundle.route_slots[0],
        driver=bundle.drivers[0],
    )

    assert result.status == "blocked"
    assert "restriction_no_shift_after_21_30" in result.reasons
    assert "rolling_7_day_limit" in result.reasons


def _build_bundle(
    *,
    route_required_skill: str,
    driver_skills: str,
    driver_restrictions: str,
    shift_end: str,
    actual_minutes: int,
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
            "rows": [["DRV-01", 4, "yes", "", "Mon,Tue,Wed,Thu"]],
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
