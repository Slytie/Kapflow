from __future__ import annotations

import pytest

from onetruth.application.services.schedule_control import build_weekly_schedule_control_bundle
from onetruth.application.services.schedule_control.route_demand_coverage_recommendations import (
    apply_route_demand_coverage_candidates,
    recommend_route_demand_coverage,
    _detect_added_route_slot_targets,
)
from onetruth.application.services.schedule_control.route_slot_requirements import (
    RouteSlotRequirement,
    expand_route_slot_requirements,
)


def test_detect_added_route_slot_targets_uses_family_delta_and_tail_slots() -> None:
    old_slots = expand_route_slot_requirements(
        (
            RouteSlotRequirement(
                service_date="2026-03-02",
                route_slot_id="slot-2026-03-02-cycle1",
                route_slot_class="cycle1_standard",
                required_skill="parcel_delivery",
                vehicle_type="XL_van",
                shift_start="11:30",
                shift_end="20:00",
                estimated_hours=8.5,
                source_snapshot_row_ref="daily:2026-03-02",
                required_count=1,
                route_id="ROUTE-2026-03-02",
                station_code="DVC4",
                service_area="Cycle1",
            ),
        )
    )
    updated_slots = expand_route_slot_requirements(
        (
            RouteSlotRequirement(
                service_date="2026-03-02",
                route_slot_id="slot-2026-03-02-cycle1*3",
                route_slot_class="cycle1_standard",
                required_skill="parcel_delivery",
                vehicle_type="XL_van",
                shift_start="11:30",
                shift_end="20:00",
                estimated_hours=8.5,
                source_snapshot_row_ref="daily:2026-03-02",
                required_count=3,
                route_id="ROUTE-2026-03-02",
                station_code="DVC4",
                service_area="Cycle1",
            ),
        )
    )

    targets = _detect_added_route_slot_targets(
        old_slots=old_slots,
        updated_slots=updated_slots,
        service_dates=["2026-03-02"],
    )

    assert [item.route_slot_id for item in targets] == [
        "slot-2026-03-02-cycle1#02",
        "slot-2026-03-02-cycle1#03",
    ]


def test_recommend_route_demand_coverage_ranks_candidates_and_flags_reserve_promotion() -> None:
    old_bundle = _build_bundle(route_count=1)
    updated_bundle = _build_bundle(route_count=2)
    recommendations = recommend_route_demand_coverage(
        old_bundle=old_bundle,
        updated_bundle=updated_bundle,
        assignment_rows=_assignment_rows(),
        reserve_rows=_reserve_rows(),
        service_dates=["2026-03-02"],
        max_candidates=4,
    )

    assert recommendations["added_route_count"] == 1
    assert recommendations["target_count"] == 1
    assert recommendations["selected_defaults"] == [
        {
            "target_id": "2026-03-02:slot-2026-03-02-cycle1#02",
            "route_slot_id": "slot-2026-03-02-cycle1#02",
            "driver_id": "DRV-PREFERRED",
            "row_kind": "assignment",
        }
    ]
    candidate_group = recommendations["candidate_groups"][0]
    assert candidate_group["target"]["route_slot_id"] == "slot-2026-03-02-cycle1#02"
    assert [item["driver_id"] for item in candidate_group["candidates"][:2]] == [
        "DRV-PREFERRED",
        "DRV-AVAILABLE",
    ]
    assert candidate_group["candidates"][0]["recommendation_rank"] == 1
    assert candidate_group["candidates"][0]["clear_same_day_on_call_reserve"] is True
    assert candidate_group["candidates"][0]["hard_filter_status"] == "pass"
    blocked_candidate = next(
        item for item in candidate_group["candidates"] if item["driver_id"] == "DRV-BLOCKED"
    )
    assert blocked_candidate["hard_filter_status"] == "blocked"
    assert blocked_candidate["hard_filter_reasons"] == ["driver_unavailable"]


def test_recommend_route_demand_coverage_defaults_to_distinct_same_day_drivers() -> None:
    old_bundle = _build_bundle(route_count=1)
    updated_bundle = _build_bundle(route_count=3)
    recommendations = recommend_route_demand_coverage(
        old_bundle=old_bundle,
        updated_bundle=updated_bundle,
        assignment_rows=_assignment_rows(),
        reserve_rows=_reserve_rows(),
        service_dates=["2026-03-02"],
        max_candidates=4,
    )

    assert recommendations["target_count"] == 2
    assert recommendations["selected_defaults"] == [
        {
            "target_id": "2026-03-02:slot-2026-03-02-cycle1#02",
            "route_slot_id": "slot-2026-03-02-cycle1#02",
            "driver_id": "DRV-PREFERRED",
            "row_kind": "assignment",
        },
        {
            "target_id": "2026-03-02:slot-2026-03-02-cycle1#03",
            "route_slot_id": "slot-2026-03-02-cycle1#03",
            "driver_id": "DRV-AVAILABLE",
            "row_kind": "assignment",
        },
    ]


def test_recommend_route_demand_coverage_omits_duplicate_defaults_when_unique_pool_is_short() -> None:
    old_bundle = _build_bundle(route_count=1)
    updated_bundle = _build_bundle(route_count=4)
    recommendations = recommend_route_demand_coverage(
        old_bundle=old_bundle,
        updated_bundle=updated_bundle,
        assignment_rows=_assignment_rows(),
        reserve_rows=_reserve_rows(),
        service_dates=["2026-03-02"],
        max_candidates=4,
    )

    assert recommendations["target_count"] == 3
    assert len(recommendations["selected_defaults"]) == 2
    assert {
        item["driver_id"] for item in recommendations["selected_defaults"]
    } == {"DRV-PREFERRED", "DRV-AVAILABLE"}


def test_apply_route_demand_coverage_candidates_promotes_reserve_driver_and_clears_reserve_row() -> None:
    old_bundle = _build_bundle(route_count=1)
    updated_bundle = _build_bundle(route_count=2)
    recommendations = recommend_route_demand_coverage(
        old_bundle=old_bundle,
        updated_bundle=updated_bundle,
        assignment_rows=_assignment_rows(),
        reserve_rows=_reserve_rows(),
        service_dates=["2026-03-02"],
        max_candidates=4,
    )

    applied = apply_route_demand_coverage_candidates(
        bundle=updated_bundle,
        assignment_rows=_assignment_rows(),
        reserve_rows=_reserve_rows(),
        selections=[
            {
                "route_slot_id": "slot-2026-03-02-cycle1#02",
                "driver_id": "DRV-PREFERRED",
                "row_kind": "assignment",
            }
        ],
        recommendations=recommendations,
        route_demand_artifact_version_id="av-route-demand-next",
    )

    assert applied["assigned_count"] == 1
    assert applied["appended_assignment_count"] == 1
    assert applied["cleared_same_day_reserve_count"] == 1
    assert applied["appended_rows"] == [
        {
            "service_date": "2026-03-02",
            "route_slot_id": "slot-2026-03-02-cycle1#02",
            "assigned_driver_id": "DRV-PREFERRED",
            "assignment_status": "manual_override",
            "projected_minutes": 510,
            "baseline_template_state": "assigned_template",
            "planned_driver_day_state": "assigned",
            "new_agreement_required": False,
            "new_agreement_trigger_reason": "",
            "template_state_preservation_fit": pytest.approx(
                applied["selected"][0]["template_state_preservation_fit"]
            ),
            "candidate_delta_id": (
                "midweek-route-demand:av-route-demand-next:"
                "slot-2026-03-02-cycle1#02:DRV-PREFERRED"
            ),
            "source_bundle_id": updated_bundle.bundle_id,
            "iteration_index": 1,
            "delta_kind": "route_demand_coverage",
            "previous_week_stability": pytest.approx(
                applied["selected"][0]["previous_week_stability"]
            ),
        }
    ]
    assert applied["reserve_rows"][0]["assigned_driver_id"] == ""


def test_apply_route_demand_coverage_candidates_rejects_stale_or_blocked_selection() -> None:
    old_bundle = _build_bundle(route_count=1)
    updated_bundle = _build_bundle(route_count=2)
    recommendations = recommend_route_demand_coverage(
        old_bundle=old_bundle,
        updated_bundle=updated_bundle,
        assignment_rows=_assignment_rows(),
        reserve_rows=_reserve_rows(),
        service_dates=["2026-03-02"],
        max_candidates=4,
    )

    with pytest.raises(ValueError, match="candidate unavailable"):
        apply_route_demand_coverage_candidates(
            bundle=updated_bundle,
            assignment_rows=_assignment_rows(),
            reserve_rows=_reserve_rows(),
            selections=[
                {
                    "route_slot_id": "slot-2026-03-02-cycle1#02",
                    "driver_id": "DRV-NOT-THERE",
                    "row_kind": "assignment",
                }
            ],
            recommendations=recommendations,
            route_demand_artifact_version_id="av-route-demand-next",
        )

    with pytest.raises(RuntimeError, match="candidate blocked"):
        apply_route_demand_coverage_candidates(
            bundle=updated_bundle,
            assignment_rows=_assignment_rows(),
            reserve_rows=_reserve_rows(),
            selections=[
                {
                    "route_slot_id": "slot-2026-03-02-cycle1#02",
                    "driver_id": "DRV-BLOCKED",
                    "row_kind": "assignment",
                }
            ],
            recommendations=recommendations,
            route_demand_artifact_version_id="av-route-demand-next",
        )


def test_apply_route_demand_coverage_candidates_rejects_duplicate_same_day_driver_selection() -> None:
    old_bundle = _build_bundle(route_count=1)
    updated_bundle = _build_bundle(route_count=3)
    recommendations = recommend_route_demand_coverage(
        old_bundle=old_bundle,
        updated_bundle=updated_bundle,
        assignment_rows=_assignment_rows(),
        reserve_rows=_reserve_rows(),
        service_dates=["2026-03-02"],
        max_candidates=4,
    )

    with pytest.raises(RuntimeError, match="candidate blocked"):
        apply_route_demand_coverage_candidates(
            bundle=updated_bundle,
            assignment_rows=_assignment_rows(),
            reserve_rows=_reserve_rows(),
            selections=[
                {
                    "route_slot_id": "slot-2026-03-02-cycle1#02",
                    "driver_id": "DRV-AVAILABLE",
                    "row_kind": "assignment",
                },
                {
                    "route_slot_id": "slot-2026-03-02-cycle1#03",
                    "driver_id": "DRV-AVAILABLE",
                    "row_kind": "assignment",
                },
            ],
            recommendations=recommendations,
            route_demand_artifact_version_id="av-route-demand-next",
        )


def _build_bundle(*, route_count: int):
    workflow_run = {
        "workflow_run_id": f"wr-route-demand-coverage-{route_count}",
        "partition_key": "PW-2026-W10",
    }
    route_slot_requirements_artifact = {
        "artifact_version_id": f"av-routes-{route_count}",
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
                "station_code",
                "service_area",
                "source_snapshot_row_ref",
            ],
            "rows": [
                [
                    "2026-03-02",
                    "slot-2026-03-02-cycle1",
                    "cycle1_standard",
                    "parcel_delivery",
                    "XL_van",
                    "11:30",
                    "20:00",
                    8.5,
                    route_count,
                    "ROUTE-2026-03-02",
                    "DVC4",
                    "Cycle1",
                    "daily:2026-03-02",
                ]
            ],
            "daily_demand_columns": [
                "service_date",
                "planned_route_count",
                "on_call_target",
                "on_call_min_target",
                "on_call_preferred_target",
                "on_call_max_target",
                "excess_capacity_target",
                "excess_capacity_min_target",
                "excess_capacity_preferred_target",
                "excess_capacity_max_target",
                "standard_slot_count",
                "rescue_slot_count",
                "overflow_slot_count",
                "source_message_id",
                "source_kind",
                "change_kind",
            ],
            "daily_demand_rows": [
                [
                    "2026-03-02",
                    route_count,
                    1,
                    1,
                    1,
                    1,
                    0,
                    0,
                    0,
                    0,
                    route_count,
                    0,
                    0,
                    "daily:2026-03-02",
                    "unit_test",
                    "override",
                ]
            ],
        },
    }
    driver_capabilities_artifact = {
        "artifact_version_id": "av-drivers",
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
                [
                    "DRV-ASSIGNED",
                    "parcel_delivery",
                    "XL_van",
                    "cycle1_standard",
                    "",
                    "full_time",
                    "already assigned",
                ],
                [
                    "DRV-PREFERRED",
                    "parcel_delivery",
                    "XL_van",
                    "cycle1_standard",
                    "",
                    "full_time",
                    "preferred reserve",
                ],
                [
                    "DRV-AVAILABLE",
                    "parcel_delivery",
                    "XL_van",
                    "cycle1_standard",
                    "",
                    "full_time",
                    "available backup",
                ],
                [
                    "DRV-BLOCKED",
                    "parcel_delivery",
                    "XL_van",
                    "cycle1_standard",
                    "",
                    "full_time",
                    "blocked by availability",
                ],
            ],
        },
    }
    approved_availability_artifact = {
        "artifact_version_id": "av-availability",
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
                    "DRV-ASSIGNED",
                    "2026-03-02",
                    "AVAILABLE",
                    3,
                    "no",
                    "cycle1_standard",
                    "",
                    "NA",
                    "no",
                ],
                [
                    "DRV-PREFERRED",
                    "2026-03-02",
                    "PREFERRED",
                    3,
                    "yes",
                    "cycle1_standard",
                    "",
                    "NA",
                    "no",
                ],
                [
                    "DRV-AVAILABLE",
                    "2026-03-02",
                    "AVAILABLE",
                    3,
                    "no",
                    "cycle1_standard",
                    "",
                    "NA",
                    "no",
                ],
                [
                    "DRV-BLOCKED",
                    "2026-03-02",
                    "CANNOT",
                    3,
                    "no",
                    "cycle1_standard",
                    "",
                    "NA",
                    "no",
                ],
            ],
        },
    }
    actual_hours_artifact = {
        "artifact_version_id": "av-hours",
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "dataset_key": "planning.actual_hours_snapshot.workbook",
        "metadata_json": {
            "columns": ["service_date", "driver_id", "actual_minutes"],
            "rows": [],
        },
    }
    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact=route_slot_requirements_artifact,
        driver_capabilities_artifact=driver_capabilities_artifact,
        approved_availability_artifact=approved_availability_artifact,
        actual_hours_artifact=actual_hours_artifact,
    )


def _assignment_rows() -> list[dict[str, object]]:
    return [
        {
            "service_date": "2026-03-02",
            "route_slot_id": "slot-2026-03-02-cycle1",
            "assigned_driver_id": "DRV-ASSIGNED",
            "assignment_status": "pass",
            "projected_minutes": 510,
            "iteration_index": 0,
            "delta_kind": "manual_edit",
        }
    ]


def _reserve_rows() -> list[dict[str, object]]:
    return [
        {
            "service_date": "2026-03-02",
            "route_slot_id": "reserve-2026-03-02-on-call-01",
            "route_id": "ON_CALL",
            "assigned_driver_id": "DRV-PREFERRED",
            "assignment_status": "manual_override",
            "assignment_action": "reserve",
            "projected_minutes": 510,
            "availability_state": "PREFERRED",
            "baseline_template_state": "assigned_template",
            "planned_driver_day_state": "on_call",
            "new_agreement_required": False,
            "new_agreement_trigger_reason": "",
            "template_state_preservation_fit": 1.0,
            "iteration_index": 0,
            "rationale_code": "reserve_selection",
        }
    ]
