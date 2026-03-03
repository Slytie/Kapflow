from __future__ import annotations

import pytest

from tests.helpers.reference_model import event_types
from tests.helpers.scenario_catalog import SCENARIO_CATALOG
from tests.helpers.trace_loader import load_trace


@pytest.mark.parametrize("scenario_id", sorted(SCENARIO_CATALOG))
def test_each_acceptance_scenario_has_required_event_evidence(scenario_id: str) -> None:
    scenario = SCENARIO_CATALOG[scenario_id]
    events = load_trace(scenario.trace_name)
    assert set(scenario.required_event_types) <= event_types(events)


def test_fully_agentive_slice_uses_agent_principals_but_preserves_canonical_approvals() -> None:
    events = load_trace(SCENARIO_CATALOG["AT-SCH-003"].trace_name)
    claim_actor_types = {event["actor"]["type"] for event in events if event["event_type"] == "task.claimed"}
    approval_actor_types = {event["actor"]["type"] for event in events if event["event_type"] == "approval.responded"}
    assert claim_actor_types == {"agent"}
    assert approval_actor_types == {"agent"}
    assert {event["event_type"] for event in events} >= {"approval.requested", "approval.responded", "artifact.pointer.promoted"}


def test_happy_path_trace_preserves_publish_then_additive_replan() -> None:
    events = load_trace(SCENARIO_CATALOG["AT-SCH-001"].trace_name)
    promoted = [event for event in events if event["event_type"] == "artifact.pointer.promoted"]
    dataset_keys = [event["payload"]["dataset_key"] for event in promoted]
    assert dataset_keys == ["schedule.published_schedule.workbook", "schedule.replan_delta.workbook"]
