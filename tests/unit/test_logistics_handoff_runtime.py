from __future__ import annotations

import pytest

from onetruth.application.services.logistics_handoff_runtime import (
    MajorReplanPolicy,
    apply_partition_transform_by_id,
    deterministic_rank_candidates,
    should_escalate_major_replan,
)


def test_typed_partition_transform_registry_expands_planning_week_to_service_days() -> None:
    service_days = apply_partition_transform_by_id(
        transform_id="planning_week_to_service_days",
        source_partition_key="PW-2026-W10",
    )
    assert service_days == [
        "SD-2026-03-02",
        "SD-2026-03-03",
        "SD-2026-03-04",
        "SD-2026-03-05",
        "SD-2026-03-06",
        "SD-2026-03-07",
        "SD-2026-03-08",
    ]


def test_unknown_partition_transform_id_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported partition transform"):
        apply_partition_transform_by_id(
            transform_id="unknown_transform",
            source_partition_key="PW-2026-W10",
        )


def test_typed_partition_transform_registry_maps_service_day_to_future_planning_week() -> None:
    planning_weeks = apply_partition_transform_by_id(
        transform_id="service_day_to_future_planning_week",
        source_partition_key="SD-2026-03-06",
    )
    assert planning_weeks == ["PW-2026-W10"]


def test_deterministic_candidate_ranking_is_stable_and_tie_broken() -> None:
    ranked = deterministic_rank_candidates(
        [
            {
                "candidate_driver_id": "C-3",
                "hard_filter_status": "pass",
                "score_bucket": "good",
            },
            {
                "candidate_driver_id": "C-1",
                "hard_filter_status": "pass",
                "score_bucket": "best",
            },
            {
                "candidate_driver_id": "C-2",
                "hard_filter_status": "pass",
                "score_bucket": "best",
            },
            {
                "candidate_driver_id": "C-4",
                "hard_filter_status": "blocked",
                "score_bucket": "best",
            },
        ]
    )
    assert [item["candidate_driver_id"] for item in ranked] == ["C-1", "C-2", "C-3", "C-4"]


def test_major_replan_escalation_only_when_threshold_crossed() -> None:
    policy = MajorReplanPolicy(route_delta_abs_threshold=2)

    assert (
        should_escalate_major_replan(
            route_delta_abs=1,
            no_compliant_candidate=False,
            after_shift_confirmation=False,
            policy=policy,
        )
        is False
    )
    assert (
        should_escalate_major_replan(
            route_delta_abs=2,
            no_compliant_candidate=False,
            after_shift_confirmation=False,
            policy=policy,
        )
        is True
    )
    assert (
        should_escalate_major_replan(
            route_delta_abs=0,
            no_compliant_candidate=True,
            after_shift_confirmation=False,
            policy=policy,
        )
        is True
    )
