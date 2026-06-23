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


LIFECYCLE_STAGE_STATE_WORKFLOW_SCHEMA_VERSION = (
    "capex.lifecycle_stage_state.workflow_outputs.v1"
)
LIFECYCLE_STAGE_STATE_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
LIFECYCLE_STAGE_STATE_SCHEMA_VERSION = "capex.lifecycle_stage_state.v1"
STAGE_READINESS_MATRIX_SCHEMA_VERSION = "capex.stage_readiness_matrix.v1"
LIFECYCLE_NAVIGATION_FLAGS_SCHEMA_VERSION = "capex.lifecycle_navigation_flags.v1"

LIFECYCLE_STAGE_IDS = (
    "intake",
    "baseline",
    "planning_procurement",
    "execution_delivery",
    "commissioning_closeout",
    "post_closeout",
)
READINESS_STATES = frozenset(
    {
        "not_started",
        "in_progress",
        "ready",
        "blocked_missing_evidence",
        "blocked_conflict",
        "ai_draft_only",
    }
)

_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
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
    "lifecycle_notes",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_evidence",
    "raw_file",
    "raw_filename",
    "raw_stage",
    "source_filename",
    "source_text",
    "stage_text",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class LifecycleStageStateWorkflowError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_lifecycle_stage_state_workflow_outputs(
    *,
    corpus_baseline_outputs: Mapping[str, Any],
    stage_observations: Sequence[Mapping[str, Any]],
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only CAPEX lifecycle navigation outputs."""

    _require_corpus_baseline(corpus_baseline_outputs)
    scope = _scope(corpus_baseline_outputs, "corpus_baseline_outputs")
    available_source_refs = _available_source_refs(corpus_baseline_outputs)
    if not stage_observations:
        raise LifecycleStageStateWorkflowError(
            "lifecycle_stage_observations_required",
            {"field": "stage_observations"},
        )

    state_rows: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    seen_stage_ids: set[str] = set()
    for index, observation in enumerate(stage_observations):
        if not isinstance(observation, Mapping):
            raise LifecycleStageStateWorkflowError(
                "lifecycle_stage_observation_must_be_object",
                {"index": index},
            )
        state_row, matrix_row, flags = _stage_rows(
            index=index,
            observation=observation,
            available_source_refs=available_source_refs,
        )
        stage_id = str(state_row["stage_id"])
        if stage_id in seen_stage_ids:
            raise LifecycleStageStateWorkflowError(
                "lifecycle_stage_duplicate_stage_id",
                {"index": index, "stage_id": stage_id},
            )
        seen_stage_ids.add(stage_id)
        state_rows.append(state_row)
        matrix_rows.append(matrix_row)
        flag_rows.extend(flags)

    state_rows = sorted(state_rows, key=lambda row: row["stage_order"])
    matrix_rows = sorted(matrix_rows, key=lambda row: row["stage_order"])
    flag_rows = sorted(flag_rows, key=lambda row: row["flag_id"])
    return {
        "schema_version": LIFECYCLE_STAGE_STATE_WORKFLOW_SCHEMA_VERSION,
        "activation_posture": LIFECYCLE_STAGE_STATE_ACTIVATION_POSTURE,
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
            "packet_register_id": _require_nonempty(
                corpus_baseline_outputs.get("basis", {}).get("packet_register_id")
                if isinstance(corpus_baseline_outputs.get("basis"), Mapping)
                else None,
                "corpus_baseline_outputs.basis.packet_register_id",
            ),
        },
        "lifecycle_stage_state": {
            "schema_version": LIFECYCLE_STAGE_STATE_SCHEMA_VERSION,
            "rows": state_rows,
            "row_count": len(state_rows),
            "snapshot_digest": _digest(state_rows),
        },
        "stage_readiness_matrix": {
            "schema_version": STAGE_READINESS_MATRIX_SCHEMA_VERSION,
            "rows": matrix_rows,
            "row_count": len(matrix_rows),
            "snapshot_digest": _digest(matrix_rows),
        },
        "lifecycle_navigation_flags": {
            "schema_version": LIFECYCLE_NAVIGATION_FLAGS_SCHEMA_VERSION,
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
            "official_stage_truth",
            "waterfall_gate_authority",
            "reviewed_baseline_creation",
            "closure_snapshot_creation",
            "evidence_sufficiency_claim",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_lifecycle_stage_state_workflow_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def lifecycle_stage_state_workflow_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_lifecycle_stage_state_workflow_bytes(outputs)
    ).hexdigest()


def _stage_rows(
    *,
    index: int,
    observation: Mapping[str, Any],
    available_source_refs: set[str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    _reject_raw_material(observation, path=f"stage_observations[{index}]")
    stage_id = _allowed_stage(
        observation.get("stage_id"),
        f"stage_observations[{index}].stage_id",
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
    requested_state = _allowed_readiness_state(
        observation.get("readiness_state", "in_progress"),
        f"stage_observations[{index}].readiness_state",
    )
    readiness_state, result, reason = _readiness_outcome(
        requested_state=requested_state,
        evidence_source_refs=evidence_source_refs,
        conflict_source_refs=conflict_source_refs,
        ai_draft_source_refs=ai_draft_source_refs,
    )
    stage_order = LIFECYCLE_STAGE_IDS.index(stage_id) + 1
    state_row = {
        "stage_id": stage_id,
        "stage_order": stage_order,
        "stage_label": _stage_label(stage_id),
        "readiness_state": readiness_state,
        "navigation_result": result,
        "reason": reason,
        "stage_summary": _require_nonempty(
            observation.get("stage_summary"),
            f"stage_observations[{index}].stage_summary",
        ),
        "source_refs": source_refs,
        "evidence_source_refs": evidence_source_refs,
        "conflict_source_refs": conflict_source_refs,
        "ai_draft_source_refs": ai_draft_source_refs,
        "derived_navigation_only": True,
        "official_truth": False,
    }
    matrix_row = {
        "stage_id": stage_id,
        "stage_order": stage_order,
        "readiness_state": readiness_state,
        "result": result,
        "reason": reason,
        "source_refs": source_refs,
        "evidence_source_refs": evidence_source_refs,
        "derived_navigation_only": True,
    }
    return state_row, matrix_row, _flag_rows(
        stage_id=stage_id,
        readiness_state=readiness_state,
        reason=reason,
        source_refs=source_refs,
        conflict_source_refs=conflict_source_refs,
        ai_draft_source_refs=ai_draft_source_refs,
    )


def _readiness_outcome(
    *,
    requested_state: str,
    evidence_source_refs: list[str],
    conflict_source_refs: list[str],
    ai_draft_source_refs: list[str],
) -> tuple[str, str, str]:
    if conflict_source_refs:
        return "blocked_conflict", "fail", "conflicting_lifecycle_evidence"
    if ai_draft_source_refs and not evidence_source_refs:
        return "ai_draft_only", "fail", "ai_draft_cannot_set_lifecycle_stage"
    if requested_state == "ready" and not evidence_source_refs:
        return "blocked_missing_evidence", "fail", "missing_stage_evidence"
    if requested_state == "blocked_conflict":
        return "blocked_conflict", "fail", "conflicting_lifecycle_evidence"
    if requested_state == "blocked_missing_evidence":
        return "blocked_missing_evidence", "fail", "missing_stage_evidence"
    if requested_state == "ai_draft_only":
        return "ai_draft_only", "fail", "ai_draft_cannot_set_lifecycle_stage"
    if requested_state == "ready":
        return "ready", "pass", "stage_supported_by_evidence"
    if requested_state == "not_started":
        return "not_started", "informational", "stage_not_started"
    return "in_progress", "informational", "stage_in_progress"


def _flag_rows(
    *,
    stage_id: str,
    readiness_state: str,
    reason: str,
    source_refs: list[str],
    conflict_source_refs: list[str],
    ai_draft_source_refs: list[str],
) -> list[dict[str, Any]]:
    flag_type_by_state = {
        "blocked_missing_evidence": "missing_stage_evidence",
        "blocked_conflict": "conflicting_lifecycle_evidence",
        "ai_draft_only": "ai_draft_cannot_set_lifecycle_stage",
    }
    if readiness_state not in flag_type_by_state:
        return []
    flag_type = flag_type_by_state[readiness_state]
    if readiness_state == "blocked_conflict":
        refs = conflict_source_refs
    elif readiness_state == "ai_draft_only":
        refs = ai_draft_source_refs
    else:
        refs = source_refs
    return [
        {
            "flag_id": f"{stage_id}:{flag_type}",
            "stage_id": stage_id,
            "flag_type": flag_type,
            "severity": "high" if readiness_state != "blocked_missing_evidence" else "medium",
            "reason": reason,
            "source_refs": refs,
        }
    ]


def _require_corpus_baseline(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION:
        raise LifecycleStageStateWorkflowError(
            "lifecycle_requires_corpus_baseline_outputs",
            {
                "expected_schema_version": CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _scope(raw: Mapping[str, Any], label: str) -> dict[str, str]:
    return {
        "tenant_id": _require_nonempty(raw.get("tenant_id"), f"{label}.tenant_id"),
        "domain_id": _require_nonempty(raw.get("domain_id"), f"{label}.domain_id"),
        "project_id": _require_nonempty(raw.get("project_id"), f"{label}.project_id"),
    }


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
        raise LifecycleStageStateWorkflowError(
            "lifecycle_source_basis_required",
            {"field": "corpus_baseline_outputs.generated_artifacts[].envelope.source_refs"},
        )
    return refs


def _source_refs(
    raw: Any,
    available_source_refs: set[str],
    *,
    index: int,
    field_name: str,
    required: bool,
) -> list[str]:
    if raw is None or raw == "":
        if required:
            raise LifecycleStageStateWorkflowError(
                "lifecycle_source_refs_required",
                {"index": index, "field": field_name},
            )
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise LifecycleStageStateWorkflowError(
            "lifecycle_source_refs_must_be_list",
            {"index": index, "field": field_name},
        )
    refs: list[str] = []
    for ref_index, value in enumerate(raw):
        source_ref = str(value)
        if not _SOURCE_REF_RE.match(source_ref):
            raise LifecycleStageStateWorkflowError(
                "lifecycle_source_ref_invalid",
                {"index": index, "field": field_name, "source_ref": source_ref},
            )
        if source_ref not in available_source_refs:
            raise LifecycleStageStateWorkflowError(
                "lifecycle_source_ref_not_in_corpus_baseline",
                {
                    "index": index,
                    "field": field_name,
                    "ref_index": ref_index,
                    "source_ref": source_ref,
                },
            )
        refs.append(source_ref)
    return sorted(refs)


def _allowed_stage(raw: Any, field: str) -> str:
    stage_id = _require_nonempty(raw, field)
    if stage_id not in LIFECYCLE_STAGE_IDS:
        raise LifecycleStageStateWorkflowError(
            "lifecycle_stage_id_invalid",
            {"field": field, "stage_id": stage_id, "allowed": list(LIFECYCLE_STAGE_IDS)},
        )
    return stage_id


def _allowed_readiness_state(raw: Any, field: str) -> str:
    state = _require_nonempty(raw, field)
    if state not in READINESS_STATES:
        raise LifecycleStageStateWorkflowError(
            "lifecycle_readiness_state_invalid",
            {"field": field, "state": state, "allowed": sorted(READINESS_STATES)},
        )
    return state


def _stage_label(stage_id: str) -> str:
    return stage_id.replace("_", " ").title()


def _require_nonempty(raw: Any, field: str) -> str:
    value = str(raw).strip() if raw is not None else ""
    if not value:
        raise LifecycleStageStateWorkflowError(
            "lifecycle_required_field_missing",
            {"field": field},
        )
    return value


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


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS:
                raise LifecycleStageStateWorkflowError(
                    "lifecycle_raw_material_rejected",
                    {"path": f"{path}.{key}", "reason": "forbidden_key"},
                )
            _reject_raw_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _reject_raw_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        stripped = value.strip()
        if (
            _ABSOLUTE_PATH_RE.match(stripped)
            or any(marker in stripped for marker in _RAW_PATH_MARKERS)
            or _RAW_FILENAME_RE.match(stripped)
        ):
            raise LifecycleStageStateWorkflowError(
                "lifecycle_raw_material_rejected",
                {"path": path, "reason": "raw_locator_or_filename"},
            )
