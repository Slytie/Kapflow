from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.corpus_baseline_workflow import (
    CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
)
from onetruth.capex_platform.governance_commitment_chain import (
    GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION,
)


ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION = (
    "capex.assumption_closure.workflow_outputs.v1"
)
ASSUMPTION_CLOSURE_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
COUNTERPARTY_ASSUMPTION_REGISTER_SCHEMA_VERSION = (
    "capex.counterparty_assumption_register.v1"
)
ASSUMPTION_CLOSURE_MATRIX_SCHEMA_VERSION = "capex.assumption_closure_matrix.v1"
ASSUMPTION_FLAGS_SCHEMA_VERSION = "capex.assumption_flags.v1"

ASSUMPTION_KINDS = frozenset(
    {
        "supplier",
        "counterparty",
        "commercial",
        "schedule",
        "technical",
        "interface",
        "permit",
        "safety",
        "scope",
    }
)
CLOSURE_STATES = frozenset(
    {
        "closed_with_evidence",
        "closed_by_waiver",
        "open_missing_evidence",
        "blocked_contradicted",
        "open_ai_draft_only",
    }
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "assumption_text",
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
    "local_path",
    "ocr_text",
    "path",
    "raw_assumption",
    "raw_bytes",
    "raw_content",
    "raw_evidence",
    "raw_file",
    "raw_filename",
    "source_filename",
    "source_text",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class AssumptionClosureWorkflowError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_assumption_closure_workflow_outputs(
    *,
    corpus_baseline_outputs: Mapping[str, Any],
    governance_commitment_outputs: Mapping[str, Any],
    assumption_observations: Sequence[Mapping[str, Any]],
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only assumption closure outputs from sanitized observations."""

    _require_corpus_baseline(corpus_baseline_outputs)
    _require_governance_commitment(governance_commitment_outputs)
    scope = _scope(corpus_baseline_outputs, "corpus_baseline_outputs")
    _require_same_scope(scope, governance_commitment_outputs, "governance_commitment_outputs")
    available_source_refs = _available_source_refs(corpus_baseline_outputs)
    _require_governance_source_refs_in_corpus(
        governance_commitment_outputs,
        available_source_refs=available_source_refs,
    )
    if not assumption_observations:
        raise AssumptionClosureWorkflowError(
            "assumption_observations_required",
            {"field": "assumption_observations"},
        )

    assumption_rows: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    seen_assumption_ids: set[str] = set()
    for index, observation in enumerate(assumption_observations):
        if not isinstance(observation, Mapping):
            raise AssumptionClosureWorkflowError(
                "assumption_observation_must_be_object",
                {"index": index},
            )
        assumption_row, matrix_row, flags = _assumption_rows(
            index=index,
            observation=observation,
            available_source_refs=available_source_refs,
        )
        if assumption_row["assumption_id"] in seen_assumption_ids:
            raise AssumptionClosureWorkflowError(
                "assumption_duplicate_id",
                {"index": index, "assumption_id": assumption_row["assumption_id"]},
            )
        seen_assumption_ids.add(assumption_row["assumption_id"])
        assumption_rows.append(assumption_row)
        matrix_rows.append(matrix_row)
        flag_rows.extend(flags)

    assumption_rows = sorted(assumption_rows, key=lambda row: row["assumption_id"])
    matrix_rows = sorted(matrix_rows, key=lambda row: row["assumption_id"])
    flag_rows = sorted(flag_rows, key=lambda row: row["flag_id"])
    return {
        "schema_version": ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION,
        "activation_posture": ASSUMPTION_CLOSURE_ACTIVATION_POSTURE,
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
            "governance_commitment_chain_workflow_id": _require_nonempty(
                governance_commitment_outputs.get("workflow_id"),
                "governance_commitment_outputs.workflow_id",
            ),
            "packet_register_id": _require_nonempty(
                corpus_baseline_outputs.get("basis", {}).get("packet_register_id")
                if isinstance(corpus_baseline_outputs.get("basis"), Mapping)
                else None,
                "corpus_baseline_outputs.basis.packet_register_id",
            ),
        },
        "counterparty_assumption_register": {
            "schema_version": COUNTERPARTY_ASSUMPTION_REGISTER_SCHEMA_VERSION,
            "rows": assumption_rows,
            "row_count": len(assumption_rows),
            "snapshot_digest": _digest(assumption_rows),
        },
        "assumption_closure_matrix": {
            "schema_version": ASSUMPTION_CLOSURE_MATRIX_SCHEMA_VERSION,
            "rows": matrix_rows,
            "row_count": len(matrix_rows),
            "snapshot_digest": _digest(matrix_rows),
        },
        "assumption_flags": {
            "schema_version": ASSUMPTION_FLAGS_SCHEMA_VERSION,
            "rows": flag_rows,
            "row_count": len(flag_rows),
            "snapshot_digest": _digest(flag_rows),
        },
        "truth_effects": {
            "creates_workflow_run": False,
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
            "closure_snapshot_creation",
            "evidence_sufficiency_claim",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_assumption_closure_workflow_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def assumption_closure_workflow_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_assumption_closure_workflow_bytes(outputs)
    ).hexdigest()


def _assumption_rows(
    *,
    index: int,
    observation: Mapping[str, Any],
    available_source_refs: set[str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    _reject_raw_material(observation, path=f"assumption_observations[{index}]")
    assumption_id = _require_nonempty(
        observation.get("assumption_id"),
        f"assumption_observations[{index}].assumption_id",
    )
    counterparty_id = _require_nonempty(
        observation.get("counterparty_id"),
        f"assumption_observations[{index}].counterparty_id",
    )
    assumption_kind = _allowed(
        observation.get("assumption_kind"),
        ASSUMPTION_KINDS,
        f"assumption_observations[{index}].assumption_kind",
        "assumption_kind_invalid",
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
    contradicted_by_source_refs = _source_refs(
        observation.get("contradicted_by_source_refs"),
        available_source_refs,
        index=index,
        field_name="contradicted_by_source_refs",
        required=False,
    )
    ai_draft_source_refs = _source_refs(
        observation.get("ai_draft_source_refs"),
        available_source_refs,
        index=index,
        field_name="ai_draft_source_refs",
        required=False,
    )
    waiver_ids = _ids(observation.get("waiver_ids"), field_name="waiver_ids", index=index)
    closure_state, result, reason = _closure_outcome(
        evidence_source_refs=evidence_source_refs,
        waiver_ids=waiver_ids,
        contradicted_by_source_refs=contradicted_by_source_refs,
        ai_draft_source_refs=ai_draft_source_refs,
    )
    assumption_row = {
        "assumption_id": assumption_id,
        "counterparty_id": counterparty_id,
        "assumption_kind": assumption_kind,
        "assumption_summary": _require_nonempty(
            observation.get("assumption_summary"),
            f"assumption_observations[{index}].assumption_summary",
        ),
        "owner_role": _optional_text(observation.get("owner_role")),
        "source_refs": source_refs,
        "official_truth": False,
    }
    matrix_row = {
        "assumption_id": assumption_id,
        "counterparty_id": counterparty_id,
        "closure_state": closure_state,
        "result": result,
        "reason": reason,
        "source_refs": source_refs,
        "evidence_source_refs": evidence_source_refs,
        "waiver_refs": [f"waiver:{waiver_id}" for waiver_id in waiver_ids],
        "contradicted_by_source_refs": contradicted_by_source_refs,
        "ai_draft_source_refs": ai_draft_source_refs,
        "closeable": closure_state in {"closed_with_evidence", "closed_by_waiver"},
    }
    return assumption_row, matrix_row, _flag_rows(
        assumption_id=assumption_id,
        counterparty_id=counterparty_id,
        closure_state=closure_state,
        reason=reason,
        source_refs=source_refs,
        contradicted_by_source_refs=contradicted_by_source_refs,
        ai_draft_source_refs=ai_draft_source_refs,
    )


def _closure_outcome(
    *,
    evidence_source_refs: list[str],
    waiver_ids: list[str],
    contradicted_by_source_refs: list[str],
    ai_draft_source_refs: list[str],
) -> tuple[str, str, str]:
    if contradicted_by_source_refs:
        return "blocked_contradicted", "fail", "contradicted_evidence"
    if evidence_source_refs:
        return "closed_with_evidence", "pass", "evidence_specific_closure"
    if waiver_ids:
        return "closed_by_waiver", "satisfied_by_waiver", "waiver_satisfies_dimension"
    if ai_draft_source_refs:
        return "open_ai_draft_only", "fail", "ai_draft_cannot_close"
    return "open_missing_evidence", "fail", "missing_evidence"


def _flag_rows(
    *,
    assumption_id: str,
    counterparty_id: str,
    closure_state: str,
    reason: str,
    source_refs: list[str],
    contradicted_by_source_refs: list[str],
    ai_draft_source_refs: list[str],
) -> list[dict[str, Any]]:
    if closure_state == "closed_with_evidence" or closure_state == "closed_by_waiver":
        return []
    if closure_state == "blocked_contradicted":
        return [
            {
                "flag_id": f"{assumption_id}:contradicted-evidence",
                "assumption_id": assumption_id,
                "counterparty_id": counterparty_id,
                "flag_type": "contradicted_evidence",
                "severity": "high",
                "reason": reason,
                "source_refs": contradicted_by_source_refs,
            }
        ]
    if closure_state == "open_ai_draft_only":
        return [
            {
                "flag_id": f"{assumption_id}:ai-draft-cannot-close",
                "assumption_id": assumption_id,
                "counterparty_id": counterparty_id,
                "flag_type": "ai_draft_cannot_close",
                "severity": "high",
                "reason": reason,
                "source_refs": ai_draft_source_refs,
            }
        ]
    return [
        {
            "flag_id": f"{assumption_id}:missing-evidence",
            "assumption_id": assumption_id,
            "counterparty_id": counterparty_id,
            "flag_type": "missing_evidence",
            "severity": "medium",
            "reason": reason,
            "source_refs": source_refs,
        }
    ]


def _require_corpus_baseline(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION:
        raise AssumptionClosureWorkflowError(
            "assumption_requires_corpus_baseline_outputs",
            {
                "expected_schema_version": CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _require_governance_commitment(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION:
        raise AssumptionClosureWorkflowError(
            "assumption_requires_governance_commitment_outputs",
            {
                "expected_schema_version": GOVERNANCE_COMMITMENT_CHAIN_SCHEMA_VERSION,
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
        raise AssumptionClosureWorkflowError(
            "assumption_workflow_scope_mismatch",
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
        raise AssumptionClosureWorkflowError(
            "assumption_source_basis_required",
            {"field": "corpus_baseline_outputs.generated_artifacts[].envelope.source_refs"},
        )
    return refs


def _require_governance_source_refs_in_corpus(
    governance_commitment_outputs: Mapping[str, Any],
    *,
    available_source_refs: set[str],
) -> None:
    for source_ref in _source_refs_in_governance(governance_commitment_outputs):
        if source_ref not in available_source_refs:
            raise AssumptionClosureWorkflowError(
                "assumption_governance_source_ref_not_in_corpus_baseline",
                {"source_ref": source_ref},
            )


def _source_refs_in_governance(raw: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for section_name in ("commitment_chain", "expenditure_ledger", "commitment_flags"):
        section = raw.get(section_name)
        if not isinstance(section, Mapping):
            continue
        for row in section.get("rows") or []:
            if not isinstance(row, Mapping):
                continue
            for source_ref in row.get("source_refs") or []:
                refs.add(str(source_ref))
    return refs


def _source_refs(
    value: Any,
    available_source_refs: set[str],
    *,
    index: int,
    field_name: str,
    required: bool,
) -> list[str]:
    if value is None:
        if required:
            raise AssumptionClosureWorkflowError(
                "assumption_source_refs_required",
                {"index": index, "field": field_name},
            )
        return []
    if not isinstance(value, list) or (required and not value):
        raise AssumptionClosureWorkflowError(
            "assumption_source_refs_required",
            {"index": index, "field": field_name},
        )
    refs: list[str] = []
    for ref_index, raw_ref in enumerate(value):
        source_ref = _require_nonempty(raw_ref, f"assumption_observations[{index}].{field_name}[{ref_index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise AssumptionClosureWorkflowError(
                "assumption_source_ref_invalid",
                {"index": index, "field": field_name, "source_ref": source_ref},
            )
        if source_ref not in available_source_refs:
            raise AssumptionClosureWorkflowError(
                "assumption_source_ref_not_in_corpus_baseline",
                {"index": index, "field": field_name, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise AssumptionClosureWorkflowError(
                "assumption_duplicate_source_ref",
                {"index": index, "field": field_name, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _ids(value: Any, *, field_name: str, index: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise AssumptionClosureWorkflowError(
            "assumption_id_list_invalid",
            {"index": index, "field": field_name},
        )
    ids: list[str] = []
    for value_index, raw_id in enumerate(value):
        normalized = _require_nonempty(
            raw_id,
            f"assumption_observations[{index}].{field_name}[{value_index}]",
        )
        if normalized in ids:
            raise AssumptionClosureWorkflowError(
                "assumption_duplicate_id_ref",
                {"index": index, "field": field_name, "id": normalized},
            )
        ids.append(normalized)
    return sorted(ids)


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field_name: str,
    error_code: str,
) -> str:
    normalized = _require_nonempty(value, field_name)
    if normalized not in allowed:
        raise AssumptionClosureWorkflowError(
            error_code,
            {"field": field_name, "value": normalized, "allowed": sorted(allowed)},
        )
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_RAW_KEYS or key_text.startswith("raw_"):
                raise AssumptionClosureWorkflowError(
                    "assumption_raw_field_forbidden",
                    {"path": path, "field": key_text},
                )
            _reject_raw_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, list | tuple):
        for index, nested in enumerate(value):
            _reject_raw_material(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if lowered.startswith("data:") or "base64," in lowered:
            raise AssumptionClosureWorkflowError(
                "assumption_inline_content_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise AssumptionClosureWorkflowError(
                "assumption_raw_value_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise AssumptionClosureWorkflowError(
                "assumption_raw_value_forbidden",
                {"path": path},
            )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _require_nonempty(value: Any, field_name: str) -> str:
    if value is None:
        raise AssumptionClosureWorkflowError(
            "assumption_required_field_missing",
            {"field": field_name},
        )
    normalized = str(value).strip()
    if not normalized:
        raise AssumptionClosureWorkflowError(
            "assumption_required_field_missing",
            {"field": field_name},
        )
    return normalized


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
    "ASSUMPTION_CLOSURE_ACTIVATION_POSTURE",
    "ASSUMPTION_CLOSURE_MATRIX_SCHEMA_VERSION",
    "ASSUMPTION_CLOSURE_WORKFLOW_SCHEMA_VERSION",
    "ASSUMPTION_FLAGS_SCHEMA_VERSION",
    "ASSUMPTION_KINDS",
    "CLOSURE_STATES",
    "COUNTERPARTY_ASSUMPTION_REGISTER_SCHEMA_VERSION",
    "AssumptionClosureWorkflowError",
    "assumption_closure_workflow_digest",
    "build_assumption_closure_workflow_outputs",
    "canonical_assumption_closure_workflow_bytes",
]
