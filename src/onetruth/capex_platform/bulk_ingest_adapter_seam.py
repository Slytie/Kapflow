from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.staged_corpus_ingest import (
    STAGED_CORPUS_INGEST_ACTIVATION_POSTURE,
    STAGED_CORPUS_INGEST_SCHEMA_VERSION,
    STAGED_INGEST_MODES,
    StagedCorpusIngestError,
    plan_staged_corpus_ingest,
)


BULK_INGEST_ADAPTER_SEAM_SCHEMA_VERSION = (
    "capex.bulk_ingest_adapter_seam.outputs.v1"
)
BULK_INGEST_ADAPTER_SEAM_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)
BULK_INGEST_ADAPTER_INTERFACE_KIND = "staged_descriptor_manifest"

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_ADAPTER_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "content",
    "content_base64",
    "document_text",
    "file_name",
    "filename",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_file",
    "raw_filename",
    "source_file_path",
    "source_filename",
    "source_path",
}


@dataclass(frozen=True)
class BulkIngestAdapterSeamError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_bulk_ingest_adapter_seam_outputs(
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    adapter_request_id: str,
    ingest_batch_id: str,
    idempotency_key: str,
    requested_by_actor_id: str,
    requested_by_actor_type: str,
    created_at: str,
    descriptors: Sequence[Mapping[str, Any]],
    interface_kind: str = BULK_INGEST_ADAPTER_INTERFACE_KIND,
) -> dict[str, Any]:
    """Validate a bulk-ingest request seam and return a deterministic handoff.

    This adapter is deliberately non-activating. It wraps the staged descriptor
    planner and never reads corpus bytes, writes artifacts, creates source
    occurrences, or promotes pointers.
    """

    adapter_request_id = _require_nonempty(
        adapter_request_id,
        "adapter_request_id",
    )
    if interface_kind != BULK_INGEST_ADAPTER_INTERFACE_KIND:
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_interface_kind_invalid",
            {
                "interface_kind": interface_kind,
                "expected_interface_kind": BULK_INGEST_ADAPTER_INTERFACE_KIND,
            },
        )
    _validate_descriptor_boundary(descriptors)

    try:
        staged_plan = plan_staged_corpus_ingest(
            tenant_id=tenant_id,
            domain_id=domain_id,
            project_id=project_id,
            ingest_batch_id=ingest_batch_id,
            idempotency_key=idempotency_key,
            requested_by_actor_id=requested_by_actor_id,
            requested_by_actor_type=requested_by_actor_type,
            created_at=created_at,
            descriptors=descriptors,
        )
    except StagedCorpusIngestError as exc:
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_staged_plan_invalid",
            {"upstream_code": exc.code, "upstream_details": exc.details},
        ) from exc

    staged_truth_effects = staged_plan.get("truth_effects")
    if staged_truth_effects != {
        "creates_source_occurrences": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }:
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_unexpected_staged_truth_effect",
            {"truth_effects": staged_truth_effects},
        )

    return {
        "schema_version": BULK_INGEST_ADAPTER_SEAM_SCHEMA_VERSION,
        "activation_posture": BULK_INGEST_ADAPTER_SEAM_ACTIVATION_POSTURE,
        "interface_kind": interface_kind,
        "adapter_request_id": adapter_request_id,
        "tenant_id": _require_nonempty(tenant_id, "tenant_id"),
        "domain_id": _require_nonempty(domain_id, "domain_id"),
        "project_id": _require_nonempty(project_id, "project_id"),
        "ingest_batch_id": _require_nonempty(ingest_batch_id, "ingest_batch_id"),
        "idempotency_key": _require_nonempty(idempotency_key, "idempotency_key"),
        "created_at": _require_nonempty(created_at, "created_at"),
        "requested_by_actor": {
            "id": _require_nonempty(
                requested_by_actor_id,
                "requested_by_actor_id",
            ),
            "type": _require_nonempty(
                requested_by_actor_type,
                "requested_by_actor_type",
            ),
        },
        "descriptor_count": staged_plan["descriptor_count"],
        "descriptor_fingerprint": staged_plan["descriptor_fingerprint"],
        "accepted_modes": list(STAGED_INGEST_MODES),
        "staged_ingest_plan_schema_version": STAGED_CORPUS_INGEST_SCHEMA_VERSION,
        "staged_ingest_plan_activation_posture": (
            STAGED_CORPUS_INGEST_ACTIVATION_POSTURE
        ),
        "handoff": {
            "next_planning_step": "capex.source_inventory.v1",
            "uses_json_base64_artifact_route": False,
            "uses_local_source_path_artifact_route": False,
            "calls_artifact_ingress_descriptor_request_bytes": False,
            "creates_source_occurrences": False,
            "creates_artifact_versions": False,
            "promotes_official_pointers": False,
        },
        "staged_ingest_plan": staged_plan,
        "truth_effects": {
            "imports_raw_corpus": False,
            "uses_json_base64_command_route": False,
            "uses_local_source_path_artifact_route": False,
            "creates_source_occurrences": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def canonical_bulk_ingest_adapter_seam_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def bulk_ingest_adapter_seam_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_bulk_ingest_adapter_seam_bytes(outputs)
    ).hexdigest()


def _validate_descriptor_boundary(descriptors: Sequence[Mapping[str, Any]]) -> None:
    if not isinstance(descriptors, Sequence) or isinstance(
        descriptors,
        str | bytes | bytearray,
    ):
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_descriptors_must_be_sequence",
            {"field": "descriptors"},
        )

    seen_descriptor_ids: set[str] = set()
    for index, descriptor in enumerate(descriptors):
        if not isinstance(descriptor, Mapping):
            raise BulkIngestAdapterSeamError(
                "bulk_ingest_adapter_descriptor_must_be_object",
                {"index": index},
            )
        _reject_raw_adapter_material(descriptor, path=f"descriptors[{index}]")
        descriptor_id = descriptor.get("descriptor_id")
        if isinstance(descriptor_id, str):
            if descriptor_id in seen_descriptor_ids:
                raise BulkIngestAdapterSeamError(
                    "bulk_ingest_adapter_duplicate_descriptor_id",
                    {"descriptor_id": descriptor_id, "index": index},
                )
            seen_descriptor_ids.add(descriptor_id)


def _reject_raw_adapter_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in _FORBIDDEN_ADAPTER_KEYS:
                raise BulkIngestAdapterSeamError(
                    "bulk_ingest_adapter_raw_material_field_forbidden",
                    {"path": f"{path}.{key}", "field": key},
                )
            _reject_raw_adapter_material(raw_value, path=f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _reject_raw_adapter_material(item, path=f"{path}[{index}]")
        return
    if isinstance(value, bytes | bytearray):
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_blob_bytes_forbidden",
            {"path": path},
        )
    if isinstance(value, str):
        _validate_safe_adapter_string(value, path=path)


def _validate_safe_adapter_string(value: str, *, path: str) -> None:
    lowered = value.lower()
    if "base64," in lowered or lowered.startswith("data:"):
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_inline_base64_forbidden",
            {"path": path},
        )
    if _ABSOLUTE_PATH_RE.match(value) or any(
        marker in value for marker in _RAW_PATH_MARKERS
    ):
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_raw_absolute_path_forbidden",
            {"path": path},
        )


def _require_nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BulkIngestAdapterSeamError(
            "bulk_ingest_adapter_required_field_missing",
            {"field": field_name},
        )
    return value.strip()


__all__ = [
    "BULK_INGEST_ADAPTER_INTERFACE_KIND",
    "BULK_INGEST_ADAPTER_SEAM_ACTIVATION_POSTURE",
    "BULK_INGEST_ADAPTER_SEAM_SCHEMA_VERSION",
    "BulkIngestAdapterSeamError",
    "build_bulk_ingest_adapter_seam_outputs",
    "bulk_ingest_adapter_seam_digest",
    "canonical_bulk_ingest_adapter_seam_bytes",
]
