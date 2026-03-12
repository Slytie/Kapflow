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
