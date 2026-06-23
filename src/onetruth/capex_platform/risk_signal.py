from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


RISK_SIGNAL_OUTPUTS_SCHEMA_VERSION = "capex.risk_signal.outputs.v1"
RISK_SIGNAL_REGISTER_SCHEMA_VERSION = "capex.risk_signal_register.v1"
RISK_SIGNAL_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION = (
    "capex.risk_ceo_transparency.workflow_outputs.v1"
)

SEVERITIES = frozenset({"critical", "high", "medium", "low", "informational"})
RISK_SIGNAL_STATUSES = frozenset(
    {
        "closed",
        "monitoring",
        "open",
        "blocked_missing_evidence",
        "blocked_conflict",
        "ai_draft_only",
        "waiver_recorded",
        "blocked_stale_pointer",
    }
)

_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RISK_REF_RE = re.compile(r"^risk_state_item:[A-Za-z0-9_.:-]+$")
_RISK_SIGNAL_ID_RE = re.compile(r"^risk_signal:[A-Za-z0-9_.:-]+$")
_PREDICATE_ID_RE = re.compile(r"^predicate:[A-Za-z0-9_.:-]+$")
_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "ai_completion",
    "ai_output",
    "ai_prompt",
    "ai_response",
    "ai_summary",
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
    "raw_ai",
    "raw_ai_text",
    "raw_bytes",
    "raw_content",
    "raw_corpus",
    "raw_evidence",
    "raw_file",
    "raw_filename",
    "raw_log",
    "raw_risk",
    "risk_text",
    "source_filename",
    "source_text",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class RiskSignalError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_risk_signal_outputs(
    *,
    risk_ceo_transparency_outputs: Mapping[str, Any],
    signal_register_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    policy_version: str,
    signal_observations: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build planning-only RiskSignal register outputs."""

    _require_risk_ceo_outputs(risk_ceo_transparency_outputs)
    _reject_raw_material(
        risk_ceo_transparency_outputs,
        path="risk_ceo_transparency_outputs",
    )
    scope = _scope(risk_ceo_transparency_outputs, "risk_ceo_transparency_outputs")
    normalized_policy_version = _require_nonempty(policy_version, "policy_version")
    risk_rows = _risk_rows(risk_ceo_transparency_outputs)
    flags = _risk_ceo_flags(risk_ceo_transparency_outputs)
    known_source_refs = _known_source_refs(risk_ceo_transparency_outputs)
    known_risk_refs = {str(row["risk_ref"]) for row in risk_rows}
    risk_by_ref = {str(row["risk_ref"]): row for row in risk_rows}
    input_digests = _basis_digests(risk_ceo_transparency_outputs)

    rows: list[dict[str, Any]] = []
    raw_rows = (
        _derived_signal_observations(risk_rows)
        if signal_observations is None
        else list(signal_observations)
    )
    if not raw_rows:
        raise RiskSignalError(
            "risk_signal_rows_required",
            {"field": "signal_observations"},
        )

    seen_signal_ids: set[str] = set()
    seen_predicates: set[tuple[str, str]] = set()
    for index, raw_row in enumerate(raw_rows):
        row = _risk_signal_row(
            index=index,
            raw_row=raw_row,
            policy_version=normalized_policy_version,
            input_digests=input_digests,
            known_risk_refs=known_risk_refs,
            known_source_refs=known_source_refs,
            risk_by_ref=risk_by_ref,
        )
        if row["risk_signal_id"] in seen_signal_ids:
            raise RiskSignalError(
                "risk_signal_duplicate_id",
                {"index": index, "risk_signal_id": row["risk_signal_id"]},
            )
        seen_signal_ids.add(row["risk_signal_id"])
        predicate_key = (row["predicate_id"], row["risk_ref"])
        if predicate_key in seen_predicates:
            raise RiskSignalError(
                "risk_signal_duplicate_predicate_for_risk",
                {
                    "index": index,
                    "predicate_id": row["predicate_id"],
                    "risk_ref": row["risk_ref"],
                },
            )
        seen_predicates.add(predicate_key)
        rows.append(row)

    rows = sorted(rows, key=lambda row: row["risk_signal_id"])
    register = {
        "schema_version": RISK_SIGNAL_REGISTER_SCHEMA_VERSION,
        "rows": rows,
        "row_count": len(rows),
        "register_digest": _digest(rows),
    }
    outputs = {
        "schema_version": RISK_SIGNAL_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": RISK_SIGNAL_ACTIVATION_POSTURE,
        "signal_register_id": _require_nonempty(
            signal_register_id,
            "signal_register_id",
        ),
        "tenant_id": scope["tenant_id"],
        "domain_id": scope["domain_id"],
        "project_id": scope["project_id"],
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "policy_version": normalized_policy_version,
        "basis": {
            "risk_ceo_transparency_workflow_id": _require_nonempty(
                risk_ceo_transparency_outputs.get("workflow_id"),
                "risk_ceo_transparency_outputs.workflow_id",
            ),
            "risk_state_snapshot_digest": input_digests["risk_state_snapshot_digest"],
            "ceo_transparency_snapshot_digest": input_digests[
                "ceo_transparency_snapshot_digest"
            ],
            "risk_ceo_flags_digest": input_digests["risk_ceo_flags_digest"],
        },
        "source_refs": sorted(known_source_refs),
        "risk_signal_register": register,
        "risk_signal_summary": {
            "risk_signal_count": len(rows),
            "critical_count": sum(1 for row in rows if row["severity"] == "critical"),
            "blocked_count": sum(
                1 for row in rows if str(row["status"]).startswith("blocked_")
            ),
            "ai_draft_only_count": sum(
                1 for row in rows if row["status"] == "ai_draft_only"
            ),
            "waiver_recorded_count": sum(
                1 for row in rows if row["status"] == "waiver_recorded"
            ),
            "risk_ceo_flag_count": len(flags),
        },
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_tasks": False,
            "creates_approvals": False,
            "creates_risk_engine_state": False,
            "creates_risk_signal_runtime_state": False,
            "creates_ceo_cockpit_state": False,
            "creates_closure_snapshots": False,
            "creates_official_project_state": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "runtime_risk_engine_activation",
            "ceo_cockpit_activation",
            "public_route_activation",
            "frontend_route_activation",
            "authored_workflow_pack_activation",
            "raw_corpus_import",
            "official_project_state",
            "closure_snapshot_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }
    canonical_risk_signal_outputs_bytes(outputs)
    return outputs


def canonical_risk_signal_outputs_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def risk_signal_outputs_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_risk_signal_outputs_bytes(outputs)
    ).hexdigest()


def _derived_signal_observations(
    risk_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for risk in risk_rows:
        risk_id = _require_nonempty(risk.get("risk_id"), "risk_state_snapshot.rows[].risk_id")
        risk_kind = _require_nonempty(
            risk.get("risk_kind"),
            f"risk_state_snapshot.rows[{risk_id}].risk_kind",
        )
        risk_status = _require_nonempty(
            risk.get("risk_status"),
            f"risk_state_snapshot.rows[{risk_id}].risk_status",
        )
        rows.append(
            {
                "risk_signal_id": f"risk_signal:{risk_id}",
                "predicate_id": f"predicate:{risk_kind}:{risk_status}",
                "risk_ref": risk.get("risk_ref"),
                "severity": risk.get("severity"),
                "status": risk_status,
                "owner_role": risk.get("owner_role"),
                "source_refs": risk.get("source_refs"),
            }
        )
    return rows


def _risk_signal_row(
    *,
    index: int,
    raw_row: Mapping[str, Any],
    policy_version: str,
    input_digests: Mapping[str, str],
    known_risk_refs: set[str],
    known_source_refs: set[str],
    risk_by_ref: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(raw_row, Mapping):
        raise RiskSignalError("risk_signal_row_must_be_object", {"index": index})
    _reject_raw_material(raw_row, path=f"signal_observations[{index}]")
    risk_ref = _risk_ref(raw_row.get("risk_ref"), index=index, known_risk_refs=known_risk_refs)
    risk_row = risk_by_ref[risk_ref]
    row_policy_version = raw_row.get("policy_version")
    if row_policy_version is not None and str(row_policy_version) != policy_version:
        raise RiskSignalError(
            "risk_signal_policy_version_mismatch",
            {
                "index": index,
                "expected": policy_version,
                "actual": str(row_policy_version),
            },
        )
    source_refs = _source_refs(
        raw_row.get("source_refs"),
        known_source_refs=known_source_refs,
        field=f"signal_observations[{index}].source_refs",
    )
    row = {
        "risk_signal_id": _risk_signal_id(raw_row.get("risk_signal_id"), index=index),
        "predicate_id": _predicate_id(raw_row.get("predicate_id"), index=index),
        "risk_ref": risk_ref,
        "severity": _allowed(
            raw_row.get("severity"),
            SEVERITIES,
            f"signal_observations[{index}].severity",
            "risk_signal_severity_invalid",
        ),
        "status": _allowed(
            raw_row.get("status"),
            RISK_SIGNAL_STATUSES,
            f"signal_observations[{index}].status",
            "risk_signal_status_invalid",
        ),
        "owner_role": _require_nonempty(
            raw_row.get("owner_role") or risk_row.get("owner_role"),
            f"signal_observations[{index}].owner_role",
        ),
        "source_refs": source_refs,
        "policy_version": policy_version,
        "input_digests": [
            input_digests["risk_state_snapshot_digest"],
            input_digests["ceo_transparency_snapshot_digest"],
            input_digests["risk_ceo_flags_digest"],
        ],
        "creates_runtime_risk_state": False,
        "creates_official_truth": False,
    }
    row["row_digest"] = _digest(row)
    return row


def _require_risk_ceo_outputs(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION:
        raise RiskSignalError(
            "risk_signal_required_basis_schema_mismatch",
            {
                "expected_schema_version": RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _risk_rows(raw: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    section = raw.get("risk_state_snapshot")
    if not isinstance(section, Mapping):
        raise RiskSignalError(
            "risk_signal_risk_state_snapshot_required",
            {"field": "risk_state_snapshot"},
        )
    rows = section.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise RiskSignalError(
            "risk_signal_risk_rows_required",
            {"field": "risk_state_snapshot.rows"},
        )
    normalized: list[Mapping[str, Any]] = []
    seen_risk_refs: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise RiskSignalError("risk_signal_risk_row_must_be_object", {"index": index})
        risk_ref = _require_nonempty(row.get("risk_ref"), f"risk_state_snapshot.rows[{index}].risk_ref")
        if not _RISK_REF_RE.match(risk_ref):
            raise RiskSignalError(
                "risk_signal_risk_ref_invalid",
                {"index": index, "risk_ref": risk_ref},
            )
        if risk_ref in seen_risk_refs:
            raise RiskSignalError(
                "risk_signal_duplicate_risk_ref",
                {"index": index, "risk_ref": risk_ref},
            )
        seen_risk_refs.add(risk_ref)
        normalized.append(row)
    return normalized


def _risk_ceo_flags(raw: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    section = raw.get("risk_ceo_flags")
    if not isinstance(section, Mapping):
        raise RiskSignalError(
            "risk_signal_flags_required",
            {"field": "risk_ceo_flags"},
        )
    rows = section.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise RiskSignalError(
            "risk_signal_flags_rows_required",
            {"field": "risk_ceo_flags.rows"},
        )
    return [row for row in rows if isinstance(row, Mapping)]


def _basis_digests(raw: Mapping[str, Any]) -> dict[str, str]:
    risk_state_snapshot = _mapping_section(raw, "risk_state_snapshot")
    ceo_snapshot = _mapping_section(raw, "ceo_transparency_snapshot")
    risk_ceo_flags = _mapping_section(raw, "risk_ceo_flags")
    return {
        "risk_state_snapshot_digest": _digest_field(
            risk_state_snapshot,
            "risk_state_snapshot.snapshot_digest",
        ),
        "ceo_transparency_snapshot_digest": _digest_field(
            ceo_snapshot,
            "ceo_transparency_snapshot.snapshot_digest",
        ),
        "risk_ceo_flags_digest": _digest_field(
            risk_ceo_flags,
            "risk_ceo_flags.snapshot_digest",
        ),
    }


def _mapping_section(raw: Mapping[str, Any], section_name: str) -> Mapping[str, Any]:
    section = raw.get(section_name)
    if not isinstance(section, Mapping):
        raise RiskSignalError(
            "risk_signal_section_required",
            {"section": section_name},
        )
    return section


def _digest_field(raw: Mapping[str, Any], field: str) -> str:
    key = field.rsplit(".", 1)[-1]
    digest = _require_nonempty(raw.get(key), field).lower()
    if not _SHA256_RE.match(digest):
        raise RiskSignalError(
            "risk_signal_digest_invalid",
            {"field": field, "digest": digest},
        )
    return digest


def _scope(raw: Mapping[str, Any], label: str) -> dict[str, str]:
    return {
        "tenant_id": _require_nonempty(raw.get("tenant_id"), f"{label}.tenant_id"),
        "domain_id": _require_nonempty(raw.get("domain_id"), f"{label}.domain_id"),
        "project_id": _require_nonempty(raw.get("project_id"), f"{label}.project_id"),
    }


def _known_source_refs(raw: Mapping[str, Any]) -> set[str]:
    refs = _source_refs_in_value(raw)
    if not refs:
        raise RiskSignalError(
            "risk_signal_source_refs_required",
            {"field": "risk_ceo_transparency_outputs"},
        )
    return refs


def _source_refs_in_value(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if (
                str(key).endswith("source_refs")
                and isinstance(nested, Sequence)
                and not isinstance(nested, (str, bytes))
            ):
                refs.update(str(item) for item in nested if _SOURCE_REF_RE.match(str(item)))
            refs.update(_source_refs_in_value(nested))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            refs.update(_source_refs_in_value(nested))
    return refs


def _source_refs(
    raw: Any,
    *,
    known_source_refs: set[str],
    field: str,
) -> list[str]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise RiskSignalError("risk_signal_source_refs_required", {"field": field})
    refs: list[str] = []
    for index, value in enumerate(raw):
        source_ref = _require_nonempty(value, f"{field}[{index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise RiskSignalError(
                "risk_signal_source_ref_invalid",
                {"field": field, "source_ref": source_ref},
            )
        if source_ref not in known_source_refs:
            raise RiskSignalError(
                "risk_signal_unknown_source_ref",
                {"field": field, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise RiskSignalError(
                "risk_signal_duplicate_source_ref",
                {"field": field, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _risk_ref(raw: Any, *, index: int, known_risk_refs: set[str]) -> str:
    risk_ref = _require_nonempty(raw, f"signal_observations[{index}].risk_ref")
    if not _RISK_REF_RE.match(risk_ref):
        raise RiskSignalError(
            "risk_signal_risk_ref_invalid",
            {"index": index, "risk_ref": risk_ref},
        )
    if risk_ref not in known_risk_refs:
        raise RiskSignalError(
            "risk_signal_unknown_risk_ref",
            {"index": index, "risk_ref": risk_ref},
        )
    return risk_ref


def _risk_signal_id(raw: Any, *, index: int) -> str:
    value = _require_nonempty(raw, f"signal_observations[{index}].risk_signal_id")
    if not _RISK_SIGNAL_ID_RE.match(value):
        raise RiskSignalError(
            "risk_signal_id_invalid",
            {"index": index, "risk_signal_id": value},
        )
    return value


def _predicate_id(raw: Any, *, index: int) -> str:
    value = _require_nonempty(raw, f"signal_observations[{index}].predicate_id")
    if not _PREDICATE_ID_RE.match(value):
        raise RiskSignalError(
            "risk_signal_predicate_id_invalid",
            {"index": index, "predicate_id": value},
        )
    return value


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_code: str,
) -> str:
    normalized = _require_nonempty(value, field)
    if normalized not in allowed:
        raise RiskSignalError(
            error_code,
            {"field": field, "value": normalized, "allowed": sorted(allowed)},
        )
    return normalized


def _require_nonempty(value: Any, field: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise RiskSignalError("risk_signal_required_field_missing", {"field": field})
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise RiskSignalError(
                    "risk_signal_raw_material_rejected",
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
            raise RiskSignalError(
                "risk_signal_raw_material_rejected",
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
    "RISK_SIGNAL_ACTIVATION_POSTURE",
    "RISK_SIGNAL_OUTPUTS_SCHEMA_VERSION",
    "RISK_SIGNAL_REGISTER_SCHEMA_VERSION",
    "RISK_SIGNAL_STATUSES",
    "RiskSignalError",
    "build_risk_signal_outputs",
    "canonical_risk_signal_outputs_bytes",
    "risk_signal_outputs_digest",
]
