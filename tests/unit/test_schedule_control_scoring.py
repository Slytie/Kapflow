from __future__ import annotations

from onetruth.application.services.schedule_control import (
    build_weekly_schedule_control_bundle,
    deterministic_rank_candidates,
)
from onetruth.application.services.schedule_control.scoring import (
    score_candidate,
    summarize_soft_scores,
)
from onetruth.application.services.schedule_control.validation import HardValidationResult


def test_deterministic_rank_candidates_orders_by_hard_filter_then_bucket_then_driver_id() -> None:
    ranked = deterministic_rank_candidates(
        [
            {
                "candidate_driver_id": "DRV-03",
                "hard_filter_status": "pass",
                "score_bucket": "good",
            },
            {
                "candidate_driver_id": "DRV-01",
                "hard_filter_status": "pass",
                "score_bucket": "best",
            },
            {
                "candidate_driver_id": "DRV-02",
                "hard_filter_status": "pass",
                "score_bucket": "best",
            },
            {
                "candidate_driver_id": "DRV-09",
                "hard_filter_status": "blocked",
                "score_bucket": "best",
            },
        ]
    )

    assert [item["candidate_driver_id"] for item in ranked] == [
        "DRV-01",
        "DRV-02",
        "DRV-03",
        "DRV-09",
    ]


def test_score_candidate_prefers_driver_with_remaining_capacity() -> None:
    bundle = _build_bundle(actual_minutes=600)
    route_slot = bundle.route_slots[0]
    driver = bundle.drivers[0]

    score = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=driver,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )

    assert score.total > 0.7
    assert score.bucket in {"best", "good"}


def test_summarize_soft_scores_averages_pass_candidates_only() -> None:
    summary = summarize_soft_scores(
        [
            {
                "hard_filter_status": "pass",
                "fairness_balance": 0.8,
                "on_call_coverage": 1.0,
                "lost_work_credit": 0.7,
            },
            {
                "hard_filter_status": "pass",
                "fairness_balance": 0.6,
                "on_call_coverage": 0.9,
                "lost_work_credit": 0.5,
            },
            {
                "hard_filter_status": "blocked",
                "fairness_balance": 1.0,
                "on_call_coverage": 1.0,
                "lost_work_credit": 1.0,
            },
        ]
    )

    assert round(summary["fairness_balance"], 4) == 0.7
    assert round(summary["on_call_coverage"], 4) == 0.95
    assert round(summary["lost_work_credit"], 4) == 0.6


def test_score_candidate_makes_previous_week_stability_a_first_class_term() -> None:
    bundle = _build_stability_bundle()
    route_slot = bundle.route_slots[0]
    driver_match = bundle.drivers[0]
    driver_non_match = bundle.drivers[1]

    matched = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=driver_match,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )
    non_matched = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=driver_non_match,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )

    assert matched.previous_week_stability > non_matched.previous_week_stability
    assert matched.total > non_matched.total


def test_score_candidate_exposes_explicit_preference_fit_terms() -> None:
    bundle = _build_preference_bundle()
    route_slot = bundle.route_slots[0]
    preferred_driver = bundle.drivers[0]
    avoid_driver = bundle.drivers[1]
    on_call_driver = bundle.drivers[2]

    preferred = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=preferred_driver,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )
    avoid = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=avoid_driver,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )
    on_call = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=on_call_driver,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )

    assert preferred.availability_state_fit > avoid.availability_state_fit > on_call.availability_state_fit
    assert preferred.preferred_shift_band_fit > avoid.preferred_shift_band_fit
    assert preferred.preferred_route_slot_class_fit > avoid.preferred_route_slot_class_fit
    assert preferred.preference_fit > avoid.preference_fit
    assert preferred.preference_fit > on_call.preference_fit


def test_score_candidate_uses_explicit_seniority_and_reliability_signals() -> None:
    bundle = _build_signal_bundle()
    route_slot = bundle.route_slots[0]
    senior_driver = bundle.drivers[0]
    junior_driver = bundle.drivers[1]

    senior = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=senior_driver,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )
    junior = score_candidate(
        bundle=bundle,
        route_slot=route_slot,
        driver=junior_driver,
        hard_validation=HardValidationResult(status="pass", reasons=()),
    )

    assert senior.seniority_preference_fit > junior.seniority_preference_fit
    assert senior.reliability_score > junior.reliability_score
    assert senior.total > junior.total


def _build_bundle(*, actual_minutes: int):
    workflow_run = {
        "workflow_run_id": "wr-weekly-score",
        "partition_key": "PW-2026-W10",
    }
    route_slots_artifact = {
        "artifact_version_id": "av-routes-score",
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
                    8.0,
                    "amazon:row-001",
                ],
            ],
        },
    }
    driver_caps_artifact = {
        "artifact_version_id": "av-driver-score",
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
        "artifact_version_id": "av-availability-score",
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
        "artifact_version_id": "av-hours-score",
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


def _build_stability_bundle():
    workflow_run = {
        "workflow_run_id": "wr-weekly-stability",
        "partition_key": "PW-2026-W10",
    }
    route_slots_artifact = {
        "artifact_version_id": "av-routes-stability",
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
                [
                    "2026-03-02",
                    "slot-20260302-cx100",
                    "cycle1_standard",
                    "parcel_delivery",
                    "XL_van",
                    "11:40",
                    "20:10",
                    8.0,
                    "amazon:row-001",
                    "CX100",
                ],
            ],
        },
    }
    driver_caps_artifact = {
        "artifact_version_id": "av-driver-stability",
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
                ["DRV-02", "parcel_delivery", "XL_van", "cycle1_standard", "", "", ""],
            ],
        },
    }
    availability_artifact = {
        "artifact_version_id": "av-availability-stability",
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
                ["DRV-01", 4, "yes", "", "Mon,Tue,Wed,Thu"],
                ["DRV-02", 4, "yes", "", "Mon,Tue,Wed,Thu"],
            ],
        },
    }
    actual_hours_artifact = {
        "artifact_version_id": "av-hours-stability",
        "artifact_kind": "planning.actual_hours_snapshot.workbook",
        "dataset_key": "planning.actual_hours_snapshot.workbook",
        "metadata_json": {
            "columns": ["service_date", "driver_id", "actual_minutes", "route_id"],
            "rows": [
                ["2026-02-23", "DRV-01", 480, "CX100"],
                ["2026-02-23", "DRV-02", 480, "CX999"],
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


def _build_preference_bundle():
    workflow_run = {
        "workflow_run_id": "wr-weekly-preference",
        "partition_key": "PW-2026-W10",
    }
    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-routes-preference",
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
                    "preferred_shift_band",
                ],
                "rows": [
                    [
                        "2026-03-02",
                        "slot-20260302-early",
                        "cycle1_standard_early",
                        "parcel_delivery",
                        "XL_van",
                        "10:00",
                        "18:00",
                        8.0,
                        "amazon:row-preference",
                        "early",
                    ],
                ],
            },
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-preference",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": {
                "columns": [
                    "driver_id",
                    "skills",
                    "vehicle_certifications",
                    "eligible_route_slot_classes",
                    "approved_restrictions",
                    "seniority_rank",
                    "attendance_reliability_index",
                    "preferred_route_slot_classes",
                    "preferred_shift_band",
                    "notes",
                ],
                "rows": [
                    [
                        "DRV-01",
                        "parcel_delivery",
                        "XL_van",
                        "cycle1_standard_early",
                        "",
                        4,
                        0.98,
                        "cycle1_standard_early",
                        "early",
                        "",
                    ],
                    [
                        "DRV-02",
                        "parcel_delivery",
                        "XL_van",
                        "cycle1_standard_early",
                        "",
                        8,
                        0.9,
                        "",
                        "late",
                        "",
                    ],
                    [
                        "DRV-03",
                        "parcel_delivery",
                        "XL_van",
                        "cycle1_standard_early",
                        "",
                        10,
                        0.92,
                        "",
                        "late",
                        "",
                    ],
                ],
            },
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-preference",
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
                        "Preferred",
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
                        "Avoid",
                        "2026-03-02",
                        "AVOID_IF_POSSIBLE",
                        "",
                        "cycle1_standard_early",
                        1,
                        "no",
                        "late",
                        "NA",
                        "no",
                        "",
                    ],
                    [
                        "DRV-03",
                        "On Call",
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


def _build_signal_bundle():
    workflow_run = {
        "workflow_run_id": "wr-weekly-signals",
        "partition_key": "PW-2026-W10",
    }
    return build_weekly_schedule_control_bundle(
        workflow_run=workflow_run,
        route_slot_requirements_artifact={
            "artifact_version_id": "av-routes-signals",
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
                    "preferred_shift_band",
                ],
                "rows": [
                    [
                        "2026-03-02",
                        "slot-20260302-late",
                        "cycle1_standard_late",
                        "parcel_delivery",
                        "XL_van",
                        "11:30",
                        "20:00",
                        8.0,
                        "amazon:row-signal",
                        "late",
                    ],
                ],
            },
        },
        driver_capabilities_artifact={
            "artifact_version_id": "av-driver-signals",
            "artifact_kind": "planning.driver_capabilities.workbook",
            "dataset_key": "planning.driver_capabilities.workbook",
            "metadata_json": {
                "columns": [
                    "driver_id",
                    "skills",
                    "vehicle_certifications",
                    "eligible_route_slot_classes",
                    "approved_restrictions",
                    "seniority_rank",
                    "attendance_reliability_index",
                    "recent_sick_calls_14d",
                    "recent_cancellations_14d",
                    "preferred_route_slot_classes",
                    "preferred_shift_band",
                    "notes",
                ],
                "rows": [
                    [
                        "DRV-01",
                        "parcel_delivery",
                        "XL_van",
                        "cycle1_standard_late",
                        "",
                        1,
                        0.99,
                        0,
                        0,
                        "cycle1_standard_late",
                        "late",
                        "",
                    ],
                    [
                        "DRV-02",
                        "parcel_delivery",
                        "XL_van",
                        "cycle1_standard_late",
                        "",
                        20,
                        0.78,
                        2,
                        1,
                        "cycle1_standard_late",
                        "late",
                        "",
                    ],
                ],
            },
        },
        approved_availability_artifact={
            "artifact_version_id": "av-availability-signals",
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
                        "Senior",
                        "2026-03-02",
                        "PREFERRED",
                        "cycle1_standard_late",
                        "",
                        1,
                        "no",
                        "late",
                        "WORKED",
                        "no",
                        "",
                    ],
                    [
                        "DRV-02",
                        "Junior",
                        "2026-03-02",
                        "PREFERRED",
                        "cycle1_standard_late",
                        "",
                        1,
                        "no",
                        "late",
                        "WORKED",
                        "no",
                        "",
                    ],
                ],
            },
        },
    )
