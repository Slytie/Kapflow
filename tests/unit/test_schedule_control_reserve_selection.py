from __future__ import annotations

from onetruth.application.services.schedule_control import build_weekly_schedule_control_bundle
from onetruth.application.services.schedule_control.reserve_selection import (
    select_on_call_reserve_rows,
)


def test_select_on_call_reserve_rows_uses_daily_targets_and_eligible_only_drivers() -> None:
    bundle = _build_bundle(
        daily_targets=(("2026-03-02", 1, 2, 0),),
        driver_rows=(
            ("DRV-ELIG-1", "parcel_delivery", "cycle1_standard", "", "full_time"),
            ("DRV-ELIG-2", "parcel_delivery", "cycle1_standard", "", "full_time"),
            ("DRV-INELIG", "parcel_delivery", "cycle1_standard", "", "full_time"),
        ),
        availability_rows=(
            ("DRV-ELIG-1", 3, "yes", "2026-03-02", "AVAILABLE"),
            ("DRV-ELIG-2", 3, "yes", "2026-03-02", "AVAILABLE"),
            ("DRV-INELIG", 3, "no", "2026-03-02", "AVAILABLE"),
        ),
        actual_rows=(),
    )

    result = select_on_call_reserve_rows(
        bundle=bundle,
        selected_candidates=[],
        iteration_index=1,
    )

    assert result.reserve_summary["target_on_call_total"] == 2
    assert result.reserve_summary["selected_on_call_total"] == 2
    assert result.reserve_summary["selected_on_call_by_service_date"] == {"2026-03-02": 2}
    assert result.reserve_summary["unmet_on_call_target_by_service_date"] == {"2026-03-02": 0}
    assert {row["candidate_driver_id"] for row in result.reserve_rows} == {
        "DRV-ELIG-1",
        "DRV-ELIG-2",
    }
    assert all(row["planned_driver_day_state"] == "on_call" for row in result.reserve_rows)


def test_select_on_call_reserve_rows_counts_on_call_toward_caps_and_rolling7() -> None:
    bundle = _build_bundle(
        daily_targets=(
            ("2026-03-02", 1, 1, 0),
            ("2026-03-03", 1, 1, 0),
        ),
        driver_rows=(
            ("DRV-CAPPED", "parcel_delivery", "cycle1_standard", "max_shifts_per_week=1,max_minutes_rolling7=3000", "full_time"),
            ("DRV-ROLLED", "parcel_delivery", "cycle1_standard", "max_shifts_per_week=3,max_minutes_rolling7=1200", "full_time"),
            ("DRV-FALLBACK", "parcel_delivery", "cycle1_standard", "max_shifts_per_week=3,max_minutes_rolling7=3000", "full_time"),
        ),
        availability_rows=(
            ("DRV-CAPPED", 1, "yes", "2026-03-02", "AVAILABLE"),
            ("DRV-CAPPED", 1, "yes", "2026-03-03", "AVAILABLE"),
            ("DRV-ROLLED", 3, "yes", "2026-03-02", "AVAILABLE"),
            ("DRV-ROLLED", 3, "yes", "2026-03-03", "AVAILABLE"),
            ("DRV-FALLBACK", 3, "yes", "2026-03-02", "AVAILABLE"),
            ("DRV-FALLBACK", 3, "yes", "2026-03-03", "AVAILABLE"),
        ),
        actual_rows=(
            ("2026-03-01", "DRV-ROLLED", 1100),
        ),
    )

    result = select_on_call_reserve_rows(
        bundle=bundle,
        selected_candidates=[],
        iteration_index=7,
    )

    assert result.reserve_summary["target_on_call_total"] == 2
    assert result.reserve_summary["selected_on_call_total"] == 2
    rows_by_date = {
        row["service_date"]: row["candidate_driver_id"]
        for row in result.reserve_rows
    }
    assert rows_by_date["2026-03-02"] == "DRV-CAPPED"
    assert rows_by_date["2026-03-03"] == "DRV-FALLBACK"
    assert "DRV-ROLLED" not in {row["candidate_driver_id"] for row in result.reserve_rows}


def test_select_on_call_reserve_rows_allocates_excess_capacity_as_assigned_work() -> None:
    bundle = _build_bundle(
        daily_targets=(("2026-03-02", 1, 1, 2),),
        driver_rows=(
            ("DRV-ONCALL", "parcel_delivery", "cycle1_standard", "", "full_time"),
            ("DRV-PREFERRED", "parcel_delivery", "cycle1_standard", "", "full_time"),
            ("DRV-AVAILABLE", "parcel_delivery", "cycle1_standard", "", "full_time"),
            ("DRV-YELLOW", "parcel_delivery", "cycle1_standard", "", "full_time"),
            ("DRV-ONCALL-ONLY", "parcel_delivery", "cycle1_standard", "", "full_time"),
        ),
        availability_rows=(
            ("DRV-ONCALL", 3, "yes", "2026-03-02", "ON_CALL_ONLY"),
            ("DRV-PREFERRED", 3, "no", "2026-03-02", "PREFERRED"),
            ("DRV-AVAILABLE", 3, "no", "2026-03-02", "AVAILABLE"),
            ("DRV-YELLOW", 3, "no", "2026-03-02", "AVOID_IF_POSSIBLE"),
            ("DRV-ONCALL-ONLY", 3, "yes", "2026-03-02", "ON_CALL_ONLY"),
        ),
        actual_rows=(),
    )

    result = select_on_call_reserve_rows(
        bundle=bundle,
        selected_candidates=[],
        iteration_index=3,
    )

    assert result.reserve_summary["selected_on_call_total"] == 1
    assert result.reserve_rows[0]["candidate_driver_id"] == "DRV-ONCALL"
    assert result.excess_capacity_summary["target_excess_capacity_total"] == 2
    assert result.excess_capacity_summary["selected_excess_capacity_total"] == 2
    assert result.excess_capacity_summary["selected_excess_capacity_by_service_date"] == {
        "2026-03-02": 2
    }
    assert [row["candidate_driver_id"] for row in result.excess_capacity_rows] == [
        "DRV-PREFERRED",
        "DRV-AVAILABLE",
    ]
    assert all(
        row["planned_driver_day_state"] == "assigned"
        for row in result.excess_capacity_rows
    )
    assert "DRV-ONCALL-ONLY" not in {
        row["candidate_driver_id"] for row in result.excess_capacity_rows
    }


def _build_bundle(
    *,
    daily_targets: tuple[tuple[str, int, int, int], ...],
    driver_rows: tuple[tuple[str, str, str, str, str], ...],
    availability_rows: tuple[tuple[str, int, str, str, str], ...],
    actual_rows: tuple[tuple[str, str, int], ...],
):
    workflow_run = {
        "workflow_run_id": "wr-weekly-reserve-tests",
        "partition_key": "PW-2026-W10",
    }
    route_slot_requirements_artifact = {
        "artifact_version_id": "av-routes-reserve-tests",
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
                "required_count",
                "route_id",
                "source_snapshot_row_ref",
            ],
            "rows": [
                [
                    service_date,
                    f"slot-{service_date}-cycle1",
                    "cycle1_standard",
                    "parcel_delivery",
                    "XL_van",
                    "11:30",
                    "20:00",
                    8.5,
                    route_count,
                    f"ROUTE-{service_date}",
                    f"daily:{service_date}",
                ]
                for service_date, route_count, _on_call_target, _excess_target in daily_targets
            ],
            "daily_demand_columns": [
                "service_date",
                "planned_route_count",
                "on_call_target",
                "excess_capacity_target",
                "standard_slot_count",
                "rescue_slot_count",
                "overflow_slot_count",
                "source_message_id",
                "source_kind",
                "change_kind",
            ],
            "daily_demand_rows": [
                [
                    service_date,
                    route_count,
                    on_call_target,
                    excess_capacity_target,
                    route_count,
                    0,
                    0,
                    f"daily:{service_date}",
                    "unit_test",
                    "override",
                ]
                for service_date, route_count, on_call_target, excess_capacity_target in daily_targets
            ],
        },
    }
    driver_capabilities_artifact = {
        "artifact_version_id": "av-driver-reserve-tests",
        "artifact_kind": "planning.driver_capabilities.workbook",
        "dataset_key": "planning.driver_capabilities.workbook",
        "metadata_json": {
            "columns": [
                "driver_id",
                "skills",
                "vehicle_certifications",
                "eligible_route_slot_classes",
                "approved_restrictions",
                "employment_type",
                "notes",
            ],
            "rows": [
                [driver_id, skills, "XL_van", eligible_classes, restrictions, employment_type, ""]
                for driver_id, skills, eligible_classes, restrictions, employment_type in driver_rows
            ],
        },
    }
    approved_availability_artifact = {
        "artifact_version_id": "av-availability-reserve-tests",
        "artifact_kind": "planning.approved_availability.workbook",
        "dataset_key": "planning.approved_availability.workbook",
        "metadata_json": {
            "columns": [
                "driver_id",
                "service_date",
                "availability_state",
                "target_shifts_per_week",
                "on_call_eligible",
                "preferred_route_slot_classes",
                "avoid_route_slot_classes",
                "previous_week_state",
                "locked_by_manager",
            ],
            "rows": [
                [
                    driver_id,
                    service_date,
                    state,
                    target_shifts_per_week,
                    on_call_eligible,
                    "cycle1_standard",
                    "",
                    "NA",
                    "no",
                ]
                for driver_id, target_shifts_per_week, on_call_eligible, service_date, state in availability_rows
            ],
        },
    }
    actual_hours_artifact = {
        "artifact_version_id": "av-actual-reserve-tests",
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "dataset_key": "planning.actual_hours_snapshot.workbook",
        "metadata_json": {
            "columns": ["service_date", "driver_id", "actual_minutes"],
            "rows": [list(row) for row in actual_rows],
        },
    }

    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=route_slot_requirements_artifact,
        driver_capabilities_artifact=driver_capabilities_artifact,
        approved_availability_artifact=approved_availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
    )
