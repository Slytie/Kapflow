from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
RUN_REAL = os.environ.get("ONETRUTH_RUN_OPENAI_E2E", "0") == "1"
STAGE06_ALLOWED_OUTCOMES = {
    "draft_is_publish_ready",
    "review_requires_more_information",
    "review_requests_changes",
}


@pytest.mark.skipif(
    not RUN_REAL,
    reason="real OpenAI integration tests are gated; set ONETRUTH_RUN_OPENAI_E2E=1 to run",
)
def test_stage06_openai_real_e2e_sandbox_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        pytest.fail(
            "ONETRUTH_RUN_OPENAI_E2E=1 is set but OPENAI_API_KEY is missing. "
            "Set OPENAI_API_KEY before running real OpenAI e2e tests."
        )

    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "openai_real_artifacts"))

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer-real",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:stage06-openai-real-claim",
        },
    )
    assert claimed.status_code == 200, claimed.payload

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={
            "idempotency_key": f"api:{harness.scenario_id}:stage06-openai-real",
        },
    )

    assert response.status_code == 200, response.payload

    result = response.payload["result"]
    outcome = result["classification"]["outcome"]
    assert outcome in STAGE06_ALLOWED_OUTCOMES
    assert result["execution_session"]["state"] == "SUCCEEDED"
    assert result["tool_execution"]["state"] == "COMPLETED"
    assert result["policy_decision"]["decision"] == "allow"
    assert result["completion_result"]["human_task"]["state"] == "COMPLETED"
    assert len(result["completion_result"]["spawned_children"]) == 1

    execution_rows = harness.query_rows(
        "SELECT state, tool_call_count FROM execution_sessions",
    )
    assert len(execution_rows) == 1
    assert execution_rows[0]["state"] == "SUCCEEDED"
    assert int(execution_rows[0]["tool_call_count"]) == 1

    tool_rows = harness.query_rows(
        "SELECT state FROM tool_executions",
    )
    assert len(tool_rows) == 1
    assert tool_rows[0]["state"] == "COMPLETED"

    policy_rows = harness.query_rows(
        "SELECT decision FROM policy_decisions",
    )
    assert len(policy_rows) == 1
    assert policy_rows[0]["decision"] == "allow"

    artifacts = harness.list_artifacts()["artifact_versions"]
    evidence = [item for item in artifacts if item["artifact_kind"] == "schedule.stage06.review_ai_evidence.json"]
    assert len(evidence) == 1

    events = harness.list_events()
    assert any(
        event["event_type"] == "task.completed"
        and event["payload"].get("human_task_id") == human_task_id
        for event in events
    )
    assert any(
        event["event_type"] == "artifact.version.created"
        and event["payload"].get("artifact_version_id") == evidence[0]["artifact_version_id"]
        for event in events
    )
    assert any(event["event_type"] == "execution.session.created" for event in events)
    assert any(event["event_type"] == "tool.execution.requested" for event in events)
    assert any(event["event_type"] == "tool.execution.approved" for event in events)
    assert any(event["event_type"] == "tool.execution.completed" for event in events)
