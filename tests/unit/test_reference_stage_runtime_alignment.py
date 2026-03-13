from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from onetruth.infrastructure.definitions.control_layer import (
    ControlCompileError,
    compile_reference_stage_runtime,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
EXECUTION_PROFILE_PATH = (
    REPO_ROOT / "docs" / "workflows" / "schedule_planning" / "v1" / "EXECUTION_PROFILE.yaml"
)
TOOL_CLASS_REGISTRY_PATH = (
    REPO_ROOT / "schemas" / "agentic" / "tool_class_registry.yaml"
)
RUNTIME_TOOL_BINDING_ID = "runtime.schedule_planning.stage06.openai_review.responses.v1"


def _compile_reference_runtime(*, registry_path: Path | None = None) -> dict[str, object]:
    return compile_reference_stage_runtime(
        repo_root=REPO_ROOT,
        execution_profile_path=EXECUTION_PROFILE_PATH,
        workflow_id="schedule_planning.v1",
        module_id="schedule_planning",
        stage_id="Stage06",
        runtime_tool_binding_id=RUNTIME_TOOL_BINDING_ID,
        workflow_run_id="wr-stage06-test",
        task_run_id="tr-stage06-test",
        principal_actor={"type": "agent", "id": "agent:stage06-reviewer"},
        idempotency_key="unit:stage06-reference-runtime",
        state="WAITING_POLICY",
        execution_session_id="xs-stage06-test",
        actor_type="agent",
        actor_id="agent:stage06-reviewer",
        budget_override={"max_tool_calls": 1, "max_wall_time_seconds": 120},
        tool_class_registry_path=registry_path,
    )


def test_reference_stage_runtime_uses_authored_profile_and_runtime_binding() -> None:
    compiled = _compile_reference_runtime()

    payload = compiled["execution_session_payload"]
    stage_runtime = compiled["stage_runtime"]
    runtime_tool_binding = compiled["runtime_tool_binding"]

    assert payload["execution_spec_id"].startswith("execspec.schedule_planning_v1.stage06.reference.")
    assert payload["budget"] == {
        "max_tool_calls": 1,
        "no_progress_ticks": 2,
        "max_wall_time_seconds": 120,
    }
    assert stage_runtime["required_evidence_keys"] == [
        "schedule.supervisor_review.doc",
        "schedule.published_schedule.workbook",
    ]
    assert stage_runtime["runtime_bindings"]["tool_execution"]["allowed_tool_classes"] == [
        "artifact.read",
        "validation",
        "approval.request",
        "projection.render",
        "artifact.publish_version",
    ]
    assert runtime_tool_binding["runtime_tool_class"] == "model.openai.responses.stage06.review"
    assert runtime_tool_binding["authored_tool_class_relationship"] == {
        "relationship": "bounded_runtime_alias",
        "uses_allowed_tool_classes": ["artifact.read", "validation"],
        "note": (
            "Engine-specific runtime tool-class strings identify the bounded executor "
            "surface and remain distinct from authored `allowed_tool_classes` capability vocabulary."
        ),
    }
    assert (
        runtime_tool_binding["runtime_tool_class"]
        not in stage_runtime["runtime_bindings"]["tool_execution"]["allowed_tool_classes"]
    )
    source_refs = payload["execution_semantics"]["compile_source_manifest"]["source_refs"]
    assert source_refs == [
        {
            "source_kind": "execution_profile",
            "path": "docs/workflows/schedule_planning/v1/EXECUTION_PROFILE.yaml",
        },
        {
            "source_kind": "tool_class_registry",
            "path": "schemas/agentic/tool_class_registry.yaml",
            "runtime_tool_binding_id": RUNTIME_TOOL_BINDING_ID,
        },
    ]


def test_reference_stage_runtime_fails_closed_when_runtime_binding_exceeds_authored_allowlist(
    tmp_path: Path,
) -> None:
    registry_doc = yaml.safe_load(TOOL_CLASS_REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(registry_doc, dict)
    bindings = registry_doc["runtime_tool_bindings"]
    assert isinstance(bindings, list)
    for binding in bindings:
        if binding["id"] == RUNTIME_TOOL_BINDING_ID:
            binding["authored_tool_class_relationship"]["uses_allowed_tool_classes"].append(
                "notification.prepare"
            )
            break

    override_path = tmp_path / "tool_class_registry.yaml"
    override_path.write_text(yaml.safe_dump(registry_doc, sort_keys=False), encoding="utf-8")

    with pytest.raises(
        ControlCompileError,
        match="runtime tool binding references authored tool classes not allowed by the stage profile",
    ):
        _compile_reference_runtime(registry_path=override_path)
