from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from onetruth.application.services.execution_evidence import (
    EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
    EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
)
from onetruth.integrations.openai import (
    OpenAIResponsesError,
    OpenAIResponseMetadata,
    Stage06ReviewClassification,
)
from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.runtime_cli import REPO_ROOT
from tests.runtime.helpers.scenario_harness import RuntimeScenarioHarness

SCENARIO_PATH = REPO_ROOT / "fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml"


class _FakeClassifier:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def classify_stage06_review(self, *, instruction_context, artifact_context, document_text):
        self.calls.append(
            {
                "instruction_context": instruction_context,
                "artifact_context": artifact_context,
                "document_text": document_text,
            }
        )
        return (
            Stage06ReviewClassification(
                outcome="draft_is_publish_ready",
                rationale_summary="Review package has enough evidence to proceed.",
                evidence_refs=["doc:summary", "doc:approval"],
                suggested_follow_on_task_kind="final_review",
            ),
            OpenAIResponseMetadata(
                response_id="resp_fake_001",
                request_id="req_fake_001",
                model="gpt-4.1-mini",
                usage={"input_tokens": 111, "output_tokens": 22},
                attempts=1,
                requested_at="2026-01-01T00:00:00Z",
                completed_at="2026-01-01T00:00:01Z",
            ),
        )


def test_stage06_openai_sandbox_endpoint_persists_evidence_and_uses_canonical_completion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    fake_classifier = _FakeClassifier()
    monkeypatch.setattr(
        "onetruth.application.services.stage06_openai_sandbox.build_stage06_review_classifier_from_env",
        lambda: fake_classifier,
    )
    monkeypatch.setenv("ONETRUTH_ARTIFACT_ROOT", str(tmp_path / "sandbox_artifacts"))

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer-1",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:stage06-openai-claim",
        },
    )
    assert claimed.status_code == 200

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage06-openai-sandbox"},
    )
    assert response.status_code == 200

    result = response.payload["result"]
    assert result["classification"]["outcome"] == "draft_is_publish_ready"
    assert result["execution_session"]["state"] == "SUCCEEDED"
    assert result["tool_execution"]["state"] == "COMPLETED"
    assert result["policy_decision"]["decision"] == "allow"
    assert {item["artifact_kind"] for item in result["execution_semantics_evidence"]} == {
        EXECUTION_COMPILED_SPEC_ARTIFACT_KIND,
        EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND,
    }
    assert result["completion_result"]["human_task"]["state"] == "COMPLETED"
    assert len(result["completion_result"]["spawned_children"]) == 1
    assert result["completion_result"]["spawned_children"][0]["task_kind"] == "final_review"

    assert len(fake_classifier.calls) == 1
    call = fake_classifier.calls[0]
    assert call["document_text"]
    artifact_context = call["artifact_context"]
    assert any(item["artifact_kind"] == "schedule.supervisor_review.doc" for item in artifact_context)

    artifacts = harness.list_artifacts()["artifact_versions"]
    semantics_artifacts = [
        item
        for item in artifacts
        if item["artifact_kind"] in {EXECUTION_COMPILED_SPEC_ARTIFACT_KIND, EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND}
    ]
    assert len(semantics_artifacts) == 2
    expected_root = (tmp_path / "sandbox_artifacts").resolve()
    for artifact in semantics_artifacts:
        linked_subjects = {
            (str(link["subject_kind"]), str(link["subject_id"]))
            for link in artifact["links"]
        }
        assert ("execution_session", str(result["execution_session"]["execution_session_id"])) in linked_subjects
        assert ("tool_execution", str(result["tool_execution"]["tool_execution_id"])) in linked_subjects
        assert ("policy_decision", str(result["policy_decision"]["policy_decision_id"])) in linked_subjects
        semantics_path = Path(urlparse(artifact["storage_uri"]).path)
        assert str(semantics_path).startswith(str(expected_root))

    compiled_spec_row = next(
        item
        for item in semantics_artifacts
        if item["artifact_kind"] == EXECUTION_COMPILED_SPEC_ARTIFACT_KIND
    )
    compiled_spec = json.loads(
        Path(urlparse(compiled_spec_row["storage_uri"]).path).read_text(encoding="utf-8")
    )
    assert compiled_spec["control_source"] == "execution_profile_reference"
    assert compiled_spec["runtime_tool_binding"]["runtime_tool_class"] == "model.openai.responses.stage06.review"
    assert compiled_spec["runtime_tool_binding"]["authored_tool_class_relationship"] == {
        "relationship": "bounded_runtime_alias",
        "uses_allowed_tool_classes": ["artifact.read", "validation"],
        "note": (
            "Engine-specific runtime tool-class strings identify the bounded executor "
            "surface and remain distinct from authored `allowed_tool_classes` capability vocabulary."
        ),
    }
    assert compiled_spec["runtime_bindings"]["tool_execution"]["allowed_tool_classes"] == [
        "artifact.read",
        "validation",
        "approval.request",
        "projection.render",
        "artifact.publish_version",
    ]
    assert (
        compiled_spec["runtime_tool_binding"]["runtime_tool_class"]
        not in compiled_spec["runtime_bindings"]["tool_execution"]["allowed_tool_classes"]
    )

    compile_source_manifest_row = next(
        item
        for item in semantics_artifacts
        if item["artifact_kind"] == EXECUTION_COMPILE_SOURCE_MANIFEST_ARTIFACT_KIND
    )
    compile_source_manifest = json.loads(
        Path(urlparse(compile_source_manifest_row["storage_uri"]).path).read_text(encoding="utf-8")
    )
    assert compile_source_manifest["source_refs"] == [
        {
            "source_kind": "execution_profile",
            "path": "docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml",
        },
        {
            "source_kind": "tool_class_registry",
            "path": "schemas/agentic/tool_class_registry.yaml",
            "runtime_tool_binding_id": "runtime.schedule_planning.stage06.openai_review.responses.v1",
        },
    ]

    evidence = [item for item in artifacts if item["artifact_kind"] == "schedule.stage06.review_ai_evidence.json"]
    assert len(evidence) == 1
    parsed_uri = urlparse(evidence[0]["storage_uri"])
    assert parsed_uri.scheme == "file"
    evidence_path = Path(parsed_uri.path)
    assert evidence_path.exists()
    assert str(evidence_path).startswith(str(expected_root))

    events = harness.list_events()
    assert any(
        event["event_type"] == "artifact.version.created"
        and event["payload"].get("artifact_version_id") == evidence[0]["artifact_version_id"]
        for event in events
    )
    assert any(
        event["event_type"] == "task.completed"
        and event["payload"].get("human_task_id") == human_task_id
        and event["payload"].get("completion_code") == "draft_is_publish_ready"
        for event in events
    )
    assert any(event["event_type"] == "execution.session.created" for event in events)
    assert any(event["event_type"] == "tool.execution.requested" for event in events)
    assert any(event["event_type"] == "tool.execution.approved" for event in events)
    assert any(event["event_type"] == "tool.execution.completed" for event in events)


def test_stage06_openai_sandbox_endpoint_requires_openai_config(tmp_path: Path, monkeypatch) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ONETRUTH_OPENAI_MODEL", "gpt-4.1-mini")

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer-1",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:stage06-openai-claim-missing-config",
        },
    )
    assert claimed.status_code == 200

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage06-openai-missing-config"},
    )
    assert response.status_code == 503
    assert response.payload["error"]["code"] == "openai_not_configured"


def test_stage06_openai_sandbox_endpoint_maps_invalid_model_output_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    harness = RuntimeScenarioHarness.from_yaml(SCENARIO_PATH, tmp_path).prepare()
    created = harness.run_named_step("create_stage06_review")
    human_task_id = created["result"]["human_task"]["human_task_id"]

    class _InvalidOutputClassifier:
        def classify_stage06_review(self, *, instruction_context, artifact_context, document_text):
            raise OpenAIResponsesError(
                code="openai_invalid_output",
                message="structured output keys do not match expected schema",
                retryable=False,
                details={"reason": "schema"},
            )

    monkeypatch.setattr(
        "onetruth.application.services.stage06_openai_sandbox.build_stage06_review_classifier_from_env",
        lambda: _InvalidOutputClassifier(),
    )

    client = RuntimeApiClient(
        db_url=harness.db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id="agent:stage06-reviewer-1",
        actor_type="agent",
        actor_roles=["dispatch_supervisor"],
    )
    claimed = client.post(
        f"/api/v1/human-tasks/{human_task_id}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": f"api:{harness.scenario_id}:stage06-openai-claim-invalid-output",
        },
    )
    assert claimed.status_code == 200

    response = client.post(
        f"/api/v1/human-tasks/{human_task_id}/stage06-agent-review",
        payload={"idempotency_key": f"api:{harness.scenario_id}:stage06-openai-invalid-output"},
    )
    assert response.status_code == 502
    assert response.payload["error"]["code"] == "openai_invalid_output"

    execution_rows = harness.query_rows("SELECT state FROM execution_sessions")
    assert len(execution_rows) == 1
    assert execution_rows[0]["state"] == "FAILED"

    tool_rows = harness.query_rows("SELECT state, error_code FROM tool_executions")
    assert len(tool_rows) == 1
    assert tool_rows[0]["state"] == "FAILED"
    assert tool_rows[0]["error_code"] == "openai_invalid_output"
