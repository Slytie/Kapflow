from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


PROJECT_INTAKE_ROUTER_SCHEMA_VERSION = "capex.project_intake_router.outputs.v1"
PROJECT_INTAKE_PROFILE_SCHEMA_VERSION = "capex.project_intake_profile.v1"
MODULE_ACTIVATION_PROFILE_SCHEMA_VERSION = "capex.module_activation_profile.v1"
PROJECT_INTAKE_HANDOFF_MANIFEST_SCHEMA_VERSION = (
    "capex.project_intake_handoff_manifest.v1"
)
PROJECT_INTAKE_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
PROJECT_INTAKE_ENTRY_MODES = (
    "new_project",
    "mid_project",
    "issue_escalation",
    "ceo_sponsor_entry",
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip)$"
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_MODULE_READINESS = frozenset({"candidate", "blocked", "deferred"})


@dataclass(frozen=True)
class ProjectIntakeRouterError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_project_intake_router_outputs(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    intake_request_id: str,
    entry_mode: str,
    requested_by_actor_id: str,
    requested_by_actor_type: str,
    created_at: str,
    human_confirmation: Mapping[str, Any],
    sanitized_context_refs: Sequence[str],
    module_candidates: Sequence[Mapping[str, Any]],
    fixture_tier: str | None = None,
    ai_draft_notes: str | None = None,
) -> dict[str, Any]:
    """Build planning-safe Project Intake Router output payloads.

    This helper validates routing shape only. It does not create workflow runs,
    source occurrences, generated artifacts, approvals, pointers, or workpages.
    """

    resolved_entry_mode = _require_nonempty(entry_mode, "entry_mode")
    if resolved_entry_mode not in PROJECT_INTAKE_ENTRY_MODES:
        raise ProjectIntakeRouterError(
            "project_intake_entry_mode_invalid",
            {
                "entry_mode": resolved_entry_mode,
                "allowed_entry_modes": list(PROJECT_INTAKE_ENTRY_MODES),
            },
        )

    context_refs = tuple(
        _safe_ref(ref, f"sanitized_context_refs[{index}]")
        for index, ref in enumerate(sanitized_context_refs)
    )
    if not context_refs:
        raise ProjectIntakeRouterError(
            "project_intake_context_refs_required",
            {"field": "sanitized_context_refs"},
        )
    if resolved_entry_mode == "mid_project" and fixture_tier is None:
        raise ProjectIntakeRouterError(
            "project_intake_mid_project_fixture_tier_required",
            {"entry_mode": resolved_entry_mode},
        )

    confirmation = _human_confirmation(human_confirmation)
    modules = tuple(_module_candidate(index, raw) for index, raw in enumerate(module_candidates))
    if not modules:
        raise ProjectIntakeRouterError(
            "project_intake_module_candidates_required",
            {"field": "module_candidates"},
        )

    actor = {
        "id": _require_nonempty(requested_by_actor_id, "requested_by_actor_id"),
        "type": _require_nonempty(requested_by_actor_type, "requested_by_actor_type"),
    }
    profile = {
        "schema_version": PROJECT_INTAKE_PROFILE_SCHEMA_VERSION,
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "domain_id": _require_nonempty(domain_id, "domain_id"),
        "project_id": _require_nonempty(project_id, "project_id"),
        "intake_request_id": _require_nonempty(
            intake_request_id,
            "intake_request_id",
        ),
        "entry_mode": resolved_entry_mode,
        "fixture_tier": fixture_tier,
        "requested_by_actor": actor,
        "created_at": _require_nonempty(created_at, "created_at"),
        "human_confirmation": confirmation,
        "ai_draft_only": True,
        "ai_draft_notes": ai_draft_notes,
        "sanitized_context_refs": list(context_refs),
    }
    module_profile = {
        "schema_version": MODULE_ACTIVATION_PROFILE_SCHEMA_VERSION,
        "tenant_id": profile["tenant_id"],
        "domain_id": profile["domain_id"],
        "project_id": profile["project_id"],
        "intake_request_id": profile["intake_request_id"],
        "module_activation_authority": "none_planning_profile_only",
        "human_confirmation_required": True,
        "module_candidates": list(modules),
    }
    handoff_manifest = {
        "schema_version": PROJECT_INTAKE_HANDOFF_MANIFEST_SCHEMA_VERSION,
        "handoff_manifest_id": f"handoff:{profile['intake_request_id']}",
        "tenant_id": profile["tenant_id"],
        "domain_id": profile["domain_id"],
        "project_id": profile["project_id"],
        "source_task_ref": "TASK-0283",
        "generated_artifact_envelope_schema": "capex.generated_artifact_envelope.v1",
        "basis_refs": list(context_refs),
        "output_refs": [
            "project_intake_profile",
            "module_activation_profile",
        ],
        "target_workflow_candidates": [
            "capex.corpus_baseline.v1",
            "capex.assumption_closure.v1",
            "capex.procurement_escalation.v1",
        ],
        "activation_allowed": False,
    }
    return {
        "schema_version": PROJECT_INTAKE_ROUTER_SCHEMA_VERSION,
        "activation_posture": PROJECT_INTAKE_ACTIVATION_POSTURE,
        "project_intake_profile": profile,
        "module_activation_profile": module_profile,
        "handoff_manifest": handoff_manifest,
        "cannot_be_used_for": [
            "capex_runtime_activation",
            "product_activation",
            "public_route_activation",
            "authored_workflow_pack_activation",
            "raw_corpus_import",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "module_activation_approval",
        ],
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_source_occurrences": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def canonical_project_intake_router_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def project_intake_router_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_project_intake_router_bytes(outputs)
    ).hexdigest()


def _human_confirmation(raw: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise ProjectIntakeRouterError(
            "project_intake_human_confirmation_required",
            {"field": "human_confirmation"},
        )
    decision = _require_nonempty(raw.get("decision"), "human_confirmation.decision")
    if decision != "confirmed":
        raise ProjectIntakeRouterError(
            "project_intake_human_confirmation_required",
            {"decision": decision},
        )
    return {
        "decision": decision,
        "confirmed_by_actor_id": _require_nonempty(
            raw.get("confirmed_by_actor_id"),
            "human_confirmation.confirmed_by_actor_id",
        ),
        "confirmed_at": _require_nonempty(
            raw.get("confirmed_at"),
            "human_confirmation.confirmed_at",
        ),
    }


def _module_candidate(index: int, raw: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise ProjectIntakeRouterError(
            "project_intake_module_candidate_must_be_object",
            {"index": index},
        )
    readiness = _require_nonempty(
        raw.get("readiness"),
        f"module_candidates[{index}].readiness",
    )
    if readiness not in _MODULE_READINESS:
        raise ProjectIntakeRouterError(
            "project_intake_module_readiness_invalid",
            {
                "index": index,
                "readiness": readiness,
                "allowed_readiness": sorted(_MODULE_READINESS),
            },
        )
    return {
        "module_id": _safe_ref(
            _require_nonempty(raw.get("module_id"), f"module_candidates[{index}].module_id"),
            f"module_candidates[{index}].module_id",
        ),
        "readiness": readiness,
        "routing_reason": _safe_ref(
            _require_nonempty(
                raw.get("routing_reason"),
                f"module_candidates[{index}].routing_reason",
            ),
            f"module_candidates[{index}].routing_reason",
        ),
    }


def _safe_ref(value: str, field_name: str) -> str:
    normalized = _require_nonempty(value, field_name)
    lowered = normalized.lower()
    if lowered.startswith("data:") or "base64," in lowered:
        raise ProjectIntakeRouterError(
            "project_intake_raw_context_ref_forbidden",
            {"field": field_name},
        )
    if (
        _ABSOLUTE_PATH_RE.match(normalized)
        or any(marker in normalized for marker in _RAW_PATH_MARKERS)
        or _RAW_FILENAME_RE.match(normalized)
    ):
        raise ProjectIntakeRouterError(
            "project_intake_raw_context_ref_forbidden",
            {"field": field_name, "value": normalized},
        )
    return normalized


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectIntakeRouterError(
            "project_intake_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


__all__ = [
    "MODULE_ACTIVATION_PROFILE_SCHEMA_VERSION",
    "PROJECT_INTAKE_ACTIVATION_POSTURE",
    "PROJECT_INTAKE_ENTRY_MODES",
    "PROJECT_INTAKE_HANDOFF_MANIFEST_SCHEMA_VERSION",
    "PROJECT_INTAKE_PROFILE_SCHEMA_VERSION",
    "PROJECT_INTAKE_ROUTER_SCHEMA_VERSION",
    "ProjectIntakeRouterError",
    "build_project_intake_router_outputs",
    "canonical_project_intake_router_bytes",
    "project_intake_router_digest",
]
