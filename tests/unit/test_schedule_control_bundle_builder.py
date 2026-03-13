from __future__ import annotations

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_realistic_weekly_stage04_fixture_payloads,
)
from onetruth.application.services.schedule_control import build_weekly_schedule_control_bundle
from onetruth.application.services.schedule_control.route_slot_requirements import (
    RouteSlotRequirement,
    expand_route_slot_requirements,
)


def test_build_weekly_schedule_control_bundle_resolves_artifacts_and_driver_context() -> None:
    workflow_run = {
        "workflow_run_id": "wr-weekly-001",
        "partition_key": "PW-2026-W10",
    }
    route_slots_artifact = {
        "artifact_version_id": "av-routes-001",
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
                    "11:40",
                    "20:10",
                    8.5,
                    "amazon:row-001",
                ],
                [
                    "2026-03-03",
                    "slot-20260303-cx086",
                    "cycle1_rescue",
                    "rescue_support",
                    "XL_van",
                    "11:45",
                    "21:00",
                    9.2,
                    "amazon:row-002",
                ],
            ],
        },
    }
    driver_caps_artifact = {
        "artifact_version_id": "av-driver-001",
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
                    "parcel_delivery,rescue_support",
                    "XL_van",
                    "cycle1_standard,cycle1_rescue",
                    "",
                    "Anchor",
                ],
                [
                    "DRV-02",
                    "parcel_delivery",
                    "XL_van",
                    "cycle1_standard",
                    "no_shift_after_21_30",
                    "On-call",
                ],
            ],
        },
    }
    availability_artifact = {
        "artifact_version_id": "av-availability-001",
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
                ["DRV-01", 4, "no", "", "Mon,Tue,Wed,Thu"],
                ["DRV-02", 3, "yes", "2026-03-03", "Mon,Wed,Fri"],
            ],
        },
    }
    actual_hours_artifact = {
        "artifact_version_id": "av-hours-001",
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "dataset_key": "planning.actual_hours_snapshot.workbook",
        "metadata_json": {
            "columns": ["service_date", "driver_id", "actual_minutes"],
            "rows": [
                ["2026-02-25", "DRV-01", 390],
                ["2026-02-26", "DRV-01", 410],
                ["2026-02-25", "DRV-02", 520],
            ],
        },
    }

    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=route_slots_artifact,
        driver_capabilities_artifact=driver_caps_artifact,
        approved_availability_artifact=availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
    )

    assert bundle.bundle_id.startswith("bundle-pw-2026-w10-stage04-")
    assert bundle.scope_start == "2026-03-02"
    assert bundle.scope_end_exclusive == "2026-03-09"
    assert [slot.route_slot_id for slot in bundle.route_slots] == [
        "slot-20260302-cx100",
        "slot-20260303-cx086",
    ]
    assert [driver.driver_id for driver in bundle.drivers] == ["DRV-01", "DRV-02"]
    assert bundle.actual_minutes_by_driver == {"DRV-01": 800, "DRV-02": 520}
    assert bundle.availability_by_driver["DRV-02"].on_call_eligible is True
    assert [item["dataset_key"] for item in bundle.referenced_artifacts] == [
        "planning.approved_availability.workbook",
        "planning.actual_hours_snapshot.workbook",
        "planning.route_slot_requirements.workbook",
        "planning.driver_capabilities.workbook",
    ]


def test_expand_route_slot_requirements_expands_multiplier_suffix() -> None:
    slots = (
        RouteSlotRequirement(
            service_date="2026-03-02",
            route_slot_id="slot-20260302-cx100*2",
            route_slot_class="cycle1_standard",
            required_skill="parcel_delivery",
            vehicle_type="XL_van",
            shift_start="11:40",
            shift_end="20:10",
            estimated_hours=8.5,
            source_snapshot_row_ref="amazon:row-001",
        ),
    )

    expanded = expand_route_slot_requirements(slots)

    assert [item.route_slot_id for item in expanded] == [
        "slot-20260302-cx100#01",
        "slot-20260302-cx100#02",
    ]


def test_build_weekly_schedule_control_bundle_parses_realistic_day_resolution_fixture() -> None:
    workflow_run = {
        "workflow_run_id": "wr-weekly-realistic-001",
        "partition_key": "PW-2026-W10",
    }
    fixture = build_realistic_weekly_stage04_fixture_payloads()

    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-route-realistic-001",
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "dataset_key": "planning.route_slot_requirements.workbook",
            "metadata_json": fixture["route_slot_requirements"],
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-realistic-001",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": fixture["driver_capabilities"],
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-realistic-001",
            "artifact_kind": "planning.approved_availability.workbook",
            "dataset_key": "planning.approved_availability.workbook",
            "metadata_json": fixture["approved_availability"],
        },
        actual_hours_artifact={
            "artifact_version_id": "av-hours-realistic-001",
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "dataset_key": "planning.actual_hours_snapshot.workbook",
            "metadata_json": fixture["actual_hours"],
        },
    )

    assert len(bundle.drivers) == 40
    assert sum(item.planned_route_count for item in bundle.daily_demand_by_service_date.values()) == 112
    assert sum(item.planned_route_count for item in bundle.daily_demand_by_service_date.values()) < (40 * 4)
    assert bundle.drivers[0].driver_name.startswith("Brahamvir Singh")
    assert bundle.drivers[0].home_station == "DVC4"
    assert bundle.availability_by_driver["RDRV-01"].daily_states[0].state == "approved_unavailable"
    assert len(bundle.availability_by_driver["RDRV-01"].daily_states) == 7
    assert len(bundle.availability_by_driver["RDRV-01"].previous_week_states) == 7
    assert bundle.availability_by_driver["RDRV-01"].previous_week_states[1].actual_minutes > 0
    assert bundle.rolling_7_compliance_by_driver["RDRV-02"].limit_minutes == 1800
    assert bundle.policy_signals_by_driver["RDRV-03"].max_shifts_per_week == 4
    assert bundle.daily_demand_by_service_date["2026-03-06"].overflow_slot_count == 2
