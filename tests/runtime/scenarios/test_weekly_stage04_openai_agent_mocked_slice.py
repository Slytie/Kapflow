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
    *,
    seed_steps: tuple[str, ...] = (
        "create_route_slot_requirements",
        "create_driver_capabilities",
        "create_approved_availability",
        "create_actual_hours",
    ),
) -> tuple[RuntimeScenarioHarness, RuntimeApiClient, str]:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    for step_id in seed_steps:
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
            "activation_key": f"scenario:{harness.scenario_id}:stage04:mocked-slice",
            "idempotency_key": f"scenario:{harness.scenario_id}:tasks.create:stage04-mocked-slice",
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
    claim = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:stage04-mocked-claim",
        },
    )
    assert claim.status_code == 200, claim.payload
    return harness, client, human_task_id


def _mock_stage04_runner() -> OpenAIResponsesFunctionCallingRunner:
    calls = {"count": 0}

    def transport(payload, _timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            return (
                200,
                {
                    "id": "resp_slice_1",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 24, "output_tokens": 9},
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
                "req_slice_1",
            )
        if calls["count"] == 2:
            assert payload.get("previous_response_id") == "resp_slice_1"
            return (
                200,
                {
                    "id": "resp_slice_2",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 12, "output_tokens": 5},
                    "output_text": (
                        '{"summary":"mocked slice complete","selected_candidate_count":2,'
                        '"recommended_action":"forward_to_stage05_manager_review","warnings":[]}'
                    ),
                },
                "req_slice_2",
            )
        raise AssertionError("runner transport called more than expected")

    return OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )


def test_weekly_stage04_openai_agent_mocked_slice_is_idempotent_and_draft_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness, client, human_task_id = _prepare_claimed_stage04_task(tmp_path)
    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _mock_stage04_runner(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    idempotency_key = f"api:{harness.scenario_id}:stage04-mocked-slice"
    first = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": idempotency_key},
    )
    assert first.status_code == 200, first.payload
    assert first.payload["result"]["stage04_build_result"]["selected_candidate_count"] == 2

    second = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": idempotency_key},
    )
    assert second.status_code == 409
    assert second.payload["error"]["code"] == "duplicate_execution_request"

    stage04_artifacts = harness.query_rows(
        """
        SELECT artifact_kind, COUNT(*) AS count
        FROM artifact_versions
        WHERE workflow_run_id = ?
          AND artifact_kind IN (
            'planning.input_bundle.doc',
            'planning.candidate_schedule_delta.workbook',
            'planning.validation_summary.doc',
            'planning.draft_weekly_schedule.workbook',
            'planning.draft_weekly_schedule.doc'
          )
        GROUP BY artifact_kind
        """,
        (harness.workflow_run_id,),
    )
    assert len(stage04_artifacts) == 5
    assert all(int(row["count"]) == 1 for row in stage04_artifacts)

    pointer_count = harness.query_rows(
        "SELECT COUNT(*) AS count FROM artifact_pointers WHERE workflow_run_id = ?",
        (harness.workflow_run_id,),
    )
    # Stage04 slice remains draft-only and should not promote official pointers.
    assert int(pointer_count[0]["count"]) == 0


def test_weekly_stage04_openai_agent_mocked_slice_fails_closed_when_bridge_input_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness, client, human_task_id = _prepare_claimed_stage04_task(
        tmp_path,
        seed_steps=(
            "create_driver_capabilities",
            "create_approved_availability",
            "create_actual_hours",
        ),
    )

    class _MustNotRun:
        def run_function_calling_loop(self, **_kwargs):
            raise AssertionError("runner should not execute when Stage04 bridge input is missing")

    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _MustNotRun(),
    )

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage04-missing-bridge-input"},
    )
    assert response.status_code == 400
    assert response.payload["error"]["code"] == "stage04_input_artifact_missing"
