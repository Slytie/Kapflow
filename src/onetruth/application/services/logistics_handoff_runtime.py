from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onetruth.application.services.schedule_control import (
    deterministic_rank_candidates as deterministic_rank_candidates,
)
from onetruth.domain.partition_codec import (
    planning_week_to_service_days,
)
from onetruth.domain.logistics_calendar import LogisticsCalendarPolicy


_LOGISTICS_CALENDAR_POLICY = LogisticsCalendarPolicy()


_PARTITION_TRANSFORMS: dict[str, Any] = {
    "planning_week_to_service_days": planning_week_to_service_days,
    "service_day_to_future_planning_week": (
        _LOGISTICS_CALENDAR_POLICY.reporting_actuals_target_planning_week
    ),
}

__all__ = [
    "MajorReplanPolicy",
    "apply_partition_transform_by_id",
    "deterministic_rank_candidates",
    "should_escalate_major_replan",
]

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
    transformed = transform(str(source_partition_key))
    if isinstance(transformed, str):
        values = [transformed]
    elif transformed is None:
        values = []
    else:
        values = list(transformed)
    return [str(value) for value in values]


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
