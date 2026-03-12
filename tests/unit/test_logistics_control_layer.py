from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from onetruth.infrastructure.definitions.control_layer import (
    ControlCompileError,
    compile_control_layer,
    validate_activation_request,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "WORKFLOW_FAMILY.yaml"
TRANSFORMS_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "PARTITION_TRANSFORMS.yaml"
METHOD_PACKAGES_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "METHOD_PACKAGES.yaml"
ACTIVATION_REQUEST_EXAMPLE_PATH = REPO_ROOT / "docs" / "examples" / "logistics_definitions" / "ACTIVATION_REQUEST.example.yaml"


def _compile(*, method_packages_path: Path | None = None) -> dict[str, object]:
    return compile_control_layer(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
        method_packages_path=method_packages_path or METHOD_PACKAGES_PATH,
    )


def _find_stage_spec(
    compiled: dict[str, object],
    *,
    module_id: str,
    stage_id: str,
) -> dict[str, object]:
    specs = compiled["compiled_stage_execution_specs"]
    assert isinstance(specs, list)
    for spec in specs:
        assert isinstance(spec, dict)
        if spec["module_id"] == module_id and spec["stage_id"] == stage_id:
            return spec
    raise AssertionError(f"missing compiled stage spec: {module_id}:{stage_id}")


def test_compiled_stage_execution_metadata_maps_to_existing_runtime_objects() -> None:
    compiled = _compile()
    assert compiled["activation_model"] == "canonical_runtime_objects_only"
    assert compiled["canonical_runtime_objects"] == [
        "workflow_run",
        "task_run",
        "human_task",
        "execution_session",
        "tool_execution",
    ]

    stage_spec = _find_stage_spec(compiled, module_id="live_dispatch", stage_id="Stage02")
    bindings = stage_spec["runtime_bindings"]
    assert isinstance(bindings, dict)

    workflow_run_binding = bindings["workflow_run"]
    assert workflow_run_binding["object_type"] == "workflow_run"
    assert workflow_run_binding["activation_policy"] == "lazy_on_event"

    task_run_binding = bindings["task_run"]
    assert task_run_binding["object_type"] == "task_run"
    assert task_run_binding["stage_id"] == "Stage02"

    execution_binding = bindings["execution_session"]
    assert execution_binding["object_type"] == "execution_session"
    assert str(execution_binding["execution_spec_id"]).startswith("execspec.")
    assert execution_binding["max_tool_calls"] == 28
    assert execution_binding["no_progress_ticks"] == 4

    tool_binding = bindings["tool_execution"]
    assert tool_binding["object_type"] == "tool_execution"
    assert "projection.render" in tool_binding["allowed_tool_classes"]


def test_method_package_pinning_distinguishes_behavior_packages(tmp_path: Path) -> None:
    baseline = _compile()
    baseline_stage = _find_stage_spec(
        baseline,
        module_id="live_dispatch",
        stage_id="Stage02",
    )

    registry_doc = yaml.safe_load(METHOD_PACKAGES_PATH.read_text(encoding="utf-8"))
    assert isinstance(registry_doc, dict)
    for package in registry_doc["registry"]["packages"]:
        applies_to = package["applies_to"]
        if applies_to["workflow_id"] == "live_dispatch.v1" and applies_to["stage_id"] == "Stage02":
            package["context_builder_ref"] = "context.live_dispatch.stage02.issue_packet.v2"
            break

    override_path = tmp_path / "METHOD_PACKAGES.yaml"
    override_path.write_text(yaml.safe_dump(registry_doc, sort_keys=False), encoding="utf-8")
    modified = _compile(method_packages_path=override_path)
    modified_stage = _find_stage_spec(
        modified,
        module_id="live_dispatch",
        stage_id="Stage02",
    )

    baseline_pin = baseline_stage["method_package_pin"]
    modified_pin = modified_stage["method_package_pin"]
    assert baseline_pin["method_package_digest"] != modified_pin["method_package_digest"]
    assert baseline_stage["runtime_bindings"]["execution_session"]["execution_spec_id"] != modified_stage[
        "runtime_bindings"
    ]["execution_session"]["execution_spec_id"]


def test_activation_requests_validate_against_compiled_definitions() -> None:
    compiled = _compile()
    activation_request_doc = yaml.safe_load(ACTIVATION_REQUEST_EXAMPLE_PATH.read_text(encoding="utf-8"))
    validated = validate_activation_request(
        compiled_control=compiled,
        activation_request_document=activation_request_doc,
    )
    assert validated["target_workflow_id"] == "live_dispatch.v1"
    assert validated["target_stage_id"] == "Stage01"
    assert validated["execution_spec_id"].startswith("execspec.")
    assert set(validated["required_input_dataset_keys"]) == {
        "dispatch.actual_hours_snapshot.workbook",
        "dispatch.base_schedule_seed.workbook",
        "dispatch.driver_capabilities.workbook",
        "dispatch.route_slot_requirements.workbook",
        "dispatch.route_delta_intake.workbook",
    }


def test_no_second_activation_model_is_introduced() -> None:
    compiled = _compile()
    assert "activation_states" not in compiled
    assert "activation_bindings" not in compiled

    specs = compiled["compiled_stage_execution_specs"]
    assert isinstance(specs, list)
    for spec in specs:
        runtime_bindings = spec["runtime_bindings"]
        assert set(runtime_bindings.keys()) == {
            "workflow_run",
            "task_run",
            "human_task",
            "execution_session",
            "tool_execution",
        }


def test_missing_control_metadata_fails_closed(tmp_path: Path) -> None:
    registry_doc = yaml.safe_load(METHOD_PACKAGES_PATH.read_text(encoding="utf-8"))
    assert isinstance(registry_doc, dict)

    packages = registry_doc["registry"]["packages"]
    assert isinstance(packages, list)
    registry_doc["registry"]["packages"] = [
        package
        for package in packages
        if not (
            package["applies_to"]["workflow_id"] == "weekly_schedule_planning.v1"
            and package["applies_to"]["stage_id"] == "Stage07"
        )
    ]

    override_path = tmp_path / "METHOD_PACKAGES.yaml"
    override_path.write_text(yaml.safe_dump(registry_doc, sort_keys=False), encoding="utf-8")

    with pytest.raises(ControlCompileError, match="missing method packages"):
        _compile(method_packages_path=override_path)
