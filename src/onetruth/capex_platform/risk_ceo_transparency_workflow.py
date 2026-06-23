from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.ceo_transparency_snapshot import (
    build_ceo_transparency_snapshot,
)
from onetruth.capex_platform.project_state_snapshot_workflow import (
    PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION,
)


RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION = (
    "capex.risk_ceo_transparency.workflow_outputs.v1"
)
RISK_CEO_TRANSPARENCY_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
RISK_STATE_SNAPSHOT_SCHEMA_VERSION = "capex.risk_state_snapshot.v1"
RISK_CEO_FLAGS_SCHEMA_VERSION = "capex.risk_ceo_flags.v1"

RISK_KINDS = frozenset(
    {
        "cost",
        "schedule",
        "scope",
        "procurement",
        "quality",
        "interface",
        "closure",
        "external_dependency",
    }
)
OBSERVATION_STATES = frozenset(
    {
        "resolved",
        "open",
        "missing_evidence",
        "conflict",
        "ai_draft_only",
        "waiver_recorded",
        "stale_pointer",
    }
)
SEVERITIES = frozenset({"critical", "high", "medium", "low", "informational"})
FORECASTABILITY_GRADES = frozenset(
    {"forecastable", "bounded_uncertainty", "not_forecastable"}
)
RISK_STATUSES = frozenset(
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
_PROJECT_COMPONENT_REF_RE = re.compile(r"^project_state_component:[A-Za-z0-9_.:-]+$")
_RISK_REF_RE = re.compile(r"^risk_state_item:[A-Za-z0-9_.:-]+$")
_WAIVER_REF_RE = re.compile(r"^waiver:[A-Za-z0-9_.:-]+$")
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
class RiskCeoTransparencyWorkflowError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_risk_ceo_transparency_workflow_outputs(
    *,
    project_state_snapshot_outputs: Mapping[str, Any],
    risk_observations: Sequence[Mapping[str, Any]],
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only risk and CEO transparency workflow outputs."""

    _require_project_state_snapshot_outputs(project_state_snapshot_outputs)
    _reject_raw_material(project_state_snapshot_outputs, path="project_state_snapshot_outputs")
    scope = _scope(project_state_snapshot_outputs, "project_state_snapshot_outputs")
    known_source_refs = _known_project_state_source_refs(project_state_snapshot_outputs)
    known_component_ids = _known_project_state_component_ids(project_state_snapshot_outputs)
    project_state_snapshot_digest = _project_state_snapshot_digest(
        project_state_snapshot_outputs
    )
    project_closure_vector_digest = _section_digest(
        project_state_snapshot_outputs,
        "project_closure_vector",
    )

    if not risk_observations:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_observations_required",
            {"field": "risk_observations"},
        )
    risk_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    seen_risk_ids: set[str] = set()
    for index, observation in enumerate(risk_observations):
        if not isinstance(observation, Mapping):
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_observation_must_be_object",
                {"index": index},
            )
        risk_row, flags = _risk_row(
            index=index,
            observation=observation,
            scope=scope,
            known_source_refs=known_source_refs,
            known_component_ids=known_component_ids,
        )
        if risk_row["risk_id"] in seen_risk_ids:
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_duplicate_risk_id",
                {"index": index, "risk_id": risk_row["risk_id"]},
            )
        seen_risk_ids.add(risk_row["risk_id"])
        risk_rows.append(risk_row)
        flag_rows.extend(flags)

    risk_rows = sorted(risk_rows, key=lambda row: row["risk_id"])
    flag_rows = sorted(flag_rows, key=lambda row: row["flag_id"])
    risk_state_snapshot = {
        "schema_version": RISK_STATE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": f"{_require_nonempty(workflow_id, 'workflow_id')}:risk-state",
        "tenant_id": scope["tenant_id"],
        "domain_id": scope["domain_id"],
        "project_id": scope["project_id"],
        "rows": risk_rows,
        "row_count": len(risk_rows),
        "official_truth": False,
        "snapshot_digest": _digest(risk_rows),
    }
    risk_ceo_flags = {
        "schema_version": RISK_CEO_FLAGS_SCHEMA_VERSION,
        "rows": flag_rows,
        "row_count": len(flag_rows),
        "snapshot_digest": _digest(flag_rows),
    }
    ceo_snapshot = _ceo_snapshot(
        risk_rows=risk_rows,
        flag_rows=flag_rows,
        scope=scope,
        workflow_id=_require_nonempty(workflow_id, "workflow_id"),
        created_at=created_at,
        created_by_actor_id=created_by_actor_id,
        created_by_actor_type=created_by_actor_type,
        project_state_snapshot_digest=project_state_snapshot_digest,
        risk_state_snapshot_digest=risk_state_snapshot["snapshot_digest"],
    )
    return {
        "schema_version": RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION,
        "activation_posture": RISK_CEO_TRANSPARENCY_ACTIVATION_POSTURE,
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
            "project_state_snapshot_workflow_id": _require_nonempty(
                project_state_snapshot_outputs.get("workflow_id"),
                "project_state_snapshot_outputs.workflow_id",
            ),
            "project_state_snapshot_digest": project_state_snapshot_digest,
            "project_closure_vector_digest": project_closure_vector_digest,
        },
        "risk_state_snapshot": risk_state_snapshot,
        "ceo_transparency_snapshot": ceo_snapshot,
        "risk_ceo_flags": risk_ceo_flags,
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_tasks": False,
            "creates_approvals": False,
            "creates_risk_engine_state": False,
            "creates_ceo_cockpit_state": False,
            "creates_closure_snapshots": False,
            "creates_official_project_state": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "authored_workflow_pack_activation",
            "runtime_risk_engine_activation",
            "ceo_cockpit_activation",
            "public_route_activation",
            "frontend_route_activation",
            "raw_corpus_import",
            "official_project_state",
            "closure_snapshot_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_risk_ceo_transparency_workflow_bytes(
    outputs: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def risk_ceo_transparency_workflow_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_risk_ceo_transparency_workflow_bytes(outputs)
    ).hexdigest()


def _risk_row(
    *,
    index: int,
    observation: Mapping[str, Any],
    scope: Mapping[str, str],
    known_source_refs: set[str],
    known_component_ids: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _reject_raw_material(observation, path=f"risk_observations[{index}]")
    _require_optional_scope_match(
        scope,
        observation,
        label=f"risk_observations[{index}]",
    )
    risk_id = _require_nonempty(
        observation.get("risk_id"),
        f"risk_observations[{index}].risk_id",
    )
    observation_state = _allowed(
        observation.get("observation_state"),
        OBSERVATION_STATES,
        f"risk_observations[{index}].observation_state",
        "risk_ceo_observation_state_invalid",
    )
    _reject_false_precision_for_blockers(
        observation,
        observation_state=observation_state,
        path=f"risk_observations[{index}]",
    )
    source_refs = _source_refs(
        observation.get("source_refs"),
        known_source_refs=known_source_refs,
        field=f"risk_observations[{index}].source_refs",
    )
    project_state_component_id = _require_nonempty(
        observation.get("project_state_component_id"),
        f"risk_observations[{index}].project_state_component_id",
    )
    if project_state_component_id not in known_component_ids:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_unknown_project_state_component",
            {"index": index, "project_state_component_id": project_state_component_id},
        )
    waiver_refs = _waiver_refs(
        observation.get("waiver_refs"),
        field=f"risk_observations[{index}].waiver_refs",
    )
    if observation_state == "waiver_recorded" and not waiver_refs:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_waiver_refs_required",
            {"index": index, "risk_id": risk_id},
        )
    severity = _mapped_severity(
        observation_state=observation_state,
        requested=observation.get("severity"),
        index=index,
    )
    forecastability_grade = _mapped_forecastability(
        observation_state=observation_state,
        requested=observation.get("forecastability_grade"),
        index=index,
    )
    risk_status = _mapped_risk_status(
        observation_state=observation_state,
        requested=observation.get("risk_status"),
        index=index,
    )
    risk_ref = f"risk_state_item:{risk_id}"
    component_ref = f"project_state_component:{project_state_component_id}"
    row = {
        "risk_id": risk_id,
        "risk_ref": risk_ref,
        "risk_kind": _allowed(
            observation.get("risk_kind"),
            RISK_KINDS,
            f"risk_observations[{index}].risk_kind",
            "risk_ceo_risk_kind_invalid",
        ),
        "risk_label": _require_nonempty(
            observation.get("risk_label"),
            f"risk_observations[{index}].risk_label",
        ),
        "observation_state": observation_state,
        "risk_status": risk_status,
        "severity": severity,
        "forecastability_grade": forecastability_grade,
        "project_state_component_ref": component_ref,
        "source_refs": source_refs,
        "waiver_refs": waiver_refs,
        "management_action_label": _require_nonempty(
            observation.get("management_action_label"),
            f"risk_observations[{index}].management_action_label",
        ),
        "owner_role": _require_nonempty(
            observation.get("owner_role"),
            f"risk_observations[{index}].owner_role",
        ),
        "ceo_drilldown_refs": sorted([risk_ref, component_ref]),
        "official_truth": False,
    }
    flags = _risk_flags(row)
    return row, flags


def _ceo_snapshot(
    *,
    risk_rows: Sequence[Mapping[str, Any]],
    flag_rows: Sequence[Mapping[str, Any]],
    scope: Mapping[str, str],
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    project_state_snapshot_digest: str,
    risk_state_snapshot_digest: str,
) -> dict[str, Any]:
    source_refs = sorted(_all_source_refs(risk_rows) | _all_source_refs(flag_rows))
    if not source_refs:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_source_refs_required",
            {"field": "risk_observations.source_refs"},
        )
    forecastability_grade = _workflow_forecastability_grade(risk_rows)
    caveats = _ceo_caveats(
        risk_rows=risk_rows,
        flag_rows=flag_rows,
        source_refs=source_refs,
        forecastability_grade=forecastability_grade,
    )
    actions = [
        {
            "action_id": f"action:{row['risk_id']}",
            "action_label": row["management_action_label"],
            "owner_role": row["owner_role"],
            "action_status": _ceo_action_status(row),
            "source_refs": list(row["source_refs"]),
            "drilldown_refs": list(row["ceo_drilldown_refs"]),
        }
        for row in risk_rows
    ]
    drilldowns: list[dict[str, Any]] = []
    for row in risk_rows:
        drilldowns.append(
            {
                "drilldown_id": f"risk:{row['risk_id']}",
                "drilldown_kind": "risk_state_item",
                "target_ref": row["risk_ref"],
                "source_refs": list(row["source_refs"]),
            }
        )
        drilldowns.append(
            {
                "drilldown_id": f"project-state:{row['risk_id']}",
                "drilldown_kind": "project_state_component",
                "target_ref": row["project_state_component_ref"],
                "source_refs": list(row["source_refs"]),
            }
        )
    return build_ceo_transparency_snapshot(
        snapshot_id=f"{workflow_id}:ceo-transparency",
        tenant_id=scope["tenant_id"],
        domain_id=scope["domain_id"],
        project_id=scope["project_id"],
        created_at=created_at,
        created_by_actor_id=created_by_actor_id,
        created_by_actor_type=created_by_actor_type,
        source_refs=source_refs,
        input_digests=[project_state_snapshot_digest, risk_state_snapshot_digest],
        forecastability_grade=forecastability_grade,
        caveats=caveats,
        management_actions=actions,
        drilldown_refs=drilldowns,
    )


def _risk_flags(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    state = str(row["observation_state"])
    flag_types: list[tuple[str, str, bool]] = []
    if state == "missing_evidence":
        flag_types.append(("missing_evidence", "high", True))
    elif state == "conflict":
        flag_types.append(("evidence_conflict", "critical", True))
    elif state == "ai_draft_only":
        flag_types.append(("ai_draft_only", "high", True))
    elif state == "stale_pointer":
        flag_types.append(("stale_pointer", "high", True))
    elif state == "waiver_recorded":
        flag_types.append(("waiver_recorded", "medium", False))
    if row["forecastability_grade"] == "not_forecastable":
        flag_types.append(("not_forecastable", "high", True))
    flags = []
    for flag_type, severity, blocks_ceo_forecast in flag_types:
        flags.append(
            {
                "flag_id": f"{row['risk_id']}:{flag_type}",
                "risk_id": row["risk_id"],
                "flag_type": flag_type,
                "severity": severity,
                "source_refs": list(row["source_refs"]),
                "blocks_ceo_forecast": blocks_ceo_forecast,
                "creates_official_truth": False,
            }
        )
    return flags


def _ceo_caveats(
    *,
    risk_rows: Sequence[Mapping[str, Any]],
    flag_rows: Sequence[Mapping[str, Any]],
    source_refs: Sequence[str],
    forecastability_grade: str,
) -> list[dict[str, Any]]:
    caveats: list[dict[str, Any]] = []
    if forecastability_grade == "not_forecastable":
        caveats.append(
            {
                "caveat_id": "caveat:not_forecastable",
                "caveat_type": "not_forecastable",
                "caveat_label": "Reviewed evidence does not support an exact CEO forecast",
                "source_refs": list(source_refs),
            }
        )
    flag_type_to_caveat_type = {
        "missing_evidence": "evidence_missing",
        "evidence_conflict": "evidence_conflict",
        "ai_draft_only": "ai_draft_only",
        "stale_pointer": "stale_pointer",
        "waiver_recorded": "waiver_recorded",
    }
    seen: set[str] = {caveat["caveat_id"] for caveat in caveats}
    for flag in flag_rows:
        flag_type = str(flag["flag_type"])
        caveat_type = flag_type_to_caveat_type.get(flag_type)
        if caveat_type is None:
            continue
        caveat_id = f"caveat:{flag['risk_id']}:{caveat_type}"
        if caveat_id in seen:
            continue
        seen.add(caveat_id)
        caveats.append(
            {
                "caveat_id": caveat_id,
                "caveat_type": caveat_type,
                "caveat_label": f"{flag['risk_id']} requires CEO caveat: {caveat_type}",
                "source_refs": list(flag["source_refs"]),
            }
        )
    if not caveats:
        caveats.append(
            {
                "caveat_id": "caveat:reviewed_basis",
                "caveat_type": "management_attention",
                "caveat_label": "CEO snapshot is planning evidence from reviewed workflow outputs",
                "source_refs": sorted(_all_source_refs(risk_rows)),
            }
        )
    return sorted(caveats, key=lambda row: row["caveat_id"])


def _workflow_forecastability_grade(risk_rows: Sequence[Mapping[str, Any]]) -> str:
    grades = {str(row["forecastability_grade"]) for row in risk_rows}
    if "not_forecastable" in grades:
        return "not_forecastable"
    if "bounded_uncertainty" in grades:
        return "bounded_uncertainty"
    return "forecastable"


def _ceo_action_status(row: Mapping[str, Any]) -> str:
    if row["observation_state"] in {
        "missing_evidence",
        "conflict",
        "ai_draft_only",
        "stale_pointer",
    }:
        return "blocked"
    if row["risk_status"] == "closed":
        return "closed"
    if row["observation_state"] == "resolved":
        return "monitoring"
    return "open"


def _mapped_severity(*, observation_state: str, requested: Any, index: int) -> str:
    if observation_state == "conflict":
        return "critical"
    if observation_state in {"missing_evidence", "ai_draft_only", "stale_pointer"}:
        return "high"
    if observation_state == "waiver_recorded":
        return "medium"
    return _allowed(
        requested,
        SEVERITIES,
        f"risk_observations[{index}].severity",
        "risk_ceo_severity_invalid",
    )


def _mapped_forecastability(
    *,
    observation_state: str,
    requested: Any,
    index: int,
) -> str:
    if observation_state in {"missing_evidence", "conflict", "ai_draft_only", "stale_pointer"}:
        return "not_forecastable"
    if observation_state == "waiver_recorded":
        return "bounded_uncertainty"
    return _allowed(
        requested,
        FORECASTABILITY_GRADES,
        f"risk_observations[{index}].forecastability_grade",
        "risk_ceo_forecastability_grade_invalid",
    )


def _mapped_risk_status(*, observation_state: str, requested: Any, index: int) -> str:
    mapped = {
        "missing_evidence": "blocked_missing_evidence",
        "conflict": "blocked_conflict",
        "ai_draft_only": "ai_draft_only",
        "waiver_recorded": "waiver_recorded",
        "stale_pointer": "blocked_stale_pointer",
    }
    if observation_state in mapped:
        return mapped[observation_state]
    return _allowed(
        requested,
        RISK_STATUSES,
        f"risk_observations[{index}].risk_status",
        "risk_ceo_risk_status_invalid",
    )


def _reject_false_precision_for_blockers(
    value: Mapping[str, Any],
    *,
    observation_state: str,
    path: str,
) -> None:
    if observation_state not in {"missing_evidence", "conflict", "ai_draft_only", "stale_pointer"}:
        return
    for key, nested in value.items():
        if str(key) in _FALSE_PRECISION_FIELDS and nested is not None:
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_false_precision_forbidden",
                {"path": f"{path}.{key}", "observation_state": observation_state},
            )
        if isinstance(nested, Mapping):
            _reject_false_precision_for_blockers(
                nested,
                observation_state=observation_state,
                path=f"{path}.{key}",
            )


def _require_project_state_snapshot_outputs(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_required_basis_schema_mismatch",
            {
                "expected_schema_version": PROJECT_STATE_SNAPSHOT_WORKFLOW_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _scope(raw: Mapping[str, Any], label: str) -> dict[str, str]:
    return {
        "tenant_id": _require_nonempty(raw.get("tenant_id"), f"{label}.tenant_id"),
        "domain_id": _require_nonempty(raw.get("domain_id"), f"{label}.domain_id"),
        "project_id": _require_nonempty(raw.get("project_id"), f"{label}.project_id"),
    }


def _require_optional_scope_match(
    scope: Mapping[str, str],
    raw: Mapping[str, Any],
    *,
    label: str,
) -> None:
    for field in ("tenant_id", "domain_id", "project_id"):
        if raw.get(field) is not None and str(raw[field]) != scope[field]:
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_scope_mismatch",
                {
                    "label": label,
                    "field": field,
                    "expected": scope[field],
                    "actual": str(raw[field]),
                },
            )


def _known_project_state_source_refs(raw: Mapping[str, Any]) -> set[str]:
    refs = _source_refs_in_value(raw)
    if not refs:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_project_state_source_refs_required",
            {"field": "project_state_snapshot_outputs"},
        )
    return refs


def _known_project_state_component_ids(raw: Mapping[str, Any]) -> set[str]:
    section = raw.get("project_closure_vector")
    if not isinstance(section, Mapping):
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_project_closure_vector_required",
            {"field": "project_closure_vector"},
        )
    rows = section.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_project_closure_vector_rows_required",
            {"field": "project_closure_vector.rows"},
        )
    component_ids = {
        str(row.get("component_id"))
        for row in rows
        if isinstance(row, Mapping) and row.get("component_id") is not None
    }
    if not component_ids:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_project_state_components_required",
            {"field": "project_closure_vector.rows[].component_id"},
        )
    return component_ids


def _project_state_snapshot_digest(raw: Mapping[str, Any]) -> str:
    snapshot = raw.get("project_state_snapshot")
    if not isinstance(snapshot, Mapping):
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_project_state_snapshot_required",
            {"field": "project_state_snapshot"},
        )
    digest = _require_nonempty(
        snapshot.get("snapshot_digest"),
        "project_state_snapshot.snapshot_digest",
    ).lower()
    if not _SHA256_RE.match(digest):
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_project_state_digest_invalid",
            {"field": "project_state_snapshot.snapshot_digest", "digest": digest},
        )
    return digest


def _section_digest(raw: Mapping[str, Any], section_name: str) -> str:
    section = raw.get(section_name)
    if not isinstance(section, Mapping):
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_section_required",
            {"section": section_name},
        )
    digest = _require_nonempty(section.get("snapshot_digest"), f"{section_name}.snapshot_digest").lower()
    if not _SHA256_RE.match(digest):
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_section_digest_invalid",
            {"section": section_name, "digest": digest},
        )
    return digest


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
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_source_refs_required",
            {"field": field},
        )
    refs: list[str] = []
    for index, value in enumerate(raw):
        source_ref = _require_nonempty(value, f"{field}[{index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_source_ref_invalid",
                {"field": field, "source_ref": source_ref},
            )
        if source_ref not in known_source_refs:
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_source_ref_not_in_project_state",
                {"field": field, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_duplicate_source_ref",
                {"field": field, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _waiver_refs(raw: Any, *, field: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_waiver_refs_must_be_list",
            {"field": field},
        )
    refs: list[str] = []
    for index, value in enumerate(raw):
        waiver_ref = _require_nonempty(value, f"{field}[{index}]")
        if not _WAIVER_REF_RE.match(waiver_ref):
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_waiver_ref_invalid",
                {"field": field, "waiver_ref": waiver_ref},
            )
        if waiver_ref in refs:
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_duplicate_waiver_ref",
                {"field": field, "waiver_ref": waiver_ref},
            )
        refs.append(waiver_ref)
    return sorted(refs)


def _all_source_refs(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for row in rows:
        for source_ref in row.get("source_refs") or []:
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
        raise RiskCeoTransparencyWorkflowError(
            error_code,
            {"field": field, "value": normalized, "allowed": sorted(allowed)},
        )
    return normalized


def _require_nonempty(value: Any, field: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise RiskCeoTransparencyWorkflowError(
            "risk_ceo_required_field_missing",
            {"field": field},
        )
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized_key = key_text.strip().lower()
            if normalized_key in _FORBIDDEN_RAW_KEYS or normalized_key.startswith("raw_"):
                raise RiskCeoTransparencyWorkflowError(
                    "risk_ceo_raw_material_rejected",
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
            raise RiskCeoTransparencyWorkflowError(
                "risk_ceo_raw_material_rejected",
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
    "RISK_CEO_FLAGS_SCHEMA_VERSION",
    "RISK_CEO_TRANSPARENCY_ACTIVATION_POSTURE",
    "RISK_CEO_TRANSPARENCY_WORKFLOW_SCHEMA_VERSION",
    "RISK_STATE_SNAPSHOT_SCHEMA_VERSION",
    "RiskCeoTransparencyWorkflowError",
    "build_risk_ceo_transparency_workflow_outputs",
    "canonical_risk_ceo_transparency_workflow_bytes",
    "risk_ceo_transparency_workflow_digest",
]
