from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

GENERATOR_VERSION = "prototype-v1"
DEFAULT_WORKFLOW_ID = "schedule_planning.v1"

WORKFLOW_SOURCE_FILES = [
    "WORKFLOW_CONTRACT.yaml",
    "ARTIFACT_MAP.yaml",
    "DECISION_CATALOG.yaml",
    "EXECUTION_PROFILE.yaml",
    "ACCEPTANCE_CRITERIA.md",
]


class GenerationError(ValueError):
    """Raised when source resolution/generation/checking fails."""


@dataclass(frozen=True)
class WorkflowSources:
    repo_root: Path
    workflow_id: str
    workflow_version: str
    workflow_dir: Path
    workflow_contract_path: Path
    artifact_map_path: Path
    decision_catalog_path: Path
    execution_profile_path: Path
    acceptance_criteria_path: Path
    workflow_contract: dict[str, Any]
    artifact_map: dict[str, Any]
    decision_catalog: dict[str, Any]
    execution_profile: dict[str, Any]
    acceptance_criteria_markdown: str

    @property
    def source_paths(self) -> list[Path]:
        return [
            self.workflow_contract_path,
            self.artifact_map_path,
            self.decision_catalog_path,
            self.execution_profile_path,
            self.acceptance_criteria_path,
        ]


@dataclass(frozen=True)
class OutputPaths:
    runbook_path: Path
    ir_path: Path
    lineage_path: Path

    @property
    def materialized_paths(self) -> list[Path]:
        return [self.runbook_path, self.ir_path, self.lineage_path]


def generate_workflow_prototype(
    *,
    repo_root: Path,
    workflow_id: str = DEFAULT_WORKFLOW_ID,
    output_root: Path | None = None,
) -> dict[str, str]:
    sources = _load_workflow_sources(repo_root=repo_root, workflow_id=workflow_id)
    output_paths = _output_paths_for(
        repo_root=repo_root,
        workflow_id=sources.workflow_id,
        output_root=output_root,
    )

    _validate_no_invention(sources)
    runbook_text = _render_runbook_markdown(sources)
    ir_json_text = _render_ir_json(sources)

    output_paths.runbook_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.ir_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.lineage_path.parent.mkdir(parents=True, exist_ok=True)
    output_paths.runbook_path.write_text(runbook_text, encoding="utf-8")
    output_paths.ir_path.write_text(ir_json_text, encoding="utf-8")

    lineage = _build_lineage_manifest(
        sources=sources,
        output_paths=output_paths,
        generated_at=_utc_now_iso(),
    )
    output_paths.lineage_path.write_text(
        json.dumps(lineage, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "workflow_id": sources.workflow_id,
        "workflow_version": sources.workflow_version,
        "runbook_path": str(output_paths.runbook_path),
        "ir_path": str(output_paths.ir_path),
        "lineage_path": str(output_paths.lineage_path),
    }


def check_workflow_prototype(
    *,
    repo_root: Path,
    workflow_id: str = DEFAULT_WORKFLOW_ID,
    output_root: Path | None = None,
) -> dict[str, str]:
    sources = _load_workflow_sources(repo_root=repo_root, workflow_id=workflow_id)
    output_paths = _output_paths_for(
        repo_root=repo_root,
        workflow_id=sources.workflow_id,
        output_root=output_root,
    )

    _validate_no_invention(sources)
    for output_path in output_paths.materialized_paths:
        if not output_path.exists():
            raise GenerationError(f"generated artifact not found: {output_path}")

    expected_runbook = _render_runbook_markdown(sources)
    current_runbook = output_paths.runbook_path.read_text(encoding="utf-8")
    if current_runbook != expected_runbook:
        raise GenerationError(
            "generated runbook is stale; regenerate via scripts/generate_prototype.py"
        )

    expected_ir = _render_ir_json(sources)
    current_ir = output_paths.ir_path.read_text(encoding="utf-8")
    if current_ir != expected_ir:
        raise GenerationError(
            "generated CompanyOS IR is stale; regenerate via scripts/generate_prototype.py"
        )

    lineage_payload = _load_json(output_paths.lineage_path)
    _validate_lineage_shape(lineage_payload, sources)
    _check_lineage_hashes(
        lineage_payload=lineage_payload,
        sources=sources,
        output_paths=output_paths,
    )
    return {
        "workflow_id": sources.workflow_id,
        "workflow_version": sources.workflow_version,
        "runbook_path": str(output_paths.runbook_path),
        "ir_path": str(output_paths.ir_path),
        "lineage_path": str(output_paths.lineage_path),
    }


def _load_workflow_sources(*, repo_root: Path, workflow_id: str) -> WorkflowSources:
    workflow_slug, workflow_version = _parse_workflow_id(workflow_id)
    workflow_dir = repo_root / "docs" / "workflows" / workflow_slug / workflow_version
    if not workflow_dir.exists():
        raise GenerationError(f"workflow source directory does not exist: {workflow_dir}")

    missing = [
        name
        for name in WORKFLOW_SOURCE_FILES
        if not (workflow_dir / name).exists()
    ]
    if missing:
        raise GenerationError(
            "workflow source files missing: "
            + ", ".join(str(workflow_dir / name) for name in missing)
        )

    workflow_contract_path = workflow_dir / "WORKFLOW_CONTRACT.yaml"
    artifact_map_path = workflow_dir / "ARTIFACT_MAP.yaml"
    decision_catalog_path = workflow_dir / "DECISION_CATALOG.yaml"
    execution_profile_path = workflow_dir / "EXECUTION_PROFILE.yaml"
    acceptance_criteria_path = workflow_dir / "ACCEPTANCE_CRITERIA.md"

    workflow_contract = _load_yaml(workflow_contract_path)
    workflow_contract_id = str(workflow_contract.get("workflow", {}).get("id", ""))
    if workflow_contract_id != workflow_id:
        raise GenerationError(
            "workflow contract ID mismatch: "
            f"expected {workflow_id}, found {workflow_contract_id or '<missing>'}"
        )

    return WorkflowSources(
        repo_root=repo_root,
        workflow_id=workflow_id,
        workflow_version=workflow_version,
        workflow_dir=workflow_dir,
        workflow_contract_path=workflow_contract_path,
        artifact_map_path=artifact_map_path,
        decision_catalog_path=decision_catalog_path,
        execution_profile_path=execution_profile_path,
        acceptance_criteria_path=acceptance_criteria_path,
        workflow_contract=workflow_contract,
        artifact_map=_load_yaml(artifact_map_path),
        decision_catalog=_load_yaml(decision_catalog_path),
        execution_profile=_load_yaml(execution_profile_path),
        acceptance_criteria_markdown=acceptance_criteria_path.read_text(encoding="utf-8"),
    )


def _validate_no_invention(sources: WorkflowSources) -> None:
    workflow_stages = sources.workflow_contract.get("stages", [])
    stage_ids = {str(stage["id"]) for stage in workflow_stages}

    artifact_sets = sources.artifact_map.get("artifact_sets", {})
    artifact_stage_ids = set(artifact_sets.keys())
    unknown_artifact_stages = artifact_stage_ids - stage_ids
    if unknown_artifact_stages:
        raise GenerationError(
            "artifact map references unknown stage IDs: "
            + ", ".join(sorted(unknown_artifact_stages))
        )

    artifact_keys = {
        str(item["key"])
        for stage_items in artifact_sets.values()
        for item in stage_items
    }
    artifact_keys.update(
        {
            str(item["key"])
            for stage_items in sources.artifact_map.get("out_of_scope", {}).values()
            for item in stage_items
        }
    )

    contract_artifact_keys = {
        str(item["dataset_key"])
        for stage in workflow_stages
        for item in stage.get("artifacts", [])
    }
    missing_artifacts = contract_artifact_keys - artifact_keys
    if missing_artifacts:
        raise GenerationError(
            "workflow contract dataset keys missing from artifact map: "
            + ", ".join(sorted(missing_artifacts))
        )

    decisions = sources.decision_catalog.get("catalog", {}).get("decisions", [])
    decision_ids = {str(decision["id"]) for decision in decisions}
    for decision in decisions:
        stage_id = str(decision["stage_id"])
        if stage_id not in stage_ids:
            raise GenerationError(
                f"decision {decision['id']} references unknown stage_id {stage_id}"
            )
        evidence_keys = (
            decision.get("evidence_requirements", {}).get("artifact_keys", [])
        )
        for key in evidence_keys:
            if str(key) not in artifact_keys:
                raise GenerationError(
                    f"decision {decision['id']} references unknown artifact key {key}"
                )

    profile_stages = sources.execution_profile.get("profile", {}).get("stages", [])
    for profile_stage in profile_stages:
        stage_id = str(profile_stage["stage_id"])
        if stage_id not in stage_ids:
            raise GenerationError(
                f"execution profile references unknown stage_id {stage_id}"
            )
        for decision_ref in profile_stage.get("decision_refs", []):
            if str(decision_ref) not in decision_ids:
                raise GenerationError(
                    f"execution profile stage {stage_id} references unknown decision {decision_ref}"
                )
        for key in profile_stage.get("required_evidence_keys", []):
            if str(key) not in artifact_keys:
                raise GenerationError(
                    f"execution profile stage {stage_id} references unknown evidence key {key}"
                )

    for stage in workflow_stages:
        stage_id = str(stage["id"])
        semantics = stage.get("semantics", {})
        for rule in semantics.get("spawn_rules", []) or []:
            target_stage_id = str(rule.get("target_stage_id", ""))
            if target_stage_id not in stage_ids:
                raise GenerationError(
                    f"spawn rule {rule.get('id')} in {stage_id} targets unknown stage_id {target_stage_id}"
                )


def _render_runbook_markdown(sources: WorkflowSources) -> str:
    workflow = sources.workflow_contract["workflow"]
    stages = sources.workflow_contract.get("stages", [])
    profile_by_stage = {
        str(stage["stage_id"]): stage
        for stage in sources.execution_profile.get("profile", {}).get("stages", [])
    }
    decisions = sources.decision_catalog.get("catalog", {}).get("decisions", [])
    artifact_sets = sources.artifact_map.get("artifact_sets", {})
    checklist = _extract_checklist_items(sources.acceptance_criteria_markdown)

    lines: list[str] = []
    lines.append("# Runbook Prototype - schedule_planning.v1")
    lines.append("")
    lines.append(
        "> Generated artifact (non-authoritative). "
        "Edit repo-native source files and regenerate."
    )
    lines.append("")
    lines.append("## Workflow")
    lines.append(f"- Workflow ID: `{sources.workflow_id}`")
    lines.append(f"- Workflow version: `{sources.workflow_version}`")
    lines.append(f"- Name: {workflow.get('name', sources.workflow_id)}")
    lines.append("")
    lines.append("## Stage List and Purpose")
    for stage in stages:
        stage_id = str(stage["id"])
        profile_stage = profile_by_stage.get(stage_id, {})
        purpose = _stage_purpose(stage, profile_stage)
        lines.append(f"- `{stage_id}` - {purpose}")
    lines.append("")
    lines.append("## Artifact Keys by Stage")
    for stage in stages:
        stage_id = str(stage["id"])
        artifacts = artifact_sets.get(stage_id, [])
        lines.append(f"### {stage_id}")
        if not artifacts:
            lines.append("- _(no artifact-map entries)_")
        for artifact in artifacts:
            lines.append(
                f"- `{artifact['key']}` ({artifact.get('role', 'unspecified')})"
            )
    lines.append("")
    lines.append("## Decisions and Approvals")
    for decision in decisions:
        allowed = ", ".join(decision.get("allowed_responses", []))
        lines.append(
            "- "
            f"`{decision['id']}` (`{decision['stage_id']}`) -> action `{decision['action']}`, "
            f"requested_from `{decision['requested_from_role']}`, "
            f"responses: {allowed}"
        )
    lines.append("")
    lines.append("## Spawn Rules and Bounded Loops")
    for stage in stages:
        stage_id = str(stage["id"])
        semantics = stage.get("semantics", {}) or {}
        profile_stage = profile_by_stage.get(stage_id, {})
        spawn_policy = semantics.get("task_spawn_policy")
        if spawn_policy is None:
            continue
        budget = semantics.get("spawn_budget", {}) or {}
        execution_pattern = profile_stage.get("execution_pattern", "unspecified")
        lines.append(
            "- "
            f"`{stage_id}`: policy `{spawn_policy}`, execution_pattern `{execution_pattern}`, "
            f"max_depth `{budget.get('max_spawn_depth', 'n/a')}`"
        )
        for rule in semantics.get("spawn_rules", []) or []:
            roles = ", ".join(rule.get("candidate_roles", []))
            lines.append(
                "  - "
                f"`{rule.get('id')}` when `{rule.get('when')}` -> "
                f"`{rule.get('target_stage_id')}` / `{rule.get('task_kind')}` "
                f"(roles: {roles})"
            )
    lines.append("")
    lines.append("## Operator Checklist Snippets (from ACCEPTANCE_CRITERIA)")
    if checklist:
        for item in checklist[:20]:
            lines.append(f"- {item}")
    else:
        lines.append("- _(no checklist snippets found)_")
    lines.append("")
    lines.append("## Source Inputs")
    for path in sources.source_paths:
        lines.append(f"- `{_relative_path(path, sources.repo_root)}`")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_ir_json(sources: WorkflowSources) -> str:
    workflow = sources.workflow_contract["workflow"]
    stages = sources.workflow_contract.get("stages", [])
    profile_by_stage = {
        str(stage["stage_id"]): stage
        for stage in sources.execution_profile.get("profile", {}).get("stages", [])
    }
    decisions = sources.decision_catalog.get("catalog", {}).get("decisions", [])

    stage_ir: list[dict[str, Any]] = []
    spawn_rules: list[dict[str, Any]] = []
    for stage in stages:
        stage_id = str(stage["id"])
        semantics = stage.get("semantics", {}) or {}
        profile_stage = profile_by_stage.get(stage_id, {})
        stage_spawn_rules = semantics.get("spawn_rules", []) or []
        for rule in stage_spawn_rules:
            spawn_rules.append(
                {
                    "stage_id": stage_id,
                    "spawn_rule_id": str(rule["id"]),
                    "when": str(rule["when"]),
                    "target_stage_id": str(rule["target_stage_id"]),
                    "task_kind": str(rule["task_kind"]),
                    "candidate_roles": list(rule.get("candidate_roles", [])),
                }
            )

        stage_ir.append(
            {
                "stage_id": stage_id,
                "name": stage.get("name"),
                "in_scope_mvp": bool(stage.get("in_scope_mvp", False)),
                "artifacts": stage.get("artifacts", []),
                "approvals": stage.get("approvals"),
                "semantics": {
                    "activation_basis": semantics.get("activation_basis"),
                    "task_spawn_policy": semantics.get("task_spawn_policy"),
                    "spawn_budget": semantics.get("spawn_budget"),
                    "spawn_rules": stage_spawn_rules,
                },
                "execution": {
                    "execution_pattern": profile_stage.get("execution_pattern"),
                    "allowed_tool_classes": profile_stage.get("allowed_tool_classes", []),
                    "required_evidence_keys": profile_stage.get("required_evidence_keys", []),
                    "decision_refs": profile_stage.get("decision_refs", []),
                    "side_effect_policy": profile_stage.get("side_effect_policy"),
                    "stop_rules": profile_stage.get("stop_rules"),
                    "projections": profile_stage.get("projections", []),
                },
            }
        )

    ir_payload = {
        "kind": "companyos.workflow_ir.prototype",
        "generator_version": GENERATOR_VERSION,
        "workflow_id": sources.workflow_id,
        "workflow_version": sources.workflow_version,
        "workflow_name": workflow.get("name"),
        "partition_key": workflow.get("partition_key"),
        "scope": workflow.get("scope"),
        "temporal_partition": workflow.get("temporal_partition"),
        "semantics": sources.workflow_contract.get("semantics", {}),
        "stages": stage_ir,
        "artifacts": {
            "artifact_sets": sources.artifact_map.get("artifact_sets", {}),
            "out_of_scope": sources.artifact_map.get("out_of_scope", {}),
        },
        "decisions": decisions,
        "spawn_rules": spawn_rules,
        "required_events": sources.workflow_contract.get("event_inventory", {}),
    }
    return json.dumps(ir_payload, indent=2, sort_keys=True) + "\n"


def _build_lineage_manifest(
    *,
    sources: WorkflowSources,
    output_paths: OutputPaths,
    generated_at: str,
) -> dict[str, Any]:
    source_entries = [
        {
            "path": _relative_path(path, sources.repo_root),
            "sha256": _sha256_path(path),
        }
        for path in sources.source_paths
    ]
    output_entries = [
        {
            "path": _relative_path(path, sources.repo_root),
            "sha256": _sha256_path(path),
        }
        for path in [output_paths.runbook_path, output_paths.ir_path]
    ]
    return {
        "kind": "onetruth.generator.prototype.lineage",
        "workflow_id": sources.workflow_id,
        "workflow_version": sources.workflow_version,
        "generator_version": GENERATOR_VERSION,
        "generated_at": generated_at,
        "sources": source_entries,
        "outputs": output_entries,
    }


def _validate_lineage_shape(lineage_payload: dict[str, Any], sources: WorkflowSources) -> None:
    if str(lineage_payload.get("workflow_id")) != sources.workflow_id:
        raise GenerationError("lineage workflow_id does not match requested workflow_id")
    if str(lineage_payload.get("workflow_version")) != sources.workflow_version:
        raise GenerationError("lineage workflow_version does not match requested workflow version")
    if str(lineage_payload.get("generator_version")) != GENERATOR_VERSION:
        raise GenerationError("lineage generator_version does not match current generator version")
    if not isinstance(lineage_payload.get("generated_at"), str) or not str(lineage_payload.get("generated_at")).strip():
        raise GenerationError("lineage generated_at is missing or invalid")
    if not isinstance(lineage_payload.get("sources"), list):
        raise GenerationError("lineage sources must be a list")
    if not isinstance(lineage_payload.get("outputs"), list):
        raise GenerationError("lineage outputs must be a list")


def _check_lineage_hashes(
    *,
    lineage_payload: dict[str, Any],
    sources: WorkflowSources,
    output_paths: OutputPaths,
) -> None:
    expected_source_hashes = {
        _relative_path(path, sources.repo_root): _sha256_path(path)
        for path in sources.source_paths
    }
    lineage_source_hashes = {
        str(entry.get("path")): str(entry.get("sha256"))
        for entry in lineage_payload.get("sources", [])
        if isinstance(entry, dict)
    }
    if lineage_source_hashes != expected_source_hashes:
        raise GenerationError(
            "lineage source hashes are stale; regenerate via scripts/generate_prototype.py"
        )

    expected_output_hashes = {
        _relative_path(path, sources.repo_root): _sha256_path(path)
        for path in [output_paths.runbook_path, output_paths.ir_path]
    }
    lineage_output_hashes = {
        str(entry.get("path")): str(entry.get("sha256"))
        for entry in lineage_payload.get("outputs", [])
        if isinstance(entry, dict)
    }
    if lineage_output_hashes != expected_output_hashes:
        raise GenerationError(
            "lineage output hashes do not match generated files; regenerate prototype outputs"
        )


def _output_paths_for(
    *,
    repo_root: Path,
    workflow_id: str,
    output_root: Path | None,
) -> OutputPaths:
    root = output_root or (repo_root / "build" / "generated")
    return OutputPaths(
        runbook_path=root / "runbooks" / workflow_id / "runbook.md",
        ir_path=root / "companyos_ir" / f"{workflow_id}.json",
        lineage_path=root / "lineage" / f"{workflow_id}.lineage.json",
    )


def _extract_checklist_items(markdown_text: str) -> list[str]:
    items: list[str] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("- [ ] "):
            continue
        item = line[6:].strip()
        if item:
            items.append(item)
    return items


def _stage_purpose(stage: dict[str, Any], profile_stage: dict[str, Any]) -> str:
    notes = stage.get("notes") or []
    if isinstance(notes, list) and notes:
        return str(notes[0])
    semantics = stage.get("semantics", {}) or {}
    activation_basis = semantics.get("activation_basis")
    if activation_basis:
        return f"Activation basis: {activation_basis}"
    execution_pattern = profile_stage.get("execution_pattern")
    if execution_pattern:
        return f"Execution pattern: {execution_pattern}"
    return str(stage.get("name", "stage"))


def _parse_workflow_id(workflow_id: str) -> tuple[str, str]:
    if "." not in workflow_id:
        raise GenerationError(
            "workflow_id must include workflow and version, for example schedule_planning.v1"
        )
    workflow_slug, workflow_version = workflow_id.rsplit(".", 1)
    if not workflow_slug or not workflow_version:
        raise GenerationError(
            "workflow_id must include workflow and version, for example schedule_planning.v1"
        )
    return workflow_slug, workflow_version


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise GenerationError(f"expected YAML object at {path}, got {type(value).__name__}")
    return value


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise GenerationError(f"expected JSON object at {path}, got {type(value).__name__}")
    return value


def _relative_path(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
