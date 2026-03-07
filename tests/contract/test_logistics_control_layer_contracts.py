from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from onetruth.infrastructure.definitions.control_layer import compile_control_layer


REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "WORKFLOW_FAMILY.yaml"
TRANSFORMS_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "PARTITION_TRANSFORMS.yaml"
METHOD_PACKAGES_PATH = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "METHOD_PACKAGES.yaml"
ACTIVATION_REQUEST_EXAMPLE_PATH = REPO_ROOT / "docs" / "examples" / "logistics_definitions" / "ACTIVATION_REQUEST.example.yaml"
COMPILED_STAGE_EXAMPLE_PATH = REPO_ROOT / "docs" / "examples" / "logistics_definitions" / "COMPILED_STAGE_EXECUTION_SPEC.example.yaml"


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), f"expected object schema at {path}"
    return loaded


def _validate(instance: Any, schema: dict[str, Any], path: Path) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    assert not errors, f"{path} failed validation: {[err.message for err in errors]}"


def test_logistics_method_package_registry_validates() -> None:
    schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "method_package.schema.json")
    method_packages = _load_yaml(METHOD_PACKAGES_PATH)
    _validate(method_packages, schema, METHOD_PACKAGES_PATH)


def test_logistics_activation_request_example_validates() -> None:
    schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "activation_request.schema.json")
    activation_request = _load_yaml(ACTIVATION_REQUEST_EXAMPLE_PATH)
    _validate(activation_request, schema, ACTIVATION_REQUEST_EXAMPLE_PATH)


def test_compiled_stage_execution_specs_are_deterministic_and_schema_valid() -> None:
    first = compile_control_layer(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
        method_packages_path=METHOD_PACKAGES_PATH,
    )
    second = compile_control_layer(
        repo_root=REPO_ROOT,
        family_path=FAMILY_PATH,
        partition_transforms_path=TRANSFORMS_PATH,
        method_packages_path=METHOD_PACKAGES_PATH,
    )
    assert first["compiled_stage_execution_specs"] == second["compiled_stage_execution_specs"]

    schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "compiled_stage_execution_spec.schema.json")
    validator = Draft202012Validator(schema)
    for spec in first["compiled_stage_execution_specs"]:
        assert list(validator.iter_errors(spec)) == []


def test_compiled_stage_execution_example_validates() -> None:
    schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "compiled_stage_execution_spec.schema.json")
    compiled_stage_example = _load_yaml(COMPILED_STAGE_EXAMPLE_PATH)
    _validate(compiled_stage_example, schema, COMPILED_STAGE_EXAMPLE_PATH)
