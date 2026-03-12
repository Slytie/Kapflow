from __future__ import annotations

from pathlib import Path

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
            "activation_key": f"scenario:{harness.scenario_id}:stage04:openai-agent",
            "idempotency_key": f"scenario:{harness.scenario_id}:tasks.create:stage04-openai-agent",
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
            "idempotency_key": f"api:{harness.scenario_id}:stage04-agent-claim",
        },
    )
    assert claimed.status_code == 200, claimed.payload
    return harness, client, human_task_id


def _mock_stage04_runner() -> OpenAIResponsesFunctionCallingRunner:
    call_count = {"value": 0}

    def transport(payload, _timeout):
        call_count["value"] += 1
        if call_count["value"] == 1:
            return (
                200,
                {
                    "id": "resp_stage04_1",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 50, "output_tokens": 20},
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_context",
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
                "req_stage04_1",
            )
        if call_count["value"] == 2:
            assert payload.get("previous_response_id") == "resp_stage04_1"
            return (
                200,
                {
                    "id": "resp_stage04_2",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 40, "output_tokens": 15},
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_validation",
                            "name": "get_stage04_validation_summary",
                            "arguments": "{}",
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_ops_packet",
                            "name": "render_stage04_ops_packet",
                            "arguments": "{}",
                        },
                    ],
                },
                "req_stage04_2",
            )
        assert payload.get("previous_response_id") == "resp_stage04_2"
        return (
            200,
            {
                "id": "resp_stage04_3",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 15, "output_tokens": 10},
                "output_text": (
                    '{"summary":"Draft weekly schedule prepared.",'
                    '"selected_candidate_count":2,'
                    '"recommended_action":"forward_to_stage05_manager_review",'
                    '"warnings":[]}'
                ),
            },
            "req_stage04_3",
        )

    return OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )


def test_weekly_stage04_openai_agent_endpoint_happy_path(tmp_path: Path, monkeypatch) -> None:
    harness, client, human_task_id = _prepare_claimed_stage04_task(tmp_path)
    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _mock_stage04_runner(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage04-openai-agent"},
    )
    assert response.status_code == 200, response.payload
    assert response.payload["command"] == "api.human_tasks.weekly_stage04_openai_agent"
    result = response.payload["result"]

    assert result["execution_session"]["state"] == "SUCCEEDED"
    assert result["tool_execution"]["state"] == "COMPLETED"
    assert result["policy_decision"]["decision"] == "allow"
    assert result["context_pack_artifact"]["artifact_kind"] == "runtime.context_pack.json"
    assert {item["artifact_kind"] for item in result["runtime_evidence_artifacts"]} == {
        "runtime.tool_request.json",
        "runtime.tool_result.json",
        "execution.trace.json",
    }
    assert result["stage04_build_result"]["candidate_count"] == 4
    assert result["stage04_build_result"]["selected_candidate_count"] == 2

    task_state = harness.query_rows(
        "SELECT state FROM human_tasks WHERE human_task_id = ?",
        (human_task_id,),
    )
    assert task_state[0]["state"] == "CLAIMED"


def test_weekly_stage04_openai_agent_endpoint_requires_openai_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness, client, human_task_id = _prepare_claimed_stage04_task(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage04-openai-agent-missing-config"},
    )
    assert response.status_code == 503
    assert response.payload["error"]["code"] == "openai_not_configured"

    sessions = harness.query_rows("SELECT state FROM execution_sessions")
    assert sessions[0]["state"] == "FAILED"
