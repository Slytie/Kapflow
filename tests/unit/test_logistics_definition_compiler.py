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
