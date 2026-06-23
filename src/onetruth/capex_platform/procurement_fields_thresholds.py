from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


PROCUREMENT_FIELDS_THRESHOLDS_OUTPUTS_SCHEMA_VERSION = (
    "capex.procurement_fields_thresholds.outputs.v1"
)
PROCUREMENT_FIELDS_THRESHOLDS_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)
PROCUREMENT_REQUIRED_FIELD_REGISTER_SCHEMA_VERSION = (
    "capex.procurement_required_field_register.v1"
)
EXECUTIVE_ESCALATION_THRESHOLD_FAMILY_REGISTER_SCHEMA_VERSION = (
    "capex.executive_escalation_threshold_family_register.v1"
)
COMMERCIAL_OBSERVATION_BOUNDARY_SCHEMA_VERSION = (
    "capex.commercial_observation_boundary.v1"
)

REQUIRED_SIGNOFF_GATE_REFS = ("SME-RP-G006", "SME-RP-G007")
ANNEX_B_PROCUREMENT_FIELD_IDS = (
    "scope_id",
    "capex_scope",
    "capex_main_group",
    "level_2_group",
    "budget_line",
    "approved_budget",
    "forecast",
    "purchase_requisition",
    "purchase_order",
    "supplier",
    "quotation",
    "change_order",
    "invoice",
    "controlling_allocation",
    "deviation_amount",
    "deviation_category",
    "technical_risk",
    "schedule_impact",
    "residual_risk",
    "evidence_refs",
    "recommendation",
    "decision_maker",
    "escalation_reason",
    "outcome",
    "conditions",
)
ANNEX_B_THRESHOLD_FAMILIES = (
    "budget deviation",
    "schedule shift with production impact",
    "safety or quality impact",
    "residual risk acceptance",
    "supplier dispute or claim exposure",
    "decision despite incomplete evidence",
    "recurring defect / system-effectiveness risk",
)
COMMERCIAL_EVIDENCE_CANNOT_CLOSE_DIMENSIONS = (
    "technical",
    "effectiveness",
    "handover",
    "assumption",
    "closure",
)

_FIELD_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_FAMILY_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_GATE_REF_RE = re.compile(r"^SME-RP-G\d{3}$")
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
    "source_filename",
    "source_text",
    "text",
    "text_excerpt",
}
_FORBIDDEN_THRESHOLD_VALUE_KEYS = {
    "amount",
    "amount_cents",
    "days",
    "limit",
    "limit_value",
    "max_amount",
    "max_value",
    "min_amount",
    "min_value",
    "numeric_threshold",
    "numeric_threshold_value",
    "percent",
    "threshold_amount",
    "threshold_days",
    "threshold_percent",
    "threshold_value",
    "value",
}


@dataclass(frozen=True)
class ProcurementFieldsThresholdsError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_procurement_fields_and_threshold_policy_outputs(
    *,
    policy_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    field_rows: Sequence[Mapping[str, Any]] | None = None,
    threshold_family_rows: Sequence[Mapping[str, Any]] | None = None,
    signoff_gate_refs: Sequence[str] = REQUIRED_SIGNOFF_GATE_REFS,
) -> dict[str, Any]:
    """Build planning-only procurement field and threshold-family policy outputs."""

    gate_refs = _signoff_gate_refs(signoff_gate_refs)
    fields = _field_rows(
        field_rows if field_rows is not None else _default_field_rows(),
    )
    threshold_families = _threshold_family_rows(
        threshold_family_rows
        if threshold_family_rows is not None
        else _default_threshold_family_rows(gate_refs),
        required_gate_refs=gate_refs,
    )
    boundary = {
        "schema_version": COMMERCIAL_OBSERVATION_BOUNDARY_SCHEMA_VERSION,
        "commercial_evidence_posture": "observed_or_reconciled_evidence_only",
        "commercial_evidence_can_directly_close_dimensions": False,
        "commercial_evidence_cannot_close_dimensions": list(
            COMMERCIAL_EVIDENCE_CANNOT_CLOSE_DIMENSIONS
        ),
        "commercial_evidence_sets_official_truth": False,
        "waiver_or_business_signoff_required_for_activation": True,
    }
    outputs = {
        "schema_version": PROCUREMENT_FIELDS_THRESHOLDS_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": PROCUREMENT_FIELDS_THRESHOLDS_ACTIVATION_POSTURE,
        "policy_id": _require_nonempty(policy_id, "policy_id"),
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "signoff_gate_refs": gate_refs,
        "procurement_required_field_register": {
            "schema_version": PROCUREMENT_REQUIRED_FIELD_REGISTER_SCHEMA_VERSION,
            "source_annex": "Annex B",
            "rows": fields,
            "row_count": len(fields),
            "all_fields_required": True,
            "register_digest": _digest(fields),
        },
        "executive_escalation_threshold_family_register": {
            "schema_version": (
                EXECUTIVE_ESCALATION_THRESHOLD_FAMILY_REGISTER_SCHEMA_VERSION
            ),
            "source_annex": "Annex B",
            "rows": threshold_families,
            "row_count": len(threshold_families),
            "threshold_value_policy": "no_numeric_thresholds_invented_by_platform",
            "threshold_values_present": False,
            "requires_business_signoff_gate_refs": gate_refs,
            "register_digest": _digest(threshold_families),
        },
        "commercial_observation_boundary": boundary,
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_tasks": False,
            "creates_approvals": False,
            "creates_threshold_values": False,
            "activates_thresholds": False,
            "activates_procurement_workflow": False,
            "creates_erp_or_accounting_behavior": False,
            "creates_ceo_cockpit_state": False,
            "creates_official_project_state": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "numeric_threshold_signoff",
            "threshold_activation",
            "procurement_workflow_activation",
            "erp_or_accounting_ledger_behavior",
            "ceo_cockpit_activation",
            "public_route_activation",
            "frontend_route_activation",
            "official_project_state",
            "closure_snapshot_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }
    outputs["policy_digest"] = _digest(
        {
            "fields": fields,
            "threshold_families": threshold_families,
            "boundary": boundary,
            "signoff_gate_refs": gate_refs,
        }
    )
    canonical_procurement_fields_thresholds_bytes(outputs)
    return outputs


def canonical_procurement_fields_thresholds_bytes(
    outputs: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def procurement_fields_thresholds_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_procurement_fields_thresholds_bytes(outputs)
    ).hexdigest()


def _default_field_rows() -> list[dict[str, Any]]:
    return [
        {
            "field_id": field_id,
            "field_family": _field_family(field_id),
            "required": True,
            "evidence_posture": "observed_or_reconciled_evidence",
            "source_annex_ref": "Annex B",
            "can_create_official_truth": False,
        }
        for field_id in ANNEX_B_PROCUREMENT_FIELD_IDS
    ]


def _default_threshold_family_rows(
    gate_refs: Sequence[str],
) -> list[dict[str, Any]]:
    return [
        {
            "threshold_family_id": _slug(family),
            "threshold_family_label": family,
            "threshold_value_state": "absent_pending_business_signoff",
            "configurable_after_business_signoff": True,
            "required_signoff_gate_refs": list(gate_refs),
            "source_annex_ref": "Annex B",
            "creates_activation": False,
        }
        for family in ANNEX_B_THRESHOLD_FAMILIES
    ]


def _field_rows(raw_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)) or not raw_rows:
        raise ProcurementFieldsThresholdsError(
            "procurement_fields_required",
            {"field": "field_rows"},
        )
    rows = []
    seen: set[str] = set()
    for index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, Mapping):
            raise ProcurementFieldsThresholdsError(
                "procurement_field_row_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"field_rows[{index}]")
        _reject_commercial_closure(raw_row, path=f"field_rows[{index}]")
        field_id = _field_id(raw_row.get("field_id"), f"field_rows[{index}].field_id")
        if field_id in seen:
            raise ProcurementFieldsThresholdsError(
                "procurement_duplicate_field_id",
                {"index": index, "field_id": field_id},
            )
        seen.add(field_id)
        rows.append(
            {
                "field_id": field_id,
                "field_family": _require_nonempty(
                    raw_row.get("field_family"),
                    f"field_rows[{index}].field_family",
                ),
                "required": _require_true(
                    raw_row.get("required"),
                    f"field_rows[{index}].required",
                ),
                "evidence_posture": _require_value(
                    raw_row.get("evidence_posture"),
                    "observed_or_reconciled_evidence",
                    f"field_rows[{index}].evidence_posture",
                ),
                "source_annex_ref": _require_value(
                    raw_row.get("source_annex_ref"),
                    "Annex B",
                    f"field_rows[{index}].source_annex_ref",
                ),
                "can_create_official_truth": _require_false(
                    raw_row.get("can_create_official_truth"),
                    f"field_rows[{index}].can_create_official_truth",
                ),
            }
        )
    missing = sorted(set(ANNEX_B_PROCUREMENT_FIELD_IDS) - seen)
    if missing:
        raise ProcurementFieldsThresholdsError(
            "procurement_required_annex_b_fields_missing",
            {"field_ids": missing},
        )
    return sorted(rows, key=lambda row: row["field_id"])


def _threshold_family_rows(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    required_gate_refs: Sequence[str],
) -> list[dict[str, Any]]:
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)) or not raw_rows:
        raise ProcurementFieldsThresholdsError(
            "procurement_threshold_families_required",
            {"field": "threshold_family_rows"},
        )
    rows = []
    seen: set[str] = set()
    for index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, Mapping):
            raise ProcurementFieldsThresholdsError(
                "procurement_threshold_family_row_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"threshold_family_rows[{index}]")
        _reject_threshold_value_material(raw_row, path=f"threshold_family_rows[{index}]")
        family_id = _family_id(
            raw_row.get("threshold_family_id"),
            f"threshold_family_rows[{index}].threshold_family_id",
        )
        if family_id in seen:
            raise ProcurementFieldsThresholdsError(
                "procurement_duplicate_threshold_family_id",
                {"index": index, "threshold_family_id": family_id},
            )
        seen.add(family_id)
        label = _require_nonempty(
            raw_row.get("threshold_family_label"),
            f"threshold_family_rows[{index}].threshold_family_label",
        )
        if label not in ANNEX_B_THRESHOLD_FAMILIES:
            raise ProcurementFieldsThresholdsError(
                "procurement_threshold_family_not_in_annex_b",
                {"index": index, "threshold_family_label": label},
            )
        rows.append(
            {
                "threshold_family_id": family_id,
                "threshold_family_label": label,
                "threshold_value_state": _require_value(
                    raw_row.get("threshold_value_state"),
                    "absent_pending_business_signoff",
                    f"threshold_family_rows[{index}].threshold_value_state",
                ),
                "configurable_after_business_signoff": _require_true(
                    raw_row.get("configurable_after_business_signoff"),
                    f"threshold_family_rows[{index}].configurable_after_business_signoff",
                ),
                "required_signoff_gate_refs": _require_gate_ref_set(
                    raw_row.get("required_signoff_gate_refs"),
                    required_gate_refs=required_gate_refs,
                    field=f"threshold_family_rows[{index}].required_signoff_gate_refs",
                ),
                "source_annex_ref": _require_value(
                    raw_row.get("source_annex_ref"),
                    "Annex B",
                    f"threshold_family_rows[{index}].source_annex_ref",
                ),
                "creates_activation": _require_false(
                    raw_row.get("creates_activation"),
                    f"threshold_family_rows[{index}].creates_activation",
                ),
            }
        )
    missing = sorted({_slug(label) for label in ANNEX_B_THRESHOLD_FAMILIES} - seen)
    if missing:
        raise ProcurementFieldsThresholdsError(
            "procurement_required_threshold_families_missing",
            {"threshold_family_ids": missing},
        )
    return sorted(rows, key=lambda row: row["threshold_family_id"])


def _signoff_gate_refs(raw_refs: Sequence[str]) -> list[str]:
    if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
        raise ProcurementFieldsThresholdsError(
            "procurement_signoff_gate_refs_required",
            {"field": "signoff_gate_refs"},
        )
    refs = []
    for index, ref in enumerate(raw_refs):
        gate_ref = _require_nonempty(ref, f"signoff_gate_refs[{index}]")
        if not _GATE_REF_RE.match(gate_ref):
            raise ProcurementFieldsThresholdsError(
                "procurement_signoff_gate_ref_invalid",
                {"gate_ref": gate_ref},
            )
        refs.append(gate_ref)
    if set(refs) != set(REQUIRED_SIGNOFF_GATE_REFS):
        raise ProcurementFieldsThresholdsError(
            "procurement_required_signoff_gate_refs_missing",
            {
                "expected": list(REQUIRED_SIGNOFF_GATE_REFS),
                "actual": sorted(set(refs)),
            },
        )
    return sorted(refs)


def _require_gate_ref_set(
    raw_refs: Any,
    *,
    required_gate_refs: Sequence[str],
    field: str,
) -> list[str]:
    if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
        raise ProcurementFieldsThresholdsError(
            "procurement_threshold_family_gate_refs_required",
            {"field": field},
        )
    refs = sorted(str(ref) for ref in raw_refs)
    if refs != sorted(required_gate_refs):
        raise ProcurementFieldsThresholdsError(
            "procurement_threshold_family_gate_refs_mismatch",
            {"field": field, "expected": sorted(required_gate_refs), "actual": refs},
        )
    return refs


def _field_id(value: Any, field: str) -> str:
    field_id = _require_nonempty(value, field)
    if not _FIELD_ID_RE.match(field_id):
        raise ProcurementFieldsThresholdsError(
            "procurement_field_id_invalid",
            {"field": field, "field_id": field_id},
        )
    return field_id


def _family_id(value: Any, field: str) -> str:
    family_id = _require_nonempty(value, field)
    if not _FAMILY_ID_RE.match(family_id):
        raise ProcurementFieldsThresholdsError(
            "procurement_threshold_family_id_invalid",
            {"field": field, "threshold_family_id": family_id},
        )
    return family_id


def _require_true(value: Any, field: str) -> bool:
    if value is not True:
        raise ProcurementFieldsThresholdsError(
            "procurement_required_boolean_invalid",
            {"field": field, "expected": True, "actual": value},
        )
    return True


def _require_false(value: Any, field: str) -> bool:
    if value is not False:
        raise ProcurementFieldsThresholdsError(
            "procurement_required_boolean_invalid",
            {"field": field, "expected": False, "actual": value},
        )
    return False


def _require_value(value: Any, expected: str, field: str) -> str:
    normalized = _require_nonempty(value, field)
    if normalized != expected:
        raise ProcurementFieldsThresholdsError(
            "procurement_required_value_invalid",
            {"field": field, "expected": expected, "actual": normalized},
        )
    return normalized


def _require_nonempty(value: Any, field: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ProcurementFieldsThresholdsError(
            "procurement_required_field_missing",
            {"field": field},
        )
    return normalized


def _field_family(field_id: str) -> str:
    if field_id in {
        "scope_id",
        "capex_scope",
        "capex_main_group",
        "level_2_group",
        "budget_line",
    }:
        return "scope_and_budget_structure"
    if field_id in {
        "approved_budget",
        "forecast",
        "controlling_allocation",
        "deviation_amount",
        "deviation_category",
    }:
        return "commercial_control"
    if field_id in {
        "purchase_requisition",
        "purchase_order",
        "supplier",
        "quotation",
        "change_order",
        "invoice",
    }:
        return "procurement_evidence"
    if field_id in {
        "technical_risk",
        "schedule_impact",
        "residual_risk",
        "evidence_refs",
        "recommendation",
    }:
        return "risk_and_recommendation"
    return "decision_and_outcome"


def _slug(value: str) -> str:
    return (
        value.replace("/", " ")
        .replace("-", " ")
        .lower()
        .replace(" ", "_")
        .replace("__", "_")
    )


def _reject_threshold_value_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_THRESHOLD_VALUE_KEYS and nested is not None:
                raise ProcurementFieldsThresholdsError(
                    "procurement_numeric_threshold_value_forbidden",
                    {"path": f"{path}.{key_text}"},
                )
            _reject_threshold_value_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _reject_threshold_value_material(item, path=f"{path}[{index}]")


def _reject_commercial_closure(value: Mapping[str, Any], *, path: str) -> None:
    candidate_fields = ("closes_dimensions", "can_close_dimensions")
    for field in candidate_fields:
        raw = value.get(field)
        if raw is None:
            continue
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise ProcurementFieldsThresholdsError(
                "procurement_commercial_closure_boundary_invalid",
                {"path": f"{path}.{field}"},
            )
        forbidden = sorted(
            set(str(item) for item in raw)
            & set(COMMERCIAL_EVIDENCE_CANNOT_CLOSE_DIMENSIONS)
        )
        if forbidden:
            raise ProcurementFieldsThresholdsError(
                "procurement_commercial_closure_boundary_violation",
                {"path": f"{path}.{field}", "dimensions": forbidden},
            )


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise ProcurementFieldsThresholdsError(
                    "procurement_raw_material_rejected",
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
            raise ProcurementFieldsThresholdsError(
                "procurement_raw_material_rejected",
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
    "ANNEX_B_PROCUREMENT_FIELD_IDS",
    "ANNEX_B_THRESHOLD_FAMILIES",
    "COMMERCIAL_EVIDENCE_CANNOT_CLOSE_DIMENSIONS",
    "COMMERCIAL_OBSERVATION_BOUNDARY_SCHEMA_VERSION",
    "EXECUTIVE_ESCALATION_THRESHOLD_FAMILY_REGISTER_SCHEMA_VERSION",
    "PROCUREMENT_FIELDS_THRESHOLDS_ACTIVATION_POSTURE",
    "PROCUREMENT_FIELDS_THRESHOLDS_OUTPUTS_SCHEMA_VERSION",
    "PROCUREMENT_REQUIRED_FIELD_REGISTER_SCHEMA_VERSION",
    "ProcurementFieldsThresholdsError",
    "REQUIRED_SIGNOFF_GATE_REFS",
    "build_procurement_fields_and_threshold_policy_outputs",
    "canonical_procurement_fields_thresholds_bytes",
    "procurement_fields_thresholds_digest",
]
