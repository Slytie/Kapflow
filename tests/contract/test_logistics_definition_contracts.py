from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]

LOGISTICS_WORKFLOW_PACKS = [
    ("weekly_schedule_planning", "weekly_schedule_planning.v1"),
    ("live_dispatch", "live_dispatch.v1"),
    ("availability_request", "availability_request.v1"),
    ("dispatch_reporting", "dispatch_reporting.v1"),
    ("timecard_audit", "timecard_audit.v1"),
]


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


def test_logistics_workflow_packs_validate_under_repo_contracts() -> None:
    workflow_schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "workflow_contract.schema.json")
    artifact_map_schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "artifact_map.schema.json")
    decision_schema = _load_json(REPO_ROOT / "schemas" / "agentic" / "decision_catalog.schema.json")
    profile_schema = _load_json(REPO_ROOT / "schemas" / "agentic" / "execution_profile.schema.json")

    for workflow_dir_name, workflow_id in LOGISTICS_WORKFLOW_PACKS:
        workflow_dir = REPO_ROOT / "docs" / "workflows" / workflow_dir_name / "v1"
        assert workflow_dir.exists(), f"missing logistics workflow pack: {workflow_dir}"

        workflow_contract = _load_yaml(workflow_dir / "WORKFLOW_CONTRACT.yaml")
        artifact_map = _load_yaml(workflow_dir / "ARTIFACT_MAP.yaml")
        decision_catalog = _load_yaml(workflow_dir / "DECISION_CATALOG.yaml")
        execution_profile = _load_yaml(workflow_dir / "EXECUTION_PROFILE.yaml")

        _validate(workflow_contract, workflow_schema, workflow_dir / "WORKFLOW_CONTRACT.yaml")
        _validate(artifact_map, artifact_map_schema, workflow_dir / "ARTIFACT_MAP.yaml")
        _validate(decision_catalog, decision_schema, workflow_dir / "DECISION_CATALOG.yaml")
        _validate(execution_profile, profile_schema, workflow_dir / "EXECUTION_PROFILE.yaml")

        assert workflow_contract["workflow"]["id"] == workflow_id
        assert execution_profile["profile"]["workflow_id"] == workflow_id
        assert decision_catalog["catalog"]["workflow_id"] == workflow_id
        assert (workflow_dir / "OPERATING_MODEL.md").exists()
        assert (workflow_dir / "ACCEPTANCE_CRITERIA.md").exists()
        assert (workflow_dir / "examples" / "README.md").exists()


def test_logistics_workflow_family_definition_validates() -> None:
    family_schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "workflow_family.schema.json")
    family_path = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "WORKFLOW_FAMILY.yaml"
    family = _load_yaml(family_path)
    _validate(family, family_schema, family_path)

    module_ids = {item["module_id"] for item in family["family"]["modules"]}
    assert {"weekly_schedule_planning", "live_dispatch"} <= module_ids

    edge_ids = {item["edge_id"] for item in family["family"]["edges"]}
    assert "weekly_seed_to_live_dispatch" in edge_ids


def test_logistics_partition_transform_registry_is_typed_and_validated() -> None:
    schema = _load_json(REPO_ROOT / "schemas" / "workflows" / "partition_transform_registry.schema.json")
    registry_path = REPO_ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1" / "PARTITION_TRANSFORMS.yaml"
    registry = _load_yaml(registry_path)
    _validate(registry, schema, registry_path)

    transform_ids = {item["id"] for item in registry["registry"]["transforms"]}
    assert "planning_week_to_service_days" in transform_ids
