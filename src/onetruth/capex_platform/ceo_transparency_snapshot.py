from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.application.handlers._shared.artifact_effects import (
    build_capex_generated_artifact_envelope,
)


CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION = "capex.ceo_transparency_snapshot.v1"
CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_KIND = "capex.ceo_transparency_snapshot"
CEO_TRANSPARENCY_SNAPSHOT_FILE_NAME = "capex.ceo_transparency_snapshot.v1.json"
CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_ROLE = "snapshot"
CEO_TRANSPARENCY_SNAPSHOT_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)

FORECASTABILITY_GRADES = frozenset(
    {"forecastable", "bounded_uncertainty", "not_forecastable"}
)
CAVEAT_TYPES = frozenset(
    {
        "not_forecastable",
        "evidence_missing",
        "evidence_conflict",
        "stale_pointer",
        "waiver_recorded",
        "ai_draft_only",
        "scope_limited",
        "management_attention",
    }
)
MANAGEMENT_ACTION_STATUSES = frozenset(
    {"open", "blocked", "monitoring", "closed"}
)
DRILLDOWN_KINDS = frozenset(
    {
        "project_state_component",
        "risk_state_item",
        "source_occurrence",
        "generated_artifact",
        "pointer_observation",
        "workflow_output",
    }
)

_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_DRILLDOWN_REF_RE = re.compile(
    r"^(?:project_state_component|risk_state_item|source_occurrence|"
    r"generated_artifact|pointer_observation|workflow_output):[A-Za-z0-9_.:-]+$"
)
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
_FALSE_PRECISION_FIELDS = {
    "exact_amount_cents",
    "exact_cost_cents",
    "exact_date",
    "exact_percent",
    "forecast_amount_cents",
    "forecast_confidence_percent",
    "forecast_cost_cents",
    "forecast_date",
    "forecast_percent",
    "percent_forecast",
    "target_date",
}


@dataclass(frozen=True)
class CeoTransparencySnapshotError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_ceo_transparency_snapshot(
    *,
    snapshot_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    source_refs: Sequence[str],
    input_digests: Sequence[str],
    forecastability_grade: str,
    caveats: Sequence[Mapping[str, Any]],
    management_actions: Sequence[Mapping[str, Any]],
    drilldown_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a planning-only CEO transparency snapshot payload."""

    normalized_source_refs = _source_refs(source_refs, field="source_refs")
    normalized_input_digests = _input_digests(input_digests)
    grade = _allowed(
        forecastability_grade,
        FORECASTABILITY_GRADES,
        "forecastability_grade",
        "ceo_transparency_forecastability_grade_invalid",
    )
    caveat_rows = _caveat_rows(
        caveats,
        available_source_refs=set(normalized_source_refs),
    )
    action_rows = _management_action_rows(
        management_actions,
        available_source_refs=set(normalized_source_refs),
        forecastability_grade=grade,
    )
    drilldown_rows = _drilldown_rows(
        drilldown_refs,
        available_source_refs=set(normalized_source_refs),
    )
    if grade == "not_forecastable" and not any(
        row["caveat_type"] == "not_forecastable" for row in caveat_rows
    ):
        raise CeoTransparencySnapshotError(
            "ceo_transparency_not_forecastable_caveat_required",
            {"forecastability_grade": grade},
        )

    payload = {
        "schema_version": CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION,
        "artifact_kind": CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_KIND,
        "artifact_file_name": CEO_TRANSPARENCY_SNAPSHOT_FILE_NAME,
        "activation_posture": CEO_TRANSPARENCY_SNAPSHOT_ACTIVATION_POSTURE,
        "snapshot_id": _require_nonempty(snapshot_id, "snapshot_id"),
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "domain_id": _require_nonempty(domain_id, "domain_id"),
        "project_id": _require_nonempty(project_id, "project_id"),
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "source_refs": normalized_source_refs,
        "input_digests": normalized_input_digests,
        "forecastability": {
            "grade": grade,
            "false_precision_blocked": True,
            "exact_forecast_fields_allowed": grade != "not_forecastable",
        },
        "caveats": caveat_rows,
        "management_actions": action_rows,
        "drilldown_refs": drilldown_rows,
        "summary": {
            "caveat_count": len(caveat_rows),
            "management_action_count": len(action_rows),
            "drilldown_ref_count": len(drilldown_rows),
            "not_forecastable": grade == "not_forecastable",
        },
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_risk_engine_state": False,
            "creates_ceo_cockpit_state": False,
            "creates_closure_snapshots": False,
            "creates_official_project_state": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "ceo_cockpit_activation",
            "public_route_activation",
            "frontend_route_activation",
            "runtime_risk_engine_activation",
            "official_project_state",
            "closure_snapshot_creation",
            "raw_corpus_import",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }
    payload["snapshot_digest"] = _digest(
        {
            "caveats": caveat_rows,
            "drilldown_refs": drilldown_rows,
            "forecastability": payload["forecastability"],
            "management_actions": action_rows,
            "scope": {
                "tenant_id": payload["tenant_id"],
                "domain_id": payload["domain_id"],
                "project_id": payload["project_id"],
            },
            "source_refs": normalized_source_refs,
        }
    )
    canonical_ceo_transparency_snapshot_bytes(payload)
    return payload


def build_ceo_transparency_snapshot_envelope(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Wrap a CEO snapshot in the canonical generated-artifact envelope."""

    if snapshot.get("schema_version") != CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION:
        raise CeoTransparencySnapshotError(
            "ceo_transparency_snapshot_schema_mismatch",
            {
                "expected_schema_version": CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION,
                "actual_schema_version": snapshot.get("schema_version"),
            },
        )
    source_refs = _source_refs(snapshot.get("source_refs"), field="source_refs")
    input_digests = _input_digests(snapshot.get("input_digests"))
    return build_capex_generated_artifact_envelope(
        artifact_kind=CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_KIND,
        artifact_role=CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_ROLE,
        source_refs=source_refs,
        input_digests=input_digests,
        validation_summary={
            "result": "planning_only_ceo_safe",
            "policy": "no_raw_ai_no_false_precision",
        },
        payload=dict(snapshot),
    )


def canonical_ceo_transparency_snapshot_bytes(
    snapshot: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        snapshot,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def ceo_transparency_snapshot_digest(snapshot: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_ceo_transparency_snapshot_bytes(snapshot)
    ).hexdigest()


def _caveat_rows(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    available_source_refs: set[str],
) -> list[dict[str, Any]]:
    if not raw_rows:
        raise CeoTransparencySnapshotError(
            "ceo_transparency_caveats_required",
            {"field": "caveats"},
        )
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, Mapping):
            raise CeoTransparencySnapshotError(
                "ceo_transparency_caveat_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"caveats[{index}]")
        caveat_id = _require_nonempty(raw_row.get("caveat_id"), f"caveats[{index}].caveat_id")
        if caveat_id in seen_ids:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_duplicate_caveat_id",
                {"index": index, "caveat_id": caveat_id},
            )
        seen_ids.add(caveat_id)
        rows.append(
            {
                "caveat_id": caveat_id,
                "caveat_type": _allowed(
                    raw_row.get("caveat_type"),
                    CAVEAT_TYPES,
                    f"caveats[{index}].caveat_type",
                    "ceo_transparency_caveat_type_invalid",
                ),
                "caveat_label": _require_nonempty(
                    raw_row.get("caveat_label"),
                    f"caveats[{index}].caveat_label",
                ),
                "source_refs": _source_refs(
                    raw_row.get("source_refs"),
                    field=f"caveats[{index}].source_refs",
                    available_source_refs=available_source_refs,
                ),
            }
        )
    return sorted(rows, key=lambda row: row["caveat_id"])


def _management_action_rows(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    available_source_refs: set[str],
    forecastability_grade: str,
) -> list[dict[str, Any]]:
    if not raw_rows:
        raise CeoTransparencySnapshotError(
            "ceo_transparency_management_actions_required",
            {"field": "management_actions"},
        )
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, Mapping):
            raise CeoTransparencySnapshotError(
                "ceo_transparency_management_action_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"management_actions[{index}]")
        _reject_false_precision_when_not_forecastable(
            raw_row,
            forecastability_grade=forecastability_grade,
            path=f"management_actions[{index}]",
        )
        action_id = _require_nonempty(
            raw_row.get("action_id"),
            f"management_actions[{index}].action_id",
        )
        if action_id in seen_ids:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_duplicate_management_action_id",
                {"index": index, "action_id": action_id},
            )
        seen_ids.add(action_id)
        row = {
            "action_id": action_id,
            "action_label": _require_nonempty(
                raw_row.get("action_label"),
                f"management_actions[{index}].action_label",
            ),
            "owner_role": _require_nonempty(
                raw_row.get("owner_role"),
                f"management_actions[{index}].owner_role",
            ),
            "action_status": _allowed(
                raw_row.get("action_status"),
                MANAGEMENT_ACTION_STATUSES,
                f"management_actions[{index}].action_status",
                "ceo_transparency_management_action_status_invalid",
            ),
            "source_refs": _source_refs(
                raw_row.get("source_refs"),
                field=f"management_actions[{index}].source_refs",
                available_source_refs=available_source_refs,
            ),
            "drilldown_refs": _optional_string_refs(
                raw_row.get("drilldown_refs"),
                field=f"management_actions[{index}].drilldown_refs",
                pattern=_DRILLDOWN_REF_RE,
                error_code="ceo_transparency_drilldown_ref_invalid",
            ),
        }
        for optional_field in (
            "forecast_date",
            "forecast_amount_cents",
            "forecast_percent",
        ):
            if raw_row.get(optional_field) is not None:
                row[optional_field] = raw_row[optional_field]
        rows.append(row)
    return sorted(rows, key=lambda row: row["action_id"])


def _drilldown_rows(
    raw_rows: Sequence[Mapping[str, Any]],
    *,
    available_source_refs: set[str],
) -> list[dict[str, Any]]:
    if not raw_rows:
        raise CeoTransparencySnapshotError(
            "ceo_transparency_drilldown_refs_required",
            {"field": "drilldown_refs"},
        )
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, Mapping):
            raise CeoTransparencySnapshotError(
                "ceo_transparency_drilldown_ref_must_be_object",
                {"index": index},
            )
        _reject_raw_material(raw_row, path=f"drilldown_refs[{index}]")
        drilldown_id = _require_nonempty(
            raw_row.get("drilldown_id"),
            f"drilldown_refs[{index}].drilldown_id",
        )
        if drilldown_id in seen_ids:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_duplicate_drilldown_id",
                {"index": index, "drilldown_id": drilldown_id},
            )
        seen_ids.add(drilldown_id)
        target_ref = _require_nonempty(
            raw_row.get("target_ref"),
            f"drilldown_refs[{index}].target_ref",
        )
        if not _DRILLDOWN_REF_RE.match(target_ref):
            raise CeoTransparencySnapshotError(
                "ceo_transparency_drilldown_ref_invalid",
                {"index": index, "target_ref": target_ref},
            )
        rows.append(
            {
                "drilldown_id": drilldown_id,
                "drilldown_kind": _allowed(
                    raw_row.get("drilldown_kind"),
                    DRILLDOWN_KINDS,
                    f"drilldown_refs[{index}].drilldown_kind",
                    "ceo_transparency_drilldown_kind_invalid",
                ),
                "target_ref": target_ref,
                "source_refs": _source_refs(
                    raw_row.get("source_refs"),
                    field=f"drilldown_refs[{index}].source_refs",
                    available_source_refs=available_source_refs,
                ),
            }
        )
    return sorted(rows, key=lambda row: row["drilldown_id"])


def _reject_false_precision_when_not_forecastable(
    value: Mapping[str, Any],
    *,
    forecastability_grade: str,
    path: str,
) -> None:
    if forecastability_grade != "not_forecastable":
        return
    for key, nested in value.items():
        if str(key) in _FALSE_PRECISION_FIELDS and nested is not None:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_false_precision_forbidden",
                {"path": f"{path}.{key}", "forecastability_grade": forecastability_grade},
            )
        if isinstance(nested, Mapping):
            _reject_false_precision_when_not_forecastable(
                nested,
                forecastability_grade=forecastability_grade,
                path=f"{path}.{key}",
            )


def _source_refs(
    raw: Any,
    *,
    field: str,
    available_source_refs: set[str] | None = None,
) -> list[str]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise CeoTransparencySnapshotError(
            "ceo_transparency_source_refs_required",
            {"field": field},
        )
    refs: list[str] = []
    for index, value in enumerate(raw):
        source_ref = _require_nonempty(value, f"{field}[{index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise CeoTransparencySnapshotError(
                "ceo_transparency_source_ref_invalid",
                {"field": field, "source_ref": source_ref},
            )
        if available_source_refs is not None and source_ref not in available_source_refs:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_source_ref_not_in_snapshot",
                {"field": field, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_duplicate_source_ref",
                {"field": field, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _input_digests(raw: Any) -> list[str]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise CeoTransparencySnapshotError(
            "ceo_transparency_input_digests_required",
            {"field": "input_digests"},
        )
    digests: list[str] = []
    for index, value in enumerate(raw):
        digest = _require_nonempty(value, f"input_digests[{index}]").lower()
        if not _SHA256_RE.match(digest):
            raise CeoTransparencySnapshotError(
                "ceo_transparency_input_digest_invalid",
                {"index": index, "digest": digest},
            )
        if digest in digests:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_duplicate_input_digest",
                {"index": index, "digest": digest},
            )
        digests.append(digest)
    return sorted(digests)


def _optional_string_refs(
    raw: Any,
    *,
    field: str,
    pattern: re.Pattern[str],
    error_code: str,
) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise CeoTransparencySnapshotError(error_code, {"field": field})
    refs: list[str] = []
    for index, value in enumerate(raw):
        normalized = _require_nonempty(value, f"{field}[{index}]")
        if not pattern.match(normalized):
            raise CeoTransparencySnapshotError(
                error_code,
                {"field": field, "index": index, "value": normalized},
            )
        if normalized in refs:
            raise CeoTransparencySnapshotError(
                "ceo_transparency_duplicate_ref",
                {"field": field, "value": normalized},
            )
        refs.append(normalized)
    return sorted(refs)


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_code: str,
) -> str:
    normalized = _require_nonempty(value, field)
    if normalized not in allowed:
        raise CeoTransparencySnapshotError(
            error_code,
            {"field": field, "value": normalized, "allowed": sorted(allowed)},
        )
    return normalized


def _require_nonempty(value: Any, field: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise CeoTransparencySnapshotError(
            "ceo_transparency_required_field_missing",
            {"field": field},
        )
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise CeoTransparencySnapshotError(
                    "ceo_transparency_raw_material_rejected",
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
            raise CeoTransparencySnapshotError(
                "ceo_transparency_raw_material_rejected",
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
    "CEO_TRANSPARENCY_SNAPSHOT_ACTIVATION_POSTURE",
    "CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_KIND",
    "CEO_TRANSPARENCY_SNAPSHOT_ARTIFACT_ROLE",
    "CEO_TRANSPARENCY_SNAPSHOT_FILE_NAME",
    "CEO_TRANSPARENCY_SNAPSHOT_SCHEMA_VERSION",
    "CeoTransparencySnapshotError",
    "build_ceo_transparency_snapshot",
    "build_ceo_transparency_snapshot_envelope",
    "canonical_ceo_transparency_snapshot_bytes",
    "ceo_transparency_snapshot_digest",
]
