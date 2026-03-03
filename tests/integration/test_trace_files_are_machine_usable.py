from __future__ import annotations

from datetime import datetime

from tests.helpers.trace_loader import list_trace_names, load_trace



def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))



def test_all_schedule_traces_are_non_empty_and_have_parseable_timestamps() -> None:
    for trace_name in list_trace_names():
        events = load_trace(trace_name)
        assert events, trace_name
        for event in events:
            _parse(event["recorded_at"])
            _parse(event["occurred_at"])
        assert events[0]["event_type"] == "workflow.run.created", trace_name
