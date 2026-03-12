from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from onetruth.application.services.execution_evidence import (
    EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
    EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
)
from onetruth.integrations.openai import OpenAIResponsesFunctionCallingRunner
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/weekly_schedule_build_deterministic_slice.yaml"
)


def _prepare_claimed_stage04_task(
    tmp_path: Path,
) -> tuple[RuntimeScenarioHarness, RuntimeApiClient, str]:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    for step_id in (
        "create_route_slot_requirements",
        "create_driver_capabilities",
        "create_approved_availability",
        "create_actual_hours",
    ):
        harness.run_named_step(step_id)

    created = harness.run_action(
        action="tasks.create",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "stage_id": "Stage04",
            "task_kind": "work_item",
            "create_human_task": True,
            "candidate_roles": ["schedule_planner"],
            "owner_role": "schedule_planner",
            "activation_key": f"scenario:{harness.scenario_id}:stage04:execution-runtime",
            "idempotency_key": f"scenario:{harness.scenario_id}:tasks.create:stage04-execution-runtime",
        },
    )
    human_task_id = str(created["result"]["human_task"]["human_task_id"])

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        actor_id="human:schedule-planner-1",
        actor_type="human",
        actor_roles=["schedule_planner"],
    )
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:stage04-runtime-claim",
        },
    )
    assert claimed.status_code == 200, claimed.payload
    return harness, client, human_task_id


def _mock_stage04_runner() -> OpenAIResponsesFunctionCallingRunner:
    calls = {"count": 0}

    def transport(payload, _timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            return (
                200,
                {
                    "id": "resp_runtime_1",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 30, "output_tokens": 12},
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_ctx",
                            "name": "get_stage04_context",
                            "arguments": "{}",
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_build",
                            "name": "materialize_weekly_stage04_draft_outputs",
                            "arguments": "{}",
                        },
                    ],
                },
                "req_runtime_1",
            )
        if calls["count"] == 2:
            assert payload.get("previous_response_id") == "resp_runtime_1"
            return (
                200,
                {
                    "id": "resp_runtime_2",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 22, "output_tokens": 8},
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_val",
                            "name": "get_stage04_validation_summary",
                            "arguments": "{}",
                        }
                    ],
                },
                "req_runtime_2",
            )
        return (
            200,
            {
                "id": "resp_runtime_3",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 10, "output_tokens": 6},
                "output_text": (
                    '{"summary":"runtime ok","selected_candidate_count":2,'
                    '"recommended_action":"forward_to_stage05_manager_review","warnings":[]}'
                ),
            },
            "req_runtime_3",
        )

    return OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )


def test_weekly_stage04_execution_runtime_persists_rows_events_and_trace_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness, client, human_task_id = _prepare_claimed_stage04_task(tmp_path)
    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _mock_stage04_runner(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage04-runtime"},
    )
    assert response.status_code == 200, response.payload
    result = response.payload["result"]

    sessions = harness.query_rows("SELECT state, tool_call_count FROM execution_sessions")
    assert sessions[0]["state"] == "SUCCEEDED"
    assert int(sessions[0]["tool_call_count"]) == 1

    tool_rows = harness.query_rows("SELECT state FROM tool_executions")
    assert tool_rows[0]["state"] == "COMPLETED"

    policy_rows = harness.query_rows("SELECT decision FROM policy_decisions")
    assert policy_rows[0]["decision"] == "allow"

    artifacts = harness.list_artifacts()["artifact_versions"]
    assert {item["artifact_kind"] for item in result["execution_semantics_evidence"]} == {
        EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
        EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
    }
    evidence_kinds = {item["artifact_kind"] for item in artifacts}
    assert "runtime.context_pack.json" in evidence_kinds
    assert "runtime.tool_request.json" in evidence_kinds
    assert "runtime.tool_result.json" in evidence_kinds
    assert "execution.trace.json" in evidence_kinds

    execution_subject = (
        "execution_session",
        str(result["execution_session"]["execution_session_id"]),
    )
    tool_subject = ("tool_execution", str(result["tool_execution"]["tool_execution_id"]))
    policy_subject = ("policy_decision", str(result["policy_decision"]["policy_decision_id"]))
    runtime_rows = [
        row
        for row in artifacts
        if row["artifact_kind"] in {"runtime.context_pack.json", "runtime.tool_request.json", "runtime.tool_result.json", "execution.trace.json"}
    ]
    for row in runtime_rows:
        linked_subjects = {(str(link["subject_kind"]), str(link["subject_id"])) for link in row["links"]}
        assert execution_subject in linked_subjects
        assert tool_subject in linked_subjects
        assert policy_subject in linked_subjects

    tool_result_row = next(item for item in artifacts if item["artifact_kind"] == "runtime.tool_result.json")
    parsed_uri = urlparse(tool_result_row["storage_uri"])
    payload = json.loads(Path(parsed_uri.path).read_text(encoding="utf-8"))
    turn_one_calls = payload["turns"][0]["function_calls"]
    assert [item["name"] for item in turn_one_calls] == [
        "get_stage04_context",
        "materialize_weekly_stage04_draft_outputs",
    ]

    events = harness.list_events()
    event_types = [event["event_type"] for event in events]
    assert "execution.session.created" in event_types
    assert "tool.execution.requested" in event_types
    assert "tool.execution.approved" in event_types
    assert "tool.execution.completed" in event_types
    assert "execution.session.state_changed" in event_types


def test_weekly_stage04_policy_denial_skips_runner_and_records_denial(tmp_path: Path, monkeypatch) -> None:
    harness, client, human_task_id = _prepare_claimed_stage04_task(tmp_path)

    class _MustNotRun:
        def run_function_calling_loop(self, **_kwargs):
            raise AssertionError("runner should not execute when policy denies")

    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _MustNotRun(),
    )

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={
            "idempotency_key": f"api:{harness.scenario_id}:stage04-runtime-deny",
            "policy_decision": "deny",
        },
    )
    assert response.status_code == 403
    assert response.payload["error"]["code"] == "tool_execution_denied"

    sessions = harness.query_rows("SELECT state FROM execution_sessions")
    assert [row["state"] for row in sessions] == ["FAILED"]

    tools = harness.query_rows("SELECT state FROM tool_executions")
    assert [row["state"] for row in tools] == ["DENIED"]

    policies = harness.query_rows("SELECT decision FROM policy_decisions")
    assert [row["decision"] for row in policies] == ["deny"]
