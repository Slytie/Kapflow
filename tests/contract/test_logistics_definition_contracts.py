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

WEEKLY_STAGE04_BRIDGE_KEYS = {
    "planning.route_slot_requirements.workbook",
    "planning.driver_capabilities.workbook",
    "planning.input_bundle.doc",
    "planning.candidate_schedule_delta.workbook",
    "planning.validation_summary.doc",
}

LIVE_STAGE01_BRIDGE_KEYS = {
    "dispatch.route_slot_requirements.workbook",
    "dispatch.driver_capabilities.workbook",
}

LIVE_STAGE02_BRIDGE_KEYS = {
    "dispatch.input_bundle.doc",
    "dispatch.candidate_schedule_delta.workbook",
    "dispatch.validation_summary.doc",
}

PROHIBITED_TRUTH_KEYS = {
    "planning.current_schedule_plan.workbook",
    "planning.open_exceptions.workbook",
    "dispatch.current_schedule_plan.workbook",
    "dispatch.open_exceptions.workbook",
}

WEEKLY_STAGE04_EXAMPLES = {
    "route_slot_requirements_example.yaml",
    "driver_capabilities_example.yaml",
    "stage04_input_bundle_example.yaml",
    "stage04_candidate_schedule_delta_example.yaml",
    "stage04_validation_summary_example.yaml",
}

LIVE_STAGE02_EXAMPLES = {
    "route_slot_requirements_service_day_example.yaml",
    "driver_capabilities_service_day_example.yaml",
    "stage02_input_bundle_example.yaml",
    "stage02_candidate_schedule_delta_example.yaml",
    "stage02_validation_summary_example.yaml",
}


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


def _stage_by_id(workflow_contract: dict[str, Any], stage_id: str) -> dict[str, Any]:
    stages = workflow_contract.get("stages")
    assert isinstance(stages, list), "workflow contract must expose stages list"
    for stage in stages:
        assert isinstance(stage, dict)
        if stage.get("id") == stage_id:
            return stage
    raise AssertionError(f"missing stage {stage_id}")


def _profile_stage_by_id(execution_profile: dict[str, Any], stage_id: str) -> dict[str, Any]:
    profile = execution_profile.get("profile")
    assert isinstance(profile, dict), "execution profile must expose profile object"
    stages = profile.get("stages")
    assert isinstance(stages, list), "execution profile must expose profile.stages list"
    for stage in stages:
        assert isinstance(stage, dict)
        if stage.get("stage_id") == stage_id:
            return stage
    raise AssertionError(f"missing execution profile stage {stage_id}")


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
        contract_keys = {
            artifact["dataset_key"]
            for stage in workflow_contract["stages"]
            for artifact in stage["artifacts"]
        }
        assert PROHIBITED_TRUTH_KEYS.isdisjoint(contract_keys)
        assert (workflow_dir / "OPERATING_MODEL.md").exists()
        assert (workflow_dir / "ACCEPTANCE_CRITERIA.md").exists()
        assert (workflow_dir / "examples" / "README.md").exists()

        if workflow_id == "weekly_schedule_planning.v1":
            stage04 = _stage_by_id(workflow_contract, "Stage04")
            stage04_keys = {artifact["dataset_key"] for artifact in stage04["artifacts"]}
            assert WEEKLY_STAGE04_BRIDGE_KEYS <= stage04_keys
            stage04_semantics = stage04.get("semantics", {})
            assert isinstance(stage04_semantics, dict)
            assert stage04_semantics.get("schedule_control_mode") == "weekly_base_build"
            assert stage04_semantics.get("bundle_artifact_key") == "planning.input_bundle.doc"
            assert (
                stage04_semantics.get("candidate_delta_artifact_key")
                == "planning.candidate_schedule_delta.workbook"
            )
            assert stage04_semantics.get("validation_artifact_key") == "planning.validation_summary.doc"

            stage04_profile = _profile_stage_by_id(execution_profile, "Stage04")
            required_evidence = set(stage04_profile["required_evidence_keys"])
            assert WEEKLY_STAGE04_BRIDGE_KEYS <= required_evidence

            examples_dir = workflow_dir / "examples"
            for name in WEEKLY_STAGE04_EXAMPLES:
                assert (examples_dir / name).exists(), f"missing weekly schedule-control example: {name}"

        if workflow_id == "live_dispatch.v1":
            stage01 = _stage_by_id(workflow_contract, "Stage01")
            stage01_keys = {artifact["dataset_key"] for artifact in stage01["artifacts"]}
            assert LIVE_STAGE01_BRIDGE_KEYS <= stage01_keys

            stage02 = _stage_by_id(workflow_contract, "Stage02")
            stage02_keys = {artifact["dataset_key"] for artifact in stage02["artifacts"]}
            assert LIVE_STAGE02_BRIDGE_KEYS <= stage02_keys
            stage02_semantics = stage02.get("semantics", {})
            assert isinstance(stage02_semantics, dict)
            assert stage02_semantics.get("schedule_control_mode") == "daily_replan"
            assert stage02_semantics.get("bundle_artifact_key") == "dispatch.input_bundle.doc"
            assert (
                stage02_semantics.get("candidate_delta_artifact_key")
                == "dispatch.candidate_schedule_delta.workbook"
            )
            assert stage02_semantics.get("validation_artifact_key") == "dispatch.validation_summary.doc"
            assert stage02_semantics.get("open_exceptions_source") == "canonical_flags"

            stage05 = _stage_by_id(workflow_contract, "Stage05")
            stage05_semantics = stage05.get("semantics", {})
            assert isinstance(stage05_semantics, dict)
            current_schedule = stage05_semantics.get("current_schedule_view", {})
            open_exceptions = stage05_semantics.get("open_exceptions_packet", {})
            assert isinstance(current_schedule, dict)
            assert isinstance(open_exceptions, dict)
            assert current_schedule.get("authority") == "derived_projection_only"
            assert open_exceptions.get("source") == "canonical_flags"

            stage01_profile = _profile_stage_by_id(execution_profile, "Stage01")
            stage01_required_evidence = set(stage01_profile["required_evidence_keys"])
            assert LIVE_STAGE01_BRIDGE_KEYS <= stage01_required_evidence

            stage02_profile = _profile_stage_by_id(execution_profile, "Stage02")
            stage02_required_evidence = set(stage02_profile["required_evidence_keys"])
            assert LIVE_STAGE02_BRIDGE_KEYS <= stage02_required_evidence

            examples_dir = workflow_dir / "examples"
            for name in LIVE_STAGE02_EXAMPLES:
                assert (examples_dir / name).exists(), f"missing live dispatch schedule-control example: {name}"


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
