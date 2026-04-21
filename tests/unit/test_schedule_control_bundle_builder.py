from __future__ import annotations

import copy

import pytest

from onetruth.application.services.logistics_weekly_agent_pilot import (
    build_actual_ops_weekly_stage04_fixture_payloads,
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
        "partition_key": "PW-2026-W12",
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
    assert sum(item.planned_route_count for item in bundle.daily_demand_by_service_date.values()) == 139
    assert sum(item.planned_route_count for item in bundle.daily_demand_by_service_date.values()) < (40 * 4)
    assert bundle.drivers[0].driver_name.startswith("Brahmvir Singh")
    assert bundle.drivers[0].home_station == "DVC4"
    assert bundle.drivers[0].seniority_rank > 0
    assert bundle.drivers[0].attendance_reliability_index > 0.0
    assert bundle.availability_by_driver["ODRV-01"].daily_states[0].state == "PREFERRED"
    assert bundle.availability_by_driver["ODRV-01"].daily_states[0].normalized_state == "available"
    assert len(bundle.availability_by_driver["ODRV-01"].daily_states) == 7
    assert len(bundle.availability_by_driver["ODRV-01"].previous_week_states) == 7
    assert bundle.availability_by_driver["ODRV-01"].previous_week_states[-1].state == "NA"
    assert bundle.rolling_7_compliance_by_driver["ODRV-05"].limit_minutes == 1800
    assert bundle.policy_signals_by_driver["ODRV-03"].max_shifts_per_week == 4
    assert bundle.daily_demand_by_service_date["2026-03-16"].standard_slot_count == 17
    assert bundle.daily_demand_by_service_date["2026-03-16"].standard_early_slot_count == 11
    assert bundle.daily_demand_by_service_date["2026-03-16"].standard_late_slot_count == 6


def test_build_weekly_schedule_control_bundle_parses_actual_ops_v3_policy_ranges() -> None:
    workflow_run = {
        "workflow_run_id": "wr-weekly-actual-ops-v3-001",
        "partition_key": "PW-2026-W13",
    }
    fixture = build_actual_ops_weekly_stage04_fixture_payloads()
    route_demand_rows = fixture["route_slot_requirements"]["daily_demand_rows"]
    assert len(route_demand_rows) == 14
    assert route_demand_rows[0][0] == "2026-03-22"
    assert route_demand_rows[-1][0] == "2026-04-04"

    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-route-actual-ops-v3-001",
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "dataset_key": "planning.route_slot_requirements.workbook",
            "metadata_json": fixture["route_slot_requirements"],
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-actual-ops-v3-001",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": fixture["driver_capabilities"],
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-actual-ops-v3-001",
            "artifact_kind": "planning.approved_availability.workbook",
            "dataset_key": "planning.approved_availability.workbook",
            "metadata_json": fixture["approved_availability"],
        },
        actual_hours_artifact={
            "artifact_version_id": "av-hours-actual-ops-v3-001",
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "dataset_key": "planning.actual_hours_snapshot.workbook",
            "metadata_json": fixture["actual_hours"],
        },
    )

    assert bundle.planning_policy.minimum_desired_shifts_per_week == 3
    assert bundle.planning_policy.preferred_target_shifts_per_week == 4
    assert bundle.planning_policy.avoid_overtime_after_shifts_per_week == 4
    assert bundle.planning_policy.heuristic_weekly_targets_are_soft is True
    assert bundle.planning_policy.heuristic_weekly_caps_are_soft is True
    assert bundle.planning_policy.heuristic_rolling7_caps_are_soft is True

    demand = bundle.daily_demand_by_service_date["2026-03-22"]
    assert demand.on_call_target == 4
    assert demand.on_call_target_range.min_count == 3
    assert demand.on_call_target_range.preferred_count == 4
    assert demand.on_call_target_range.max_count == 5
    assert demand.excess_capacity_target == 3
    assert demand.excess_capacity_target_range.min_count == 2
    assert demand.excess_capacity_target_range.preferred_count == 3
    assert demand.excess_capacity_target_range.max_count == 5

    policy_signal = bundle.policy_signals_by_driver["A185MOPEG4MOST"]
    assert policy_signal.source_target_shifts_per_week == 1
    assert policy_signal.target_shifts_per_week == 4
    assert policy_signal.max_shifts_per_week == 1
    assert policy_signal.hard_max_shifts_per_week is None
    assert policy_signal.max_minutes_rolling7 == 600
    assert policy_signal.hard_max_minutes_rolling7 is None
    assert policy_signal.minimum_desired_shifts_per_week == 3
    assert policy_signal.avoid_overtime_after_shifts_per_week == 4


def test_realistic_weekly_stage04_fixture_payloads_lock_overcapacity_contract() -> None:
    fixture = build_realistic_weekly_stage04_fixture_payloads()

    route_slots = fixture["route_slot_requirements"]
    driver_caps = fixture["driver_capabilities"]
    availability = fixture["approved_availability"]
    actual_hours = fixture["actual_hours"]

    assert sum(int(item[1]) for item in route_slots["daily_demand_rows"]) == 139
    assert "route_family" in route_slots["columns"]
    assert "preferred_shift_band" in route_slots["columns"]
    assert "projected_minutes" in route_slots["columns"]

    assert len(driver_caps["rows"]) == 40
    assert "seniority_rank" in driver_caps["columns"]
    assert "attendance_reliability_index" in driver_caps["columns"]
    assert "recent_sick_calls_14d" in driver_caps["columns"]
    assert "recent_cancellations_14d" in driver_caps["columns"]
    assert "preferred_route_slot_classes" in driver_caps["columns"]
    assert "preferred_shift_band" in driver_caps["columns"]

    assert len(availability["rows"]) == 280
    assert "availability_state" in availability["columns"]
    assert "previous_week_state" in availability["columns"]
    availability_rows = [
        dict(zip(availability["columns"], row))
        for row in availability["rows"]
    ]
    assert {row["availability_state"] for row in availability_rows} == {
        "AVAILABLE",
        "AVOID_IF_POSSIBLE",
        "CANNOT",
        "ON_CALL_ONLY",
        "PREFERRED",
    }
    assert {row["previous_week_state"] for row in availability_rows} == {
        "CANCELLED",
        "DISPATCH",
        "NA",
        "ON_CALL",
        "SICK_CALL",
        "WORKED",
    }

    assert len(actual_hours["rows"]) == 280
    assert "historical_state" in actual_hours["columns"]
    assert "rolling_7_total_minutes" in actual_hours["columns"]
    assert "rolling_7_limit_minutes" in actual_hours["columns"]
    assert "rolling_7_remaining_minutes" in actual_hours["columns"]
    actual_rows = [dict(zip(actual_hours["columns"], row)) for row in actual_hours["rows"]]
    assert {row["historical_state"] for row in actual_rows} == {
        "CANCELLED",
        "DISPATCH",
        "NA",
        "ON_CALL",
        "SICK_CALL",
        "WORKED",
    }


def test_build_weekly_schedule_control_bundle_resolves_actual_ops_explicit_scope() -> None:
    workflow_run = {
        "workflow_run_id": "wr-weekly-actual-ops-001",
        "partition_key": "PW-2026-W13",
    }
    fixture = build_actual_ops_weekly_stage04_fixture_payloads()

    bundle = build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-route-actual-ops-001",
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "dataset_key": "planning.route_slot_requirements.workbook",
            "metadata_json": fixture["route_slot_requirements"],
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-actual-ops-001",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": fixture["driver_capabilities"],
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-actual-ops-001",
            "artifact_kind": "planning.approved_availability.workbook",
            "dataset_key": "planning.approved_availability.workbook",
            "metadata_json": fixture["approved_availability"],
        },
        actual_hours_artifact={
            "artifact_version_id": "av-hours-actual-ops-001",
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "dataset_key": "planning.actual_hours_snapshot.workbook",
            "metadata_json": fixture["actual_hours"],
        },
    )

    assert bundle.scope_start == "2026-03-22"
    assert bundle.scope_end_exclusive == "2026-03-29"
    assert "2026-04-04" not in bundle.daily_demand_by_service_date
    assert bundle.availability_by_driver["A11X1NH2FPH5RV"].previous_week_states[0].service_date == "2026-03-15"
    assert bundle.availability_by_driver["A11X1NH2FPH5RV"].previous_week_states[-1].service_date == "2026-03-21"
    assert len(bundle.drivers) == 51
    assert sum(item.planned_route_count for item in bundle.daily_demand_by_service_date.values()) == 134
    assert {
        service_date: item.planned_route_count
        for service_date, item in bundle.daily_demand_by_service_date.items()
    } == {
        "2026-03-22": 16,
        "2026-03-23": 23,
        "2026-03-24": 20,
        "2026-03-25": 19,
        "2026-03-26": 21,
        "2026-03-27": 18,
        "2026-03-28": 17,
    }
    assert {
        service_date: item.on_call_target
        for service_date, item in bundle.daily_demand_by_service_date.items()
    } == {
        "2026-03-22": 4,
        "2026-03-23": 4,
        "2026-03-24": 4,
        "2026-03-25": 4,
        "2026-03-26": 4,
        "2026-03-27": 4,
        "2026-03-28": 4,
    }
    assert sum(item.on_call_target for item in bundle.daily_demand_by_service_date.values()) == 28
    assert {
        service_date: item.excess_capacity_target
        for service_date, item in bundle.daily_demand_by_service_date.items()
    } == {
        "2026-03-22": 3,
        "2026-03-23": 3,
        "2026-03-24": 3,
        "2026-03-25": 3,
        "2026-03-26": 3,
        "2026-03-27": 3,
        "2026-03-28": 3,
    }
    assert sum(item.excess_capacity_target for item in bundle.daily_demand_by_service_date.values()) == 21


def test_build_weekly_schedule_control_bundle_rejects_conflicting_explicit_scope_bounds() -> None:
    workflow_run, route_slots_artifact, driver_caps_artifact, availability_artifact, actual_hours_artifact = (
        _small_scope_test_inputs()
    )
    route_slots_artifact["metadata_json"]["scope_start"] = "2026-03-02"
    route_slots_artifact["metadata_json"]["scope_end_exclusive"] = "2026-03-09"
    driver_caps_artifact["metadata_json"]["scope_start"] = "2026-03-03"
    driver_caps_artifact["metadata_json"]["scope_end_exclusive"] = "2026-03-10"

    with pytest.raises(ValueError, match="conflicting explicit scope bounds"):
        build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=route_slots_artifact,
            driver_capabilities_artifact=driver_caps_artifact,
            approved_availability_artifact=availability_artifact,
            actual_hours_artifact=actual_hours_artifact,
        )


def test_build_weekly_schedule_control_bundle_rejects_partial_explicit_scope_bounds() -> None:
    workflow_run, route_slots_artifact, driver_caps_artifact, availability_artifact, actual_hours_artifact = (
        _small_scope_test_inputs()
    )
    route_slots_artifact["metadata_json"]["scope_start"] = "2026-03-02"

    with pytest.raises(ValueError, match="must declare both scope_start and scope_end_exclusive"):
        build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=route_slots_artifact,
            driver_capabilities_artifact=driver_caps_artifact,
            approved_availability_artifact=availability_artifact,
            actual_hours_artifact=actual_hours_artifact,
        )


def test_build_weekly_schedule_control_bundle_rejects_out_of_scope_route_slot_dates() -> None:
    workflow_run, route_slots_artifact, driver_caps_artifact, availability_artifact, actual_hours_artifact = (
        _small_scope_test_inputs()
    )
    route_slots_artifact["metadata_json"]["scope_start"] = "2026-03-03"
    route_slots_artifact["metadata_json"]["scope_end_exclusive"] = "2026-03-10"

    with pytest.raises(ValueError, match="route-slot service_date values outside resolved weekly scope"):
        build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=route_slots_artifact,
            driver_capabilities_artifact=driver_caps_artifact,
            approved_availability_artifact=availability_artifact,
            actual_hours_artifact=actual_hours_artifact,
        )


def test_build_weekly_schedule_control_bundle_rejects_out_of_scope_explicit_availability_dates() -> None:
    workflow_run, route_slots_artifact, driver_caps_artifact, availability_artifact, actual_hours_artifact = (
        _small_scope_test_inputs()
    )
    route_slots_artifact["metadata_json"]["scope_start"] = "2026-03-02"
    route_slots_artifact["metadata_json"]["scope_end_exclusive"] = "2026-03-09"
    availability_artifact["metadata_json"]["rows"][0][2] = "2026-03-09"

    with pytest.raises(
        ValueError,
        match="explicit availability service_date values outside resolved weekly scope",
    ):
        build_weekly_schedule_control_bundle(
            workflow_run=workflow_run,
            route_slot_requirements_artifact=route_slots_artifact,
            driver_capabilities_artifact=driver_caps_artifact,
            approved_availability_artifact=availability_artifact,
            actual_hours_artifact=actual_hours_artifact,
        )


def _small_scope_test_inputs() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    workflow_run = {
        "workflow_run_id": "wr-weekly-scope-001",
        "partition_key": "PW-2026-W10",
    }
    route_slots_artifact = {
        "artifact_version_id": "av-routes-scope-001",
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
            ],
        },
    }
    driver_caps_artifact = {
        "artifact_version_id": "av-driver-scope-001",
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
    }
    availability_artifact = {
        "artifact_version_id": "av-availability-scope-001",
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
                "previous_week_state",
                "locked_by_manager",
                "notes",
            ],
            "rows": [
                [
                    "DRV-01",
                    "Driver One",
                    "2026-03-02",
                    "AVAILABLE",
                    "",
                    "",
                    4,
                    "yes",
                    "",
                    "WORKED",
                    "no",
                    "",
                ],
            ],
        },
    }
    actual_hours_artifact = {
        "artifact_version_id": "av-hours-scope-001",
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "dataset_key": "planning.actual_hours_snapshot.workbook",
        "metadata_json": {
            "columns": ["service_date", "driver_id", "actual_minutes"],
            "rows": [["2026-02-24", "DRV-01", 390]],
        },
    }
    return (
        copy.deepcopy(workflow_run),
        copy.deepcopy(route_slots_artifact),
        copy.deepcopy(driver_caps_artifact),
        copy.deepcopy(availability_artifact),
        copy.deepcopy(actual_hours_artifact),
    )
