from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from onetruth.infrastructure.definitions.control_layer import (
    ControlCompileError,
    compile_control_layer,
)
from onetruth.infrastructure.definitions.family_compiler import (
    DefinitionCompileError,
    compile_workflow_family,
)
from scripts.repo_assurance.core import (
    AssuranceState,
    ROOT,
    load_json,
    load_yaml,
    validate_against_schema,
    validate_schema_file,
    workflow_pack_paths,
)


def run_schema_domain(state: AssuranceState) -> None:
    indexes = build_indexes(state)
    validate_event_registry_schema(state, indexes)
    validate_runtime_schema_coverage(state)
    validate_workflow_pack_documents(state)
    validate_workflow_family_schema_surfaces(state)


def run_governance_domain(state: AssuranceState) -> None:
    indexes = build_indexes(state)
    event_map = load_event_map(state, indexes)
    validate_shared_vocab(indexes, state)
    validate_workflow_pack_semantics(indexes, event_map, state)
    validate_workflow_family_semantics(state)
    validate_schedule_template_registry(indexes, state)
    validate_schedule_runbook_assets(state)


def build_indexes(state: AssuranceState) -> dict[str, Any]:
    if state.indexes is not None:
        return state.indexes
    governance = load_yaml(ROOT / "schemas" / "policy" / "governance_vocabulary.yaml")
    tool_registry = load_yaml(ROOT / "schemas" / "agentic" / "tool_class_registry.yaml")
    permissions = load_yaml(ROOT / "schemas" / "policy" / "permissions.yaml")
    dataset_registry = load_yaml(ROOT / "schemas" / "artifacts" / "dataset_keys.yaml")
    event_registry = load_yaml(ROOT / "schemas" / "events" / "event_type_registry.yaml")
    state.indexes = {
        "governance": governance,
        "tool_registry": tool_registry,
        "permissions": permissions,
        "dataset_registry": dataset_registry,
        "event_registry": event_registry,
        "dataset_keys": {item["key"] for item in dataset_registry["datasets"]},
        "tool_classes": {item["id"] for item in tool_registry["tool_classes"]},
        "roles": {item["id"] for item in permissions["roles"]},
        "actions": {item["id"] for item in permissions["actions"]},
        "event_ids": {item["id"] for item in event_registry["event_types"]},
        "approval_responses": {
            item["id"] for item in governance["approval_response_verbs"]
        },
        "approval_outcomes": set(governance["approval_outcomes"]),
        "actor_types": [item["id"] for item in governance["actor_types"]],
    }
    return state.indexes


def load_event_map(state: AssuranceState, indexes: dict[str, Any] | None = None) -> dict[str, Any]:
    if state.event_map is not None:
        return state.event_map
    loaded_indexes = indexes if indexes is not None else build_indexes(state)
    state.event_map = {
        item["id"]: item for item in loaded_indexes["event_registry"]["event_types"]
    }
    return state.event_map


def validate_event_registry_schema(
    state: AssuranceState,
    indexes: dict[str, Any],
) -> None:
    collector = state.collector
    registry = indexes["event_registry"]
    seen: set[str] = set()
    event_map: dict[str, Any] = {}
    for item in registry["event_types"]:
        event_id = item["id"]
        if event_id in seen:
            collector.fail(f"duplicate event id in registry: {event_id}")
        seen.add(event_id)
        event_map[event_id] = item
        payload_path = ROOT / item["payload_schema"]
        collector.require(payload_path.exists(), f"payload schema exists for {event_id}")
        if payload_path.exists():
            validate_schema_file(payload_path, collector)
    collector.ok("event registry has unique ids")
    state.event_map = event_map


def validate_runtime_schema_coverage(state: AssuranceState) -> None:
    collector = state.collector
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


def validate_workflow_pack_documents(state: AssuranceState) -> None:
    collector = state.collector
    contract_schema = ROOT / "schemas/workflows/workflow_contract.schema.json"
    artifact_map_schema = ROOT / "schemas/workflows/artifact_map.schema.json"
    decision_schema = ROOT / "schemas/agentic/decision_catalog.schema.json"
    profile_schema = ROOT / "schemas/agentic/execution_profile.schema.json"
    for schema_path in (
        contract_schema,
        artifact_map_schema,
        decision_schema,
        profile_schema,
    ):
        validate_schema_file(schema_path, collector)

    for contract_path in workflow_pack_paths():
        workflow_dir = contract_path.parent
        validate_against_schema(contract_path, contract_schema, collector)
        validate_against_schema(workflow_dir / "ARTIFACT_MAP.yaml", artifact_map_schema, collector)
        validate_against_schema(
            workflow_dir / "DECISION_CATALOG.yaml", decision_schema, collector
        )
        validate_against_schema(workflow_dir / "EXECUTION_PROFILE.yaml", profile_schema, collector)


def validate_workflow_family_schema_surfaces(state: AssuranceState) -> None:
    collector = state.collector
    schema_paths = (
        ROOT / "schemas" / "workflows" / "workflow_family.schema.json",
        ROOT / "schemas" / "workflows" / "partition_transform_registry.schema.json",
        ROOT / "schemas" / "workflows" / "compiled_module_definition.schema.json",
        ROOT / "schemas" / "workflows" / "compiled_family_edge.schema.json",
        ROOT / "schemas" / "workflows" / "state_ref.schema.json",
        ROOT / "schemas" / "workflows" / "method_package.schema.json",
        ROOT / "schemas" / "workflows" / "compiled_stage_execution_spec.schema.json",
        ROOT / "schemas" / "workflows" / "activation_request.schema.json",
    )
    for schema_path in schema_paths:
        collector.require(
            schema_path.exists(),
            f"workflow family schema exists: {schema_path.relative_to(ROOT)}",
        )
        if schema_path.exists():
            validate_schema_file(schema_path, collector)

    family_dir = ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1"
    family_path = family_dir / "WORKFLOW_FAMILY.yaml"
    transforms_path = family_dir / "PARTITION_TRANSFORMS.yaml"
    method_packages_path = family_dir / "METHOD_PACKAGES.yaml"
    collector.require(
        family_path.exists(),
        f"logistics family definition exists: {family_path.relative_to(ROOT)}",
    )
    collector.require(
        transforms_path.exists(),
        f"partition transforms exist: {transforms_path.relative_to(ROOT)}",
    )
    collector.require(
        method_packages_path.exists(),
        f"method package registry exists: {method_packages_path.relative_to(ROOT)}",
    )
    if not family_path.exists() or not transforms_path.exists() or not method_packages_path.exists():
        return

    validate_against_schema(
        family_path,
        ROOT / "schemas" / "workflows" / "workflow_family.schema.json",
        collector,
    )
    validate_against_schema(
        transforms_path,
        ROOT / "schemas" / "workflows" / "partition_transform_registry.schema.json",
        collector,
    )
    validate_against_schema(
        method_packages_path,
        ROOT / "schemas" / "workflows" / "method_package.schema.json",
        collector,
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
            ROOT / "schemas" / "workflows" / "activation_request.schema.json",
            collector,
        )


def validate_shared_vocab(indexes: dict[str, Any], state: AssuranceState) -> None:
    collector = state.collector
    permissions = indexes["permissions"]
    collector.require(
        "approval.grant" not in indexes["actions"],
        "permissions vocabulary no longer contains approval.grant",
    )
    collector.require(
        set(indexes["governance"]["approval_permission_actions"]) <= indexes["actions"],
        "governance approval permission actions exist in permissions.yaml",
    )
    for rule in permissions["default_rules"]:
        collector.require(
            rule["role"] in indexes["roles"],
            f"default rule role exists: {rule['role']}",
        )
        for action in rule["allow"]:
            collector.require(
                action in indexes["actions"],
                f"default rule action exists: {rule['role']} -> {action}",
            )

    envelope_actor_enum = load_json(ROOT / "schemas" / "events" / "envelope.schema.json")[
        "properties"
    ]["actor"]["properties"]["type"]["enum"]
    artifact_actor_enum = load_json(
        ROOT / "schemas" / "artifacts" / "artifact_version_metadata.schema.json"
    )["properties"]["created_by"]["properties"]["type"]["enum"]
    flag_actor_enum = load_json(ROOT / "schemas" / "runtime" / "flag.schema.json")[
        "properties"
    ]["created_by"]["properties"]["type"]["enum"]
    expected = indexes["actor_types"]
    collector.require(
        envelope_actor_enum == expected,
        "event envelope actor types match governance vocabulary",
    )
    collector.require(
        artifact_actor_enum == expected,
        "artifact metadata actor types match governance vocabulary",
    )
    collector.require(
        flag_actor_enum == expected,
        "flag schema actor types match governance vocabulary",
    )


def validate_spawn_semantics(
    workflow_id: str,
    stages: list[dict[str, Any]],
    roles: set[str],
    state: AssuranceState,
) -> None:
    collector = state.collector
    valid_policies = {"conditional_follow_on", "issue_scoped", "none"}
    stage_ids = {stage["id"] for stage in stages}
    for stage in stages:
        semantics = stage.get("semantics", {}) or {}
        policy = semantics.get("task_spawn_policy")
        if policy is None:
            continue
        collector.require(
            policy in valid_policies,
            f"task spawn policy recognized: {workflow_id} -> {stage['id']} -> {policy}",
        )
        if policy == "none":
            continue
        budget = semantics.get("spawn_budget")
        rules = semantics.get("spawn_rules")
        collector.require(
            isinstance(budget, dict),
            f"spawn budget exists: {workflow_id} -> {stage['id']}",
        )
        collector.require(
            isinstance(rules, list) and len(rules) > 0,
            f"spawn rules exist: {workflow_id} -> {stage['id']}",
        )
        if isinstance(rules, list):
            for rule in rules:
                collector.require(
                    "id" in rule,
                    f"spawn rule id exists: {workflow_id} -> {stage['id']}",
                )
                collector.require(
                    "when" in rule,
                    f"spawn rule condition exists: {workflow_id} -> {stage['id']}",
                )
                collector.require(
                    rule.get("target_stage_id") in stage_ids,
                    f"spawn rule target stage exists: {workflow_id} -> {stage['id']} -> {rule.get('id')}",
                )
                collector.require(
                    "task_kind" in rule,
                    f"spawn rule task_kind exists: {workflow_id} -> {stage['id']} -> {rule.get('id')}",
                )
                candidate_roles = rule.get("candidate_roles", [])
                collector.require(
                    isinstance(candidate_roles, list) and len(candidate_roles) > 0,
                    f"spawn rule candidate_roles exist: {workflow_id} -> {stage['id']} -> {rule.get('id')}",
                )
                for role in candidate_roles:
                    collector.require(
                        role in roles,
                        f"spawn rule role exists: {workflow_id} -> {stage['id']} -> {rule.get('id')} -> {role}",
                    )


def validate_template_pack_examples(
    workflow_dir_name: str,
    artifact_map: dict[str, Any],
    state: AssuranceState,
) -> None:
    collector = state.collector
    template_root = ROOT / "fixtures" / "workflows" / workflow_dir_name / "template_pack"
    docs_examples_root = ROOT / "docs" / "workflows" / workflow_dir_name / "v1" / "examples"
    if not template_root.exists():
        collector.require(
            docs_examples_root.exists(),
            f"examples exist when template pack is absent: docs/workflows/{workflow_dir_name}/v1/examples",
        )
        if docs_examples_root.exists():
            collector.ok(
                f"template-pack validation skipped (examples-only workflow): {workflow_dir_name}"
            )
        return

    collector.require(
        template_root.exists(),
        f"template pack exists: fixtures/workflows/{workflow_dir_name}/template_pack",
    )
    for items in artifact_map["artifact_sets"].values():
        for artifact in items:
            template_source = artifact.get("template_source")
            if not template_source:
                continue
            template_path = template_root / template_source
            collector.require(
                template_path.exists(),
                f"template source exists: {workflow_dir_name} -> {template_source}",
            )
            if template_path.exists():
                example_name = template_path.name.replace(
                    "Template_EMPTY", "Example_COMPLETED"
                )
                example_path = template_path.parent / example_name
                collector.require(
                    example_path.exists(),
                    f"completed example exists: {workflow_dir_name} -> {example_path.relative_to(template_root)}",
                )


def validate_workflow_pack_semantics(
    indexes: dict[str, Any],
    event_map: dict[str, Any],
    state: AssuranceState,
) -> None:
    collector = state.collector
    for contract_path in workflow_pack_paths():
        workflow_dir = contract_path.parent
        try:
            workflow = load_yaml(contract_path)
            artifact_map = load_yaml(workflow_dir / "ARTIFACT_MAP.yaml")
            decisions = load_yaml(workflow_dir / "DECISION_CATALOG.yaml")
            profile = load_yaml(workflow_dir / "EXECUTION_PROFILE.yaml")
            stage_ids = {stage["id"] for stage in workflow["stages"]}
            artifact_stage_ids = set(artifact_map["artifact_sets"].keys())
            collector.require(
                stage_ids >= artifact_stage_ids,
                f"{workflow_dir.relative_to(ROOT)} artifact stages exist in workflow contract",
            )

            contract_keys = {
                artifact["dataset_key"]
                for stage in workflow["stages"]
                for artifact in stage["artifacts"]
            }
            map_keys = {
                artifact["key"]
                for items in artifact_map["artifact_sets"].values()
                for artifact in items
            }
            out_of_scope_keys = {
                artifact["key"]
                for items in artifact_map.get("out_of_scope", {}).values()
                for artifact in items
            }
            for key in sorted(contract_keys | map_keys | out_of_scope_keys):
                collector.require(
                    key in indexes["dataset_keys"],
                    f"dataset key registered: {key}",
                )

            for decision in decisions["catalog"]["decisions"]:
                collector.require(
                    decision["stage_id"] in stage_ids,
                    f"decision stage exists: {decision['id']}",
                )
                collector.require(
                    decision["requested_from_role"] in indexes["roles"],
                    f"decision role exists: {decision['requested_from_role']}",
                )
                for response in decision["allowed_responses"]:
                    collector.require(
                        response in indexes["approval_responses"],
                        f"decision response verb valid: {decision['id']} -> {response}",
                    )
                for key in decision["evidence_requirements"]["artifact_keys"]:
                    collector.require(
                        key in indexes["dataset_keys"],
                        f"decision evidence key registered: {decision['id']} -> {key}",
                    )

            decision_ids = {decision["id"] for decision in decisions["catalog"]["decisions"]}
            for stage in profile["profile"]["stages"]:
                collector.require(
                    stage["stage_id"] in stage_ids,
                    f"execution profile stage exists: {stage['stage_id']}",
                )
                for tool in stage["allowed_tool_classes"]:
                    collector.require(
                        tool in indexes["tool_classes"],
                        f"tool class registered: {stage['stage_id']} -> {tool}",
                    )
                for ref in stage["decision_refs"]:
                    collector.require(
                        ref in decision_ids,
                        f"execution profile decision ref exists: {stage['stage_id']} -> {ref}",
                    )
                for key in stage["required_evidence_keys"]:
                    collector.require(
                        key in indexes["dataset_keys"],
                        f"execution evidence key registered: {stage['stage_id']} -> {key}",
                    )

            inventory = workflow["event_inventory"]
            all_required_events = set(inventory["platform_required"]) | set(
                inventory["workflow_required"]
            )
            for event_id in sorted(all_required_events):
                collector.require(
                    event_id in event_map,
                    f"event inventory entry exists in registry: {workflow['workflow']['id']} -> {event_id}",
                )

            validate_spawn_semantics(
                workflow["workflow"]["id"],
                workflow["stages"],
                indexes["roles"],
                state,
            )
            validate_template_pack_examples(workflow_dir.parent.name, artifact_map, state)
        except (KeyError, TypeError) as exc:
            collector.fail(
                f"{workflow_dir.relative_to(ROOT)} governance validation failed to load expected fields: {exc}"
            )


def validate_workflow_family_semantics(state: AssuranceState) -> None:
    collector = state.collector
    family_dir = ROOT / "docs" / "workflows" / "logistics_ops_family" / "v1"
    family_path = family_dir / "WORKFLOW_FAMILY.yaml"
    transforms_path = family_dir / "PARTITION_TRANSFORMS.yaml"
    method_packages_path = family_dir / "METHOD_PACKAGES.yaml"
    collector.require(
        family_path.exists(),
        f"logistics family definition exists: {family_path.relative_to(ROOT)}",
    )
    collector.require(
        transforms_path.exists(),
        f"partition transforms exist: {transforms_path.relative_to(ROOT)}",
    )
    collector.require(
        method_packages_path.exists(),
        f"method package registry exists: {method_packages_path.relative_to(ROOT)}",
    )
    if not family_path.exists() or not transforms_path.exists() or not method_packages_path.exists():
        return

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

    module_validator = Draft202012Validator(
        load_json(ROOT / "schemas" / "workflows" / "compiled_module_definition.schema.json")
    )
    edge_validator = Draft202012Validator(
        load_json(ROOT / "schemas" / "workflows" / "compiled_family_edge.schema.json")
    )
    for module in compiled_once.get("compiled_modules", []):
        errors = sorted(module_validator.iter_errors(module), key=lambda error: list(error.path))
        if errors:
            for error in errors:
                collector.fail(f"compiled module descriptor invalid: {error.message}")
        else:
            collector.ok(f"compiled module descriptor valid: {module['module_id']}")
    for edge in compiled_once.get("compiled_edges", []):
        errors = sorted(edge_validator.iter_errors(edge), key=lambda error: list(error.path))
        if errors:
            for error in errors:
                collector.fail(f"compiled edge descriptor invalid: {error.message}")
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

    stage_spec_validator = Draft202012Validator(
        load_json(
            ROOT / "schemas" / "workflows" / "compiled_stage_execution_spec.schema.json"
        )
    )
    for stage_spec in control_compiled_once.get("compiled_stage_execution_specs", []):
        errors = sorted(
            stage_spec_validator.iter_errors(stage_spec),
            key=lambda error: list(error.path),
        )
        if errors:
            for error in errors:
                collector.fail(f"compiled stage execution spec invalid: {error.message}")
        else:
            collector.ok(
                "compiled stage execution spec valid: "
                f"{stage_spec['module_id']}:{stage_spec['stage_id']}"
            )


def validate_schedule_template_registry(indexes: dict[str, Any], state: AssuranceState) -> None:
    collector = state.collector
    registry_path = (
        ROOT / "fixtures" / "workflows" / "schedule_planning" / "template_registry.v1.yaml"
    )
    if not registry_path.exists():
        collector.fail(
            "schedule template registry is missing: "
            "fixtures/workflows/schedule_planning/template_registry.v1.yaml"
        )
        return
    loaded = load_yaml(registry_path)
    if not isinstance(loaded, dict):
        collector.fail("schedule template registry must parse as an object")
        return
    registry = loaded.get("registry")
    collector.require(
        isinstance(registry, dict),
        "template registry has registry metadata object",
    )
    if not isinstance(registry, dict):
        return
    templates = registry.get("templates")
    collector.require(isinstance(templates, list), "template registry has templates list")
    if not isinstance(templates, list):
        return

    collector.require(
        registry.get("workflow_id") == "schedule_planning.v1",
        "template registry workflow_id is schedule_planning.v1",
    )
    collector.require(
        int(registry.get("version") or 0) >= 1,
        "template registry version is positive",
    )

    seen_ids: set[str] = set()
    seen_variants: set[str] = set()
    for index, item in enumerate(templates):
        if not isinstance(item, dict):
            collector.fail(f"template registry entry must be object: index={index}")
            continue
        required = [
            "template_id",
            "stage_id",
            "dataset_key",
            "variant",
            "media_type",
            "source_path",
        ]
        for field in required:
            collector.require(
                item.get(field) is not None,
                f"template registry field present: index={index} field={field}",
            )
        template_id = str(item.get("template_id") or "")
        if template_id:
            collector.require(
                template_id not in seen_ids,
                f"template registry template_id unique: {template_id}",
            )
            seen_ids.add(template_id)
        dataset_key = str(item.get("dataset_key") or "")
        if dataset_key:
            collector.require(
                dataset_key in indexes["dataset_keys"],
                f"template registry dataset key registered: {dataset_key}",
            )
        variant = str(item.get("variant") or "")
        if variant:
            seen_variants.add(variant)
        source_path = str(item.get("source_path") or "")
        if source_path:
            collector.require(
                (ROOT / source_path).exists(),
                f"template registry file exists: {source_path}",
            )

    collector.require("empty" in seen_variants, "template registry includes empty variants")
    collector.require(
        "completed_example" in seen_variants,
        "template registry includes completed_example variants",
    )


def validate_schedule_runbook_assets(state: AssuranceState) -> None:
    collector = state.collector
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
        collector.require(
            "derived output" in readme or "derived outputs" in readme,
            "runbook README marks assets as derived outputs",
        )
