#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from onetruth.infrastructure.definitions.family_compiler import (  # noqa: E402
    DefinitionCompileError,
    compile_workflow_family,
)
from onetruth.infrastructure.definitions.control_layer import (  # noqa: E402
    ControlCompileError,
    compile_control_layer,
)


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class ValidationError(Exception):
    pass


class Collector:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks: list[str] = []

    def ok(self, msg: str) -> None:
        self.checks.append(msg)

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def require(self, cond: bool, msg: str) -> None:
        if cond:
            self.ok(msg)
        else:
            self.fail(msg)

    def report(self) -> int:
        if self.errors:
            print("VALIDATION FAILED\n")
            for e in self.errors:
                print(f"- {e}")
            print(f"\n{len(self.errors)} error(s), {len(self.checks)} check(s) passed")
            return 1
        print("VALIDATION PASSED\n")
        for c in self.checks:
            print(f"- {c}")
        print(f"\n{len(self.checks)} check(s) passed")
        return 0


def validate_against_schema(path: Path, schema_path: Path, collector: Collector) -> Any:
    doc = load_yaml(path) if path.suffix in {".yaml", ".yml"} else load_json(path)
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        for err in errs:
            collector.fail(f"{path.relative_to(ROOT)} violates {schema_path.relative_to(ROOT)}: {err.message}")
    else:
        collector.ok(f"{path.relative_to(ROOT)} validates against {schema_path.relative_to(ROOT)}")
    return doc


def validate_schema_file(schema_path: Path, collector: Collector) -> None:
    try:
        Draft202012Validator.check_schema(load_json(schema_path))
    except Exception as exc:  # pragma: no cover - defensive
        collector.fail(f"Invalid JSON schema {schema_path.relative_to(ROOT)}: {exc}")
    else:
        collector.ok(f"Schema parses: {schema_path.relative_to(ROOT)}")


def workflow_pack_paths() -> list[Path]:
    return sorted((ROOT / "docs" / "workflows").glob("*/v1/WORKFLOW_CONTRACT.yaml"))


def build_indexes(collector: Collector) -> dict[str, Any]:
    governance = load_yaml(ROOT / "schemas" / "policy" / "governance_vocabulary.yaml")
    tool_registry = load_yaml(ROOT / "schemas" / "agentic" / "tool_class_registry.yaml")
    permissions = load_yaml(ROOT / "schemas" / "policy" / "permissions.yaml")
    dataset_registry = load_yaml(ROOT / "schemas" / "artifacts" / "dataset_keys.yaml")
    event_registry = load_yaml(ROOT / "schemas" / "events" / "event_type_registry.yaml")
    return {
        "governance": governance,
        "tool_registry": tool_registry,
        "permissions": permissions,
        "dataset_registry": dataset_registry,
        "event_registry": event_registry,
        "dataset_keys": {d["key"] for d in dataset_registry["datasets"]},
        "tool_classes": {t["id"] for t in tool_registry["tool_classes"]},
        "roles": {r["id"] for r in permissions["roles"]},
        "actions": {a["id"] for a in permissions["actions"]},
        "event_ids": {e["id"] for e in event_registry["event_types"]},
        "approval_responses": {r["id"] for r in governance["approval_response_verbs"]},
        "approval_outcomes": set(governance["approval_outcomes"]),
        "actor_types": [a["id"] for a in governance["actor_types"]],
    }


def validate_shared_vocab(indexes: dict[str, Any], collector: Collector) -> None:
    permissions = indexes["permissions"]
    collector.require("approval.grant" not in indexes["actions"], "permissions vocabulary no longer contains approval.grant")
    collector.require(
        set(indexes["governance"]["approval_permission_actions"]) <= indexes["actions"],
        "governance approval permission actions exist in permissions.yaml",
    )
    for rule in permissions["default_rules"]:
        collector.require(rule["role"] in indexes["roles"], f"default rule role exists: {rule['role']}")
        for action in rule["allow"]:
            collector.require(action in indexes["actions"], f"default rule action exists: {rule['role']} -> {action}")

    envelope_actor_enum = load_json(ROOT / "schemas" / "events" / "envelope.schema.json")["properties"]["actor"]["properties"]["type"]["enum"]
    artifact_actor_enum = load_json(ROOT / "schemas" / "artifacts" / "artifact_version_metadata.schema.json")["properties"]["created_by"]["properties"]["type"]["enum"]
    flag_actor_enum = load_json(ROOT / "schemas" / "runtime" / "flag.schema.json")["properties"]["created_by"]["properties"]["type"]["enum"]
    expected = indexes["actor_types"]
    collector.require(envelope_actor_enum == expected, "event envelope actor types match governance vocabulary")
    collector.require(artifact_actor_enum == expected, "artifact metadata actor types match governance vocabulary")
    collector.require(flag_actor_enum == expected, "flag schema actor types match governance vocabulary")


def validate_event_registry(indexes: dict[str, Any], collector: Collector) -> dict[str, Any]:
    registry = indexes["event_registry"]
    seen: set[str] = set()
    event_map: dict[str, Any] = {}
    for item in registry["event_types"]:
        eid = item["id"]
        if eid in seen:
            collector.fail(f"duplicate event id in registry: {eid}")
        seen.add(eid)
        event_map[eid] = item
        payload_path = ROOT / item["payload_schema"]
        collector.require(payload_path.exists(), f"payload schema exists for {eid}")
        if payload_path.exists():
            validate_schema_file(payload_path, collector)
    collector.ok("event registry has unique ids")
    return event_map


def validate_runtime_schema_coverage(collector: Collector) -> None:
    required = {
        "workflow_run": ROOT / "schemas/runtime/workflow_run.schema.json",
        "task_run": ROOT / "schemas/runtime/task_run.schema.json",
        "human_task": ROOT / "schemas/runtime/human_task.schema.json",
        "execution_session": ROOT / "schemas/runtime/execution_session.schema.json",
        "approval": ROOT / "schemas/runtime/approval.schema.json",
        "pointer": ROOT / "schemas/runtime/pointer.schema.json",
        "tool_execution": ROOT / "schemas/runtime/tool_execution.schema.json",
        "projection": ROOT / "schemas/runtime/projection.schema.json",
        "flag": ROOT / "schemas/runtime/flag.schema.json",
        "policy_decision": ROOT / "schemas/runtime/policy_decision.schema.json",
        "execution_spec": ROOT / "schemas/runtime/execution_spec.schema.json",
    }
    for name, path in required.items():
        collector.require(path.exists(), f"runtime schema exists for {name}")
        if path.exists():
            validate_schema_file(path, collector)


def validate_spawn_semantics(
    workflow_id: str,
    stages: list[dict[str, Any]],
    roles: set[str],
    collector: Collector,
) -> None:
    valid_policies = {"conditional_follow_on", "issue_scoped", "none"}
    stage_ids = {s["id"] for s in stages}
    for stage in stages:
        semantics = stage.get("semantics", {}) or {}
        policy = semantics.get("task_spawn_policy")
        if policy is None:
            continue
        collector.require(policy in valid_policies, f"task spawn policy recognized: {workflow_id} -> {stage['id']} -> {policy}")
        if policy == "none":
            continue
        budget = semantics.get("spawn_budget")
        rules = semantics.get("spawn_rules")
        collector.require(isinstance(budget, dict), f"spawn budget exists: {workflow_id} -> {stage['id']}")
        collector.require(isinstance(rules, list) and len(rules) > 0, f"spawn rules exist: {workflow_id} -> {stage['id']}")
        if isinstance(rules, list):
            for rule in rules:
                collector.require("id" in rule, f"spawn rule id exists: {workflow_id} -> {stage['id']}")
                collector.require("when" in rule, f"spawn rule condition exists: {workflow_id} -> {stage['id']}")
                collector.require(rule.get("target_stage_id") in stage_ids, f"spawn rule target stage exists: {workflow_id} -> {stage['id']} -> {rule.get('id')}")
                collector.require("task_kind" in rule, f"spawn rule task_kind exists: {workflow_id} -> {stage['id']} -> {rule.get('id')}")
                candidate_roles = rule.get("candidate_roles", [])
                collector.require(isinstance(candidate_roles, list) and len(candidate_roles) > 0, f"spawn rule candidate_roles exist: {workflow_id} -> {stage['id']} -> {rule.get('id')}")
                for role in candidate_roles:
                    collector.require(role in roles, f"spawn rule role exists: {workflow_id} -> {stage['id']} -> {rule.get('id')} -> {role}")


def validate_template_pack_examples(
    workflow_dir_name: str,
    artifact_map: dict[str, Any],
    collector: Collector,
) -> None:
    template_root = ROOT / "fixtures" / "workflows" / workflow_dir_name / "template_pack"
    docs_examples_root = ROOT / "docs" / "workflows" / workflow_dir_name / "v1" / "examples"
    if not template_root.exists():
        collector.require(
            docs_examples_root.exists(),
            f"examples exist when template pack is absent: docs/workflows/{workflow_dir_name}/v1/examples",
        )
        if docs_examples_root.exists():
            collector.ok(f"template-pack validation skipped (examples-only workflow): {workflow_dir_name}")
        return

    collector.require(template_root.exists(), f"template pack exists: fixtures/workflows/{workflow_dir_name}/template_pack")
    for items in artifact_map["artifact_sets"].values():
        for artifact in items:
            template_source = artifact.get("template_source")
            if not template_source:
                continue
            template_path = template_root / template_source
            collector.require(template_path.exists(), f"template source exists: {workflow_dir_name} -> {template_source}")
            if template_path.exists():
                example_name = template_path.name.replace("Template_EMPTY", "Example_COMPLETED")
                example_path = template_path.parent / example_name
                collector.require(example_path.exists(), f"completed example exists: {workflow_dir_name} -> {example_path.relative_to(template_root)}")


def validate_schedule_template_registry(indexes: dict[str, Any], collector: Collector) -> None:
    registry_path = ROOT / "fixtures" / "workflows" / "schedule_planning" / "template_registry.v1.yaml"
    if not registry_path.exists():
        collector.fail("schedule template registry is missing: fixtures/workflows/schedule_planning/template_registry.v1.yaml")
        return
    loaded = load_yaml(registry_path)
    if not isinstance(loaded, dict):
        collector.fail("schedule template registry must parse as an object")
        return
    registry = loaded.get("registry")
    collector.require(isinstance(registry, dict), "template registry has registry metadata object")
    if not isinstance(registry, dict):
        return
    templates = registry.get("templates")
    collector.require(isinstance(templates, list), "template registry has templates list")
    if not isinstance(templates, list):
        return

    collector.require(registry.get("workflow_id") == "schedule_planning.v1", "template registry workflow_id is schedule_planning.v1")
    collector.require(int(registry.get("version") or 0) >= 1, "template registry version is positive")

    seen_ids: set[str] = set()
    seen_variants: set[str] = set()
    for index, item in enumerate(templates):
        if not isinstance(item, dict):
            collector.fail(f"template registry entry must be object: index={index}")
            continue
        required = ["template_id", "stage_id", "dataset_key", "variant", "media_type", "source_path"]
        for field in required:
            collector.require(item.get(field) is not None, f"template registry field present: index={index} field={field}")
        template_id = str(item.get("template_id") or "")
        if template_id:
            collector.require(template_id not in seen_ids, f"template registry template_id unique: {template_id}")
            seen_ids.add(template_id)
        dataset_key = str(item.get("dataset_key") or "")
        if dataset_key:
            collector.require(dataset_key in indexes["dataset_keys"], f"template registry dataset key registered: {dataset_key}")
        variant = str(item.get("variant") or "")
        if variant:
            seen_variants.add(variant)
        source_path = str(item.get("source_path") or "")
        if source_path:
            collector.require((ROOT / source_path).exists(), f"template registry file exists: {source_path}")

    collector.require("empty" in seen_variants, "template registry includes empty variants")
    collector.require("completed_example" in seen_variants, "template registry includes completed_example variants")


def validate_schedule_runbook_assets(collector: Collector) -> None:
    runbook_root = ROOT / "fixtures" / "workflows" / "schedule_planning" / "runbooks"
    collector.require(
        runbook_root.exists(),
        "derived schedule runbook pack exists: fixtures/workflows/schedule_planning/runbooks",
    )
    required_files = [
        "00_DERIVED_Schedule_Agent_Runbook_Template.docx",
        "01_DERIVED_Schedule_Planning_Agentic_Workflow_Runbook_Example.docx",
        "02_DERIVED_Schedule_Tool_Registry_and_Policy_Matrix.xlsx",
        "03_DERIVED_Schedule_Approval_and_Decision_Log.xlsx",
        "README.md",
    ]
    for filename in required_files:
        collector.require(
            (runbook_root / filename).exists(),
            f"derived runbook asset exists: fixtures/workflows/schedule_planning/runbooks/{filename}",
        )
    readme_path = runbook_root / "README.md"
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8").lower()
        collector.require("derived output" in readme or "derived outputs" in readme, "runbook README marks assets as derived outputs")


def validate_workflow_packs(indexes: dict[str, Any], event_map: dict[str, Any], collector: Collector) -> None:
    contract_schema = ROOT / "schemas/workflows/workflow_contract.schema.json"
    artifact_map_schema = ROOT / "schemas/workflows/artifact_map.schema.json"
    decision_schema = ROOT / "schemas/agentic/decision_catalog.schema.json"
    profile_schema = ROOT / "schemas/agentic/execution_profile.schema.json"
    for schema_path in [contract_schema, artifact_map_schema, decision_schema, profile_schema]:
        validate_schema_file(schema_path, collector)

    for contract_path in workflow_pack_paths():
        wf_dir = contract_path.parent
        wf = validate_against_schema(contract_path, contract_schema, collector)
        artifact_map = validate_against_schema(wf_dir / "ARTIFACT_MAP.yaml", artifact_map_schema, collector)
        decisions = validate_against_schema(wf_dir / "DECISION_CATALOG.yaml", decision_schema, collector)
        profile = validate_against_schema(wf_dir / "EXECUTION_PROFILE.yaml", profile_schema, collector)

        stage_ids = {s["id"] for s in wf["stages"]}
        artifact_stage_ids = set(artifact_map["artifact_sets"].keys())
        collector.require(stage_ids >= artifact_stage_ids, f"{wf_dir.relative_to(ROOT)} artifact stages exist in workflow contract")

        contract_keys = {a["dataset_key"] for s in wf["stages"] for a in s["artifacts"]}
        map_keys = {a["key"] for items in artifact_map["artifact_sets"].values() for a in items}
        out_of_scope_keys = {a["key"] for items in artifact_map.get("out_of_scope", {}).values() for a in items}
        for key in sorted(contract_keys | map_keys | out_of_scope_keys):
            collector.require(key in indexes["dataset_keys"], f"dataset key registered: {key}")

        for d in decisions["catalog"]["decisions"]:
            collector.require(d["stage_id"] in stage_ids, f"decision stage exists: {d['id']}")
            collector.require(d["requested_from_role"] in indexes["roles"], f"decision role exists: {d['requested_from_role']}")
            for response in d["allowed_responses"]:
                collector.require(response in indexes["approval_responses"], f"decision response verb valid: {d['id']} -> {response}")
            for key in d["evidence_requirements"]["artifact_keys"]:
                collector.require(key in indexes["dataset_keys"], f"decision evidence key registered: {d['id']} -> {key}")

        decision_ids = {d["id"] for d in decisions["catalog"]["decisions"]}
        for stage in profile["profile"]["stages"]:
            collector.require(stage["stage_id"] in stage_ids, f"execution profile stage exists: {stage['stage_id']}")
            for tool in stage["allowed_tool_classes"]:
                collector.require(tool in indexes["tool_classes"], f"tool class registered: {stage['stage_id']} -> {tool}")
            for ref in stage["decision_refs"]:
                collector.require(ref in decision_ids, f"execution profile decision ref exists: {stage['stage_id']} -> {ref}")
            for key in stage["required_evidence_keys"]:
                collector.require(key in indexes["dataset_keys"], f"execution evidence key registered: {stage['stage_id']} -> {key}")

        inventory = wf["event_inventory"]
        all_required_events = set(inventory["platform_required"]) | set(inventory["workflow_required"])
        for event_id in sorted(all_required_events):
            collector.require(event_id in event_map, f"event inventory entry exists in registry: {wf['workflow']['id']} -> {event_id}")

        validate_spawn_semantics(wf["workflow"]["id"], wf["stages"], indexes["roles"], collector)
        validate_template_pack_examples(wf_dir.parent.name, artifact_map, collector)


def validate_workflow_family_surfaces(collector: Collector) -> None:
    workflow_family_schema = ROOT / "schemas" / "workflows" / "workflow_family.schema.json"
    partition_transform_schema = ROOT / "schemas" / "workflows" / "partition_transform_registry.schema.json"
    compiled_module_schema = ROOT / "schemas" / "workflows" / "compiled_module_definition.schema.json"
    compiled_edge_schema = ROOT / "schemas" / "workflows" / "compiled_family_edge.schema.json"
    state_ref_schema = ROOT / "schemas" / "workflows" / "state_ref.schema.json"
    method_package_schema = ROOT / "schemas" / "workflows" / "method_package.schema.json"
    compiled_stage_execution_spec_schema = ROOT / "schemas" / "workflows" / "compiled_stage_execution_spec.schema.json"
    activation_request_schema = ROOT / "schemas" / "workflows" / "activation_request.schema.json"
    for schema_path in (
        workflow_family_schema,
        partition_transform_schema,
        compiled_module_schema,
        compiled_edge_schema,
        state_ref_schema,
        method_package_schema,
        compiled_stage_execution_spec_schema,
        activation_request_schema,
    ):
        collector.require(schema_path.exists(), f"workflow family schema exists: {schema_path.relative_to(ROOT)}")
        if schema_path.exists():
            validate_schema_file(schema_path, collector)

    family_dir = ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1"
    family_path = family_dir / "WORKFLOW_FAMILY.yaml"
    transforms_path = family_dir / "PARTITION_TRANSFORMS.yaml"
    method_packages_path = family_dir / "METHOD_PACKAGES.yaml"
    collector.require(family_path.exists(), f"logistics family definition exists: {family_path.relative_to(ROOT)}")
    collector.require(transforms_path.exists(), f"partition transforms exist: {transforms_path.relative_to(ROOT)}")
    collector.require(method_packages_path.exists(), f"method package registry exists: {method_packages_path.relative_to(ROOT)}")
    if not family_path.exists() or not transforms_path.exists() or not method_packages_path.exists():
        return

    validate_against_schema(family_path, workflow_family_schema, collector)
    validate_against_schema(transforms_path, partition_transform_schema, collector)
    validate_against_schema(method_packages_path, method_package_schema, collector)

    try:
        compiled_once = compile_workflow_family(
            repo_root=ROOT,
            family_path=family_path,
            partition_transforms_path=transforms_path,
        )
        compiled_twice = compile_workflow_family(
            repo_root=ROOT,
            family_path=family_path,
            partition_transforms_path=transforms_path,
        )
    except DefinitionCompileError as exc:
        collector.fail(f"logistics family compilation failed: {exc}")
        return

    collector.require(
        compiled_once == compiled_twice,
        "workflow family compilation is deterministic for modules and edges",
    )

    module_validator = Draft202012Validator(load_json(compiled_module_schema))
    edge_validator = Draft202012Validator(load_json(compiled_edge_schema))
    for module in compiled_once.get("compiled_modules", []):
        errs = sorted(module_validator.iter_errors(module), key=lambda e: list(e.path))
        if errs:
            for err in errs:
                collector.fail(f"compiled module descriptor invalid: {err.message}")
        else:
            collector.ok(f"compiled module descriptor valid: {module['module_id']}")
    for edge in compiled_once.get("compiled_edges", []):
        errs = sorted(edge_validator.iter_errors(edge), key=lambda e: list(e.path))
        if errs:
            for err in errs:
                collector.fail(f"compiled edge descriptor invalid: {err.message}")
        else:
            collector.ok(f"compiled edge descriptor valid: {edge['edge_id']}")

    try:
        control_compiled_once = compile_control_layer(
            repo_root=ROOT,
            family_path=family_path,
            partition_transforms_path=transforms_path,
            method_packages_path=method_packages_path,
        )
        control_compiled_twice = compile_control_layer(
            repo_root=ROOT,
            family_path=family_path,
            partition_transforms_path=transforms_path,
            method_packages_path=method_packages_path,
        )
    except ControlCompileError as exc:
        collector.fail(f"logistics control-layer compilation failed: {exc}")
        return

    collector.require(
        control_compiled_once == control_compiled_twice,
        "control-layer compilation is deterministic for stage execution specs",
    )

    stage_spec_validator = Draft202012Validator(load_json(compiled_stage_execution_spec_schema))
    for stage_spec in control_compiled_once.get("compiled_stage_execution_specs", []):
        errs = sorted(stage_spec_validator.iter_errors(stage_spec), key=lambda e: list(e.path))
        if errs:
            for err in errs:
                collector.fail(f"compiled stage execution spec invalid: {err.message}")
        else:
            collector.ok(
                "compiled stage execution spec valid: "
                f"{stage_spec['module_id']}:{stage_spec['stage_id']}"
            )

    activation_request_example_path = (
        ROOT / "docs" / "examples" / "logistics_definitions" / "ACTIVATION_REQUEST.example.yaml"
    )
    collector.require(
        activation_request_example_path.exists(),
        "activation request example exists: docs/examples/logistics_definitions/ACTIVATION_REQUEST.example.yaml",
    )
    if activation_request_example_path.exists():
        validate_against_schema(
            activation_request_example_path,
            activation_request_schema,
            collector,
        )


def validate_task_index(collector: Collector) -> None:
    task_index_path = ROOT / "docs/planning/TASK_INDEX.md"
    content = task_index_path.read_text(encoding="utf-8").splitlines()
    indexed: set[str] = set()
    task_dir = ROOT / "codex/tasks"
    task_files = {p.name[:9]: p for p in task_dir.glob("TASK-*.md")}
    for line in content:
        if line.startswith("| TASK-"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            task_id = cols[0]
            indexed.add(task_id)
            collector.require(task_id in task_files, f"task index entry has file: {task_id}")
    for task_id in sorted(task_files):
        collector.require(task_id in indexed, f"task file indexed: {task_id}")


def validate_current_focus(collector: Collector) -> None:
    text = (ROOT / "docs/status/CURRENT_FOCUS.md").read_text(encoding="utf-8")
    task_dir = ROOT / "codex/tasks"
    task_files = {p.name[:9] for p in task_dir.glob("TASK-*.md")}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(tuple(f"{i}. TASK-" for i in range(1, 20))):
            task_id = line.split()[1]
            collector.require(task_id in task_files, f"current focus references task file: {task_id}")


def validate_traces(event_map: dict[str, Any], collector: Collector) -> None:
    envelope_schema = load_json(ROOT / "schemas/events/envelope.schema.json")
    envelope_validator = Draft202012Validator(envelope_schema)
    payload_validators = {eid: Draft202012Validator(load_json(ROOT / info["payload_schema"])) for eid, info in event_map.items()}
    trace_files = sorted((ROOT / "fixtures/workflows/schedule_planning/golden_event_traces").glob("*.jsonl"))
    for trace in trace_files:
        seen_ids: set[str] = set()
        lines = trace.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                collector.fail(f"{trace.relative_to(ROOT)}:{i} invalid JSON: {exc}")
                continue
            errs = sorted(envelope_validator.iter_errors(obj), key=lambda e: list(e.path))
            for err in errs:
                collector.fail(f"{trace.relative_to(ROOT)}:{i} envelope error: {err.message}")
            event_id = obj.get("event_id")
            if event_id:
                if event_id in seen_ids:
                    collector.fail(f"{trace.relative_to(ROOT)} duplicate event_id: {event_id}")
                seen_ids.add(event_id)
            event_type = obj.get("event_type")
            if event_type not in event_map:
                collector.fail(f"{trace.relative_to(ROOT)}:{i} unknown event type: {event_type}")
                continue
            req_types = set(event_map[event_type]["required_links"])
            actual_types = {l["type"] for l in obj.get("links", [])}
            missing = req_types - actual_types
            if missing:
                collector.fail(f"{trace.relative_to(ROOT)}:{i} missing required link types for {event_type}: {sorted(missing)}")
            payload_validator = payload_validators[event_type]
            p_errs = sorted(payload_validator.iter_errors(obj.get("payload", {})), key=lambda e: list(e.path))
            for err in p_errs:
                collector.fail(f"{trace.relative_to(ROOT)}:{i} payload error for {event_type}: {err.message}")
        collector.ok(f"trace validated: {trace.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces-only", action="store_true")
    parser.add_argument("--schemas-only", action="store_true")
    args = parser.parse_args()

    collector = Collector()
    indexes = build_indexes(collector)
    event_map = validate_event_registry(indexes, collector)

    if not args.traces_only:
        validate_shared_vocab(indexes, collector)
        validate_runtime_schema_coverage(collector)
        validate_workflow_packs(indexes, event_map, collector)
        validate_workflow_family_surfaces(collector)
        validate_schedule_template_registry(indexes, collector)
        validate_schedule_runbook_assets(collector)
        validate_task_index(collector)
        validate_current_focus(collector)
    if not args.schemas_only:
        validate_traces(event_map, collector)
    return collector.report()


if __name__ == "__main__":
    sys.exit(main())
