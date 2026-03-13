from __future__ import annotations

from pathlib import Path

import pytest

from onetruth.application.handlers.workflow_task_lifecycle import (
    complete_tool_execution_command,
    evaluate_policy_decision_command,
)
from onetruth.application.services.execution_evidence import (
    EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
    EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
)
from onetruth.infrastructure.db.session import open_sqlite_connection
from onetruth.infrastructure.events.event_store import (
    append_event,
    event_id_for_type,
    utc_now_iso,
)
from onetruth.integrations.openai import (
    OpenAIResponseMetadata,
    OpenAIResponsesError,
    Stage06ReviewClassification,
)
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"
SAMPLE_STAGE06_DOC = (
    REPO_ROOT
    / "fixtures/workflows/schedule_planning/template_pack/Stage06_Supervisor_Review_Publish/"
    "Stage06_Supervisor_Review_Publish_Document_Example_COMPLETED.docx"
)


class _AllowClassifier:
    def classify_stage06_review(self, *, instruction_context, artifact_context, document_text):
        assert instruction_context
        assert artifact_context
        assert document_text
        return (
            Stage06ReviewClassification(
                outcome="draft_is_publish_ready",
                rationale_summary="Structured evidence supports publish-ready outcome.",
                evidence_refs=["doc:summary"],
                suggested_follow_on_task_kind="final_review",
            ),
            OpenAIResponseMetadata(
                response_id="resp_allow_001",
                request_id="req_allow_001",
                model="gpt-4.1-mini",
                usage={"input_tokens": 120, "output_tokens": 25},
                attempts=1,
                requested_at="2026-01-01T00:00:00Z",
                completed_at="2026-01-01T00:00:01Z",
            ),
        )


class _FailureClassifier:
    def classify_stage06_review(self, *, instruction_context, artifact_context, document_text):
        raise OpenAIResponsesError(
            code="openai_invalid_output",
            message="structured output keys do not match expected schema",
            retryable=False,
            details={"reason": "schema"},
        )


def _stage06_task_id(harness: RuntimeScenarioHarness) -> str:
    created = harness.run_named_step("create_stage06_review")
    return str(created["result"]["human_task"]["human_task_id"])


def _claim_task(harness: RuntimeScenarioHarness, client: RuntimeApiClient, human_task_id: str, suffix: str) -> None:
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:{suffix}:claim",
        },
    )
    assert claimed.status_code == 200, claimed.payload


def _events_for_run(harness: RuntimeScenarioHarness) -> list[dict[str, object]]:
    return harness.list_events()


def test_execution_session_happy_path_persists_canonical_rows_and_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    human_task_id = _stage06_task_id(harness)

    monkeypatch.setattr(
        "onetruth.application.services.stage06_openai_sandbox.build_stage06_review_classifier_from_env",
        lambda: _AllowClassifier(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_task(harness, client, human_task_id, "execution-happy")

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={"idempotency_key": f"api:{harness.scenario_id}:execution-happy"},
    )
    assert response.status_code == 200, response.payload

    result = response.payload["result"]
    assert result["execution_session"]["state"] == "SUCCEEDED"
    assert result["tool_execution"]["state"] == "COMPLETED"
    assert result["policy_decision"]["decision"] == "allow"
    semantics_artifacts = result["execution_semantics_evidence"]
    assert len(semantics_artifacts) == 2
    assert {item["artifact_kind"] for item in semantics_artifacts} == {
        EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
        EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
    }

    sessions = harness.query_rows(
        "SELECT execution_session_id, execution_spec_id, state, tool_call_count FROM execution_sessions"
    )
    assert len(sessions) == 1
    assert str(sessions[0]["execution_spec_id"]).startswith("execspec.schedule_planning_v1.stage06.reference.")
    assert sessions[0]["state"] == "SUCCEEDED"
    assert int(sessions[0]["tool_call_count"]) == 1

    tools = harness.query_rows("SELECT tool_execution_id, tool_class, state FROM tool_executions")
    assert len(tools) == 1
    assert tools[0]["tool_class"] == "model.openai.responses.stage06.review"
    assert tools[0]["state"] == "COMPLETED"

    policies = harness.query_rows("SELECT policy_decision_id, decision FROM policy_decisions")
    assert len(policies) == 1
    assert policies[0]["decision"] == "allow"

    artifact_rows = harness.list_artifacts()["artifact_versions"]
    pinned_semantics_rows = [
        row
        for row in artifact_rows
        if row["artifact_kind"] in {EXECUTION_COMPILED_SPEC_ARTIFACT_KIND, EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND}
    ]
    assert len(pinned_semantics_rows) == 2
    for row in pinned_semantics_rows:
        linked_subjects = {
            (str(link["subject_kind"]), str(link["subject_id"]))
            for link in row["links"]
        }
        assert (("execution_session", str(result["execution_session"]["execution_session_id"]))) in linked_subjects
        assert (("tool_execution", str(result["tool_execution"]["tool_execution_id"]))) in linked_subjects
        assert (("policy_decision", str(result["policy_decision"]["policy_decision_id"]))) in linked_subjects

    event_types = [event["event_type"] for event in _events_for_run(harness)]
    assert "execution.session.created" in event_types
    assert "tool.execution.requested" in event_types
    assert "tool.execution.approved" in event_types
    assert "tool.execution.completed" in event_types
    assert "execution.session.state_changed" in event_types
    policy_allow_transitions = [
        event
        for event in _events_for_run(harness)
        if event["event_type"] == "execution.session.state_changed"
        and event["payload"].get("reason") == "policy_allow"
    ]
    assert len(policy_allow_transitions) == 1
    assert policy_allow_transitions[0]["payload"]["from_state"] == "WAITING_POLICY"
    assert policy_allow_transitions[0]["payload"]["to_state"] == "RUNNING"


def test_execution_policy_denial_creates_auditable_truth_without_model_side_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    human_task_id = _stage06_task_id(harness)

    # If policy deny is not honored, this classifier would run and fail the test.
    class _MustNotRunClassifier:
        def classify_stage06_review(self, *, instruction_context, artifact_context, document_text):
            raise AssertionError("classifier should not run when policy denies tool execution")

    monkeypatch.setattr(
        "onetruth.application.services.stage06_openai_sandbox.build_stage06_review_classifier_from_env",
        lambda: _MustNotRunClassifier(),
    )

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer-denied",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_task(harness, client, human_task_id, "execution-denied")

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={
            "idempotency_key": f"api:{harness.scenario_id}:execution-denied",
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

    evidence_count = harness.query_rows(
        "SELECT COUNT(*) AS count FROM artifact_versions WHERE artifact_kind = ?",
        ("schedule.stage06.review_ai_evidence.json",),
    )
    assert int(evidence_count[0]["count"]) == 0
    semantics_count = harness.query_rows(
        "SELECT COUNT(*) AS count FROM artifact_versions WHERE artifact_kind IN (?, ?)",
        (
            EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
            EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
        ),
    )
    assert int(semantics_count[0]["count"]) == 2

    event_types = [event["event_type"] for event in _events_for_run(harness)]
    assert "tool.execution.denied" in event_types
    assert "tool.execution.completed" not in event_types


def test_execution_failure_path_maps_into_canonical_failed_states(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    human_task_id = _stage06_task_id(harness)

    monkeypatch.setattr(
        "onetruth.application.services.stage06_openai_sandbox.build_stage06_review_classifier_from_env",
        lambda: _FailureClassifier(),
    )

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer-failure",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_task(harness, client, human_task_id, "execution-failed")

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={"idempotency_key": f"api:{harness.scenario_id}:execution-failed"},
    )
    assert response.status_code == 502
    assert response.payload["error"]["code"] == "openai_invalid_output"

    sessions = harness.query_rows("SELECT state FROM execution_sessions")
    assert [row["state"] for row in sessions] == ["FAILED"]

    tools = harness.query_rows("SELECT state, error_code FROM tool_executions")
    assert [row["state"] for row in tools] == ["FAILED"]
    assert tools[0]["error_code"] == "openai_invalid_output"

    event_types = [event["event_type"] for event in _events_for_run(harness)]
    assert "tool.execution.completed" in event_types
    assert "execution.session.state_changed" in event_types


def test_execution_retry_same_idempotency_does_not_duplicate_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    human_task_id = _stage06_task_id(harness)

    monkeypatch.setattr(
        "onetruth.application.services.stage06_openai_sandbox.build_stage06_review_classifier_from_env",
        lambda: _AllowClassifier(),
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "artifacts"))

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer-retry",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    _claim_task(harness, client, human_task_id, "execution-retry")

    idempotency_key = f"api:{harness.scenario_id}:execution-retry"
    first = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={"idempotency_key": idempotency_key},
    )
    assert first.status_code == 200, first.payload

    second = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={"idempotency_key": idempotency_key},
    )
    assert second.status_code == 409
    assert second.payload["error"]["code"] == "duplicate_execution_request"

    session_count = harness.query_rows("SELECT COUNT(*) AS count FROM execution_sessions")
    assert int(session_count[0]["count"]) == 1
    tool_count = harness.query_rows("SELECT COUNT(*) AS count FROM tool_executions")
    assert int(tool_count[0]["count"]) == 1
    policy_count = harness.query_rows("SELECT COUNT(*) AS count FROM policy_decisions")
    assert int(policy_count[0]["count"]) == 1

    events = _events_for_run(harness)
    assert sum(1 for event in events if event["event_type"] == "tool.execution.requested") == 1


def test_reconcile_executions_fails_stale_open_sessions_without_duplication(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    task_run_id = str(created["result"]["task_run"]["task_run_id"])

    created_session = harness.run_action(
        action="execution-sessions.create",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "task_run_id": task_run_id,
            "execution_spec_id": "test.execution.spec.v1",
            "owner_mode": "service",
            "state": "RUNNING",
            "idempotency_key": f"scenario:{harness.scenario_id}:execution-session",
            "actor_id": "system:tests",
            "actor_type": "system",
        },
    )
    execution_session_id = str(created_session["execution_session"]["execution_session_id"])

    harness.run_action(
        action="tool-executions.request",
        payload={
            "execution_session_id": execution_session_id,
            "tool_class": "model.test.noop",
            "idempotency_key": f"scenario:{harness.scenario_id}:tool-request",
            "actor_id": "system:tests",
            "actor_type": "system",
        },
    )

    reconcile = harness.run_action(
        action="maintenance.reconcile-executions",
        payload={
            "now": "2026-12-31T23:59:59Z",
            "stale_seconds": 0,
        },
    )
    assert reconcile["result"]["processed_count"] == 1
    assert reconcile["result"]["processed"][0]["execution_session_id"] == execution_session_id

    sessions = harness.query_rows(
        "SELECT state FROM execution_sessions WHERE execution_session_id = ?",
        (execution_session_id,),
    )
    assert sessions[0]["state"] == "FAILED"

    tools = harness.query_rows("SELECT state, error_code FROM tool_executions")
    assert tools[0]["state"] == "FAILED"
    assert tools[0]["error_code"] == "execution_reconcile_timeout"

    event_types = [event["event_type"] for event in _events_for_run(harness)]
    assert "tool.execution.completed" in event_types
    assert "execution.session.state_changed" in event_types


def test_reconcile_partial_session_does_not_duplicate_completed_tool_effects(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    task_run_id = str(created["result"]["task_run"]["task_run_id"])

    created_session = harness.run_action(
        action="execution-sessions.create",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "task_run_id": task_run_id,
            "execution_spec_id": "test.execution.spec.v1",
            "owner_mode": "agent",
            "state": "WAITING_POLICY",
            "idempotency_key": f"scenario:{harness.scenario_id}:partial:execution-session",
            "actor_id": "agent:tests",
            "actor_type": "agent",
            "principal_actor": {"type": "agent", "id": "agent:tests"},
        },
    )
    execution_session_id = str(created_session["execution_session"]["execution_session_id"])

    requested_tool = harness.run_action(
        action="tool-executions.request",
        payload={
            "execution_session_id": execution_session_id,
            "tool_class": "model.test.noop",
            "idempotency_key": f"scenario:{harness.scenario_id}:partial:tool-request",
            "actor_id": "agent:tests",
            "actor_type": "agent",
        },
    )
    tool_execution_id = str(requested_tool["tool_execution"]["tool_execution_id"])

    evidence = harness.run_action(
        action="artifacts.ingest",
        payload={
            "workflow_run_id": harness.workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": "schedule.stage06.review_ai_evidence.json",
            "artifact_role": "agent_evidence",
            "source_path": str(SAMPLE_STAGE06_DOC),
            "file_name": SAMPLE_STAGE06_DOC.name,
            "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "storage_root": str(tmp_path / "artifacts"),
            "idempotency_key": f"scenario:{harness.scenario_id}:partial:evidence",
            "actor_id": "agent:tests",
            "actor_type": "agent",
        },
    )
    evidence_artifact_version_id = str(evidence["artifact_version"]["artifact_version_id"])

    connection = open_sqlite_connection(harness.db_url)
    try:
        policy_result = evaluate_policy_decision_command(
            connection,
            {
                "tool_execution_id": tool_execution_id,
                "decision": "allow",
                "principal_actor": {"type": "agent", "id": "agent:tests"},
                "idempotency_key": f"scenario:{harness.scenario_id}:partial:policy",
            },
        )
        assert policy_result["execution_session"]["state"] == "RUNNING"

        completed_tool = complete_tool_execution_command(
            connection,
            {
                "tool_execution_id": tool_execution_id,
                "result": "succeeded",
                "output_artifact_version_ids": [evidence_artifact_version_id],
                "idempotency_key": f"scenario:{harness.scenario_id}:partial:tool-complete",
                "actor_id": "agent:tests",
                "actor_type": "agent",
            },
        )
        assert completed_tool["state"] == "COMPLETED"
    finally:
        connection.close()

    reconcile = harness.run_action(
        action="maintenance.reconcile-executions",
        payload={
            "now": "2026-12-31T23:59:59Z",
            "stale_seconds": 0,
        },
    )
    assert reconcile["result"]["processed_count"] == 1
    assert reconcile["result"]["processed"][0]["execution_session_id"] == execution_session_id
    assert reconcile["result"]["processed"][0]["failed_tool_execution_ids"] == []

    session_rows = harness.query_rows(
        "SELECT state FROM execution_sessions WHERE execution_session_id = ?",
        (execution_session_id,),
    )
    assert session_rows[0]["state"] == "FAILED"

    tool_rows = harness.query_rows(
        "SELECT state FROM tool_executions WHERE tool_execution_id = ?",
        (tool_execution_id,),
    )
    assert tool_rows[0]["state"] == "COMPLETED"

    completed_events = [
        event
        for event in _events_for_run(harness)
        if event["event_type"] == "tool.execution.completed"
        and event["payload"].get("tool_execution_id") == tool_execution_id
    ]
    assert len(completed_events) == 1

    evidence_events = [
        event
        for event in _events_for_run(harness)
        if event["event_type"] == "artifact.version.created"
        and event["payload"].get("artifact_version_id") == evidence_artifact_version_id
    ]
    assert len(evidence_events) == 1


def test_execution_event_required_links_are_enforced_at_runtime(tmp_path: Path) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    task_run_id = str(created["result"]["task_run"]["task_run_id"])

    connection = open_sqlite_connection(harness.db_url)
    try:
        now = utc_now_iso()
        missing_execution_spec = {
            "event_id": event_id_for_type("execution.session.created"),
            "event_type": "execution.session.created",
            "schema_version": "1.0",
            "occurred_at": now,
            "recorded_at": now,
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "actor": {"type": "system", "id": "system:test"},
            "links": [
                {"rel": "subject", "type": "task_run", "id": task_run_id},
                {"rel": "subject", "type": "execution_session", "id": "xs-missing-link"},
            ],
            "payload": {
                "execution_session_id": "xs-missing-link",
                "execution_spec_id": "execspec.test.v1",
                "owner_mode": "service",
            },
            "idempotency_key": f"runtime-required-links:{harness.scenario_id}:missing",
        }
        with pytest.raises(ValueError, match="missing required link types"):
            append_event(connection, missing_execution_spec)

        with_execution_spec = {
            **missing_execution_spec,
            "event_id": event_id_for_type("execution.session.created"),
            "idempotency_key": f"runtime-required-links:{harness.scenario_id}:present",
            "links": [
                *missing_execution_spec["links"],
                {"rel": "uses_execution_spec", "type": "execution_spec", "id": "execspec.test.v1"},
            ],
        }
        append_event(connection, with_execution_spec)
        connection.commit()
    finally:
        connection.close()
