from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"

REQUIRED_EVENT_KEYS = {
    "sequence_no",
    "event_id",
    "event_type",
    "occurred_at",
    "recorded_at",
    "tenant_id",
    "domain_id",
    "actor",
    "links",
    "payload",
}


def _api_client(harness: RuntimeScenarioHarness) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=["dispatch_supervisor"],
    )


def test_timeline_events_list_contract_supports_scope_and_filtering(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(harness)
    result = client.get(
        "/api/v1/timeline-events",
        query={"workflow_run_id": harness.workflow_run_id, "limit": 10},
    )
    assert result.status_code == 200

    payload = result.payload
    assert payload["status"] == "ok"
    assert payload["command"] == "api.timeline_events.list"

    events = payload["events"]
    assert len(events) >= 1
    assert payload["page"] == {"limit": 10, "offset": 0}

    for event in events:
        assert REQUIRED_EVENT_KEYS.issubset(set(event.keys()))

    sequence_numbers = [event["sequence_no"] for event in events]
    assert sequence_numbers == sorted(sequence_numbers, reverse=True)

    first_event_type = events[0]["event_type"]
    filtered = client.get(
        "/api/v1/timeline-events",
        query={"workflow_run_id": harness.workflow_run_id, "event_type": first_event_type},
    )
    assert filtered.status_code == 200
    assert all(event["event_type"] == first_event_type for event in filtered.payload["events"])
