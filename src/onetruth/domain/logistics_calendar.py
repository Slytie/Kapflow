from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from onetruth.domain.partition_codec import (
    parse_service_date_id,
    planning_week_id_for_date,
    planning_week_to_service_days,
    validate_partition_key,
)


LOGISTICS_CALENDAR_POLICY_ID = "logistics_calendar_policy.v1"
REPORTING_TO_PLANNING_CYCLE_POLICY_ID = "reporting_actuals_to_next_planning_week.v1"
LATE_WEEKLY_REPUBLISH_POLICY_ID = "late_weekly_republish_after_live_prepare.v1"
LATE_REPORTING_TO_PLANNING_POLICY_ID = "late_reporting_to_planning_input.v1"

SAME_WEEK_RELATION = "same_iso_planning_week"
NEXT_WEEK_RELATION = "next_iso_planning_week"
DEPRECATED_SAME_WEEK_RELATION = "same_week"
LATE_WEEKLY_REPUBLISH_POLICY_STATE = "late_weekly_republish_after_live_prepare"
LATE_REPORTING_CONFLICT_CODE = "late_reporting_handoff_conflict"


@dataclass(frozen=True)
class PlanningCycleResolution:
    service_date_id: str
    service_date: str
    same_week_planning_week_id: str
    future_planning_week_id: str
    target_planning_week_id: str
    target_relation: str
    policy_id: str = REPORTING_TO_PLANNING_CYCLE_POLICY_ID
    calendar_policy_id: str = LOGISTICS_CALENDAR_POLICY_ID

    def as_policy_context(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "calendar_policy_id": self.calendar_policy_id,
            "source_partition": {
                "partition_kind": "ServiceDateID",
                "partition_key": self.service_date_id,
            },
            "same_week_planning_week_id": self.same_week_planning_week_id,
            "future_planning_week_id": self.future_planning_week_id,
            "target_planning_week_id": self.target_planning_week_id,
            "target_relation": self.target_relation,
            "relation_names": {
                "same_week_relation": SAME_WEEK_RELATION,
                "deprecated_same_week_relation": DEPRECATED_SAME_WEEK_RELATION,
                "future_week_relation": NEXT_WEEK_RELATION,
            },
        }


@dataclass(frozen=True)
class LateReportingPolicy:
    boundary_profile: str
    replace_on_conflict_allowed: bool
    policy_id: str = LATE_REPORTING_TO_PLANNING_POLICY_ID
    conflict_code: str = LATE_REPORTING_CONFLICT_CODE

    def as_policy_context(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "boundary_profile": self.boundary_profile,
            "replace_on_conflict_allowed": self.replace_on_conflict_allowed,
            "conflict_code": self.conflict_code,
            "required_action": (
                "resolve late-report policy before mutating weekly planning input truth"
            ),
        }


class LogisticsCalendarPolicy:
    policy_id = LOGISTICS_CALENDAR_POLICY_ID

    def planning_cycle_for_service_date(self, service_date_id: str) -> PlanningCycleResolution:
        service_date = parse_service_date_id(service_date_id)
        same_week_planning_week_id = planning_week_id_for_date(service_date)
        future_planning_week_id = planning_week_id_for_date(service_date + timedelta(days=7))
        return PlanningCycleResolution(
            service_date_id=service_date_id,
            service_date=service_date.isoformat(),
            same_week_planning_week_id=same_week_planning_week_id,
            future_planning_week_id=future_planning_week_id,
            target_planning_week_id=future_planning_week_id,
            target_relation=NEXT_WEEK_RELATION,
        )

    def reporting_actuals_target_planning_week(self, service_date_id: str) -> str:
        return self.planning_cycle_for_service_date(service_date_id).target_planning_week_id

    def planning_week_service_dates(self, planning_week_id: str) -> tuple[str, ...]:
        validate_partition_key("PlanningWeekID", planning_week_id)
        return tuple(planning_week_to_service_days(planning_week_id))


def late_reporting_policy_for_boundary(boundary_profile: str) -> LateReportingPolicy:
    normalized_profile = str(boundary_profile or "").strip() or "shared_env"
    return LateReportingPolicy(
        boundary_profile=normalized_profile,
        replace_on_conflict_allowed=normalized_profile in {"ci_test", "local_dev"},
    )


def late_weekly_republish_policy_state(**details: Any) -> dict[str, Any]:
    return {
        "policy_id": LATE_WEEKLY_REPUBLISH_POLICY_ID,
        "policy_state": LATE_WEEKLY_REPUBLISH_POLICY_STATE,
        **details,
    }
