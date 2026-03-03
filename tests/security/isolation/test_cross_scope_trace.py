from __future__ import annotations

from tests.helpers.reference_model import reduce_events
from tests.helpers.trace_loader import load_trace


def test_cross_scope_denial_leaves_audit_evidence_and_no_official_write() -> None:
    events = load_trace("schedule_cross_scope_denial.jsonl")
    state = reduce_events(events)
    denied = state["tool_executions"]["tx-stage05-scope-001"]
    assert denied["state"] == "DENIED"
    assert denied["denial_reason"] == "cross_scope_read_denied"
    assert state["execution_sessions"]["xs-stage05-scope-001"]["state"] == "FAILED"
    assert state["task_runs"]["tr-stage05-scope-001"]["state"] == "FAILED"
    assert state["pointer_targets_by_dataset"] == {}
