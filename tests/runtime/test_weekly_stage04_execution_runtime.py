from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from onetruth.application.handlers.workflow_task_lifecycle import CommandError
from onetruth.application.services.execution_evidence import (
    EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
    EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
)
from onetruth.application.services.schedule_control.stage04_input_registry import (
    resolve_weekly_stage04_input_artifacts,
)
from onetruth.integrations.openai import OpenAIResponsesFunctionCallingRunner
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/weekly_schedule_build_deterministic_slice.yaml"
)

_STAGE04_REQUIRED_KEYS = [
    "planning.route_slot_requirements.workbook",
    "planning.driver_capabilities.workbook",
    "planning.input_bundle.doc",
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
    "planning.draft_weekly_schedule.doc",
    "planning.draft_weekly_schedule.workbook",
]


def _artifact_record(
    dataset_key: str,
    *,
    artifact_version_id: str,
    created_at: str,
) -> dict[str, object]:
    return {
        "artifact_version_id": artifact_version_id,
        "dataset_key": dataset_key,
        "artifact_kind": dataset_key,
        "created_at": created_at,
        "metadata_json": {},
    }


def _stage04_stage_spec(required_evidence_keys: list[str]) -> dict[str, object]:
    return {
        "workflow_id": "weekly_schedule_planning.v1",
        "stage_id": "Stage04",
        "required_evidence_keys": required_evidence_keys,
    }


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
                            "call_id": "call_preview",
                            "name": "preview_stage04_next_iteration",
                            "arguments": "{}",
                        },
                    ],
                },
                "req_runtime_1",
            )
        assert payload.get("previous_response_id") == f"resp_runtime_{calls['count'] - 1}"
        outputs = [
            json.loads(str(item.get("output") or "{}"))
            for item in payload.get("input", [])
            if isinstance(item, dict) and str(item.get("type") or "") == "function_call_output"
        ]
        if any(
            isinstance(item, dict) and item.get("stage04_build_result")
            for item in outputs
        ):
            return (
                200,
                {
                    "id": f"resp_runtime_{calls['count']}",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 10, "output_tokens": 6},
                    "output_text": (
                        '{"summary":"runtime ok","selected_candidate_count":2,'
                        '"recommended_action":"forward_to_stage05_manager_review","warnings":[]}'
                    ),
                },
                f"req_runtime_{calls['count']}",
            )
        if any(
            isinstance(item, dict)
            and item.get("planner_complete") is True
            and item.get("iteration_result")
            for item in outputs
        ):
            return (
                200,
                {
                    "id": f"resp_runtime_{calls['count']}",
                    "model": "gpt-4.1-mini",
                    "usage": {"input_tokens": 22, "output_tokens": 8},
                    "output": [
                        {
                            "type": "function_call",
                            "call_id": "call_val",
                            "name": "get_stage04_validation_summary",
                            "arguments": "{}",
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_iter",
                            "name": "get_stage04_iteration_analysis",
                            "arguments": "{\"iteration_index\":1}",
                        },
                        {
                            "type": "function_call",
                            "call_id": "call_finalize",
                            "name": "finalize_weekly_stage04_draft_outputs",
                            "arguments": "{}",
                        },
                    ],
                },
                f"req_runtime_{calls['count']}",
            )
        return (
            200,
            {
                "id": f"resp_runtime_{calls['count']}",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 18, "output_tokens": 7},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call_apply",
                        "name": "apply_stage04_next_iteration",
                        "arguments": "{}",
                    }
                ],
            },
            f"req_runtime_{calls['count']}",
        )

    return OpenAIResponsesFunctionCallingRunner(
        api_key="sk-test",
        model="gpt-4.1-mini",
        base_url="https://api.openai.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=transport,
    )


def _stalled_stage04_runner() -> OpenAIResponsesFunctionCallingRunner:
    calls = {"count": 0}

    def transport(_payload, _timeout):
        calls["count"] += 1
        return (
            200,
            {
                "id": f"resp_stalled_{calls['count']}",
                "model": "gpt-4.1-mini",
                "usage": {"input_tokens": 9, "output_tokens": 4},
                "output": [
                    {
                        "type": "function_call",
                        "call_id": f"call_ctx_{calls['count']}",
                        "name": "get_stage04_context",
                        "arguments": "{}",
                    }
                ],
            },
            f"req_stalled_{calls['count']}",
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
    request_rows = [
        row for row in artifacts if row["artifact_kind"] == "runtime.tool_request.json"
    ]
    result_rows = [
        row for row in artifacts if row["artifact_kind"] == "runtime.tool_result.json"
    ]
    assert len(result["runtime_turn_evidence"]) == 4
    assert len(request_rows) == 4
    assert len(result_rows) == 4

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

    tool_result_row = sorted(
        result_rows,
        key=lambda item: int(
            ((item.get("metadata_json") or {}).get("turn_index") or 0)
            if isinstance(item.get("metadata_json"), dict)
            else 0
        ),
    )[0]
    parsed_uri = urlparse(tool_result_row["storage_uri"])
    payload = json.loads(Path(parsed_uri.path).read_text(encoding="utf-8"))
    turn_one_calls = payload["function_calls"]
    assert [item["name"] for item in turn_one_calls] == [
        "get_stage04_context",
        "preview_stage04_next_iteration",
    ]

    events = harness.list_events()
    event_types = [event["event_type"] for event in events]
    assert "execution.session.created" in event_types
    assert "tool.execution.requested" in event_types
    assert "tool.execution.approved" in event_types
    assert "tool.execution.completed" in event_types
    assert "execution.session.state_changed" in event_types


def test_weekly_stage04_execution_runtime_enforces_authored_no_progress_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness, client, human_task_id = _prepare_claimed_stage04_task(tmp_path)
    monkeypatch.setattr(
        "onetruth.application.services.weekly_stage04_openai_agent.build_weekly_stage04_openai_agent_runner_from_env",
        lambda: _stalled_stage04_runner(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage04-runtime-stalled"},
    )
    assert response.status_code == 502
    assert response.payload["error"]["code"] == "openai_tool_no_progress"

    sessions = harness.query_rows("SELECT state FROM execution_sessions")
    assert [row["state"] for row in sessions] == ["FAILED"]

    artifacts = harness.list_artifacts()["artifact_versions"]
    request_rows = [
        row for row in artifacts if row["artifact_kind"] == "runtime.tool_request.json"
    ]
    result_rows = [
        row for row in artifacts if row["artifact_kind"] == "runtime.tool_result.json"
    ]
    assert len(request_rows) == 3
    assert len(result_rows) == 3
    assert any(row["artifact_kind"] == "execution.trace.json" for row in artifacts)


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


def test_stage04_input_resolution_rejects_missing_authored_required_binding() -> None:
    artifacts = [
        _artifact_record(
            "planning.route_slot_requirements.workbook",
            artifact_version_id="av-route-001",
            created_at="2026-03-10T10:00:00Z",
        ),
        _artifact_record(
            "planning.driver_capabilities.workbook",
            artifact_version_id="av-driver-001",
            created_at="2026-03-10T10:05:00Z",
        ),
    ]
    stage_spec = _stage04_stage_spec(
        [
            "planning.driver_capabilities.workbook",
            "planning.input_bundle.doc",
            "planning.candidate_schedule_delta.workbook",
            "planning.validation_summary.doc",
            "planning.draft_weekly_schedule.doc",
            "planning.draft_weekly_schedule.workbook",
        ]
    )

    with pytest.raises(CommandError) as exc_info:
        resolve_weekly_stage04_input_artifacts(
            artifacts=artifacts,
            stage_spec=stage_spec,
        )

    assert exc_info.value.code == "invalid_weekly_stage04_control_spec"
    assert exc_info.value.details["missing_required_evidence_keys"] == [
        "planning.route_slot_requirements.workbook"
    ]


def test_stage04_input_resolution_rejects_ambiguous_required_binding_alias() -> None:
    artifacts = [
        _artifact_record(
            "planning.route_slot_requirements.workbook",
            artifact_version_id="av-route-001",
            created_at="2026-03-10T10:00:00Z",
        ),
        _artifact_record(
            "planning.driver_capabilities.workbook",
            artifact_version_id="av-driver-001",
            created_at="2026-03-10T10:05:00Z",
        ),
    ]
    stage_spec = _stage04_stage_spec(
        [*_STAGE04_REQUIRED_KEYS, "dispatch.route_slot_requirements.workbook"]
    )

    with pytest.raises(CommandError) as exc_info:
        resolve_weekly_stage04_input_artifacts(
            artifacts=artifacts,
            stage_spec=stage_spec,
        )

    assert exc_info.value.code == "invalid_weekly_stage04_control_spec"
    assert exc_info.value.details["ambiguous_required_evidence_keys"] == [
        {
            "slot_key": "route_slot_requirements",
            "expected_dataset_key": "planning.route_slot_requirements.workbook",
            "conflicting_dataset_keys": ["dispatch.route_slot_requirements.workbook"],
        }
    ]
