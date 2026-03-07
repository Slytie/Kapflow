from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onetruth.domain.partition_codec import planning_week_to_service_days


_PARTITION_TRANSFORMS: dict[str, Any] = {
    "planning_week_to_service_days": planning_week_to_service_days,
}

_SCORE_BUCKET_ORDER = {
    "best": 0,
    "good": 1,
    "fair": 2,
    "ok": 3,
    "poor": 4,
    "blocked": 5,
}

_HARD_FILTER_ORDER = {
    "pass": 0,
    "blocked": 1,
    "fail": 2,
}


@dataclass(frozen=True)
class MajorReplanPolicy:
    route_delta_abs_threshold: int = 2
    escalate_on_no_compliant_candidate: bool = True
    escalate_after_shift_confirmation: bool = True


def apply_partition_transform_by_id(
    *,
    transform_id: str,
    source_partition_key: str,
) -> list[str]:
    transform = _PARTITION_TRANSFORMS.get(transform_id)
    if transform is None:
        raise ValueError(f"unsupported partition transform: {transform_id}")
    values = transform(str(source_partition_key))
    return [str(value) for value in values]


def deterministic_rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[int, int, str]:
        hard_filter_status = str(item.get("hard_filter_status", "blocked")).strip().lower()
        score_bucket = str(item.get("score_bucket", "blocked")).strip().lower()
        candidate_driver_id = str(item.get("candidate_driver_id", ""))
        return (
            _HARD_FILTER_ORDER.get(hard_filter_status, 99),
            _SCORE_BUCKET_ORDER.get(score_bucket, 99),
            candidate_driver_id,
        )

    return sorted(candidates, key=sort_key)


def should_escalate_major_replan(
    *,
    route_delta_abs: int,
    no_compliant_candidate: bool,
    after_shift_confirmation: bool,
    policy: MajorReplanPolicy,
) -> bool:
    if int(route_delta_abs) >= int(policy.route_delta_abs_threshold):
        return True
    if bool(no_compliant_candidate) and bool(policy.escalate_on_no_compliant_candidate):
        return True
    if bool(after_shift_confirmation) and bool(policy.escalate_after_shift_confirmation):
        return True
    return False
