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


OWNER_INTERFACE_RESOLUTION_WORKFLOW_SCHEMA_VERSION = (
    "capex.owner_interface_resolution.workflow_outputs.v1"
)
OWNER_INTERFACE_RESOLUTION_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)
DISTRIBUTED_REQUIREMENT_REGISTER_SCHEMA_VERSION = (
    "capex.distributed_requirement_register.v1"
)
INTERFACE_REGISTER_SCHEMA_VERSION = "capex.interface_register.v1"
OWNER_INTERFACE_FLAGS_SCHEMA_VERSION = "capex.owner_interface_flags.v1"

REQUIREMENT_KINDS = frozenset(
    {
        "owner_decision",
        "site_access",
        "supplier_deliverable",
        "contractor_deliverable",
        "permit",
        "safety",
        "scope",
        "technical_interface",
    }
)
INTERFACE_KINDS = frozenset(
    {"owner", "site", "supplier", "contractor", "utility", "regulator", "internal"}
)
RESOLUTION_STATES = frozenset(
    {
        "resolved_with_evidence",
        "open_missing_responsibility",
        "open_missing_evidence",
        "blocked_conflict",
        "open_ai_draft_only",
        "open_waiver_only",
    }
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_ASSUMPTION_REF_RE = re.compile(r"^assumption:[A-Za-z0-9_.:-]+$")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "document_text",
    "evidence_text",
    "extracted_text",
    "file_name",
    "filename",
    "full_text",
    "interface_notes",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_evidence",
    "raw_file",
    "raw_filename",
    "raw_interface",
    "raw_requirement",
    "requirement_text",
    "source_filename",
    "source_text",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class OwnerInterfaceResolutionWorkflowError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_owner_interface_resolution_workflow_outputs(
    *,
    corpus_baseline_outputs: Mapping[str, Any],
    assumption_closure_outputs: Mapping[str, Any],
    interface_observations: Sequence[Mapping[str, Any]],
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only owner interface resolution outputs."""

    _require_corpus_baseline(corpus_baseline_outputs)
    _require_assumption_closure(assumption_closure_outputs)
    scope = _scope(corpus_baseline_outputs, "corpus_baseline_outputs")
    _require_same_scope(scope, assumption_closure_outputs, "assumption_closure_outputs")
    available_source_refs = _available_source_refs(corpus_baseline_outputs)
    known_assumptions = _known_assumption_ids(assumption_closure_outputs)
    _require_assumption_source_refs_in_corpus(
        assumption_closure_outputs,
        available_source_refs=available_source_refs,
    )
    if not interface_observations:
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_observations_required",
            {"field": "interface_observations"},
        )

    requirement_rows: list[dict[str, Any]] = []
    interface_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    seen_requirement_ids: set[str] = set()
    seen_interface_ids: set[str] = set()
    for index, observation in enumerate(interface_observations):
        if not isinstance(observation, Mapping):
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_observation_must_be_object",
                {"index": index},
            )
        requirement_row, interface_row, flags = _interface_rows(
            index=index,
            observation=observation,
            available_source_refs=available_source_refs,
            known_assumptions=known_assumptions,
        )
        if requirement_row["requirement_id"] in seen_requirement_ids:
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_duplicate_requirement_id",
                {"index": index, "requirement_id": requirement_row["requirement_id"]},
            )
        if interface_row["interface_id"] in seen_interface_ids:
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_duplicate_interface_id",
                {"index": index, "interface_id": interface_row["interface_id"]},
            )
        seen_requirement_ids.add(requirement_row["requirement_id"])
        seen_interface_ids.add(interface_row["interface_id"])
        requirement_rows.append(requirement_row)
        interface_rows.append(interface_row)
        flag_rows.extend(flags)

    requirement_rows = sorted(requirement_rows, key=lambda row: row["requirement_id"])
    interface_rows = sorted(interface_rows, key=lambda row: row["interface_id"])
    flag_rows = sorted(flag_rows, key=lambda row: row["flag_id"])
    return {
        "schema_version": OWNER_INTERFACE_RESOLUTION_WORKFLOW_SCHEMA_VERSION,
        "activation_posture": OWNER_INTERFACE_RESOLUTION_ACTIVATION_POSTURE,
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
            "assumption_closure_workflow_id": _require_nonempty(
                assumption_closure_outputs.get("workflow_id"),
                "assumption_closure_outputs.workflow_id",
            ),
            "packet_register_id": _require_nonempty(
                corpus_baseline_outputs.get("basis", {}).get("packet_register_id")
                if isinstance(corpus_baseline_outputs.get("basis"), Mapping)
                else None,
                "corpus_baseline_outputs.basis.packet_register_id",
            ),
        },
        "distributed_requirement_register": {
            "schema_version": DISTRIBUTED_REQUIREMENT_REGISTER_SCHEMA_VERSION,
            "rows": requirement_rows,
            "row_count": len(requirement_rows),
            "snapshot_digest": _digest(requirement_rows),
        },
        "interface_register": {
            "schema_version": INTERFACE_REGISTER_SCHEMA_VERSION,
            "rows": interface_rows,
            "row_count": len(interface_rows),
            "snapshot_digest": _digest(interface_rows),
        },
        "owner_interface_flags": {
            "schema_version": OWNER_INTERFACE_FLAGS_SCHEMA_VERSION,
            "rows": flag_rows,
            "row_count": len(flag_rows),
            "snapshot_digest": _digest(flag_rows),
        },
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_tasks": False,
            "creates_approvals": False,
            "creates_closure_snapshots": False,
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
            "responsibility_assignment_authority",
            "closure_snapshot_creation",
            "evidence_sufficiency_claim",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_owner_interface_resolution_workflow_bytes(
    outputs: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def owner_interface_resolution_workflow_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_owner_interface_resolution_workflow_bytes(outputs)
    ).hexdigest()


def _interface_rows(
    *,
    index: int,
    observation: Mapping[str, Any],
    available_source_refs: set[str],
    known_assumptions: set[str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    _reject_raw_material(observation, path=f"interface_observations[{index}]")
    requirement_id = _require_nonempty(
        observation.get("requirement_id"),
        f"interface_observations[{index}].requirement_id",
    )
    interface_id = _require_nonempty(
        observation.get("interface_id"),
        f"interface_observations[{index}].interface_id",
    )
    requirement_kind = _allowed(
        observation.get("requirement_kind"),
        REQUIREMENT_KINDS,
        f"interface_observations[{index}].requirement_kind",
        "owner_interface_requirement_kind_invalid",
    )
    interface_kind = _allowed(
        observation.get("interface_kind"),
        INTERFACE_KINDS,
        f"interface_observations[{index}].interface_kind",
        "owner_interface_kind_invalid",
    )
    source_refs = _source_refs(
        observation.get("source_refs"),
        available_source_refs,
        index=index,
        field_name="source_refs",
        required=True,
    )
    evidence_source_refs = _source_refs(
        observation.get("evidence_source_refs"),
        available_source_refs,
        index=index,
        field_name="evidence_source_refs",
        required=False,
    )
    conflict_source_refs = _source_refs(
        observation.get("conflict_source_refs"),
        available_source_refs,
        index=index,
        field_name="conflict_source_refs",
        required=False,
    )
    ai_draft_source_refs = _source_refs(
        observation.get("ai_draft_source_refs"),
        available_source_refs,
        index=index,
        field_name="ai_draft_source_refs",
        required=False,
    )
    assumption_refs = _assumption_refs(
        observation.get("assumption_refs"),
        known_assumptions=known_assumptions,
        index=index,
    )
    waiver_ids = _ids(observation.get("waiver_ids"), field_name="waiver_ids", index=index)
    conflicting_responsible_party_ids = _ids(
        observation.get("conflicting_responsible_party_ids"),
        field_name="conflicting_responsible_party_ids",
        index=index,
    )
    previous_responsible_party_id = _optional_text(
        observation.get("previous_responsible_party_id")
    )
    responsible_party_id = _optional_text(observation.get("responsible_party_id"))
    handoff_to_party_id = _optional_text(observation.get("handoff_to_party_id"))
    if previous_responsible_party_id and not (responsible_party_id or handoff_to_party_id):
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_responsibility_disappeared",
            {
                "index": index,
                "requirement_id": requirement_id,
                "previous_responsible_party_id": previous_responsible_party_id,
            },
        )
    assigned_responsible_party_id = responsible_party_id or handoff_to_party_id
    state, result, reason = _resolution_outcome(
        assigned_responsible_party_id=assigned_responsible_party_id,
        evidence_source_refs=evidence_source_refs,
        conflict_source_refs=conflict_source_refs,
        conflicting_responsible_party_ids=conflicting_responsible_party_ids,
        ai_draft_source_refs=ai_draft_source_refs,
        waiver_ids=waiver_ids,
    )
    requirement_row = {
        "requirement_id": requirement_id,
        "interface_id": interface_id,
        "requirement_kind": requirement_kind,
        "requirement_summary": _require_nonempty(
            observation.get("requirement_summary"),
            f"interface_observations[{index}].requirement_summary",
        ),
        "assumption_refs": assumption_refs,
        "responsible_party_id": assigned_responsible_party_id,
        "source_refs": source_refs,
        "official_truth": False,
    }
    interface_row = {
        "interface_id": interface_id,
        "requirement_id": requirement_id,
        "interface_kind": interface_kind,
        "owner_party_id": _optional_text(observation.get("owner_party_id")),
        "site_party_id": _optional_text(observation.get("site_party_id")),
        "supplier_party_id": _optional_text(observation.get("supplier_party_id")),
        "previous_responsible_party_id": previous_responsible_party_id,
        "responsible_party_id": assigned_responsible_party_id,
        "handoff_to_party_id": handoff_to_party_id,
        "resolution_state": state,
        "result": result,
        "reason": reason,
        "evidence_source_refs": evidence_source_refs,
        "conflict_source_refs": conflict_source_refs,
        "conflicting_responsible_party_ids": conflicting_responsible_party_ids,
        "ai_draft_source_refs": ai_draft_source_refs,
        "waiver_refs": [f"waiver:{waiver_id}" for waiver_id in waiver_ids],
        "source_refs": source_refs,
        "resolved_authoritatively": False,
    }
    return requirement_row, interface_row, _flag_rows(
        requirement_id=requirement_id,
        interface_id=interface_id,
        state=state,
        reason=reason,
        source_refs=source_refs,
        conflict_source_refs=conflict_source_refs,
        ai_draft_source_refs=ai_draft_source_refs,
    )


def _resolution_outcome(
    *,
    assigned_responsible_party_id: str | None,
    evidence_source_refs: list[str],
    conflict_source_refs: list[str],
    conflicting_responsible_party_ids: list[str],
    ai_draft_source_refs: list[str],
    waiver_ids: list[str],
) -> tuple[str, str, str]:
    if conflict_source_refs or conflicting_responsible_party_ids:
        return "blocked_conflict", "fail", "conflicting_responsibility"
    if assigned_responsible_party_id and evidence_source_refs:
        return "resolved_with_evidence", "pass", "responsibility_supported_by_evidence"
    if ai_draft_source_refs and not evidence_source_refs:
        return "open_ai_draft_only", "fail", "ai_draft_cannot_resolve"
    if waiver_ids and not evidence_source_refs:
        return "open_waiver_only", "waiver_recorded_not_resolved", "waiver_not_responsibility"
    if not assigned_responsible_party_id:
        return "open_missing_responsibility", "fail", "missing_responsibility"
    return "open_missing_evidence", "fail", "missing_evidence"


def _flag_rows(
    *,
    requirement_id: str,
    interface_id: str,
    state: str,
    reason: str,
    source_refs: list[str],
    conflict_source_refs: list[str],
    ai_draft_source_refs: list[str],
) -> list[dict[str, Any]]:
    if state == "resolved_with_evidence":
        return []
    flag_type_by_state = {
        "blocked_conflict": "conflicting_responsibility",
        "open_ai_draft_only": "ai_draft_cannot_resolve",
        "open_missing_responsibility": "missing_responsibility",
        "open_missing_evidence": "missing_evidence",
        "open_waiver_only": "waiver_not_responsibility",
    }
    severity_by_state = {
        "blocked_conflict": "high",
        "open_ai_draft_only": "high",
        "open_missing_responsibility": "high",
        "open_missing_evidence": "medium",
        "open_waiver_only": "medium",
    }
    flag_type = flag_type_by_state[state]
    if state == "blocked_conflict":
        refs = conflict_source_refs
    elif state == "open_ai_draft_only":
        refs = ai_draft_source_refs
    else:
        refs = source_refs
    return [
        {
            "flag_id": f"{interface_id}:{flag_type}",
            "requirement_id": requirement_id,
            "interface_id": interface_id,
            "flag_type": flag_type,
            "severity": severity_by_state[state],
            "reason": reason,
            "source_refs": refs,
        }
    ]


def _require_corpus_baseline(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION:
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_requires_corpus_baseline_outputs",
            {
                "expected_schema_version": CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _require_assumption_closure(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION:
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_requires_assumption_closure_outputs",
            {
                "expected_schema_version": ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION,
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
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_scope_mismatch",
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
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_source_basis_required",
            {"field": "corpus_baseline_outputs.generated_artifacts[].envelope.source_refs"},
        )
    return refs


def _known_assumption_ids(assumption_closure_outputs: Mapping[str, Any]) -> set[str]:
    register = assumption_closure_outputs.get("counterparty_assumption_register")
    if not isinstance(register, Mapping):
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_assumption_register_required",
            {"field": "counterparty_assumption_register"},
        )
    rows = register.get("rows")
    if not isinstance(rows, list) or not rows:
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_assumption_rows_required",
            {"field": "counterparty_assumption_register.rows"},
        )
    assumption_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_assumption_row_must_be_object",
                {"index": index},
            )
        assumption_ids.add(
            _require_nonempty(
                row.get("assumption_id"),
                f"counterparty_assumption_register.rows[{index}].assumption_id",
            )
        )
    return assumption_ids


def _require_assumption_source_refs_in_corpus(
    assumption_closure_outputs: Mapping[str, Any],
    *,
    available_source_refs: set[str],
) -> None:
    for source_ref in _source_refs_in_assumption_outputs(assumption_closure_outputs):
        if source_ref not in available_source_refs:
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_assumption_source_ref_not_in_corpus_baseline",
                {"source_ref": source_ref},
            )


def _source_refs_in_assumption_outputs(raw: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for section_name in (
        "counterparty_assumption_register",
        "assumption_closure_matrix",
        "assumption_flags",
    ):
        section = raw.get(section_name)
        if not isinstance(section, Mapping):
            continue
        rows = section.get("rows")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            for key in (
                "source_refs",
                "evidence_source_refs",
                "contradicted_by_source_refs",
                "ai_draft_source_refs",
            ):
                value = row.get(key)
                if isinstance(value, list):
                    for source_ref in value:
                        source_ref_text = str(source_ref)
                        if _SOURCE_REF_RE.match(source_ref_text):
                            refs.add(source_ref_text)
    return refs


def _source_refs(
    value: Any,
    available_source_refs: set[str],
    *,
    index: int,
    field_name: str,
    required: bool,
) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value):
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_source_refs_required",
            {"index": index, "field": field_name},
        )
    refs: list[str] = []
    for source_ref in value:
        source_ref_text = _require_nonempty(source_ref, field_name)
        if not _SOURCE_REF_RE.match(source_ref_text):
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_source_ref_invalid",
                {"index": index, "source_ref": source_ref_text},
            )
        if source_ref_text not in available_source_refs:
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_source_ref_not_in_corpus_baseline",
                {"index": index, "source_ref": source_ref_text},
            )
        refs.append(source_ref_text)
    return sorted(set(refs))


def _assumption_refs(
    value: Any,
    *,
    known_assumptions: set[str],
    index: int,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_assumption_refs_invalid",
            {"index": index},
        )
    refs: list[str] = []
    for assumption_ref in value:
        assumption_ref_text = _require_nonempty(assumption_ref, "assumption_refs")
        if not _ASSUMPTION_REF_RE.match(assumption_ref_text):
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_assumption_ref_invalid",
                {"index": index, "assumption_ref": assumption_ref_text},
            )
        assumption_id = assumption_ref_text.removeprefix("assumption:")
        if assumption_id not in known_assumptions:
            raise OwnerInterfaceResolutionWorkflowError(
                "owner_interface_unknown_assumption_ref",
                {"index": index, "assumption_ref": assumption_ref_text},
            )
        refs.append(assumption_ref_text)
    return sorted(set(refs))


def _ids(value: Any, *, field_name: str, index: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_ids_invalid",
            {"index": index, "field": field_name},
        )
    ids: list[str] = []
    for item in value:
        ids.append(_require_nonempty(item, f"interface_observations[{index}].{field_name}[]"))
    return sorted(set(ids))


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_code: str,
) -> str:
    text = _require_nonempty(value, field)
    if text not in allowed:
        raise OwnerInterfaceResolutionWorkflowError(
            error_code,
            {"field": field, "value": text, "allowed": sorted(allowed)},
        )
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return _require_nonempty(value, "optional_text")


def _require_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_nonempty_string_required",
            {"field": field},
        )
    text = value.strip()
    _reject_raw_value(text, path=field)
    return text


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_RAW_KEYS:
                raise OwnerInterfaceResolutionWorkflowError(
                    "owner_interface_raw_field_forbidden",
                    {"path": f"{path}.{key_text}"},
                )
            _reject_raw_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_raw_material(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        _reject_raw_value(value, path=path)


def _reject_raw_value(value: str, *, path: str) -> None:
    if value.startswith("data:") or "base64," in value:
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_inline_content_forbidden",
            {"path": path},
        )
    if (
        _ABSOLUTE_PATH_RE.match(value)
        or _RAW_FILENAME_RE.match(value)
        or any(marker in value for marker in _RAW_PATH_MARKERS)
    ):
        raise OwnerInterfaceResolutionWorkflowError(
            "owner_interface_raw_value_forbidden",
            {"path": path},
        )


def _digest(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(
        list(rows),
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
