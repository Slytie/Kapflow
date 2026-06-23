from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from onetruth.application.handlers._shared.artifact_effects import (
    build_capex_generated_artifact_envelope,
    canonical_capex_generated_artifact_file_name,
    canonical_json_bytes,
)
from onetruth.capex_platform.generated_artifact_validators import (
    GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION,
    capex_generated_artifact_digest,
    validate_capex_generated_artifact_bundle,
)
from onetruth.capex_platform.role_packet_register import (
    PACKET_REGISTER_ARTIFACT_KIND,
    PACKET_REGISTER_SCHEMA_VERSION,
    ROLE_ASSIGNMENT_REGISTER_ARTIFACT_KIND,
    ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION,
    role_packet_digest,
)
from onetruth.capex_platform.source_inventory import SOURCE_INVENTORY_SCHEMA_VERSION
from onetruth.capex_platform.source_occurrence_register import (
    SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION,
    source_occurrence_register_digest,
)


CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION = "capex.corpus_baseline.workflow_outputs.v1"
CORPUS_BASELINE_ACTIVATION_POSTURE = "planning_only_no_capex_activation"


@dataclass(frozen=True)
class CorpusBaselineWorkflowError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_corpus_baseline_workflow_outputs(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    workflow_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    source_inventory: Mapping[str, Any],
    source_occurrence_register: Mapping[str, Any],
    role_assignment_register: Mapping[str, Any],
    packet_register: Mapping[str, Any],
    handoff_manifest_ref: str,
) -> dict[str, Any]:
    """Build the planning-only Corpus Baseline workflow output bundle."""

    scope = {
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "domain_id": _require_nonempty(domain_id, "domain_id"),
        "project_id": _require_nonempty(project_id, "project_id"),
    }
    _require_schema(source_inventory, SOURCE_INVENTORY_SCHEMA_VERSION, "source_inventory")
    _require_schema(
        source_occurrence_register,
        SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION,
        "source_occurrence_register",
    )
    _require_schema(
        role_assignment_register,
        ROLE_ASSIGNMENT_REGISTER_SCHEMA_VERSION,
        "role_assignment_register",
    )
    _require_schema(packet_register, PACKET_REGISTER_SCHEMA_VERSION, "packet_register")
    for label, artifact in (
        ("source_inventory", source_inventory),
        ("source_occurrence_register", source_occurrence_register),
        ("role_assignment_register", role_assignment_register),
        ("packet_register", packet_register),
    ):
        _require_scope(artifact, scope, label)

    if int(source_inventory.get("descriptor_count") or 0) <= 0:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_inventory_empty",
            {"field": "source_inventory.descriptor_count"},
        )
    if int(source_occurrence_register.get("row_count") or 0) <= 0:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_occurrence_register_empty",
            {"field": "source_occurrence_register.row_count"},
        )
    if int(role_assignment_register.get("row_count") or 0) <= 0:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_role_register_empty",
            {"field": "role_assignment_register.row_count"},
        )
    if int(packet_register.get("packet_count") or 0) <= 0:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_packet_register_empty",
            {"field": "packet_register.packet_count"},
        )

    source_refs = sorted(
        {
            str(row["source_ref"])
            for row in _rows(source_occurrence_register, "source_occurrence_register.rows")
        }
    )
    input_digests = sorted(
        {
            source_occurrence_register_digest(source_occurrence_register),
            role_packet_digest(role_assignment_register),
            role_packet_digest(packet_register),
        }
    )
    role_envelope = build_capex_generated_artifact_envelope(
        artifact_kind=ROLE_ASSIGNMENT_REGISTER_ARTIFACT_KIND,
        artifact_role="evidence",
        source_refs=source_refs,
        input_digests=input_digests,
        validation_summary={
            "result": "planning_only",
            "policy": "role_assignment_register_shape_only",
        },
        payload=role_assignment_register,
    )
    packet_envelope = build_capex_generated_artifact_envelope(
        artifact_kind=PACKET_REGISTER_ARTIFACT_KIND,
        artifact_role="evidence",
        source_refs=source_refs,
        input_digests=input_digests,
        validation_summary={
            "result": "planning_only",
            "policy": "packet_register_shape_only",
        },
        payload=packet_register,
    )
    artifacts = [
        _artifact(ROLE_ASSIGNMENT_REGISTER_ARTIFACT_KIND, role_envelope),
        _artifact(PACKET_REGISTER_ARTIFACT_KIND, packet_envelope),
    ]
    validator_result = validate_capex_generated_artifact_bundle(
        {
            "schema_version": GENERATED_ARTIFACT_BUNDLE_SCHEMA_VERSION,
            "available_source_refs": source_refs,
            "available_input_digests": input_digests,
            "artifacts": artifacts,
        }
    )
    if not validator_result.valid:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_generated_artifact_bundle_invalid",
            {"error_codes": list(validator_result.error_codes)},
        )

    return {
        "schema_version": CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION,
        "activation_posture": CORPUS_BASELINE_ACTIVATION_POSTURE,
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
            "source_inventory_id": _require_nonempty(
                source_inventory.get("inventory_id"),
                "source_inventory.inventory_id",
            ),
            "source_occurrence_register_id": _require_nonempty(
                source_occurrence_register.get("register_id"),
                "source_occurrence_register.register_id",
            ),
            "role_assignment_register_id": _require_nonempty(
                role_assignment_register.get("register_id"),
                "role_assignment_register.register_id",
            ),
            "packet_register_id": _require_nonempty(
                packet_register.get("register_id"),
                "packet_register.register_id",
            ),
            "handoff_manifest_ref": _require_nonempty(
                handoff_manifest_ref,
                "handoff_manifest_ref",
            ),
        },
        "generated_artifacts": artifacts,
        "validator_result": validator_result.to_dict(),
        "summary": {
            "descriptor_count": int(source_inventory["descriptor_count"]),
            "source_occurrence_count": int(source_occurrence_register["row_count"]),
            "role_assignment_count": int(role_assignment_register["row_count"]),
            "packet_count": int(packet_register["packet_count"]),
        },
        "cannot_be_used_for": [
            "authored_workflow_pack_activation",
            "workflow_run_creation",
            "public_route_activation",
            "frontend_route_activation",
            "raw_corpus_import",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
        "truth_effects": {
            "creates_workflow_run": False,
            "creates_reviewed_baseline": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def canonical_corpus_baseline_workflow_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def corpus_baseline_workflow_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_corpus_baseline_workflow_bytes(outputs)
    ).hexdigest()


def _artifact(artifact_kind: str, envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "file_name": canonical_capex_generated_artifact_file_name(artifact_kind),
        "envelope": dict(envelope),
        "content_digest": capex_generated_artifact_digest(envelope),
        "byte_size": len(canonical_json_bytes(envelope)),
    }


def _require_schema(raw: Mapping[str, Any], expected: str, label: str) -> None:
    if raw.get("schema_version") != expected:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_schema_mismatch",
            {
                "label": label,
                "expected_schema_version": expected,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _require_scope(raw: Mapping[str, Any], scope: Mapping[str, str], label: str) -> None:
    for field in ("tenant_id", "domain_id", "project_id"):
        if str(raw.get(field) or "") != scope[field]:
            raise CorpusBaselineWorkflowError(
                "corpus_baseline_scope_mismatch",
                {"label": label, "field": field},
            )


def _rows(raw: Mapping[str, Any], field_name: str) -> list[Mapping[str, Any]]:
    rows = raw.get("rows")
    if not isinstance(rows, list) or not rows:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_rows_required",
            {"field": field_name},
        )
    return [row for row in rows if isinstance(row, Mapping)]


def _require_nonempty(value: Any, field_name: str) -> str:
    if value is None:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_required_field_missing",
            {"field": field_name},
        )
    normalized = str(value).strip()
    if not normalized:
        raise CorpusBaselineWorkflowError(
            "corpus_baseline_required_field_missing",
            {"field": field_name},
        )
    return normalized


__all__ = [
    "CORPUS_BASELINE_ACTIVATION_POSTURE",
    "CORPUS_BASELINE_WORKFLOW_SCHEMA_VERSION",
    "CorpusBaselineWorkflowError",
    "build_corpus_baseline_workflow_outputs",
    "canonical_corpus_baseline_workflow_bytes",
    "corpus_baseline_workflow_digest",
]
