from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.assumption_closure_workflow import (
    ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION,
)
from onetruth.capex_platform.corpus_baseline_workflow import (
    CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
)
from onetruth.capex_platform.governance_commitment_chain import (
    GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION,
)
from onetruth.capex_platform.lifecycle_stage_state_workflow import (
    LIFECYCLE_STAGE_STATE_WORKFLOW_SCHEMA_VERSION,
)
from onetruth.capex_platform.owner_interface_resolution_workflow import (
    OWNER_INTERFACE_RESOLUTION_WORKFLOW_SCHEMA_VERSION,
)


PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION = (
    "capex.project_state_snapshot.workflow_outputs.v1"
)
PROJECT_STATE_SNAPSHOT_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
PROJECT_STATE_SNAPSHOT_SCHEMA_VERSION = "capex.project_state_snapshot.v1"
PROJECT_CLOSURE_VECTOR_SCHEMA_VERSION = "capex.project_closure_vector.v1"
PROJECT_STATE_SNAPSHOT_FLAGS_SCHEMA_VERSION = "capex.project_state_snapshot_flags.v1"

POINTER_STATES = frozenset({"current", "stale", "missing", "draft_only"})
POINTER_REVIEW_STATES = frozenset({"reviewed", "unreviewed", "draft", "stale"})

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_ARTIFACT_REF_RE = re.compile(r"^(?:artifact_version|generated_artifact):[A-Za-z0-9_.:-]+$")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "document_text",
    "evidence_text",
    "excerpt",
    "extracted_text",
    "file_name",
    "filename",
    "full_text",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_evidence",
    "raw_file",
    "raw_filename",
    "raw_log",
    "raw_snapshot",
    "source_filename",
    "source_text",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class ProjectStateSnapshotWorkflowError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_project_state_snapshot_workflow_outputs(
    *,
    corpus_baseline_outputs: Mapping[str, Any],
    lifecycle_stage_state_outputs: Mapping[str, Any],
    governance_commitment_outputs: Mapping[str, Any],
    assumption_closure_outputs: Mapping[str, Any],
    owner_interface_resolution_outputs: Mapping[str, Any],
    pointer_observations: Sequence[Mapping[str, Any]],
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only project state snapshot outputs."""

    _require_schema(
        corpus_baseline_outputs,
        CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
        "corpus_baseline_outputs",
    )
    _require_schema(
        lifecycle_stage_state_outputs,
        LIFECYCLE_STAGE_STATE_WORKFLOW_SCHEMA_VERSION,
        "lifecycle_stage_state_outputs",
    )
    _require_schema(
        governance_commitment_outputs,
        GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION,
        "governance_commitment_outputs",
    )
    _require_schema(
        assumption_closure_outputs,
        ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION,
        "assumption_closure_outputs",
    )
    _require_schema(
        owner_interface_resolution_outputs,
        OWNER_INTERFACE_RESOLUTION_WORKFLOW_SCHEMA_VERSION,
        "owner_interface_resolution_outputs",
    )
    scope = _scope(corpus_baseline_outputs, "corpus_baseline_outputs")
    for label, raw in (
        ("lifecycle_stage_state_outputs", lifecycle_stage_state_outputs),
        ("governance_commitment_outputs", governance_commitment_outputs),
        ("assumption_closure_outputs", assumption_closure_outputs),
        ("owner_interface_resolution_outputs", owner_interface_resolution_outputs),
    ):
        _require_same_scope(scope, raw, label)

    available_source_refs = _available_source_refs(corpus_baseline_outputs)
    for label, raw in (
        ("lifecycle_stage_state_outputs", lifecycle_stage_state_outputs),
        ("governance_commitment_outputs", governance_commitment_outputs),
        ("assumption_closure_outputs", assumption_closure_outputs),
        ("owner_interface_resolution_outputs", owner_interface_resolution_outputs),
    ):
        _require_output_source_refs_in_corpus(
            raw,
            available_source_refs=available_source_refs,
            label=label,
        )

    known_refs = _known_refs(
        lifecycle_stage_state_outputs=lifecycle_stage_state_outputs,
        governance_commitment_outputs=governance_commitment_outputs,
        assumption_closure_outputs=assumption_closure_outputs,
        owner_interface_resolution_outputs=owner_interface_resolution_outputs,
    )
    pointers = _pointer_rows(
        pointer_observations,
        available_source_refs=available_source_refs,
        known_refs=known_refs,
    )
    components = _closure_components(
        lifecycle_stage_state_outputs=lifecycle_stage_state_outputs,
        governance_commitment_outputs=governance_commitment_outputs,
        assumption_closure_outputs=assumption_closure_outputs,
        owner_interface_resolution_outputs=owner_interface_resolution_outputs,
        pointer_rows=pointers,
    )
    flags = _snapshot_flags(components)
    closure_ready = all(row["result"] == "pass" for row in components)
    project_state_snapshot = {
        "schema_version": PROJECT_STATE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": f"{_require_nonempty(workflow_id, 'workflow_id')}:snapshot",
        "tenant_id": scope["tenant_id"],
        "domain_id": scope["domain_id"],
        "project_id": scope["project_id"],
        "closure_ready": closure_ready,
        "reviewed_state_only": True,
        "official_truth": False,
        "summary": {
            "stage_count": _row_count(lifecycle_stage_state_outputs, "lifecycle_stage_state"),
            "commitment_count": _row_count(governance_commitment_outputs, "commitment_chain"),
            "assumption_count": _row_count(assumption_closure_outputs, "counterparty_assumption_register"),
            "interface_count": _row_count(owner_interface_resolution_outputs, "interface_register"),
            "pointer_count": len(pointers),
            "blocking_component_count": len([row for row in components if row["result"] != "pass"]),
        },
        "pointer_observations": pointers,
        "snapshot_digest": _digest(
            {
                "components": components,
                "pointers": pointers,
                "scope": scope,
            }
        ),
    }
    return {
        "schema_version": PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION,
        "activation_posture": PROJECT_STATE_SNAPSHOT_ACTIVATION_POSTURE,
        "workflow_id": _require_nonempty(workflow_id, "workflow_id"),
        "tenant_id": scope["tenant_id"],
        "domain_id": scope["domain_id"],
        "project_id": scope["project_id"],
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "basis": {
            "corpus_baseline_workflow_id": _require_nonempty(
                corpus_baseline_outputs.get("workflow_id"),
                "corpus_baseline_outputs.workflow_id",
            ),
            "lifecycle_stage_state_workflow_id": _require_nonempty(
                lifecycle_stage_state_outputs.get("workflow_id"),
                "lifecycle_stage_state_outputs.workflow_id",
            ),
            "governance_commitment_chain_workflow_id": _require_nonempty(
                governance_commitment_outputs.get("workflow_id"),
                "governance_commitment_outputs.workflow_id",
            ),
            "assumption_closure_workflow_id": _require_nonempty(
                assumption_closure_outputs.get("workflow_id"),
                "assumption_closure_outputs.workflow_id",
            ),
            "owner_interface_resolution_workflow_id": _require_nonempty(
                owner_interface_resolution_outputs.get("workflow_id"),
                "owner_interface_resolution_outputs.workflow_id",
            ),
            "packet_register_id": _require_nonempty(
                corpus_baseline_outputs.get("basis", {}).get("packet_register_id")
                if isinstance(corpus_baseline_outputs.get("basis"), Mapping)
                else None,
                "corpus_baseline_outputs.basis.packet_register_id",
            ),
        },
        "project_state_snapshot": project_state_snapshot,
        "project_closure_vector": {
            "schema_version": PROJECT_CLOSURE_VECTOR_SCHEMA_VERSION,
            "rows": components,
            "row_count": len(components),
            "closure_ready": closure_ready,
            "snapshot_digest": _digest(components),
        },
        "project_state_snapshot_flags": {
            "schema_version": PROJECT_STATE_SNAPSHOT_FLAGS_SCHEMA_VERSION,
            "rows": flags,
            "row_count": len(flags),
            "snapshot_digest": _digest(flags),
        },
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_tasks": False,
            "creates_approvals": False,
            "creates_closure_snapshots": False,
            "creates_project_state": False,
            "creates_reviewed_baseline": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "authored_workflow_pack_activation",
            "workflow_run_creation",
            "public_route_activation",
            "frontend_route_activation",
            "official_project_state",
            "closure_snapshot_creation",
            "evidence_sufficiency_claim",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_project_state_snapshot_workflow_bytes(
    outputs: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def project_state_snapshot_workflow_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_project_state_snapshot_workflow_bytes(outputs)
    ).hexdigest()


def _pointer_rows(
    pointer_observations: Sequence[Mapping[str, Any]],
    *,
    available_source_refs: set[str],
    known_refs: Mapping[str, set[str]],
) -> list[dict[str, Any]]:
    if not pointer_observations:
        raise ProjectStateSnapshotWorkflowError(
            "project_state_pointer_observations_required",
            {"field": "pointer_observations"},
        )
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, observation in enumerate(pointer_observations):
        if not isinstance(observation, Mapping):
            raise ProjectStateSnapshotWorkflowError(
                "project_state_pointer_observation_must_be_object",
                {"index": index},
            )
        _reject_raw_material(observation, path=f"pointer_observations[{index}]")
        pointer_id = _require_nonempty(
            observation.get("pointer_id"),
            f"pointer_observations[{index}].pointer_id",
        )
        if pointer_id in seen_ids:
            raise ProjectStateSnapshotWorkflowError(
                "project_state_duplicate_pointer_id",
                {"index": index, "pointer_id": pointer_id},
            )
        seen_ids.add(pointer_id)
        pointer_state = _allowed(
            observation.get("pointer_state"),
            POINTER_STATES,
            f"pointer_observations[{index}].pointer_state",
            "project_state_pointer_state_invalid",
        )
        review_state = _allowed(
            observation.get("review_state"),
            POINTER_REVIEW_STATES,
            f"pointer_observations[{index}].review_state",
            "project_state_pointer_review_state_invalid",
        )
        target_artifact_ref = _optional_artifact_ref(
            observation.get("target_artifact_ref"),
            f"pointer_observations[{index}].target_artifact_ref",
        )
        if pointer_state == "current" and (review_state != "reviewed" or not target_artifact_ref):
            raise ProjectStateSnapshotWorkflowError(
                "project_state_current_pointer_requires_reviewed_target",
                {"index": index, "pointer_id": pointer_id},
            )
        row = {
            "pointer_id": pointer_id,
            "pointer_family": _require_nonempty(
                observation.get("pointer_family"),
                f"pointer_observations[{index}].pointer_family",
            ),
            "pointer_state": pointer_state,
            "review_state": review_state,
            "target_artifact_ref": target_artifact_ref,
            "related_stage_id": _known_optional_ref(
                observation.get("related_stage_id"),
                known_refs["stage_ids"],
                "stage_id",
                index,
            ),
            "related_commitment_id": _known_optional_ref(
                observation.get("related_commitment_id"),
                known_refs["commitment_ids"],
                "commitment_id",
                index,
            ),
            "related_assumption_id": _known_optional_ref(
                observation.get("related_assumption_id"),
                known_refs["assumption_ids"],
                "assumption_id",
                index,
            ),
            "related_interface_id": _known_optional_ref(
                observation.get("related_interface_id"),
                known_refs["interface_ids"],
                "interface_id",
                index,
            ),
            "source_refs": _source_refs(
                observation.get("source_refs"),
                available_source_refs,
                index=index,
                field_name="source_refs",
                required=True,
            ),
            "official_truth": False,
        }
        rows.append(row)
    return sorted(rows, key=lambda row: row["pointer_id"])


def _closure_components(
    *,
    lifecycle_stage_state_outputs: Mapping[str, Any],
    governance_commitment_outputs: Mapping[str, Any],
    assumption_closure_outputs: Mapping[str, Any],
    owner_interface_resolution_outputs: Mapping[str, Any],
    pointer_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    components = [
        _component(
            component_id="lifecycle_stage_state",
            result=_lifecycle_result(lifecycle_stage_state_outputs),
        ),
        _component(
            component_id="governance_commitments",
            result=_governance_result(governance_commitment_outputs),
        ),
        _component(
            component_id="assumption_closure",
            result=_assumption_result(assumption_closure_outputs),
        ),
        _component(
            component_id="owner_interface_resolution",
            result=_interface_result(owner_interface_resolution_outputs),
        ),
        _component(
            component_id="official_pointer_posture",
            result=_pointer_result(pointer_rows),
        ),
    ]
    seen = set()
    for row in components:
        if row["component_id"] in seen:
            raise ProjectStateSnapshotWorkflowError(
                "project_state_duplicate_closure_component_id",
                {"component_id": row["component_id"]},
            )
        seen.add(row["component_id"])
    return sorted(components, key=lambda row: row["component_id"])


def _component(component_id: str, result: tuple[str, str, str, list[str]]) -> dict[str, Any]:
    status, outcome, reason, source_refs = result
    return {
        "component_id": component_id,
        "status": status,
        "result": outcome,
        "reason": reason,
        "source_refs": sorted(source_refs),
        "creates_official_truth": False,
    }


def _lifecycle_result(raw: Mapping[str, Any]) -> tuple[str, str, str, list[str]]:
    rows = _rows(raw, "lifecycle_stage_state")
    flags = _rows(raw, "lifecycle_navigation_flags")
    source_refs = _all_row_source_refs(rows) | _all_row_source_refs(flags)
    if flags:
        return "blocked", "fail", "lifecycle_flags_open", sorted(source_refs)
    if any(row.get("readiness_state") != "ready" for row in rows):
        return "not_ready", "fail", "lifecycle_stage_not_ready", sorted(source_refs)
    return "ready", "pass", "lifecycle_stages_ready", sorted(source_refs)


def _governance_result(raw: Mapping[str, Any]) -> tuple[str, str, str, list[str]]:
    commitments = _rows(raw, "commitment_chain")
    flags = _rows(raw, "commitment_flags")
    source_refs = _all_row_source_refs(commitments) | _all_row_source_refs(flags)
    if flags:
        return "blocked", "fail", "commitment_flags_open", sorted(source_refs)
    if any(row.get("commercial_status") in {"draft", "proposed"} for row in commitments):
        return "not_reviewed", "fail", "draft_or_proposed_commitment", sorted(source_refs)
    return "reviewed", "pass", "commitments_reviewed", sorted(source_refs)


def _assumption_result(raw: Mapping[str, Any]) -> tuple[str, str, str, list[str]]:
    matrix = _rows(raw, "assumption_closure_matrix")
    flags = _rows(raw, "assumption_flags")
    source_refs = _all_row_source_refs(matrix) | _all_row_source_refs(flags)
    if flags or any(row.get("result") == "fail" for row in matrix):
        return "blocked", "fail", "assumption_closure_blocked", sorted(source_refs)
    if any(row.get("result") == "satisfied_by_waiver" for row in matrix):
        return "waiver_recorded", "waiver", "assumption_waiver_not_pass", sorted(source_refs)
    return "closed", "pass", "assumptions_closed_with_evidence", sorted(source_refs)


def _interface_result(raw: Mapping[str, Any]) -> tuple[str, str, str, list[str]]:
    interfaces = _rows(raw, "interface_register")
    flags = _rows(raw, "owner_interface_flags")
    source_refs = _all_row_source_refs(interfaces) | _all_row_source_refs(flags)
    if flags or any(row.get("result") != "pass" for row in interfaces):
        return "blocked", "fail", "owner_interface_resolution_blocked", sorted(source_refs)
    return "resolved", "pass", "owner_interfaces_resolved_with_evidence", sorted(source_refs)


def _pointer_result(pointer_rows: Sequence[Mapping[str, Any]]) -> tuple[str, str, str, list[str]]:
    source_refs = _all_row_source_refs(pointer_rows)
    if any(row.get("pointer_state") == "missing" for row in pointer_rows):
        return "missing", "fail", "official_pointer_missing", sorted(source_refs)
    if any(row.get("pointer_state") == "stale" for row in pointer_rows):
        return "stale", "fail", "official_pointer_stale", sorted(source_refs)
    if any(row.get("pointer_state") == "draft_only" or row.get("review_state") != "reviewed" for row in pointer_rows):
        return "draft_only", "fail", "official_pointer_draft_only", sorted(source_refs)
    return "current", "pass", "official_pointers_current_and_reviewed", sorted(source_refs)


def _snapshot_flags(components: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for component in components:
        if component["result"] == "pass":
            continue
        severity = "medium" if component["result"] == "waiver" else "high"
        rows.append(
            {
                "flag_id": f"{component['component_id']}:{component['reason']}",
                "component_id": component["component_id"],
                "flag_type": component["reason"],
                "severity": severity,
                "source_refs": list(component["source_refs"]),
                "blocks_closure_ready": component["result"] != "pass",
            }
        )
    return sorted(rows, key=lambda row: row["flag_id"])


def _known_refs(
    *,
    lifecycle_stage_state_outputs: Mapping[str, Any],
    governance_commitment_outputs: Mapping[str, Any],
    assumption_closure_outputs: Mapping[str, Any],
    owner_interface_resolution_outputs: Mapping[str, Any],
) -> dict[str, set[str]]:
    return {
        "stage_ids": {
            str(row["stage_id"])
            for row in _rows(lifecycle_stage_state_outputs, "lifecycle_stage_state")
        },
        "commitment_ids": {
            str(row["commitment_id"])
            for row in _rows(governance_commitment_outputs, "commitment_chain")
        },
        "assumption_ids": {
            str(row["assumption_id"])
            for row in _rows(assumption_closure_outputs, "counterparty_assumption_register")
        },
        "interface_ids": {
            str(row["interface_id"])
            for row in _rows(owner_interface_resolution_outputs, "interface_register")
        },
    }


def _require_schema(raw: Mapping[str, Any], expected: str, label: str) -> None:
    if raw.get("schema_version") != expected:
        raise ProjectStateSnapshotWorkflowError(
            "project_state_required_basis_schema_mismatch",
            {
                "label": label,
                "expected_schema_version": expected,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _scope(raw: Mapping[str, Any], label: str) -> dict[str, str]:
    return {
        "tenant_id": _require_nonempty(raw.get("tenant_id"), f"{label}.tenant_id"),
        "domain_id": _require_nonempty(raw.get("domain_id"), f"{label}.domain_id"),
        "project_id": _require_nonempty(raw.get("project_id"), f"{label}.project_id"),
    }


def _require_same_scope(scope: Mapping[str, str], raw: Mapping[str, Any], label: str) -> None:
    candidate = _scope(raw, label)
    if candidate != dict(scope):
        raise ProjectStateSnapshotWorkflowError(
            "project_state_scope_mismatch",
            {"expected": dict(scope), "actual": candidate, "label": label},
        )


def _available_source_refs(corpus_baseline_outputs: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for artifact in corpus_baseline_outputs.get("generated_artifacts") or []:
        if not isinstance(artifact, Mapping):
            continue
        envelope = artifact.get("envelope")
        if not isinstance(envelope, Mapping):
            continue
        for source_ref in envelope.get("source_refs") or []:
            source_ref_text = str(source_ref)
            if _SOURCE_REF_RE.match(source_ref_text):
                refs.add(source_ref_text)
    if not refs:
        raise ProjectStateSnapshotWorkflowError(
            "project_state_source_basis_required",
            {"field": "corpus_baseline_outputs.generated_artifacts[].envelope.source_refs"},
        )
    return refs


def _require_output_source_refs_in_corpus(
    raw: Mapping[str, Any],
    *,
    available_source_refs: set[str],
    label: str,
) -> None:
    for source_ref in _source_refs_in_value(raw):
        if source_ref not in available_source_refs:
            raise ProjectStateSnapshotWorkflowError(
                "project_state_source_ref_not_in_corpus_baseline",
                {"label": label, "source_ref": source_ref},
            )


def _source_refs_in_value(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key).endswith("source_refs") and isinstance(nested, Sequence) and not isinstance(nested, (str, bytes)):
                refs.update(str(item) for item in nested if _SOURCE_REF_RE.match(str(item)))
            refs.update(_source_refs_in_value(nested))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            refs.update(_source_refs_in_value(nested))
    return refs


def _source_refs(
    raw: Any,
    available_source_refs: set[str],
    *,
    index: int,
    field_name: str,
    required: bool,
) -> list[str]:
    if raw is None:
        if required:
            raise ProjectStateSnapshotWorkflowError(
                "project_state_source_refs_required",
                {"index": index, "field": field_name},
            )
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or (required and not raw):
        raise ProjectStateSnapshotWorkflowError(
            "project_state_source_refs_must_be_list",
            {"index": index, "field": field_name},
        )
    refs: list[str] = []
    for ref_index, value in enumerate(raw):
        source_ref = _require_nonempty(value, f"{field_name}[{ref_index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise ProjectStateSnapshotWorkflowError(
                "project_state_source_ref_invalid",
                {"index": index, "field": field_name, "source_ref": source_ref},
            )
        if source_ref not in available_source_refs:
            raise ProjectStateSnapshotWorkflowError(
                "project_state_source_ref_not_in_corpus_baseline",
                {"index": index, "field": field_name, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise ProjectStateSnapshotWorkflowError(
                "project_state_duplicate_source_ref",
                {"index": index, "field": field_name, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _known_optional_ref(
    raw: Any,
    known_values: set[str],
    field_name: str,
    index: int,
) -> str | None:
    if raw is None:
        return None
    value = _require_nonempty(raw, f"pointer_observations[{index}].related_{field_name}")
    if value not in known_values:
        raise ProjectStateSnapshotWorkflowError(
            "project_state_unknown_related_ref",
            {"index": index, "field": field_name, "value": value},
        )
    return value


def _optional_artifact_ref(raw: Any, field: str) -> str | None:
    if raw is None:
        return None
    value = _require_nonempty(raw, field)
    if not _ARTIFACT_REF_RE.match(value):
        raise ProjectStateSnapshotWorkflowError(
            "project_state_artifact_ref_invalid",
            {"field": field, "value": value},
        )
    return value


def _rows(raw: Mapping[str, Any], section_name: str) -> list[Mapping[str, Any]]:
    section = raw.get(section_name)
    if not isinstance(section, Mapping):
        raise ProjectStateSnapshotWorkflowError(
            "project_state_section_required",
            {"section": section_name},
        )
    rows = section.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ProjectStateSnapshotWorkflowError(
            "project_state_section_rows_required",
            {"section": section_name},
        )
    normalized: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ProjectStateSnapshotWorkflowError(
                "project_state_section_row_must_be_object",
                {"section": section_name, "index": index},
            )
        normalized.append(row)
    return normalized


def _row_count(raw: Mapping[str, Any], section_name: str) -> int:
    return len(_rows(raw, section_name))


def _all_row_source_refs(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for row in rows:
        for source_ref in row.get("source_refs") or []:
            refs.add(str(source_ref))
        for source_ref in row.get("evidence_source_refs") or []:
            refs.add(str(source_ref))
        for source_ref in row.get("conflict_source_refs") or []:
            refs.add(str(source_ref))
        for source_ref in row.get("ai_draft_source_refs") or []:
            refs.add(str(source_ref))
        for source_ref in row.get("contradicted_by_source_refs") or []:
            refs.add(str(source_ref))
    return refs


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_code: str,
) -> str:
    normalized = _require_nonempty(value, field)
    if normalized not in allowed:
        raise ProjectStateSnapshotWorkflowError(
            error_code,
            {"field": field, "value": normalized, "allowed": sorted(allowed)},
        )
    return normalized


def _require_nonempty(value: Any, field: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ProjectStateSnapshotWorkflowError(
            "project_state_required_field_missing",
            {"field": field},
        )
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise ProjectStateSnapshotWorkflowError(
                    "project_state_raw_material_rejected",
                    {"path": f"{path}.{key_text}", "reason": "forbidden_key"},
                )
            _reject_raw_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _reject_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        stripped = value.strip()
        lowered = stripped.lower()
        if (
            lowered.startswith("data:")
            or "base64," in lowered
            or _ABSOLUTE_PATH_RE.match(stripped)
            or any(marker in stripped for marker in _RAW_PATH_MARKERS)
            or _RAW_FILENAME_RE.match(stripped)
        ):
            raise ProjectStateSnapshotWorkflowError(
                "project_state_raw_material_rejected",
                {"path": path, "reason": "forbidden_value"},
            )


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "PROJECT_CLOSURE_VECTOR_SCHEMA_VERSION",
    "PROJECT_STATE_SNAPSHOT_ACTIVATION_POSTURE",
    "PROJECT_STATE_SNAPSHOT_FLAGS_SCHEMA_VERSION",
    "PROJECT_STATE_SNAPSHOT_SCHEMA_VERSION",
    "PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION",
    "ProjectStateSnapshotWorkflowError",
    "build_project_state_snapshot_workflow_outputs",
    "canonical_project_state_snapshot_workflow_bytes",
    "project_state_snapshot_workflow_digest",
]
