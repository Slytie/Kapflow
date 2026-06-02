from __future__ import annotations

from onetruth.domain.logistics_calendar import (
    LATE_REPORTING_CONFLICT_CODE,
    LATE_WEEKLY_REPUBLISH_POLICY_ID,
    LATE_WEEKLY_REPUBLISH_POLICY_STATE,
    LogisticsCalendarPolicy,
    late_reporting_policy_for_boundary,
    late_weekly_republish_policy_state,
)


def test_calendar_policy_distinguishes_same_week_from_next_planning_week() -> None:
    policy = LogisticsCalendarPolicy()

    cycle = policy.planning_cycle_for_service_date("SD-2026-03-06")

    assert cycle.same_week_planning_week_id == "PW-2026-W10"
    assert cycle.future_planning_week_id == "PW-2026-W11"
    assert cycle.target_planning_week_id == "PW-2026-W11"
    assert cycle.as_policy_context()["relation_names"] == {
        "same_week_relation": "same_iso_planning_week",
        "deprecated_same_week_relation": "same_week",
        "future_week_relation": "next_iso_planning_week",
    }


def test_calendar_policy_does_not_skip_next_iso_week_for_sunday_service_day() -> None:
    policy = LogisticsCalendarPolicy()

    cycle = policy.planning_cycle_for_service_date("SD-2026-03-08")

    assert cycle.same_week_planning_week_id == "PW-2026-W10"
    assert cycle.future_planning_week_id == "PW-2026-W11"
    assert cycle.target_planning_week_id == "PW-2026-W11"


def test_calendar_policy_handles_iso_year_rollover() -> None:
    policy = LogisticsCalendarPolicy()

    cycle = policy.planning_cycle_for_service_date("SD-2027-01-03")

    assert cycle.same_week_planning_week_id == "PW-2026-W53"
    assert cycle.future_planning_week_id == "PW-2027-W01"
    assert cycle.target_planning_week_id == "PW-2027-W01"


def test_late_reporting_policy_allows_replacement_only_in_local_profiles() -> None:
    shared = late_reporting_policy_for_boundary("shared_env")
    local = late_reporting_policy_for_boundary("local_dev")
    ci = late_reporting_policy_for_boundary("ci_test")

    assert shared.replace_on_conflict_allowed is False
    assert shared.as_policy_context()["conflict_code"] == LATE_REPORTING_CONFLICT_CODE
    assert local.replace_on_conflict_allowed is True
    assert ci.replace_on_conflict_allowed is True


def test_late_weekly_republish_policy_state_is_named_and_compatible() -> None:
    state = late_weekly_republish_policy_state(reason="unit-test")

    assert state["policy_id"] == LATE_WEEKLY_REPUBLISH_POLICY_ID
    assert state["policy_state"] == LATE_WEEKLY_REPUBLISH_POLICY_STATE
    assert state["reason"] == "unit-test"
