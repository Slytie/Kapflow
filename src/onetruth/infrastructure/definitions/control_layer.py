from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from onetruth.domain.pointer_address import PointerAddressError, PointerId
from onetruth.infrastructure.definitions.family_compiler import compile_workflow_family


class ControlCompileError(ValueError):
    """Raised when compiled control metadata is underspecified or inconsistent."""


CANONICAL_RUNTIME_OBJECTS = [
    "workflow_run",
    "task_run",
    "human_task",
    "execution_session",
    "tool_execution",
]
FIRST_SLICE_MODULE_STATUSES = {"first_slice"}
ENTRY_STAGE_ID = "Stage01"

TASK_KIND_BY_PATTERN = {
    "linear_chain": "work_item",
    "approval_gate": "approval_prep",
    "bounded_exception_loop": "exception_triage",
}

OWNER_MODE_BY_PATTERN = {
    "linear_chain": "agent",
    "approval_gate": "mixed",
    "bounded_exception_loop": "agent",
}
REFERENCE_MODULE_STATUS = "reference_only"


def compile_control_layer(
    *,
    repo_root: Path,
    family_path: Path,
    partition_transforms_path: Path,
    method_packages_path: Path,
) -> dict[str, Any]:
    compiled_family = compile_workflow_family(
        repo_root=repo_root,
        family_path=family_path,
        partition_transforms_path=partition_transforms_path,
    )
    method_registry = _load_method_package_registry(method_packages_path)
    method_packages_by_key = _index_method_packages(method_registry)

    compiled_stage_specs: list[dict[str, Any]] = []
    missing_required_method_packages: list[str] = []

    modules = compiled_family.get("compiled_modules", [])
    if not isinstance(modules, list):
        raise ControlCompileError("compiled family must expose compiled_modules list")

    for module in modules:
        module_id = _require_nonempty_string(module.get("module_id"), "compiled_module.module_id")
        module_status = _require_nonempty_string(module.get("status"), f"compiled_module[{module_id}].status")

        source_workflow = _require_mapping(module.get("source_workflow"), f"compiled_module[{module_id}].source_workflow")
        workflow_id = _require_nonempty_string(source_workflow.get("workflow_id"), f"compiled_module[{module_id}].source_workflow.workflow_id")
        workflow_path_rel = _require_nonempty_string(source_workflow.get("path"), f"compiled_module[{module_id}].source_workflow.path")

        partition = _require_mapping(module.get("partition"), f"compiled_module[{module_id}].partition")
        module_partition_kind = _require_nonempty_string(partition.get("kind"), f"compiled_module[{module_id}].partition.kind")
        module_activation_policy = _require_nonempty_string(
            partition.get("activation_policy"),
            f"compiled_module[{module_id}].partition.activation_policy",
        )

        execution_profile_path = (repo_root / workflow_path_rel / "EXECUTION_PROFILE.yaml").resolve()
        if not execution_profile_path.exists():
            raise ControlCompileError(
                f"missing execution profile for compiled module {module_id}: {workflow_path_rel}/EXECUTION_PROFILE.yaml"
            )
        execution_profile_stages = _load_execution_profile_stage_index(execution_profile_path)

        module_inputs = _require_sequence(module.get("inputs"), f"compiled_module[{module_id}].inputs")
        module_stages = _require_sequence(module.get("stages"), f"compiled_module[{module_id}].stages")
        for stage in module_stages:
            stage_mapping = _require_mapping(stage, f"compiled_module[{module_id}].stages[]")
            stage_id = _require_nonempty_string(stage_mapping.get("stage_id"), f"compiled_module[{module_id}].stage.stage_id")
            execution_pattern = _require_nonempty_string(
                stage_mapping.get("execution_pattern"),
                f"compiled_module[{module_id}].stage[{stage_id}].execution_pattern",
            )
            stage_key = (workflow_id, stage_id)
            method_package = method_packages_by_key.get(stage_key)
            if method_package is None and module_status in FIRST_SLICE_MODULE_STATUSES:
                missing_required_method_packages.append(f"{workflow_id}:{stage_id}")
                continue
            if method_package is None:
                continue

            profile_stage = execution_profile_stages.get(stage_id)
            if profile_stage is None:
                raise ControlCompileError(
                    f"missing execution profile stage for control compilation: {workflow_id}:{stage_id}"
                )
            if _require_nonempty_string(
                method_package.get("execution_pattern"),
                f"method_package[{workflow_id}:{stage_id}].execution_pattern",
            ) != execution_pattern:
                raise ControlCompileError(
                    f"method package execution_pattern mismatch for {workflow_id}:{stage_id}"
                )
            _validate_method_package(method_package, workflow_id=workflow_id, stage_id=stage_id)

            method_pin = _build_method_package_pin(method_package)
            required_input_dataset_keys = sorted(
                {
                    _require_nonempty_string(io.get("dataset_key"), f"compiled_module[{module_id}].inputs[].dataset_key")
                    for io in module_inputs
                    if (
                        _require_nonempty_string(io.get("stage_id"), "compiled_module.input.stage_id") == stage_id
                        and not _require_nonempty_string(
                            io.get("dataset_key"),
                            f"compiled_module[{module_id}].inputs[].dataset_key",
                        ).endswith(".doc")
                    )
                }
            )
            decision_refs = [
                _require_nonempty_string(ref, f"compiled_module[{module_id}].stage[{stage_id}].decision_refs[]")
                for ref in _require_sequence(stage_mapping.get("decision_refs"), f"compiled_module[{module_id}].stage[{stage_id}].decision_refs")
            ]
            required_evidence_keys = [
                _require_nonempty_string(key, f"execution_profile[{workflow_id}:{stage_id}].required_evidence_keys[]")
                for key in _require_sequence(
                    profile_stage.get("required_evidence_keys"),
                    f"execution_profile[{workflow_id}:{stage_id}].required_evidence_keys",
                )
            ]
            allowed_tool_classes = [
                _require_nonempty_string(tool, f"execution_profile[{workflow_id}:{stage_id}].allowed_tool_classes[]")
                for tool in _require_sequence(
                    profile_stage.get("allowed_tool_classes"),
                    f"execution_profile[{workflow_id}:{stage_id}].allowed_tool_classes",
                )
            ]
            side_effect_policy = _require_nonempty_string(
                profile_stage.get("side_effect_policy"),
                f"execution_profile[{workflow_id}:{stage_id}].side_effect_policy",
            )

            execution_spec_id = _build_execution_spec_id(
                workflow_id=workflow_id,
                stage_id=stage_id,
                method_package_id=_require_nonempty_string(method_package.get("id"), "method_package.id"),
                method_package_digest=_require_nonempty_string(method_pin.get("method_package_digest"), "method_pin.digest"),
            )

            runtime_bindings = {
                "workflow_run": {
                    "object_type": "workflow_run",
                    "partition_kind": module_partition_kind,
                    "activation_policy": module_activation_policy,
                },
                "task_run": {
                    "object_type": "task_run",
                    "stage_id": stage_id,
                    "task_kind_default": TASK_KIND_BY_PATTERN.get(execution_pattern, "work_item"),
                    "owner_mode": OWNER_MODE_BY_PATTERN.get(execution_pattern, "agent"),
                },
                "human_task": {
                    "object_type": "human_task",
                    "required": True,
                },
                "execution_session": {
                    "object_type": "execution_session",
                    "execution_spec_id": execution_spec_id,
                    "owner_mode": OWNER_MODE_BY_PATTERN.get(execution_pattern, "agent"),
                    "max_tool_calls": int(method_pin["stop_policy"]["max_tool_calls"]),
                    "no_progress_ticks": int(method_pin["stop_policy"]["no_progress_ticks"]),
                    "on_exhaustion": str(method_pin["stop_policy"]["on_exhaustion"]),
                },
                "tool_execution": {
                    "object_type": "tool_execution",
                    "allowed_tool_classes": allowed_tool_classes,
                    "side_effect_policy": side_effect_policy,
                },
            }

            stage_control_digest = _sha256_json(
                {
                    "family_id": compiled_family["family_id"],
                    "family_version": compiled_family["family_version"],
                    "module_id": module_id,
                    "module_status": module_status,
                    "workflow_id": workflow_id,
                    "stage_id": stage_id,
                    "execution_pattern": execution_pattern,
                    "module_partition_kind": module_partition_kind,
                    "module_activation_policy": module_activation_policy,
                    "required_input_dataset_keys": required_input_dataset_keys,
                    "required_evidence_keys": required_evidence_keys,
                    "decision_refs": decision_refs,
                    "method_package_pin": method_pin,
                    "runtime_bindings": runtime_bindings,
                }
            )

            compiled_stage_specs.append(
                {
                    "family_id": compiled_family["family_id"],
                    "family_version": compiled_family["family_version"],
                    "module_id": module_id,
                    "workflow_id": workflow_id,
                    "stage_id": stage_id,
                    "execution_pattern": execution_pattern,
                    "module_partition_kind": module_partition_kind,
                    "module_activation_policy": module_activation_policy,
                    "module_status": module_status,
                    "stage_control_digest": stage_control_digest,
                    "required_input_dataset_keys": required_input_dataset_keys,
                    "required_evidence_keys": required_evidence_keys,
                    "decision_refs": decision_refs,
                    "method_package_pin": method_pin,
                    "runtime_bindings": runtime_bindings,
                }
            )

    if missing_required_method_packages:
        missing_tokens = ", ".join(sorted(missing_required_method_packages))
        raise ControlCompileError(
            "missing method packages for first-slice stages: " + missing_tokens
        )

    compiled_stage_specs.sort(key=lambda item: (str(item["module_id"]), str(item["stage_id"])))

    return {
        "family_id": compiled_family["family_id"],
        "family_version": compiled_family["family_version"],
        "activation_model": "canonical_runtime_objects_only",
        "canonical_runtime_objects": list(CANONICAL_RUNTIME_OBJECTS),
        "compiled_stage_execution_specs": compiled_stage_specs,
    }


def resolve_stage_execution_spec(
    *,
    compiled_control: dict[str, Any],
    module_id: str,
    stage_id: str,
) -> dict[str, Any]:
    specs = _require_sequence(
        compiled_control.get("compiled_stage_execution_specs"),
        "compiled_control.compiled_stage_execution_specs",
    )
    for spec in specs:
        mapping = _require_mapping(spec, "compiled_control.stage_spec")
        if (
            _require_nonempty_string(mapping.get("module_id"), "stage_spec.module_id") == module_id
            and _require_nonempty_string(mapping.get("stage_id"), "stage_spec.stage_id") == stage_id
        ):
            return mapping
    raise ControlCompileError(f"missing compiled stage execution spec for {module_id}:{stage_id}")


def derive_execution_session_payload(
    *,
    compiled_control: dict[str, Any],
    module_id: str,
    stage_id: str,
    workflow_run_id: str,
    task_run_id: str,
    principal_actor: dict[str, Any],
    idempotency_key: str,
    state: str = "WAITING_POLICY",
    execution_session_id: str | None = None,
    actor_type: str = "system",
    actor_id: str = "system:control-layer",
) -> dict[str, Any]:
    stage_spec = resolve_stage_execution_spec(
        compiled_control=compiled_control,
        module_id=module_id,
        stage_id=stage_id,
    )
    runtime_bindings = _require_mapping(stage_spec.get("runtime_bindings"), "stage_spec.runtime_bindings")
    execution_binding = _require_mapping(runtime_bindings.get("execution_session"), "stage_spec.runtime_bindings.execution_session")
    execution_spec_id = _require_nonempty_string(
        execution_binding.get("execution_spec_id"),
        "execution_spec_id",
    )
    stage_control_digest = _require_nonempty_string(
        stage_spec.get("stage_control_digest"),
        "stage_spec.stage_control_digest",
    )
    method_pin = _require_mapping(stage_spec.get("method_package_pin"), "stage_spec.method_package_pin")
    method_package_id = _require_nonempty_string(
        method_pin.get("method_package_id"),
        "stage_spec.method_package_pin.method_package_id",
    )
    method_package_version = int(method_pin.get("method_package_version"))
    method_package_digest = _require_nonempty_string(
        method_pin.get("method_package_digest"),
        "stage_spec.method_package_pin.method_package_digest",
    )

    budget = {
        "max_tool_calls": int(execution_binding["max_tool_calls"]),
        "no_progress_ticks": int(execution_binding["no_progress_ticks"]),
    }
    execution_semantics = {
        "compiled_execution_spec": {
            "schema_version": "1.0",
            "kind": "compiled_stage_execution_spec",
            "family_id": _require_nonempty_string(stage_spec.get("family_id"), "stage_spec.family_id"),
            "family_version": int(stage_spec.get("family_version")),
            "module_id": _require_nonempty_string(stage_spec.get("module_id"), "stage_spec.module_id"),
            "workflow_id": _require_nonempty_string(stage_spec.get("workflow_id"), "stage_spec.workflow_id"),
            "stage_id": _require_nonempty_string(stage_spec.get("stage_id"), "stage_spec.stage_id"),
            "execution_pattern": _require_nonempty_string(
                stage_spec.get("execution_pattern"),
                "stage_spec.execution_pattern",
            ),
            "module_partition_kind": _require_nonempty_string(
                stage_spec.get("module_partition_kind"),
                "stage_spec.module_partition_kind",
            ),
            "module_activation_policy": _require_nonempty_string(
                stage_spec.get("module_activation_policy"),
                "stage_spec.module_activation_policy",
            ),
            "module_status": _require_nonempty_string(stage_spec.get("module_status"), "stage_spec.module_status"),
            "execution_spec_id": execution_spec_id,
            "stage_control_digest": stage_control_digest,
            "method_package_pin": method_pin,
            "required_input_dataset_keys": [
                _require_nonempty_string(
                    key,
                    "stage_spec.required_input_dataset_keys[]",
                )
                for key in _require_sequence(
                    stage_spec.get("required_input_dataset_keys"),
                    "stage_spec.required_input_dataset_keys",
                )
            ],
            "required_evidence_keys": [
                _require_nonempty_string(
                    key,
                    "stage_spec.required_evidence_keys[]",
                )
                for key in _require_sequence(
                    stage_spec.get("required_evidence_keys"),
                    "stage_spec.required_evidence_keys",
                )
            ],
            "decision_refs": [
                _require_nonempty_string(ref, "stage_spec.decision_refs[]")
                for ref in _require_sequence(stage_spec.get("decision_refs"), "stage_spec.decision_refs")
            ],
            "runtime_bindings": runtime_bindings,
        },
        "compile_source_manifest": {
            "schema_version": "1.0",
            "kind": "execution_compile_source_manifest",
            "source_chain": {
                "authority_model": "one_truth_substrate",
                "activation_model": _require_nonempty_string(
                    compiled_control.get("activation_model"),
                    "compiled_control.activation_model",
                ),
                "family_id": _require_nonempty_string(stage_spec.get("family_id"), "stage_spec.family_id"),
                "family_version": int(stage_spec.get("family_version")),
                "module_id": _require_nonempty_string(stage_spec.get("module_id"), "stage_spec.module_id"),
                "workflow_id": _require_nonempty_string(stage_spec.get("workflow_id"), "stage_spec.workflow_id"),
                "stage_id": _require_nonempty_string(stage_spec.get("stage_id"), "stage_spec.stage_id"),
                "execution_spec_id": execution_spec_id,
            },
            "pins": {
                "stage_control_digest": stage_control_digest,
                "method_package_id": method_package_id,
                "method_package_version": method_package_version,
                "method_package_digest": method_package_digest,
            },
        },
    }
    payload: dict[str, Any] = {
        "workflow_run_id": _require_nonempty_string(workflow_run_id, "workflow_run_id"),
        "task_run_id": _require_nonempty_string(task_run_id, "task_run_id"),
        "execution_spec_id": execution_spec_id,
        "owner_mode": _require_nonempty_string(execution_binding.get("owner_mode"), "owner_mode"),
        "state": _require_nonempty_string(state, "state"),
        "principal_actor": _require_mapping(principal_actor, "principal_actor"),
        "budget": budget,
        "execution_semantics": execution_semantics,
        "idempotency_key": _require_nonempty_string(idempotency_key, "idempotency_key"),
        "actor_type": _require_nonempty_string(actor_type, "actor_type"),
        "actor_id": _require_nonempty_string(actor_id, "actor_id"),
    }
    if execution_session_id is not None:
        payload["execution_session_id"] = _require_nonempty_string(
            execution_session_id,
            "execution_session_id",
        )
    return payload


def compile_reference_stage_runtime(
    *,
    repo_root: Path,
    execution_profile_path: Path,
    workflow_id: str,
    module_id: str,
    stage_id: str,
    runtime_tool_binding_id: str,
    workflow_run_id: str,
    task_run_id: str,
    principal_actor: dict[str, Any],
    idempotency_key: str,
    state: str = "WAITING_POLICY",
    execution_session_id: str | None = None,
    actor_type: str = "system",
    actor_id: str = "system:control-layer",
    budget_override: Mapping[str, Any] | None = None,
    tool_class_registry_path: Path | None = None,
) -> dict[str, Any]:
    execution_profile_doc = _load_yaml_object(execution_profile_path)
    profile = _require_mapping(
        execution_profile_doc.get("profile"),
        f"execution_profile[{execution_profile_path}].profile",
    )
    profile_workflow_id = _require_nonempty_string(
        profile.get("workflow_id"),
        f"execution_profile[{execution_profile_path}].profile.workflow_id",
    )
    if profile_workflow_id != workflow_id:
        raise ControlCompileError(
            "execution profile workflow_id mismatch: "
            f"{profile_workflow_id} != {workflow_id}"
        )
    profile_stage = _load_execution_profile_stage_index(execution_profile_path).get(stage_id)
    if profile_stage is None:
        raise ControlCompileError(
            f"missing execution profile stage for reference runtime compilation: {workflow_id}:{stage_id}"
        )

    registry_path = tool_class_registry_path or (
        repo_root / "schemas" / "agentic" / "tool_class_registry.yaml"
    )
    runtime_tool_binding = _resolve_runtime_tool_binding(
        registry_path=registry_path,
        workflow_id=workflow_id,
        stage_id=stage_id,
        runtime_tool_binding_id=runtime_tool_binding_id,
        allowed_tool_classes=_stage_allowed_tool_classes(profile_stage, workflow_id=workflow_id, stage_id=stage_id),
    )

    execution_pattern = _require_nonempty_string(
        profile_stage.get("execution_pattern"),
        f"execution_profile[{workflow_id}:{stage_id}].execution_pattern",
    )
    side_effect_policy = _require_nonempty_string(
        profile_stage.get("side_effect_policy"),
        f"execution_profile[{workflow_id}:{stage_id}].side_effect_policy",
    )
    stop_rules = _validated_stop_rules(
        profile_stage.get("stop_rules"),
        workflow_id=workflow_id,
        stage_id=stage_id,
    )
    required_evidence_keys = [
        _require_nonempty_string(
            key,
            f"execution_profile[{workflow_id}:{stage_id}].required_evidence_keys[]",
        )
        for key in _require_sequence(
            profile_stage.get("required_evidence_keys"),
            f"execution_profile[{workflow_id}:{stage_id}].required_evidence_keys",
        )
    ]
    decision_refs = [
        _require_nonempty_string(
            ref,
            f"execution_profile[{workflow_id}:{stage_id}].decision_refs[]",
        )
        for ref in _require_sequence(
            profile_stage.get("decision_refs"),
            f"execution_profile[{workflow_id}:{stage_id}].decision_refs",
        )
    ]
    projections = [
        _require_nonempty_string(
            projection,
            f"execution_profile[{workflow_id}:{stage_id}].projections[]",
        )
        for projection in _require_sequence(
            profile_stage.get("projections"),
            f"execution_profile[{workflow_id}:{stage_id}].projections",
        )
    ]

    runtime_budget = _build_runtime_budget(
        stop_rules=stop_rules,
        budget_override=budget_override,
        workflow_id=workflow_id,
        stage_id=stage_id,
    )
    execution_binding = {
        "object_type": "execution_session",
        "execution_spec_id": "",
        "owner_mode": OWNER_MODE_BY_PATTERN.get(execution_pattern, "agent"),
        "max_tool_calls": int(runtime_budget["max_tool_calls"]),
        "no_progress_ticks": int(runtime_budget.get("no_progress_ticks", stop_rules["no_progress_ticks"])),
        "on_exhaustion": str(stop_rules["on_exhaustion"]),
    }
    tool_execution_binding = {
        "object_type": "tool_execution",
        "allowed_tool_classes": _stage_allowed_tool_classes(
            profile_stage,
            workflow_id=workflow_id,
            stage_id=stage_id,
        ),
        "side_effect_policy": side_effect_policy,
        "runtime_tool_binding_id": runtime_tool_binding_id,
        "runtime_tool_class": _require_nonempty_string(
            runtime_tool_binding.get("runtime_tool_class"),
            f"runtime_tool_binding[{runtime_tool_binding_id}].runtime_tool_class",
        ),
        "runtime_tool_name": _require_nonempty_string(
            runtime_tool_binding.get("runtime_tool_name"),
            f"runtime_tool_binding[{runtime_tool_binding_id}].runtime_tool_name",
        ),
    }
    stage_runtime = {
        "control_source": "execution_profile_reference",
        "module_id": _require_nonempty_string(module_id, "module_id"),
        "workflow_id": workflow_id,
        "stage_id": stage_id,
        "execution_pattern": execution_pattern,
        "module_status": REFERENCE_MODULE_STATUS,
        "required_input_dataset_keys": [],
        "required_evidence_keys": required_evidence_keys,
        "decision_refs": decision_refs,
        "projections": projections,
        "side_effect_policy": side_effect_policy,
        "authored_stop_rules": stop_rules,
        "runtime_budget": runtime_budget,
        "runtime_tool_binding": runtime_tool_binding,
        "runtime_bindings": {
            "execution_session": execution_binding,
            "tool_execution": tool_execution_binding,
        },
    }
    stage_control_digest = _sha256_json(stage_runtime)
    execution_spec_id = _build_reference_execution_spec_id(
        workflow_id=workflow_id,
        stage_id=stage_id,
        stage_control_digest=stage_control_digest,
    )
    execution_binding["execution_spec_id"] = execution_spec_id

    execution_profile_rel = _path_relative_to_repo(
        repo_root=repo_root,
        path=execution_profile_path,
    )
    registry_rel = _path_relative_to_repo(repo_root=repo_root, path=registry_path)
    execution_semantics = {
        "compiled_execution_spec": {
            "schema_version": "1.0",
            "kind": "compiled_execution_spec",
            "control_source": "execution_profile_reference",
            "module_id": _require_nonempty_string(module_id, "module_id"),
            "workflow_id": workflow_id,
            "stage_id": stage_id,
            "execution_pattern": execution_pattern,
            "module_status": REFERENCE_MODULE_STATUS,
            "execution_spec_id": execution_spec_id,
            "stage_control_digest": stage_control_digest,
            "required_input_dataset_keys": [],
            "required_evidence_keys": required_evidence_keys,
            "decision_refs": decision_refs,
            "projections": projections,
            "side_effect_policy": side_effect_policy,
            "authored_stop_rules": stop_rules,
            "runtime_budget": runtime_budget,
            "runtime_tool_binding": runtime_tool_binding,
            "runtime_bindings": {
                "execution_session": dict(execution_binding),
                "tool_execution": dict(tool_execution_binding),
            },
        },
        "compile_source_manifest": {
            "schema_version": "1.0",
            "kind": "execution_compile_source_manifest",
            "source_chain": {
                "authority_model": "one_truth_substrate",
                "control_source": "execution_profile_reference",
                "module_id": _require_nonempty_string(module_id, "module_id"),
                "workflow_id": workflow_id,
                "stage_id": stage_id,
                "execution_spec_id": execution_spec_id,
            },
            "source_refs": [
                {
                    "source_kind": "execution_profile",
                    "path": execution_profile_rel,
                },
                {
                    "source_kind": "tool_class_registry",
                    "path": registry_rel,
                    "runtime_tool_binding_id": runtime_tool_binding_id,
                },
            ],
            "pins": {
                "stage_control_digest": stage_control_digest,
                "runtime_tool_binding_id": runtime_tool_binding_id,
                "runtime_tool_class": tool_execution_binding["runtime_tool_class"],
            },
        },
    }
    payload: dict[str, Any] = {
        "workflow_run_id": _require_nonempty_string(workflow_run_id, "workflow_run_id"),
        "task_run_id": _require_nonempty_string(task_run_id, "task_run_id"),
        "execution_spec_id": execution_spec_id,
        "owner_mode": _require_nonempty_string(
            execution_binding.get("owner_mode"),
            "execution_binding.owner_mode",
        ),
        "state": _require_nonempty_string(state, "state"),
        "principal_actor": _require_mapping(principal_actor, "principal_actor"),
        "budget": runtime_budget,
        "execution_semantics": execution_semantics,
        "idempotency_key": _require_nonempty_string(idempotency_key, "idempotency_key"),
        "actor_type": _require_nonempty_string(actor_type, "actor_type"),
        "actor_id": _require_nonempty_string(actor_id, "actor_id"),
    }
    if execution_session_id is not None:
        payload["execution_session_id"] = _require_nonempty_string(
            execution_session_id,
            "execution_session_id",
        )
    return {
        "execution_session_payload": payload,
        "runtime_tool_binding": runtime_tool_binding,
        "stage_runtime": {
            **stage_runtime,
            "execution_spec_id": execution_spec_id,
            "stage_control_digest": stage_control_digest,
        },
    }


def validate_activation_request(
    *,
    compiled_control: dict[str, Any],
    activation_request_document: dict[str, Any],
) -> dict[str, Any]:
    request_container = _require_mapping(activation_request_document, "activation_request_document")
    request = _require_mapping(
        request_container.get("activation_request"),
        "activation_request_document.activation_request",
    )

    request_family_id = _require_nonempty_string(request.get("family_id"), "activation_request.family_id")
    expected_family_id = _require_nonempty_string(compiled_control.get("family_id"), "compiled_control.family_id")
    if request_family_id != expected_family_id:
        raise ControlCompileError(
            f"activation request family_id mismatch: request={request_family_id}, compiled={expected_family_id}"
        )

    target_module_id = _require_nonempty_string(request.get("target_module_id"), "activation_request.target_module_id")
    target_stage_id = _require_nonempty_string(request.get("target_stage_id", ENTRY_STAGE_ID), "activation_request.target_stage_id")
    stage_spec = resolve_stage_execution_spec(
        compiled_control=compiled_control,
        module_id=target_module_id,
        stage_id=target_stage_id,
    )

    target_partition = _require_mapping(request.get("target_partition"), "activation_request.target_partition")
    target_partition_kind = _require_nonempty_string(target_partition.get("kind"), "activation_request.target_partition.kind")
    target_partition_key = _require_nonempty_string(target_partition.get("key"), "activation_request.target_partition.key")
    expected_partition_kind = _require_nonempty_string(
        stage_spec.get("module_partition_kind"),
        "stage_spec.module_partition_kind",
    )
    if target_partition_kind != expected_partition_kind:
        raise ControlCompileError(
            "activation request partition kind mismatch: "
            f"request={target_partition_kind}, stage_spec={expected_partition_kind}"
        )

    governance_context = _require_mapping(
        request.get("governance_context"),
        "activation_request.governance_context",
    )
    tenant_id = _require_nonempty_string(governance_context.get("tenant_id"), "activation_request.governance_context.tenant_id")
    domain_id = _require_nonempty_string(governance_context.get("domain_id"), "activation_request.governance_context.domain_id")

    required_input_rows = _require_sequence(request.get("required_inputs"), "activation_request.required_inputs")
    provided_dataset_keys: set[str] = set()
    for row in required_input_rows:
        binding = _require_mapping(row, "activation_request.required_inputs[]")
        _require_nonempty_string(binding.get("binding_key"), "activation_request.required_inputs[].binding_key")
        expected_generation = binding.get("expected_generation")
        if not isinstance(expected_generation, int) or expected_generation < 0:
            raise ControlCompileError("activation_request.required_inputs[].expected_generation must be a non-negative integer")

        state_ref = _require_mapping(binding.get("state_ref"), "activation_request.required_inputs[].state_ref")
        kind = _require_nonempty_string(state_ref.get("kind"), "activation_request.required_inputs[].state_ref.kind")
        if kind != "registry":
            raise ControlCompileError("activation_request.required_inputs[].state_ref.kind must be registry")

        pointer_id_value = _require_nonempty_string(
            state_ref.get("pointer_id"),
            "activation_request.required_inputs[].state_ref.pointer_id",
        )
        try:
            address = PointerId.parse(pointer_id_value).to_address()
        except PointerAddressError as exc:
            raise ControlCompileError(f"invalid activation_request pointer_id: {pointer_id_value}") from exc

        if address.tenant_id != tenant_id or address.domain_id != domain_id:
            raise ControlCompileError(
                "activation_request pointer scope mismatch: "
                f"{address.tenant_id}/{address.domain_id} != {tenant_id}/{domain_id}"
            )
        if address.partition_ref.key != target_partition_kind:
            raise ControlCompileError(
                "activation_request pointer partition kind mismatch: "
                f"{address.partition_ref.key} != {target_partition_kind}"
            )
        if address.partition_ref.value != target_partition_key:
            raise ControlCompileError(
                "activation_request pointer partition key mismatch: "
                f"{address.partition_ref.value} != {target_partition_key}"
            )

        provided_dataset_keys.add(address.dataset_key)

    required_dataset_keys = {
        _require_nonempty_string(key, "stage_spec.required_input_dataset_keys[]")
        for key in _require_sequence(
            stage_spec.get("required_input_dataset_keys"),
            "stage_spec.required_input_dataset_keys",
        )
    }
    missing_dataset_keys = sorted(required_dataset_keys - provided_dataset_keys)
    if missing_dataset_keys:
        raise ControlCompileError(
            "activation request is missing required dataset bindings: "
            + ", ".join(missing_dataset_keys)
        )

    execution_binding = _require_mapping(
        _require_mapping(stage_spec.get("runtime_bindings"), "stage_spec.runtime_bindings").get("execution_session"),
        "stage_spec.runtime_bindings.execution_session",
    )

    return {
        "request_id": _require_nonempty_string(request.get("request_id"), "activation_request.request_id"),
        "family_id": request_family_id,
        "target_module_id": target_module_id,
        "target_workflow_id": _require_nonempty_string(stage_spec.get("workflow_id"), "stage_spec.workflow_id"),
        "target_stage_id": target_stage_id,
        "target_partition": {
            "kind": target_partition_kind,
            "key": target_partition_key,
        },
        "execution_spec_id": _require_nonempty_string(execution_binding.get("execution_spec_id"), "execution_binding.execution_spec_id"),
        "required_input_dataset_keys": sorted(required_dataset_keys),
        "provided_input_dataset_keys": sorted(provided_dataset_keys),
        "idempotency_key": _require_nonempty_string(request.get("idempotency_key"), "activation_request.idempotency_key"),
    }


def _load_execution_profile_stage_index(path: Path) -> dict[str, dict[str, Any]]:
    loaded = _load_yaml_object(path)
    profile = _require_mapping(loaded.get("profile"), f"execution_profile[{path}].profile")
    stages = _require_sequence(profile.get("stages"), f"execution_profile[{path}].profile.stages")
    index: dict[str, dict[str, Any]] = {}
    for stage in stages:
        stage_mapping = _require_mapping(stage, f"execution_profile[{path}].profile.stages[]")
        stage_id = _require_nonempty_string(stage_mapping.get("stage_id"), f"execution_profile[{path}].stage_id")
        index[stage_id] = stage_mapping
    return index


def _resolve_runtime_tool_binding(
    *,
    registry_path: Path,
    workflow_id: str,
    stage_id: str,
    runtime_tool_binding_id: str,
    allowed_tool_classes: list[str],
) -> dict[str, Any]:
    registry = _load_yaml_object(registry_path)
    authored_tool_class_ids = {
        _require_nonempty_string(item.get("id"), f"tool_class_registry[{registry_path}].tool_classes[].id")
        for item in _require_sequence(
            registry.get("tool_classes"),
            f"tool_class_registry[{registry_path}].tool_classes",
        )
    }
    bindings = _require_sequence(
        registry.get("runtime_tool_bindings"),
        f"tool_class_registry[{registry_path}].runtime_tool_bindings",
    )
    for item in bindings:
        binding = _require_mapping(item, f"tool_class_registry[{registry_path}].runtime_tool_bindings[]")
        if _require_nonempty_string(
            binding.get("id"),
            f"tool_class_registry[{registry_path}].runtime_tool_bindings[].id",
        ) != runtime_tool_binding_id:
            continue
        applies_to = _require_mapping(
            binding.get("applies_to"),
            f"runtime_tool_binding[{runtime_tool_binding_id}].applies_to",
        )
        bound_workflow_id = _require_nonempty_string(
            applies_to.get("workflow_id"),
            f"runtime_tool_binding[{runtime_tool_binding_id}].applies_to.workflow_id",
        )
        bound_stage_id = _require_nonempty_string(
            applies_to.get("stage_id"),
            f"runtime_tool_binding[{runtime_tool_binding_id}].applies_to.stage_id",
        )
        if bound_workflow_id != workflow_id or bound_stage_id != stage_id:
            raise ControlCompileError(
                "runtime tool binding applies_to mismatch: "
                f"{bound_workflow_id}:{bound_stage_id} != {workflow_id}:{stage_id}"
            )
        runtime_tool_class = _require_nonempty_string(
            binding.get("runtime_tool_class"),
            f"runtime_tool_binding[{runtime_tool_binding_id}].runtime_tool_class",
        )
        if runtime_tool_class in authored_tool_class_ids:
            raise ControlCompileError(
                "runtime tool class must not reuse authored allowed_tool_classes vocabulary: "
                f"{runtime_tool_class}"
            )
        relationship = _require_mapping(
            binding.get("authored_tool_class_relationship"),
            f"runtime_tool_binding[{runtime_tool_binding_id}].authored_tool_class_relationship",
        )
        used_authored_classes = [
            _require_nonempty_string(
                item,
                f"runtime_tool_binding[{runtime_tool_binding_id}].authored_tool_class_relationship.uses_allowed_tool_classes[]",
            )
            for item in _require_sequence(
                relationship.get("uses_allowed_tool_classes"),
                (
                    "runtime_tool_binding["
                    f"{runtime_tool_binding_id}"
                    "].authored_tool_class_relationship.uses_allowed_tool_classes"
                ),
            )
        ]
        invalid_authored_classes = sorted(
            set(used_authored_classes) - set(allowed_tool_classes)
        )
        if invalid_authored_classes:
            raise ControlCompileError(
                "runtime tool binding references authored tool classes not allowed by the stage profile: "
                + ", ".join(invalid_authored_classes)
            )
        return {
            "id": runtime_tool_binding_id,
            "runtime_tool_class": runtime_tool_class,
            "runtime_tool_name": _require_nonempty_string(
                binding.get("runtime_tool_name"),
                f"runtime_tool_binding[{runtime_tool_binding_id}].runtime_tool_name",
            ),
            "engine_family": _require_nonempty_string(
                binding.get("engine_family"),
                f"runtime_tool_binding[{runtime_tool_binding_id}].engine_family",
            ),
            "applies_to": {
                "workflow_id": bound_workflow_id,
                "stage_id": bound_stage_id,
            },
            "authored_tool_class_relationship": {
                "relationship": _require_nonempty_string(
                    relationship.get("relationship"),
                    f"runtime_tool_binding[{runtime_tool_binding_id}].authored_tool_class_relationship.relationship",
                ),
                "uses_allowed_tool_classes": used_authored_classes,
                "note": _require_nonempty_string(
                    relationship.get("note"),
                    f"runtime_tool_binding[{runtime_tool_binding_id}].authored_tool_class_relationship.note",
                ),
            },
        }
    raise ControlCompileError(
        f"missing runtime tool binding: {runtime_tool_binding_id}"
    )


def _load_method_package_registry(path: Path) -> dict[str, Any]:
    loaded = _load_yaml_object(path)
    registry = _require_mapping(loaded.get("registry"), f"method_packages[{path}].registry")
    _require_nonempty_string(registry.get("id"), f"method_packages[{path}].registry.id")
    version = registry.get("version")
    if not isinstance(version, int) or version <= 0:
        raise ControlCompileError(f"method_packages[{path}].registry.version must be a positive integer")
    _require_sequence(registry.get("packages"), f"method_packages[{path}].registry.packages")
    return registry


def _index_method_packages(registry: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    packages = _require_sequence(registry.get("packages"), "method_packages.registry.packages")
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for item in packages:
        package = _require_mapping(item, "method_packages.registry.packages[]")
        applies_to = _require_mapping(package.get("applies_to"), "method_packages.registry.packages[].applies_to")
        workflow_id = _require_nonempty_string(applies_to.get("workflow_id"), "method_packages.registry.packages[].applies_to.workflow_id")
        stage_id = _require_nonempty_string(applies_to.get("stage_id"), "method_packages.registry.packages[].applies_to.stage_id")
        key = (workflow_id, stage_id)
        if key in indexed:
            raise ControlCompileError(f"duplicate method package applies_to binding: {workflow_id}:{stage_id}")
        indexed[key] = package
    return indexed


def _validate_method_package(package: dict[str, Any], *, workflow_id: str, stage_id: str) -> None:
    _require_nonempty_string(package.get("id"), f"method_package[{workflow_id}:{stage_id}].id")
    version = package.get("version")
    if not isinstance(version, int) or version <= 0:
        raise ControlCompileError(f"method_package[{workflow_id}:{stage_id}].version must be a positive integer")

    replay_policy = _require_mapping(package.get("replay_policy"), f"method_package[{workflow_id}:{stage_id}].replay_policy")
    deterministic_fields = _require_sequence(
        replay_policy.get("deterministic_fields"),
        f"method_package[{workflow_id}:{stage_id}].replay_policy.deterministic_fields",
    )
    if len(deterministic_fields) == 0:
        raise ControlCompileError(
            f"method_package[{workflow_id}:{stage_id}] must pin at least one deterministic field"
        )
    for field_name in deterministic_fields:
        _require_nonempty_string(
            field_name,
            f"method_package[{workflow_id}:{stage_id}].replay_policy.deterministic_fields[]",
        )

    stop_policy = _require_mapping(package.get("stop_policy"), f"method_package[{workflow_id}:{stage_id}].stop_policy")
    max_tool_calls = stop_policy.get("max_tool_calls")
    no_progress_ticks = stop_policy.get("no_progress_ticks")
    if not isinstance(max_tool_calls, int) or max_tool_calls < 0:
        raise ControlCompileError(
            f"method_package[{workflow_id}:{stage_id}].stop_policy.max_tool_calls must be a non-negative integer"
        )
    if not isinstance(no_progress_ticks, int) or no_progress_ticks < 0:
        raise ControlCompileError(
            f"method_package[{workflow_id}:{stage_id}].stop_policy.no_progress_ticks must be a non-negative integer"
        )
    _require_nonempty_string(stop_policy.get("on_exhaustion"), f"method_package[{workflow_id}:{stage_id}].stop_policy.on_exhaustion")


def _build_method_package_pin(method_package: dict[str, Any]) -> dict[str, Any]:
    package_id = _require_nonempty_string(method_package.get("id"), "method_package.id")
    version = method_package.get("version")
    if not isinstance(version, int):
        raise ControlCompileError("method_package.version must be an integer")

    return {
        "method_package_id": package_id,
        "method_package_version": version,
        "method_package_digest": _sha256_json(method_package),
        "context_builder_ref": _require_nonempty_string(method_package.get("context_builder_ref"), "method_package.context_builder_ref"),
        "tool_profile_ref": _require_nonempty_string(method_package.get("tool_profile_ref"), "method_package.tool_profile_ref"),
        "output_schema_ref": _require_nonempty_string(method_package.get("output_schema_ref"), "method_package.output_schema_ref"),
        "lowering_rule_ref": _require_nonempty_string(method_package.get("lowering_rule_ref"), "method_package.lowering_rule_ref"),
        "stop_policy": _require_mapping(method_package.get("stop_policy"), "method_package.stop_policy"),
        "replay_policy": _require_mapping(method_package.get("replay_policy"), "method_package.replay_policy"),
    }


def _build_execution_spec_id(
    *,
    workflow_id: str,
    stage_id: str,
    method_package_id: str,
    method_package_digest: str,
) -> str:
    workflow_token = workflow_id.replace(".", "_")
    stage_token = stage_id.lower()
    package_token = method_package_id.replace(".", "_")[:24]
    digest_suffix = method_package_digest.split(":", 1)[-1][:16]
    return f"execspec.{workflow_token}.{stage_token}.{package_token}.{digest_suffix}"


def _load_yaml_object(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ControlCompileError(f"expected YAML object at {path}")
    return loaded


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ControlCompileError(f"{field} must be an object")
    return value


def _require_sequence(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ControlCompileError(f"{field} must be a list")
    return value


def _require_nonempty_string(value: Any, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ControlCompileError(f"{field} must be a non-empty string")
    return text


def _validated_stop_rules(
    value: Any,
    *,
    workflow_id: str,
    stage_id: str,
) -> dict[str, Any]:
    stop_rules = _require_mapping(
        value,
        f"execution_profile[{workflow_id}:{stage_id}].stop_rules",
    )
    max_tool_calls = stop_rules.get("max_tool_calls")
    no_progress_ticks = stop_rules.get("no_progress_ticks")
    if not isinstance(max_tool_calls, int) or max_tool_calls < 0:
        raise ControlCompileError(
            f"execution_profile[{workflow_id}:{stage_id}].stop_rules.max_tool_calls must be a non-negative integer"
        )
    if not isinstance(no_progress_ticks, int) or no_progress_ticks < 0:
        raise ControlCompileError(
            f"execution_profile[{workflow_id}:{stage_id}].stop_rules.no_progress_ticks must be a non-negative integer"
        )
    return {
        "max_tool_calls": max_tool_calls,
        "no_progress_ticks": no_progress_ticks,
        "on_exhaustion": _require_nonempty_string(
            stop_rules.get("on_exhaustion"),
            f"execution_profile[{workflow_id}:{stage_id}].stop_rules.on_exhaustion",
        ),
    }


def _stage_allowed_tool_classes(
    profile_stage: Mapping[str, Any],
    *,
    workflow_id: str,
    stage_id: str,
) -> list[str]:
    return [
        _require_nonempty_string(
            item,
            f"execution_profile[{workflow_id}:{stage_id}].allowed_tool_classes[]",
        )
        for item in _require_sequence(
            profile_stage.get("allowed_tool_classes"),
            f"execution_profile[{workflow_id}:{stage_id}].allowed_tool_classes",
        )
    ]


def _build_runtime_budget(
    *,
    stop_rules: Mapping[str, Any],
    budget_override: Mapping[str, Any] | None,
    workflow_id: str,
    stage_id: str,
) -> dict[str, Any]:
    runtime_budget = {
        "max_tool_calls": int(stop_rules["max_tool_calls"]),
        "no_progress_ticks": int(stop_rules["no_progress_ticks"]),
    }
    if budget_override is None:
        return runtime_budget
    for key in ("max_tool_calls", "no_progress_ticks", "max_wall_time_seconds"):
        if key not in budget_override:
            continue
        value = budget_override[key]
        if not isinstance(value, int) or value < 0:
            raise ControlCompileError(
                f"runtime budget override {workflow_id}:{stage_id}:{key} must be a non-negative integer"
            )
        runtime_budget[key] = value
    return runtime_budget


def _build_reference_execution_spec_id(
    *,
    workflow_id: str,
    stage_id: str,
    stage_control_digest: str,
) -> str:
    workflow_token = workflow_id.replace(".", "_")
    stage_token = stage_id.lower()
    digest_suffix = stage_control_digest.split(":", 1)[-1][:16]
    return f"execspec.{workflow_token}.{stage_token}.reference.{digest_suffix}"


def _path_relative_to_repo(*, repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
