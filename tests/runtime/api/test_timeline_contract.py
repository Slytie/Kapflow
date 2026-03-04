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
    "schema_version",
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


def test_workflow_run_timeline_contract_and_filters(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    harness.run_steps()

    client = _api_client(harness)
    response = client.get(f"/api/v1/workflow-runs/{harness.workflow_run_id}/timeline")
    assert response.status_code == 200
    assert response.payload["status"] == "ok"
    assert response.payload["command"] == "api.workflow_runs.timeline"
    assert response.payload["workflow_run_id"] == harness.workflow_run_id

    events = response.payload["events"]
    assert events
    assert REQUIRED_EVENT_KEYS.issubset(set(events[0].keys()))
    assert [event["sequence_no"] for event in events] == sorted(
        event["sequence_no"] for event in events
    )
    assert any(event["event_type"] == "workflow.run.created" for event in events)
    assert any(event["event_type"] == "artifact.pointer.promoted" for event in events)

    workflow_subject_events = [
        event
        for event in events
        if any(
            link.get("type") == "workflow_run"
            and link.get("id") == harness.workflow_run_id
            for link in event["links"]
        )
    ]
    assert workflow_subject_events

    completed_only = client.get(
        f"/api/v1/workflow-runs/{harness.workflow_run_id}/timeline",
        query={"event_type": "task.completed"},
    )
    assert completed_only.status_code == 200
    assert completed_only.payload["events"]
    assert {event["event_type"] for event in completed_only.payload["events"]} == {
        "task.completed"
    }

    pivot = events[2]
    since = client.get(
        f"/api/v1/workflow-runs/{harness.workflow_run_id}/timeline",
        query={"since_event_id": pivot["event_id"]},
    )
    assert since.status_code == 200
    assert since.payload["events"]
    assert all(event["sequence_no"] > pivot["sequence_no"] for event in since.payload["events"])
