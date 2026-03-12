from __future__ import annotations

from pathlib import Path

import json
import pytest
import yaml
from jsonschema import Draft202012Validator

from onetruth.infrastructure.definitions.family_compiler import (
    DefinitionCompileError,
    compile_workflow_family,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "WORKFLOW_FAMILY.yaml"
TRANSFORMS_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "PARTITION_TRANSFORMS.yaml"

WEEKLY_STAGE04_BRIDGE_KEYS = {
    "planning.route_slot_requirements.workbook",
    "planning.driver_capabilities.workbook",
    "planning.input_bundle.doc",
    "planning.candidate_schedule_delta.workbook",
}

LIVE_STAGE02_BRIDGE_KEYS = {
    "dispatch.input_bundle.doc",
    "dispatch.candidate_schedule_delta.workbook",
}

LIVE_STAGE01_BRIDGE_KEYS = {
    "dispatch.route_slot_requirements.workbook",
    "dispatch.driver_capabilities.workbook",
}

PROHIBITED_TRUTH_KEYS = {
    "planning.current_schedule_plan.workbook",
    "planning.open_exceptions.workbook",
    "dispatch.current_schedule_plan.workbook",
    "dispatch.open_exceptions.workbook",
}


def _compiled_module(compiled: dict[str, object], module_id: str) -> dict[str, object]:
    modules = compiled["compiled_modules"]
    assert isinstance(modules, list)
    for module in modules:
        assert isinstance(module, dict)
        if module["module_id"] == module_id:
            return module
    raise AssertionError(f"missing compiled module: {module_id}")


def _input_keys_for_stage(module: dict[str, object], stage_id: str) -> set[str]:
    inputs = module["inputs"]
    assert isinstance(inputs, list)
    return {
        str(item["dataset_key"])
        for item in inputs
        if isinstance(item, dict) and item.get("stage_id") == stage_id
    }


def test_compiled_module_descriptors_are_deterministic() -> None:
    first = compile_workflow_family(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
    )
    second = compile_workflow_family(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
    )
    assert first["compiled_modules"] == second["compiled_modules"]


def test_compiled_family_edges_are_deterministic() -> None:
    first = compile_workflow_family(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
    )
    second = compile_workflow_family(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
    )
    assert first["compiled_edges"] == second["compiled_edges"]


def test_compiled_descriptors_validate_against_compiled_schemas() -> None:
    compiled = compile_workflow_family(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
    )
    module_schema = json.loads(
        (REPO_ROOT / "schemas" / "workflows" / "compiled_module_definition.schema.json").read_text(encoding="utf-8")
    )
    edge_schema = json.loads(
        (REPO_ROOT / "schemas" / "workflows" / "compiled_family_edge.schema.json").read_text(encoding="utf-8")
    )
    module_validator = Draft202012Validator(module_schema)
    edge_validator = Draft202012Validator(edge_schema)

    for module in compiled["compiled_modules"]:
        assert list(module_validator.iter_errors(module)) == []
    for edge in compiled["compiled_edges"]:
        assert list(edge_validator.iter_errors(edge)) == []


def test_compiler_captures_schedule_control_bridge_inputs_for_weekly_and_live() -> None:
    compiled = compile_workflow_family(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
    )

    weekly_module = _compiled_module(compiled, "weekly_schedule_planning")
    weekly_stage04_inputs = _input_keys_for_stage(weekly_module, "Stage04")
    assert WEEKLY_STAGE04_BRIDGE_KEYS <= weekly_stage04_inputs

    live_module = _compiled_module(compiled, "live_dispatch")
    live_stage01_inputs = _input_keys_for_stage(live_module, "Stage01")
    assert LIVE_STAGE01_BRIDGE_KEYS <= live_stage01_inputs

    live_stage02_inputs = _input_keys_for_stage(live_module, "Stage02")
    assert LIVE_STAGE02_BRIDGE_KEYS <= live_stage02_inputs


def test_compiler_excludes_prohibited_peer_truth_dataset_keys() -> None:
    compiled = compile_workflow_family(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
    )
    for module in compiled["compiled_modules"]:
        assert isinstance(module, dict)
        inputs = module["inputs"]
        outputs = module["outputs"]
        assert isinstance(inputs, list)
        assert isinstance(outputs, list)
        dataset_keys = {
            str(item["dataset_key"])
            for item in [*inputs, *outputs]
            if isinstance(item, dict) and "dataset_key" in item
        }
        assert PROHIBITED_TRUTH_KEYS.isdisjoint(dataset_keys)


def test_compiler_fails_closed_when_first_slice_handoff_is_underspecified(tmp_path: Path) -> None:
    family_doc = yaml.safe_load(FAMILY_PATH.read_text(encoding="utf-8"))
    assert isinstance(family_doc, dict)
    for edge in family_doc["family"]["edges"]:
        if edge["edge_id"] == "weekly_seed_to_live_dispatch":
            edge.pop("idempotency_mode", None)
            break
    family_override = tmp_path / "WORKFLOW_FAMILY.yaml"
    family_override.write_text(yaml.safe_dump(family_doc, sort_keys=False), encoding="utf-8")

    with pytest.raises(DefinitionCompileError, match="idempotency_mode"):
        compile_workflow_family(
            repo_root=REPO_ROOT,
            family_path=family_override,
            partition_transforms_path=TRANSFORMS_PATH,
        )


def test_compiler_rejects_ambiguous_or_missing_partition_transform_semantics(tmp_path: Path) -> None:
    transforms_text = TRANSFORMS_PATH.read_text(encoding="utf-8")
    edited = transforms_text.replace("source_kind: PlanningWeekID\n", "source_kind: ServiceDateID\n")
    transforms_override = tmp_path / "PARTITION_TRANSFORMS.yaml"
    transforms_override.write_text(edited, encoding="utf-8")

    with pytest.raises(DefinitionCompileError, match="partition transform kind mismatch"):
        compile_workflow_family(
            repo_root=REPO_ROOT,
            family_path=FAMILY_PATH,
            partition_transforms_path=transforms_override,
        )
