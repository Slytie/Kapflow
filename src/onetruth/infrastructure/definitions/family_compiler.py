from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from onetruth.domain.partition_codec import (
    PARTITION_PATTERNS,
    PartitionCodecError,
    validate_transform_contract,
)


class DefinitionCompileError(ValueError):
    """Raised when authored family/workflow semantics are underspecified or inconsistent."""


FIRST_SLICE_DEFAULTS = {
    "daily_seed_shape": "one_logical_seed_per_service_date",
    "live_delta_semantics": "ordered_stream",
    "connectors_mode": "fixture_only",
    "partition_transform_policy": "typed_registry_required",
}

ORDERED_STREAM_DATASETS = {
    "dispatch.route_delta_intake.workbook",
    "dispatch.official_replan_delta.workbook",
    "planning.daily_dispatch_seed.workbook",
}

STREAM_KEY_BY_DATASET = {
    "dispatch.route_delta_intake.workbook": "intake",
    "dispatch.official_replan_delta.workbook": "delta",
    "planning.daily_dispatch_seed.workbook": "seed",
}

WORKFLOW_SOURCE_FILES = (
    "WORKFLOW_CONTRACT.yaml",
    "ARTIFACT_MAP.yaml",
    "DECISION_CATALOG.yaml",
    "EXECUTION_PROFILE.yaml",
)


def compile_workflow_family(
    *,
    repo_root: Path,
    family_path: Path,
    partition_transforms_path: Path,
) -> dict[str, Any]:
    family_doc = _load_yaml_object(family_path)
    family = _require_mapping(family_doc.get("family"), "family")
    family_id = _require_nonempty_string(family.get("id"), "family.id")
    family_version = _require_positive_int(family.get("version"), "family.version")
    first_slice_defaults = _extract_first_slice_defaults(family)

    transforms_doc = _load_yaml_object(partition_transforms_path)
    transform_registry = _require_mapping(transforms_doc.get("registry"), "registry")
    transforms_by_id = _index_transforms(transform_registry)

    module_specs = _require_sequence(family.get("modules"), "family.modules")
    edge_specs = _require_sequence(family.get("edges"), "family.edges")

    compiled_modules: list[dict[str, Any]] = []
    module_contexts: dict[str, dict[str, Any]] = {}
    for module_spec in sorted(module_specs, key=lambda item: str(item.get("module_id", ""))):
        compiled_module, context = _compile_module(
            repo_root=repo_root,
            module_spec=_require_mapping(module_spec, "family.modules[]"),
            defaults=first_slice_defaults,
        )
        module_id = compiled_module["module_id"]
        if module_id in module_contexts:
            raise DefinitionCompileError(f"duplicate module_id in family: {module_id}")
        module_contexts[module_id] = context
        compiled_modules.append(compiled_module)

    compiled_edges: list[dict[str, Any]] = []
    seen_edge_ids: set[str] = set()
    for edge_spec in sorted(edge_specs, key=lambda item: str(item.get("edge_id", ""))):
        compiled_edge = _compile_edge(
            family_id=family_id,
            family_version=family_version,
            edge_spec=_require_mapping(edge_spec, "family.edges[]"),
            transforms_by_id=transforms_by_id,
            module_contexts=module_contexts,
            defaults=first_slice_defaults,
        )
        if compiled_edge["edge_id"] in seen_edge_ids:
            raise DefinitionCompileError(f"duplicate edge_id in family: {compiled_edge['edge_id']}")
        seen_edge_ids.add(compiled_edge["edge_id"])
        compiled_edges.append(compiled_edge)

    return {
        "family_id": family_id,
        "family_version": family_version,
        "defaults": {
            "daily_seed_shape": first_slice_defaults["daily_seed_shape"],
            "live_delta_semantics": first_slice_defaults["live_delta_semantics"],
            "connectors_mode": first_slice_defaults["connectors_mode"],
        },
        "compiled_modules": compiled_modules,
        "compiled_edges": compiled_edges,
    }


def _compile_module(
    *,
    repo_root: Path,
    module_spec: dict[str, Any],
    defaults: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    module_id = _require_nonempty_string(module_spec.get("module_id"), "module.module_id")
    status = _require_nonempty_string(module_spec.get("status"), f"module[{module_id}].status")
    partition = _require_mapping(module_spec.get("partition"), f"module[{module_id}].partition")
    partition_kind = _require_nonempty_string(partition.get("kind"), f"module[{module_id}].partition.kind")
    activation_policy = _require_nonempty_string(
        partition.get("activation_policy"),
        f"module[{module_id}].partition.activation_policy",
    )

    workflow_pack_ref = _require_mapping(
        module_spec.get("workflow_pack_ref"),
        f"module[{module_id}].workflow_pack_ref",
    )
    workflow_id = _require_nonempty_string(
        workflow_pack_ref.get("workflow_id"),
        f"module[{module_id}].workflow_pack_ref.workflow_id",
    )
    workflow_version = _require_positive_int(
        workflow_pack_ref.get("version"),
        f"module[{module_id}].workflow_pack_ref.version",
    )
    workflow_path_rel = _require_nonempty_string(
        workflow_pack_ref.get("path"),
        f"module[{module_id}].workflow_pack_ref.path",
    )
    workflow_dir = (repo_root / workflow_path_rel).resolve()
    if not workflow_dir.exists():
        raise DefinitionCompileError(f"workflow pack path not found for module {module_id}: {workflow_path_rel}")

    workflow_contract_path = workflow_dir / "WORKFLOW_CONTRACT.yaml"
    execution_profile_path = workflow_dir / "EXECUTION_PROFILE.yaml"
    decision_catalog_path = workflow_dir / "DECISION_CATALOG.yaml"
    for file_name in WORKFLOW_SOURCE_FILES:
        if not (workflow_dir / file_name).exists():
            raise DefinitionCompileError(
                f"missing workflow source file for module {module_id}: {workflow_path_rel}/{file_name}"
            )

    workflow_contract = _load_yaml_object(workflow_contract_path)
    contract_workflow = _require_mapping(
        workflow_contract.get("workflow"),
        f"workflow_contract[{workflow_id}].workflow",
    )
    contract_workflow_id = _require_nonempty_string(
        contract_workflow.get("id"),
        f"workflow_contract[{workflow_id}].workflow.id",
    )
    if contract_workflow_id != workflow_id:
        raise DefinitionCompileError(
            f"workflow_id mismatch for module {module_id}: family={workflow_id}, contract={contract_workflow_id}"
        )
    contract_partition_key = _require_mapping(
        contract_workflow.get("partition_key"),
        f"workflow_contract[{workflow_id}].workflow.partition_key",
    )
    contract_partition_kind = _require_nonempty_string(
        contract_partition_key.get("name"),
        f"workflow_contract[{workflow_id}].workflow.partition_key.name",
    )
    if contract_partition_kind != partition_kind:
        raise DefinitionCompileError(
            f"partition kind mismatch for module {module_id}: module={partition_kind}, workflow={contract_partition_kind}"
        )

    execution_profile = _load_yaml_object(execution_profile_path)
    profile = _require_mapping(execution_profile.get("profile"), f"execution_profile[{workflow_id}].profile")
    profile_stages_raw = _require_sequence(profile.get("stages"), f"execution_profile[{workflow_id}].profile.stages")
    profile_stages_by_id = {
        _require_nonempty_string(item.get("stage_id"), f"execution_profile[{workflow_id}].stage_id"): _require_mapping(
            item, f"execution_profile[{workflow_id}].stage[]"
        )
        for item in profile_stages_raw
    }

    decision_catalog = _load_yaml_object(decision_catalog_path)
    decisions_raw = _require_sequence(
        _require_mapping(decision_catalog.get("catalog"), f"decision_catalog[{workflow_id}].catalog").get("decisions"),
        f"decision_catalog[{workflow_id}].catalog.decisions",
    )
    decision_ids = {
        _require_nonempty_string(item.get("id"), f"decision_catalog[{workflow_id}].decision.id")
        for item in decisions_raw
    }

    contract_stages = _require_sequence(workflow_contract.get("stages"), f"workflow_contract[{workflow_id}].stages")
    inputs: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    stage_lookup: dict[str, dict[str, Any]] = {}
    for stage_raw in contract_stages:
        stage = _require_mapping(stage_raw, f"workflow_contract[{workflow_id}].stage[]")
        stage_id = _require_nonempty_string(stage.get("id"), f"workflow_contract[{workflow_id}].stage.id")
        profile_stage = profile_stages_by_id.get(stage_id)
        if profile_stage is None:
            raise DefinitionCompileError(f"missing execution profile stage for {workflow_id}:{stage_id}")

        execution_pattern = _require_nonempty_string(
            profile_stage.get("execution_pattern"),
            f"execution_profile[{workflow_id}].{stage_id}.execution_pattern",
        )
        stage_decision_refs = [
            _require_nonempty_string(ref, f"execution_profile[{workflow_id}].{stage_id}.decision_ref")
            for ref in _require_sequence(
                profile_stage.get("decision_refs"),
                f"execution_profile[{workflow_id}].{stage_id}.decision_refs",
            )
        ]
        unknown_decisions = sorted(set(stage_decision_refs) - decision_ids)
        if unknown_decisions:
            raise DefinitionCompileError(
                f"unknown decision refs in {workflow_id}:{stage_id}: {unknown_decisions}"
            )
        stages.append(
            {
                "stage_id": stage_id,
                "execution_pattern": execution_pattern,
                "decision_refs": stage_decision_refs,
            }
        )
        stage_lookup[stage_id] = stage

        for artifact_raw in _require_sequence(stage.get("artifacts"), f"{workflow_id}:{stage_id}.artifacts"):
            artifact = _require_mapping(artifact_raw, f"{workflow_id}:{stage_id}.artifact[]")
            dataset_key = _require_nonempty_string(
                artifact.get("dataset_key"),
                f"{workflow_id}:{stage_id}.artifact.dataset_key",
            )
            artifact_role = _require_nonempty_string(
                artifact.get("role"),
                f"{workflow_id}:{stage_id}.artifact.role",
            )
            if artifact_role not in {"official_input", "official_output", "evidence"}:
                raise DefinitionCompileError(
                    f"unsupported artifact role in {workflow_id}:{stage_id}:{dataset_key}: {artifact_role}"
                )
            if artifact_role == "evidence":
                continue
            io_descriptor = {
                "dataset_key": dataset_key,
                "stage_id": stage_id,
                "artifact_role": artifact_role,
                "state_ref": _compiled_state_ref(partition_kind=partition_kind, dataset_key=dataset_key),
            }
            if artifact_role == "official_output":
                outputs.append(io_descriptor)
            else:
                inputs.append(io_descriptor)

    digest_payload = {
        "module_id": module_id,
        "workflow_id": workflow_id,
        "workflow_version": workflow_version,
        "status": status,
        "partition": {"kind": partition_kind, "activation_policy": activation_policy},
        "defaults": defaults,
        "inputs": inputs,
        "outputs": outputs,
        "stages": stages,
    }
    compiled_module = {
        "module_id": module_id,
        "source_workflow": {
            "workflow_id": workflow_id,
            "version": workflow_version,
            "path": workflow_path_rel,
        },
        "semantic_digest": _sha256_json(digest_payload),
        "status": status,
        "partition": {
            "kind": partition_kind,
            "activation_policy": activation_policy,
        },
        "defaults": {
            "daily_seed_shape": defaults["daily_seed_shape"],
            "live_delta_semantics": defaults["live_delta_semantics"],
            "connectors_mode": defaults["connectors_mode"],
        },
        "inputs": sorted(inputs, key=lambda item: (item["stage_id"], item["dataset_key"])),
        "outputs": sorted(outputs, key=lambda item: (item["stage_id"], item["dataset_key"])),
        "stages": stages,
    }
    context = {
        "module_id": module_id,
        "status": status,
        "partition_kind": partition_kind,
        "workflow_contract": workflow_contract,
        "stage_lookup": stage_lookup,
    }
    return compiled_module, context


def _compile_edge(
    *,
    family_id: str,
    family_version: int,
    edge_spec: dict[str, Any],
    transforms_by_id: dict[str, dict[str, Any]],
    module_contexts: dict[str, dict[str, Any]],
    defaults: dict[str, str],
) -> dict[str, Any]:
    edge_id = _require_nonempty_string(edge_spec.get("edge_id"), "edge.edge_id")
    source_module_id = _require_nonempty_string(edge_spec.get("source_module_id"), f"edge[{edge_id}].source_module_id")
    target_module_id = _require_nonempty_string(edge_spec.get("target_module_id"), f"edge[{edge_id}].target_module_id")
    status = _require_nonempty_string(edge_spec.get("status"), f"edge[{edge_id}].status")

    source_module = module_contexts.get(source_module_id)
    if source_module is None:
        raise DefinitionCompileError(f"edge {edge_id} references unknown source module {source_module_id}")
    target_module = module_contexts.get(target_module_id)
    if target_module is None:
        raise DefinitionCompileError(f"edge {edge_id} references unknown target module {target_module_id}")

    source_output_ref = _require_mapping(edge_spec.get("source_output_ref"), f"edge[{edge_id}].source_output_ref")
    source_dataset_key = _require_nonempty_string(
        source_output_ref.get("dataset_key"),
        f"edge[{edge_id}].source_output_ref.dataset_key",
    )
    source_stage_id = _require_nonempty_string(
        source_output_ref.get("stage_id"),
        f"edge[{edge_id}].source_output_ref.stage_id",
    )
    _assert_artifact_role(
        workflow_contract=source_module["workflow_contract"],
        stage_lookup=source_module["stage_lookup"],
        stage_id=source_stage_id,
        dataset_key=source_dataset_key,
        expected_role="official_output",
        edge_id=edge_id,
        edge_side="source_output_ref",
    )

    target_input_ref = _require_mapping(edge_spec.get("target_input_ref"), f"edge[{edge_id}].target_input_ref")
    target_dataset_key = _require_nonempty_string(
        target_input_ref.get("dataset_key"),
        f"edge[{edge_id}].target_input_ref.dataset_key",
    )
    target_stage_id = _require_nonempty_string(
        target_input_ref.get("stage_id"),
        f"edge[{edge_id}].target_input_ref.stage_id",
    )
    _assert_artifact_role(
        workflow_contract=target_module["workflow_contract"],
        stage_lookup=target_module["stage_lookup"],
        stage_id=target_stage_id,
        dataset_key=target_dataset_key,
        expected_role="official_input",
        edge_id=edge_id,
        edge_side="target_input_ref",
    )

    if status == "first_slice":
        for field_name in (
            "activation_policy",
            "handoff_mode",
            "idempotency_mode",
            "writer_mode",
            "compensation_mode",
        ):
            if field_name not in edge_spec:
                raise DefinitionCompileError(
                    f"first_slice edge {edge_id} must declare {field_name} explicitly"
                )

    activation_policy = _require_nonempty_string(
        edge_spec.get("activation_policy"),
        f"edge[{edge_id}].activation_policy",
    )
    handoff_mode = _require_nonempty_string(edge_spec.get("handoff_mode"), f"edge[{edge_id}].handoff_mode")
    idempotency_mode = _require_nonempty_string(
        edge_spec.get("idempotency_mode"),
        f"edge[{edge_id}].idempotency_mode",
    )
    writer_mode = _require_nonempty_string(edge_spec.get("writer_mode"), f"edge[{edge_id}].writer_mode")
    compensation_mode = _require_nonempty_string(
        edge_spec.get("compensation_mode"),
        f"edge[{edge_id}].compensation_mode",
    )

    transform_ref = _require_nonempty_string(
        edge_spec.get("partition_transform_ref"),
        f"edge[{edge_id}].partition_transform_ref",
    )
    transform = transforms_by_id.get(transform_ref)
    if transform is None:
        raise DefinitionCompileError(
            f"edge {edge_id} references unknown partition transform: {transform_ref}"
        )
    transform_source_kind = _require_nonempty_string(
        transform.get("source_kind"),
        f"transform[{transform_ref}].source_kind",
    )
    transform_target_kind = _require_nonempty_string(
        transform.get("target_kind"),
        f"transform[{transform_ref}].target_kind",
    )
    if (
        transform_source_kind != source_module["partition_kind"]
        or transform_target_kind != target_module["partition_kind"]
    ):
        raise DefinitionCompileError(
            "partition transform kind mismatch for edge "
            f"{edge_id}: transform=({transform_source_kind}->{transform_target_kind}), "
            f"modules=({source_module['partition_kind']}->{target_module['partition_kind']})"
        )
    try:
        validate_transform_contract(
            implementation_ref=_require_nonempty_string(
                transform.get("implementation_ref"),
                f"transform[{transform_ref}].implementation_ref",
            ),
            source_kind=transform_source_kind,
            target_kind=transform_target_kind,
            shape=_require_nonempty_string(transform.get("shape"), f"transform[{transform_ref}].shape"),
        )
    except PartitionCodecError as exc:
        raise DefinitionCompileError(str(exc)) from exc

    digest_payload = {
        "family_id": family_id,
        "family_version": family_version,
        "edge_id": edge_id,
        "source_module_id": source_module_id,
        "source_output_ref": {"dataset_key": source_dataset_key, "stage_id": source_stage_id},
        "target_module_id": target_module_id,
        "target_input_ref": {"dataset_key": target_dataset_key, "stage_id": target_stage_id},
        "partition_transform": transform,
        "activation_policy": activation_policy,
        "handoff_mode": handoff_mode,
        "idempotency_mode": idempotency_mode,
        "writer_mode": writer_mode,
        "compensation_mode": compensation_mode,
        "defaults": defaults,
    }

    return {
        "family_id": family_id,
        "family_version": family_version,
        "edge_id": edge_id,
        "semantic_digest": _sha256_json(digest_payload),
        "status": status,
        "source_module_id": source_module_id,
        "source_output_ref": {"dataset_key": source_dataset_key, "stage_id": source_stage_id},
        "target_module_id": target_module_id,
        "target_input_ref": {"dataset_key": target_dataset_key, "stage_id": target_stage_id},
        "partition_transform": {
            "id": _require_nonempty_string(transform.get("id"), f"transform[{transform_ref}].id"),
            "source_kind": transform_source_kind,
            "target_kind": transform_target_kind,
            "shape": _require_nonempty_string(transform.get("shape"), f"transform[{transform_ref}].shape"),
            "implementation_ref": _require_nonempty_string(
                transform.get("implementation_ref"),
                f"transform[{transform_ref}].implementation_ref",
            ),
            "deterministic": bool(transform.get("deterministic", False)),
        },
        "activation_policy": activation_policy,
        "handoff_mode": handoff_mode,
        "idempotency_mode": idempotency_mode,
        "writer_mode": writer_mode,
        "compensation_mode": compensation_mode,
        "defaults": {
            "daily_seed_shape": defaults["daily_seed_shape"],
            "live_delta_semantics": defaults["live_delta_semantics"],
            "connectors_mode": defaults["connectors_mode"],
        },
    }


def _assert_artifact_role(
    *,
    workflow_contract: dict[str, Any],
    stage_lookup: dict[str, dict[str, Any]],
    stage_id: str,
    dataset_key: str,
    expected_role: str,
    edge_id: str,
    edge_side: str,
) -> None:
    _ = workflow_contract
    stage = stage_lookup.get(stage_id)
    if stage is None:
        raise DefinitionCompileError(f"edge {edge_id} {edge_side} references unknown stage_id {stage_id}")
    artifacts = _require_sequence(stage.get("artifacts"), f"stage[{stage_id}].artifacts")
    matched_roles: list[str] = []
    for artifact_raw in artifacts:
        artifact = _require_mapping(artifact_raw, f"stage[{stage_id}].artifact[]")
        artifact_dataset_key = _require_nonempty_string(
            artifact.get("dataset_key"),
            f"stage[{stage_id}].artifact.dataset_key",
        )
        if artifact_dataset_key != dataset_key:
            continue
        matched_roles.append(
            _require_nonempty_string(
                artifact.get("role"),
                f"stage[{stage_id}].artifact.role",
            )
        )
    if not matched_roles:
        raise DefinitionCompileError(
            f"edge {edge_id} {edge_side} dataset_key not found in stage {stage_id}: {dataset_key}"
        )
    if len(matched_roles) > 1:
        raise DefinitionCompileError(
            f"edge {edge_id} {edge_side} dataset_key is ambiguous in stage {stage_id}: {dataset_key}"
        )
    actual_role = matched_roles[0]
    if actual_role != expected_role:
        raise DefinitionCompileError(
            f"edge {edge_id} {edge_side} must reference {expected_role}; got {actual_role} "
            f"for dataset {dataset_key} in {stage_id}"
        )


def _extract_first_slice_defaults(family: dict[str, Any]) -> dict[str, str]:
    defaults = _require_mapping(family.get("defaults"), "family.defaults")
    first_slice = _require_mapping(defaults.get("first_slice"), "family.defaults.first_slice")
    resolved = {}
    for key, expected_value in FIRST_SLICE_DEFAULTS.items():
        value = _require_nonempty_string(first_slice.get(key), f"family.defaults.first_slice.{key}")
        if value != expected_value:
            raise DefinitionCompileError(
                f"family.defaults.first_slice.{key} must be {expected_value}; got {value}"
            )
        resolved[key] = value
    return resolved


def _index_transforms(transform_registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    transforms_raw = _require_sequence(
        transform_registry.get("transforms"),
        "registry.transforms",
    )
    indexed: dict[str, dict[str, Any]] = {}
    for transform_raw in transforms_raw:
        transform = _require_mapping(transform_raw, "registry.transforms[]")
        transform_id = _require_nonempty_string(transform.get("id"), "registry.transforms[].id")
        source_kind = _require_nonempty_string(
            transform.get("source_kind"),
            f"registry.transforms[{transform_id}].source_kind",
        )
        target_kind = _require_nonempty_string(
            transform.get("target_kind"),
            f"registry.transforms[{transform_id}].target_kind",
        )
        if source_kind not in PARTITION_PATTERNS or target_kind not in PARTITION_PATTERNS:
            raise DefinitionCompileError(
                f"transform {transform_id} uses unsupported partition kinds: "
                f"{source_kind} -> {target_kind}"
            )
        deterministic = bool(transform.get("deterministic", False))
        if not deterministic:
            raise DefinitionCompileError(
                f"transform {transform_id} must be deterministic=true for fail-closed compilation"
            )
        if transform_id in indexed:
            raise DefinitionCompileError(f"duplicate transform id: {transform_id}")
        indexed[transform_id] = transform
    return indexed


def _compiled_state_ref(*, partition_kind: str, dataset_key: str) -> dict[str, Any]:
    registry_kind = "ordered_stream" if dataset_key in ORDERED_STREAM_DATASETS else "singleton"
    stream_key = STREAM_KEY_BY_DATASET.get(dataset_key, "latest")
    return {
        "kind": "registry",
        "address": {
            "tenant_id": "{{tenant_id}}",
            "domain_id": "{{domain_id}}",
            "dataset_key": dataset_key,
            "partition_kind": partition_kind,
            "partition_key": f"{{{{{partition_kind}}}}}",
            "stream_key": stream_key,
            "registry_kind": registry_kind,
        },
    }


def _load_yaml_object(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise DefinitionCompileError(f"expected YAML object at {path}")
    return loaded


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DefinitionCompileError(f"{field} must be an object")
    return value


def _require_sequence(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise DefinitionCompileError(f"{field} must be a list")
    return value


def _require_nonempty_string(value: Any, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise DefinitionCompileError(f"{field} must be a non-empty string")
    return text


def _require_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise DefinitionCompileError(f"{field} must be a positive integer")
    return value


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
