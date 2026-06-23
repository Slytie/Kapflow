from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.risk_ceo_transparency_workflow import (
    RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION,
)


RISK_STALE_CEO_COCKPIT_PROJECTION_SCHEMA_VERSION = (
    "capex.risk_stale_ceo_cockpit.projection.v1"
)
RISK_STALE_CEO_COCKPIT_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
RISK_COCKPIT_RISK_CARDS_SCHEMA_VERSION = "capex.risk_cockpit.risk_cards.v1"
RISK_COCKPIT_STALE_BLOCKER_CARDS_SCHEMA_VERSION = (
    "capex.risk_cockpit.stale_blocker_cards.v1"
)
RISK_COCKPIT_MANAGEMENT_ACTION_CARDS_SCHEMA_VERSION = (
    "capex.risk_cockpit.management_action_cards.v1"
)
RISK_COCKPIT_SOURCE_DRILLDOWNS_SCHEMA_VERSION = (
    "capex.risk_cockpit.source_drilldowns.v1"
)
RISK_COCKPIT_FORECASTABILITY_DISPLAY_SCHEMA_VERSION = (
    "capex.risk_cockpit.forecastability_display.v1"
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
_BLOCKING_FLAG_TYPES = frozenset(
    {
        "stale_pointer",
        "missing_evidence",
        "evidence_conflict",
        "ai_draft_only",
        "not_forecastable",
    }
)
_NONBLOCKING_CAVEAT_FLAG_TYPES = frozenset({"waiver_recorded"})
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
class RiskStaleCeoCockpitWorkpageError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_risk_stale_ceo_cockpit_projection(
    *,
    risk_ceo_transparency_outputs: Mapping[str, Any],
    projection_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build a planning-only CEO cockpit projection from Risk/CEO outputs."""

    _require_basis(risk_ceo_transparency_outputs)
    _reject_raw_material(
        risk_ceo_transparency_outputs,
        path="risk_ceo_transparency_outputs",
    )
    scope = _scope(risk_ceo_transparency_outputs, "risk_ceo_transparency_outputs")
    risk_state_snapshot = _section(
        risk_ceo_transparency_outputs,
        "risk_state_snapshot",
    )
    ceo_snapshot = _section(
        risk_ceo_transparency_outputs,
        "ceo_transparency_snapshot",
    )
    risk_ceo_flags = _section(risk_ceo_transparency_outputs, "risk_ceo_flags")
    _require_scope_match(scope, risk_state_snapshot, label="risk_state_snapshot")
    _require_scope_match(scope, ceo_snapshot, label="ceo_transparency_snapshot")

    risk_rows = _rows(risk_state_snapshot, "risk_state_snapshot.rows")
    flag_rows = _rows(risk_ceo_flags, "risk_ceo_flags.rows", allow_empty=True)
    action_rows = _rows(
        ceo_snapshot,
        "ceo_transparency_snapshot.management_actions",
        row_key="management_actions",
    )
    drilldown_rows = _rows(
        ceo_snapshot,
        "ceo_transparency_snapshot.drilldown_refs",
        row_key="drilldown_refs",
    )
    known_source_refs = _known_source_refs(ceo_snapshot)
    known_risk_refs = _known_risk_refs(risk_rows)
    known_drilldown_refs = _known_drilldown_refs(
        risk_rows=risk_rows,
        drilldown_rows=drilldown_rows,
        known_source_refs=known_source_refs,
    )
    forecastability_grade = _forecastability_grade(ceo_snapshot)
    if forecastability_grade == "not_forecastable":
        _reject_false_precision(
            risk_ceo_transparency_outputs,
            path="risk_ceo_transparency_outputs",
        )

    risk_cards = _risk_cards(
        risk_rows,
        known_source_refs=known_source_refs,
        known_drilldown_refs=known_drilldown_refs,
    )
    blocker_cards = _stale_blocker_cards(
        flag_rows,
        known_risk_refs=known_risk_refs,
        known_source_refs=known_source_refs,
    )
    action_cards = _management_action_cards(
        action_rows,
        known_source_refs=known_source_refs,
        known_drilldown_refs=known_drilldown_refs,
        forecastability_grade=forecastability_grade,
    )
    source_drilldowns = _source_drilldowns(
        drilldown_rows,
        known_source_refs=known_source_refs,
        known_drilldown_refs=known_drilldown_refs,
    )
    _ensure_unique_card_ids(risk_cards + blocker_cards + action_cards)

    forecastability_display = {
        "schema_version": RISK_COCKPIT_FORECASTABILITY_DISPLAY_SCHEMA_VERSION,
        "grade": forecastability_grade,
        "false_precision_blocked": True,
        "exact_forecast_fields_allowed": forecastability_grade != "not_forecastable",
        "caveats": _forecastability_caveats(
            ceo_snapshot,
            known_source_refs=known_source_refs,
        ),
        "source_refs": _source_refs(
            ceo_snapshot.get("source_refs"),
            field="ceo_transparency_snapshot.source_refs",
            known_source_refs=known_source_refs,
        ),
    }
    projection = {
        "schema_version": RISK_STALE_CEO_COCKPIT_PROJECTION_SCHEMA_VERSION,
        "activation_posture": RISK_STALE_CEO_COCKPIT_ACTIVATION_POSTURE,
        "projection_id": _require_nonempty(projection_id, "projection_id"),
        "tenant_id": scope["tenant_id"],
        "domain_id": scope["domain_id"],
        "project_id": scope["project_id"],
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "basis": {
            "risk_ceo_transparency_workflow_id": _require_nonempty(
                risk_ceo_transparency_outputs.get("workflow_id"),
                "risk_ceo_transparency_outputs.workflow_id",
            ),
            "risk_state_snapshot_digest": _sha256(
                risk_state_snapshot.get("snapshot_digest"),
                "risk_state_snapshot.snapshot_digest",
            ),
            "ceo_transparency_snapshot_digest": _sha256(
                ceo_snapshot.get("snapshot_digest"),
                "ceo_transparency_snapshot.snapshot_digest",
            ),
            "risk_ceo_flags_digest": _sha256(
                risk_ceo_flags.get("snapshot_digest"),
                "risk_ceo_flags.snapshot_digest",
            ),
        },
        "risk_cards": {
            "schema_version": RISK_COCKPIT_RISK_CARDS_SCHEMA_VERSION,
            "rows": risk_cards,
            "row_count": len(risk_cards),
            "projection_digest": _digest(risk_cards),
        },
        "stale_blocker_cards": {
            "schema_version": RISK_COCKPIT_STALE_BLOCKER_CARDS_SCHEMA_VERSION,
            "rows": blocker_cards,
            "row_count": len(blocker_cards),
            "projection_digest": _digest(blocker_cards),
        },
        "ceo_management_action_cards": {
            "schema_version": RISK_COCKPIT_MANAGEMENT_ACTION_CARDS_SCHEMA_VERSION,
            "rows": action_cards,
            "row_count": len(action_cards),
            "projection_digest": _digest(action_cards),
        },
        "source_drilldown_refs": {
            "schema_version": RISK_COCKPIT_SOURCE_DRILLDOWNS_SCHEMA_VERSION,
            "rows": source_drilldowns,
            "row_count": len(source_drilldowns),
            "projection_digest": _digest(source_drilldowns),
        },
        "forecastability_display": forecastability_display,
        "summary": {
            "risk_card_count": len(risk_cards),
            "stale_blocker_card_count": len(blocker_cards),
            "management_action_card_count": len(action_cards),
            "source_drilldown_count": len(source_drilldowns),
            "not_forecastable": forecastability_grade == "not_forecastable",
            "blocking_card_count": sum(
                1 for card in blocker_cards if card["blocks_ceo_forecast"]
            ),
        },
        "truth_effects": {
            "creates_public_route": False,
            "creates_frontend_route": False,
            "creates_ceo_cockpit_state": False,
            "creates_risk_engine_state": False,
            "creates_workflow_run": False,
            "creates_tasks": False,
            "creates_approvals": False,
            "creates_closure_snapshots": False,
            "creates_official_project_state": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "public_route_activation",
            "frontend_route_activation",
            "ceo_cockpit_activation",
            "runtime_risk_engine_activation",
            "authored_workflow_pack_activation",
            "closure_snapshot_creation",
            "official_project_state",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }
    projection["projection_digest"] = _digest(
        {
            "basis": projection["basis"],
            "risk_cards": risk_cards,
            "stale_blocker_cards": blocker_cards,
            "ceo_management_action_cards": action_cards,
            "source_drilldown_refs": source_drilldowns,
            "forecastability_display": forecastability_display,
        }
    )
    canonical_risk_stale_ceo_cockpit_projection_bytes(projection)
    return projection


def canonical_risk_stale_ceo_cockpit_projection_bytes(
    projection: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        projection,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def risk_stale_ceo_cockpit_projection_digest(
    projection: Mapping[str, Any],
) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_risk_stale_ceo_cockpit_projection_bytes(projection)
    ).hexdigest()


def _risk_cards(
    rows: Sequence[Mapping[str, Any]],
    *,
    known_source_refs: set[str],
    known_drilldown_refs: set[str],
) -> list[dict[str, Any]]:
    cards = []
    for index, row in enumerate(rows):
        risk_id = _require_nonempty(row.get("risk_id"), f"risk_rows[{index}].risk_id")
        risk_ref = _require_nonempty(row.get("risk_ref"), f"risk_rows[{index}].risk_ref")
        if not risk_ref.startswith("risk_state_item:"):
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_risk_ref_invalid",
                {"index": index, "risk_ref": risk_ref},
            )
        cards.append(
            {
                "card_id": f"risk:{risk_id}",
                "card_kind": "risk",
                "risk_id": risk_id,
                "risk_ref": risk_ref,
                "risk_kind": _require_nonempty(
                    row.get("risk_kind"),
                    f"risk_rows[{index}].risk_kind",
                ),
                "risk_label": _require_nonempty(
                    row.get("risk_label"),
                    f"risk_rows[{index}].risk_label",
                ),
                "risk_status": _require_nonempty(
                    row.get("risk_status"),
                    f"risk_rows[{index}].risk_status",
                ),
                "severity": _require_nonempty(
                    row.get("severity"),
                    f"risk_rows[{index}].severity",
                ),
                "forecastability_grade": _require_nonempty(
                    row.get("forecastability_grade"),
                    f"risk_rows[{index}].forecastability_grade",
                ),
                "source_refs": _source_refs(
                    row.get("source_refs"),
                    field=f"risk_rows[{index}].source_refs",
                    known_source_refs=known_source_refs,
                ),
                "drilldown_refs": _drilldown_refs(
                    row.get("ceo_drilldown_refs"),
                    field=f"risk_rows[{index}].ceo_drilldown_refs",
                    known_drilldown_refs=known_drilldown_refs,
                ),
                "display_precision": (
                    "no_exact_forecast"
                    if row.get("forecastability_grade") == "not_forecastable"
                    else "forecast_display_allowed"
                ),
                "official_truth": False,
            }
        )
    return sorted(cards, key=lambda card: card["card_id"])


def _stale_blocker_cards(
    rows: Sequence[Mapping[str, Any]],
    *,
    known_risk_refs: set[str],
    known_source_refs: set[str],
) -> list[dict[str, Any]]:
    cards = []
    for index, row in enumerate(rows):
        flag_type = _require_nonempty(row.get("flag_type"), f"flag_rows[{index}].flag_type")
        if flag_type not in _BLOCKING_FLAG_TYPES | _NONBLOCKING_CAVEAT_FLAG_TYPES:
            continue
        risk_id = _require_nonempty(row.get("risk_id"), f"flag_rows[{index}].risk_id")
        flag_id = _require_nonempty(row.get("flag_id"), f"flag_rows[{index}].flag_id")
        risk_ref = f"risk_state_item:{risk_id}"
        if risk_ref not in known_risk_refs:
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_unknown_risk_ref",
                {"index": index, "risk_ref": risk_ref},
            )
        cards.append(
            {
                "card_id": f"blocker:{flag_id}",
                "card_kind": "stale_or_blocker",
                "risk_id": risk_id,
                "risk_ref": risk_ref,
                "blocker_type": flag_type,
                "blocker_classification": (
                    "blocking" if flag_type in _BLOCKING_FLAG_TYPES else "waiver_caveat"
                ),
                "severity": _require_nonempty(
                    row.get("severity"),
                    f"flag_rows[{index}].severity",
                ),
                "source_refs": _source_refs(
                    row.get("source_refs"),
                    field=f"flag_rows[{index}].source_refs",
                    known_source_refs=known_source_refs,
                ),
                "drilldown_refs": [risk_ref],
                "blocks_ceo_forecast": bool(row.get("blocks_ceo_forecast")),
                "creates_official_truth": False,
            }
        )
    return sorted(cards, key=lambda card: card["card_id"])


def _management_action_cards(
    rows: Sequence[Mapping[str, Any]],
    *,
    known_source_refs: set[str],
    known_drilldown_refs: set[str],
    forecastability_grade: str,
) -> list[dict[str, Any]]:
    cards = []
    for index, row in enumerate(rows):
        if forecastability_grade == "not_forecastable":
            _reject_false_precision(row, path=f"management_actions[{index}]")
        action_id = _require_nonempty(
            row.get("action_id"),
            f"management_actions[{index}].action_id",
        )
        cards.append(
            {
                "card_id": f"action:{action_id}",
                "card_kind": "ceo_management_action",
                "action_id": action_id,
                "action_label": _require_nonempty(
                    row.get("action_label"),
                    f"management_actions[{index}].action_label",
                ),
                "owner_role": _require_nonempty(
                    row.get("owner_role"),
                    f"management_actions[{index}].owner_role",
                ),
                "action_status": _require_nonempty(
                    row.get("action_status"),
                    f"management_actions[{index}].action_status",
                ),
                "source_refs": _source_refs(
                    row.get("source_refs"),
                    field=f"management_actions[{index}].source_refs",
                    known_source_refs=known_source_refs,
                ),
                "drilldown_refs": _drilldown_refs(
                    row.get("drilldown_refs"),
                    field=f"management_actions[{index}].drilldown_refs",
                    known_drilldown_refs=known_drilldown_refs,
                ),
                "forecastability_grade": forecastability_grade,
                "official_truth": False,
            }
        )
    return sorted(cards, key=lambda card: card["card_id"])


def _source_drilldowns(
    rows: Sequence[Mapping[str, Any]],
    *,
    known_source_refs: set[str],
    known_drilldown_refs: set[str],
) -> list[dict[str, Any]]:
    drilldowns = []
    for index, row in enumerate(rows):
        target_ref = _drilldown_ref(
            row.get("target_ref"),
            field=f"drilldown_refs[{index}].target_ref",
            known_drilldown_refs=known_drilldown_refs,
        )
        drilldowns.append(
            {
                "drilldown_id": _require_nonempty(
                    row.get("drilldown_id"),
                    f"drilldown_refs[{index}].drilldown_id",
                ),
                "drilldown_kind": _require_nonempty(
                    row.get("drilldown_kind"),
                    f"drilldown_refs[{index}].drilldown_kind",
                ),
                "target_ref": target_ref,
                "source_refs": _source_refs(
                    row.get("source_refs"),
                    field=f"drilldown_refs[{index}].source_refs",
                    known_source_refs=known_source_refs,
                ),
                "official_truth": False,
            }
        )
    return sorted(drilldowns, key=lambda row: row["drilldown_id"])


def _forecastability_caveats(
    ceo_snapshot: Mapping[str, Any],
    *,
    known_source_refs: set[str],
) -> list[dict[str, Any]]:
    rows = _rows(
        ceo_snapshot,
        "ceo_transparency_snapshot.caveats",
        row_key="caveats",
        allow_empty=False,
    )
    caveats = []
    for index, row in enumerate(rows):
        caveats.append(
            {
                "caveat_id": _require_nonempty(
                    row.get("caveat_id"),
                    f"caveats[{index}].caveat_id",
                ),
                "caveat_type": _require_nonempty(
                    row.get("caveat_type"),
                    f"caveats[{index}].caveat_type",
                ),
                "caveat_label": _require_nonempty(
                    row.get("caveat_label"),
                    f"caveats[{index}].caveat_label",
                ),
                "source_refs": _source_refs(
                    row.get("source_refs"),
                    field=f"caveats[{index}].source_refs",
                    known_source_refs=known_source_refs,
                ),
            }
        )
    return sorted(caveats, key=lambda row: row["caveat_id"])


def _ensure_unique_card_ids(cards: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for index, card in enumerate(cards):
        card_id = _require_nonempty(card.get("card_id"), f"cards[{index}].card_id")
        if card_id in seen:
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_duplicate_card_id",
                {"index": index, "card_id": card_id},
            )
        seen.add(card_id)


def _require_basis(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_required_basis_schema_mismatch",
            {
                "expected_schema_version": RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _section(raw: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    section = raw.get(name)
    if not isinstance(section, Mapping):
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_section_required",
            {"section": name},
        )
    return section


def _rows(
    section: Mapping[str, Any],
    field: str,
    *,
    row_key: str = "rows",
    allow_empty: bool = False,
) -> list[Mapping[str, Any]]:
    rows = section.get(row_key)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_rows_required",
            {"field": field},
        )
    if not rows and not allow_empty:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_rows_required",
            {"field": field},
        )
    normalized: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_row_must_be_object",
                {"field": field, "index": index},
            )
        normalized.append(row)
    return normalized


def _scope(raw: Mapping[str, Any], label: str) -> dict[str, str]:
    return {
        "tenant_id": _require_nonempty(raw.get("tenant_id"), f"{label}.tenant_id"),
        "domain_id": _require_nonempty(raw.get("domain_id"), f"{label}.domain_id"),
        "project_id": _require_nonempty(raw.get("project_id"), f"{label}.project_id"),
    }


def _require_scope_match(
    scope: Mapping[str, str],
    raw: Mapping[str, Any],
    *,
    label: str,
) -> None:
    for field in ("tenant_id", "domain_id", "project_id"):
        if raw.get(field) is not None and str(raw[field]) != scope[field]:
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_scope_mismatch",
                {
                    "label": label,
                    "field": field,
                    "expected": scope[field],
                    "actual": str(raw[field]),
                },
            )


def _known_source_refs(ceo_snapshot: Mapping[str, Any]) -> set[str]:
    raw_refs = ceo_snapshot.get("source_refs")
    if not isinstance(raw_refs, Sequence) or isinstance(raw_refs, (str, bytes)):
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_source_refs_required",
            {"field": "ceo_transparency_snapshot.source_refs"},
        )
    refs = {
        str(ref)
        for ref in raw_refs
        if isinstance(ref, str) and _SOURCE_REF_RE.match(ref)
    }
    if not refs:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_source_refs_required",
            {"field": "ceo_transparency_snapshot.source_refs"},
        )
    return refs


def _known_risk_refs(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    refs = {
        str(row.get("risk_ref"))
        for row in rows
        if isinstance(row.get("risk_ref"), str)
    }
    if not refs:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_risk_refs_required",
            {"field": "risk_state_snapshot.rows[].risk_ref"},
        )
    return refs


def _known_drilldown_refs(
    *,
    risk_rows: Sequence[Mapping[str, Any]],
    drilldown_rows: Sequence[Mapping[str, Any]],
    known_source_refs: set[str],
) -> set[str]:
    refs = set(known_source_refs)
    for row in risk_rows:
        for field in ("risk_ref", "project_state_component_ref"):
            if isinstance(row.get(field), str):
                refs.add(str(row[field]))
        for ref in row.get("ceo_drilldown_refs") or []:
            if isinstance(ref, str):
                refs.add(ref)
    for row in drilldown_rows:
        if isinstance(row.get("target_ref"), str):
            refs.add(str(row["target_ref"]))
    return refs


def _source_refs(
    raw: Any,
    *,
    field: str,
    known_source_refs: set[str],
) -> list[str]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_source_refs_required",
            {"field": field},
        )
    refs: list[str] = []
    for index, value in enumerate(raw):
        source_ref = _require_nonempty(value, f"{field}[{index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_source_ref_invalid",
                {"field": field, "source_ref": source_ref},
            )
        if source_ref not in known_source_refs:
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_unknown_source_ref",
                {"field": field, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_duplicate_source_ref",
                {"field": field, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _drilldown_refs(
    raw: Any,
    *,
    field: str,
    known_drilldown_refs: set[str],
) -> list[str]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_drilldown_refs_required",
            {"field": field},
        )
    refs: list[str] = []
    for index, value in enumerate(raw):
        ref = _drilldown_ref(
            value,
            field=f"{field}[{index}]",
            known_drilldown_refs=known_drilldown_refs,
        )
        if ref in refs:
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_duplicate_drilldown_ref",
                {"field": field, "drilldown_ref": ref},
            )
        refs.append(ref)
    return sorted(refs)


def _drilldown_ref(
    value: Any,
    *,
    field: str,
    known_drilldown_refs: set[str],
) -> str:
    ref = _require_nonempty(value, field)
    if not _DRILLDOWN_REF_RE.match(ref):
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_drilldown_ref_invalid",
            {"field": field, "drilldown_ref": ref},
        )
    if ref not in known_drilldown_refs:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_unknown_drilldown_ref",
            {"field": field, "drilldown_ref": ref},
        )
    return ref


def _forecastability_grade(ceo_snapshot: Mapping[str, Any]) -> str:
    forecastability = ceo_snapshot.get("forecastability")
    if not isinstance(forecastability, Mapping):
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_forecastability_required",
            {"field": "ceo_transparency_snapshot.forecastability"},
        )
    return _require_nonempty(
        forecastability.get("grade"),
        "ceo_transparency_snapshot.forecastability.grade",
    )


def _sha256(value: Any, field: str) -> str:
    digest = _require_nonempty(value, field).lower()
    if not _SHA256_RE.match(digest):
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_digest_invalid",
            {"field": field, "digest": digest},
        )
    return digest


def _require_nonempty(value: Any, field: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise RiskStaleCeoCockpitWorkpageError(
            "risk_cockpit_required_field_missing",
            {"field": field},
        )
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise RiskStaleCeoCockpitWorkpageError(
                    "risk_cockpit_raw_material_rejected",
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
            raise RiskStaleCeoCockpitWorkpageError(
                "risk_cockpit_raw_material_rejected",
                {"path": path, "reason": "forbidden_value"},
            )


def _reject_false_precision(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FALSE_PRECISION_FIELDS and nested is not None:
                raise RiskStaleCeoCockpitWorkpageError(
                    "risk_cockpit_false_precision_forbidden",
                    {"path": f"{path}.{key_text}"},
                )
            _reject_false_precision(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _reject_false_precision(item, path=f"{path}[{index}]")


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
    "RISK_COCKPIT_FORECASTABILITY_DISPLAY_SCHEMA_VERSION",
    "RISK_COCKPIT_MANAGEMENT_ACTION_CARDS_SCHEMA_VERSION",
    "RISK_COCKPIT_RISK_CARDS_SCHEMA_VERSION",
    "RISK_COCKPIT_SOURCE_DRILLDOWNS_SCHEMA_VERSION",
    "RISK_COCKPIT_STALE_BLOCKER_CARDS_SCHEMA_VERSION",
    "RISK_STALE_CEO_COCKPIT_ACTIVATION_POSTURE",
    "RISK_STALE_CEO_COCKPIT_PROJECTION_SCHEMA_VERSION",
    "RiskStaleCeoCockpitWorkpageError",
    "build_risk_stale_ceo_cockpit_projection",
    "canonical_risk_stale_ceo_cockpit_projection_bytes",
    "risk_stale_ceo_cockpit_projection_digest",
]
