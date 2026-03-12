from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = (
    REPO_ROOT / "fixtures/scenarios/logistics/weekly_schedule_build_deterministic_slice.yaml"
)
RUN_REAL = os.environ.get("ONETRUTH_RUN_OPENAI_E2E", "0") == "1" and os.environ.get(
    "ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E",
    "0",
) == "1"

REQUIRED_EVIDENCE_KINDS = {
    "execution.compiled_spec.json",
    "execution.compile_source_manifest.json",
    "runtime.context_pack.json",
    "runtime.tool_request.json",
    "runtime.tool_result.json",
    "execution.trace.json",
}
REQUIRED_STAGE04_OUTPUT_KINDS = {
    "planning.input_bundle.doc",
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
    "planning.draft_weekly_schedule.workbook",
    "planning.draft_weekly_schedule.doc",
}


@pytest.mark.skipif(
    not RUN_REAL,
    reason=(
        "weekly Stage04 real OpenAI integration tests are gated; set "
        "ONETRUTH_RUN_OPENAI_E2E=1 and ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1 to run"
    ),
)
def test_weekly_stage04_openai_real_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        pytest.fail(
            "ONETRUTH_RUN_OPENAI_E2E=1 and ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1 are set but OPENAI_API_KEY is missing. "
            "Set OPENAI_API_KEY before running weekly Stage04 real OpenAI e2e tests."
        )

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
            "activation_key": f"scenario:{harness.scenario_id}:stage04:openai-real",
            "idempotency_key": f"scenario:{harness.scenario_id}:tasks.create:stage04-openai-real",
        },
    )
    human_task_id = str(created["result"]["human_task"]["human_task_id"])

    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "openai_weekly_real_artifacts"))

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-logistics",
        domain_id="domain-hub",
        actor_id="human:schedule-planner-real",
        actor_type="human",
        actor_roles=["schedule_planner"],
    )
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:stage04-openai-real-claim",
        },
    )
    assert claimed.status_code == 200, claimed.payload

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage04-openai-real"},
    )
    assert response.status_code == 200, response.payload

    result = response.payload["result"]
    assert result["execution_session"]["state"] == "SUCCEEDED"
    assert result["tool_execution"]["state"] == "COMPLETED"
    assert result["policy_decision"]["decision"] == "allow"
    assert result["stage04_build_result"]["candidate_count"] >= 1
    assert (
        result["stage04_build_result"]["candidate_count"]
        >= result["stage04_build_result"]["selected_candidate_count"]
        >= 1
    )

    sessions = harness.query_rows("SELECT state, tool_call_count FROM execution_sessions")
    assert len(sessions) == 1
    assert sessions[0]["state"] == "SUCCEEDED"
    assert int(sessions[0]["tool_call_count"]) == 1

    tools = harness.query_rows("SELECT state FROM tool_executions")
    assert len(tools) == 1
    assert tools[0]["state"] == "COMPLETED"

    policies = harness.query_rows("SELECT decision FROM policy_decisions")
    assert len(policies) == 1
    assert policies[0]["decision"] == "allow"

    artifacts = harness.list_artifacts()["artifact_versions"]
    kinds = {str(item["artifact_kind"]) for item in artifacts}
    assert REQUIRED_EVIDENCE_KINDS.issubset(kinds)
    assert REQUIRED_STAGE04_OUTPUT_KINDS.issubset(kinds)

    pointer_rows = harness.query_rows(
        "SELECT COUNT(*) AS count FROM artifact_pointers WHERE workflow_run_id = ?",
        (harness.workflow_run_id,),
    )
    assert int(pointer_rows[0]["count"]) == 0

    events = harness.list_events()
    assert any(event["event_type"] == "execution.session.created" for event in events)
    assert any(event["event_type"] == "tool.execution.requested" for event in events)
    assert any(event["event_type"] == "tool.execution.approved" for event in events)
    assert any(event["event_type"] == "tool.execution.completed" for event in events)
    assert any(
        event["event_type"] == "artifact.version.created"
        and event["payload"].get("artifact_version_id")
        == result["context_pack_artifact"]["artifact_version_id"]
        for event in events
    )
