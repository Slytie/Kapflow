from __future__ import annotations

from onetruth.application.services.schedule_control import (
    build_weekly_schedule_control_bundle,
    run_iterative_weekly_allocation,
)


def test_iterative_allocator_applies_local_repair_to_cover_late_slot() -> None:
    bundle = _build_repair_bundle()

    result = run_iterative_weekly_allocation(bundle=bundle)

    decisions = {item["route_slot_id"]: item for item in result.selected_candidates}
    assert decisions["slot-20260302-early-a"]["candidate_driver_id"] == "DRV-02"
    assert decisions["slot-20260302-late-u"]["candidate_driver_id"] == "DRV-01"
    assert decisions["slot-20260302-early-a"]["delta_kind"] == "repair"
    assert decisions["slot-20260302-late-u"]["delta_kind"] == "repair"

    assert len(result.repair_moves) == 1
    repair = result.repair_moves[0]
    assert repair.filled_route_slot_id == "slot-20260302-late-u"
    assert repair.reassigned_route_slot_id == "slot-20260302-early-a"
    assert repair.previous_driver_id == "DRV-01"
    assert repair.replacement_driver_id == "DRV-02"

    assert result.iteration_summaries[0].batch_size == 6
    assert result.iteration_summaries[0].repair_move_count == 1
    assert result.coverage_summary["assigned_route_slots"] == 6
    assert result.coverage_summary["repair_move_count"] == 1
    assert len(result.candidate_matrix) > 36


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
