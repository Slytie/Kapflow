from __future__ import annotations

from tests.helpers.reference_model import reduce_events
from tests.helpers.trace_loader import load_trace



def test_policy_gate_trace_requires_denial_before_approved_tool_execution() -> None:
    events = load_trace("schedule_policy_gate_enforced.jsonl")
    event_types = [event["event_type"] for event in events]
    first_denied = event_types.index("tool.execution.denied")
    approval_responded = event_types.index("approval.responded")
    first_approved = event_types.index("tool.execution.approved")
    assert first_denied < approval_responded < first_approved

    state = reduce_events(events)
    assert state["tool_executions"]["tx-stage07-policy-denied-001"]["state"] == "DENIED"
    assert state["tool_executions"]["tx-stage07-policy-approved-001"]["state"] == "COMPLETED"
    assert state["execution_sessions"]["xs-stage07-policy-001"]["state"] == "SUCCEEDED"


def test_fully_agentive_trace_does_not_bypass_canonical_state_objects() -> None:
    events = load_trace("schedule_fully_agentive_whole_flow.jsonl")
    state = reduce_events(events)
    assert len(state["task_runs"]) == 5
    assert len(state["human_tasks"]) == 5
    assert len(state["approvals"]) == 2
    assert len(state["execution_sessions"]) == 5
    assert len(state["tool_executions"]) == 5
