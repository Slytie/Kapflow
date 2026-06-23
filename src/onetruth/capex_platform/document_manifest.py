from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.source_inventory import SOURCE_INVENTORY_SCHEMA_VERSION


DOCUMENT_MANIFEST_SCHEMA_VERSION = "capex.document_manifest.v1"
EXTRACTION_STATE_REGISTER_SCHEMA_VERSION = "capex.extraction_state_register.v1"
DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION = "capex.document_manifest.outputs.v1"
DOCUMENT_MANIFEST_ACTIVATION_POSTURE = "planning_only_no_capex_activation"
DOCUMENT_MANIFEST_ARTIFACT_KIND = "capex.document_manifest"
EXTRACTION_STATE_REGISTER_ARTIFACT_KIND = "capex.extraction_state_register"
DOCUMENT_MANIFEST_ARTIFACT_ROLE = "evidence"

EXTRACTION_STATUSES = frozenset(
    {
        "pending",
        "queued",
        "in_progress",
        "retry_pending",
        "partial",
        "completed",
        "failed",
        "skipped",
    }
)
TERMINAL_EXTRACTION_STATUSES = frozenset({"completed", "failed", "skipped"})

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
    "error_log",
    "extracted_text",
    "file_name",
    "filename",
    "local_path",
    "ocr_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_error",
    "raw_file",
    "raw_filename",
    "raw_log",
    "source_filename",
    "stack_trace",
    "stderr",
    "stdout",
}


@dataclass(frozen=True)
class DocumentManifestError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_document_manifest_outputs(
    *,
    source_inventory: Mapping[str, Any],
    documents: Sequence[Mapping[str, Any]],
    manifest_id: str,
    created_at: str,
    prepared_by_actor_id: str,
    prepared_by_actor_type: str,
) -> dict[str, Any]:
    """Build document manifest and extraction-state artifacts from sanitized rows."""

    _require_inventory(source_inventory)
    tenant_id = _require_nonempty(source_inventory.get("tenant_id"), "tenant_id")
    domain_id = _require_nonempty(source_inventory.get("domain_id"), "domain_id")
    project_id = _require_nonempty(source_inventory.get("project_id"), "project_id")
    inventory_items = {
        _require_nonempty(item.get("descriptor_id"), "source_inventory.items[].descriptor_id"): item
        for item in _require_items(source_inventory.get("items"))
    }
    if not documents:
        raise DocumentManifestError(
            "document_manifest_rows_required",
            {"field": "documents"},
        )

    manifest_rows: list[dict[str, Any]] = []
    extraction_rows: list[dict[str, Any]] = []
    seen_descriptor_ids: set[str] = set()
    for index, document in enumerate(documents):
        if not isinstance(document, Mapping):
            raise DocumentManifestError(
                "document_manifest_row_must_be_object",
                {"index": index},
            )
        manifest_row, extraction_row = _document_rows(
            index=index,
            document=document,
            inventory_items=inventory_items,
            manifest_id=manifest_id,
        )
        if manifest_row["descriptor_id"] in seen_descriptor_ids:
            raise DocumentManifestError(
                "document_manifest_duplicate_descriptor",
                {"index": index, "descriptor_id": manifest_row["descriptor_id"]},
            )
        seen_descriptor_ids.add(manifest_row["descriptor_id"])
        manifest_rows.append(manifest_row)
        extraction_rows.append(extraction_row)

    manifest_rows = sorted(manifest_rows, key=lambda row: row["document_id"])
    extraction_rows = sorted(extraction_rows, key=lambda row: row["document_id"])
    actor = {
        "id": _require_nonempty(prepared_by_actor_id, "prepared_by_actor_id"),
        "type": _require_nonempty(prepared_by_actor_type, "prepared_by_actor_type"),
    }
    document_manifest = {
        "schema_version": DOCUMENT_MANIFEST_SCHEMA_VERSION,
        "activation_posture": DOCUMENT_MANIFEST_ACTIVATION_POSTURE,
        "manifest_id": _require_nonempty(manifest_id, "manifest_id"),
        "source_inventory_id": _require_nonempty(
            source_inventory.get("inventory_id"),
            "source_inventory.inventory_id",
        ),
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "project_id": project_id,
        "created_at": _require_nonempty(created_at, "created_at"),
        "prepared_by_actor": actor,
        "document_count": len(manifest_rows),
        "rows": manifest_rows,
        "snapshot_digest": _digest(manifest_rows),
    }
    extraction_state_register = {
        "schema_version": EXTRACTION_STATE_REGISTER_SCHEMA_VERSION,
        "activation_posture": DOCUMENT_MANIFEST_ACTIVATION_POSTURE,
        "register_id": f"{manifest_id}:extraction-state",
        "document_manifest_id": document_manifest["manifest_id"],
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "project_id": project_id,
        "created_at": document_manifest["created_at"],
        "prepared_by_actor": actor,
        "row_count": len(extraction_rows),
        "rows": extraction_rows,
        "snapshot_digest": _digest(extraction_rows),
    }
    return {
        "schema_version": DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": DOCUMENT_MANIFEST_ACTIVATION_POSTURE,
        "document_manifest": document_manifest,
        "extraction_state_register": extraction_state_register,
        "truth_effects": {
            "creates_extraction_jobs": False,
            "creates_reviewed_evidence": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def canonical_document_manifest_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def document_manifest_digest(value: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_document_manifest_bytes(value)).hexdigest()


def _document_rows(
    *,
    index: int,
    document: Mapping[str, Any],
    inventory_items: Mapping[str, Mapping[str, Any]],
    manifest_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _reject_raw_material(document, path=f"documents[{index}]")
    descriptor_id = _require_nonempty(document.get("descriptor_id"), f"documents[{index}].descriptor_id")
    inventory_item = inventory_items.get(descriptor_id)
    if inventory_item is None:
        raise DocumentManifestError(
            "document_manifest_unknown_descriptor",
            {"index": index, "descriptor_id": descriptor_id},
        )
    document_id = str(document.get("document_id") or f"{manifest_id}:document:{index + 1:04d}")
    storage_ref = _require_nonempty(document.get("storage_ref"), f"documents[{index}].storage_ref")
    extraction_status = _require_nonempty(
        document.get("extraction_status"),
        f"documents[{index}].extraction_status",
    )
    if extraction_status not in EXTRACTION_STATUSES:
        raise DocumentManifestError(
            "document_manifest_extraction_status_invalid",
            {
                "index": index,
                "extraction_status": extraction_status,
                "allowed_statuses": sorted(EXTRACTION_STATUSES),
            },
        )
    extraction_progress = _progress(document.get("extraction_progress"), index)
    retry_count = _nonnegative_int(document.get("retry_count", 0), f"documents[{index}].retry_count")
    failure_code = document.get("failure_code")
    failure_summary = document.get("failure_summary")
    if extraction_status == "failed" and not failure_code:
        raise DocumentManifestError(
            "document_manifest_failure_code_required",
            {"index": index},
        )
    if failure_summary is not None and len(str(failure_summary)) > 240:
        raise DocumentManifestError(
            "document_manifest_failure_summary_too_long",
            {"index": index},
        )
    media_type = document.get("media_type") or inventory_item.get("content_media_type")
    byte_size = document.get("byte_size")
    if byte_size is None:
        byte_size = inventory_item.get("content_byte_size")
    manifest_row = {
        "document_id": document_id,
        "descriptor_id": descriptor_id,
        "storage_ref": storage_ref,
        "content_identity_id": _require_nonempty(
            inventory_item.get("content_identity_id"),
            f"source_inventory.items[{descriptor_id}].content_identity_id",
        ),
        "content_digest": _require_nonempty(
            inventory_item.get("content_digest"),
            f"source_inventory.items[{descriptor_id}].content_digest",
        ),
        "media_type": media_type,
        "byte_size": _optional_nonnegative_int(byte_size, f"documents[{index}].byte_size"),
        "canonicalization_profile": _require_nonempty(
            inventory_item.get("canonicalization_profile"),
            f"source_inventory.items[{descriptor_id}].canonicalization_profile",
        ),
    }
    extraction_row = {
        "document_id": document_id,
        "descriptor_id": descriptor_id,
        "extraction_status": extraction_status,
        "extraction_progress": extraction_progress,
        "retry_count": retry_count,
        "terminal": extraction_status in TERMINAL_EXTRACTION_STATUSES,
        "failure_code": str(failure_code) if failure_code is not None else None,
        "failure_summary": str(failure_summary) if failure_summary is not None else None,
        "recovery_posture": _require_nonempty(
            document.get("recovery_posture") or _default_recovery_posture(extraction_status),
            f"documents[{index}].recovery_posture",
        ),
    }
    return manifest_row, extraction_row


def _default_recovery_posture(status: str) -> str:
    if status == "failed":
        return "retry_or_quarantine_required"
    if status == "partial":
        return "review_partial_extraction_before_use"
    if status == "skipped":
        return "document_not_processed_no_evidence_claim"
    return "continue_manifest_tracking"


def _progress(value: Any, index: int) -> int:
    progress = _nonnegative_int(value if value is not None else 0, f"documents[{index}].extraction_progress")
    if progress > 100:
        raise DocumentManifestError(
            "document_manifest_progress_invalid",
            {"index": index, "extraction_progress": progress},
        )
    return progress


def _require_inventory(raw: Mapping[str, Any]) -> None:
    if raw.get("schema_version") != SOURCE_INVENTORY_SCHEMA_VERSION:
        raise DocumentManifestError(
            "document_manifest_requires_source_inventory",
            {
                "expected_schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )


def _require_items(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value:
        raise DocumentManifestError(
            "document_manifest_inventory_items_required",
            {"field": "source_inventory.items"},
        )
    items: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise DocumentManifestError(
                "document_manifest_inventory_item_must_be_object",
                {"index": index},
            )
        items.append(item)
    return items


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_RAW_KEYS or key_text.startswith("raw_"):
                raise DocumentManifestError(
                    "document_manifest_raw_field_forbidden",
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
            raise DocumentManifestError(
                "document_manifest_inline_content_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise DocumentManifestError(
                "document_manifest_raw_value_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise DocumentManifestError(
                "document_manifest_raw_value_forbidden",
                {"path": path},
            )


def _require_nonempty(value: Any, field_name: str) -> str:
    if value is None:
        raise DocumentManifestError(
            "document_manifest_required_field_missing",
            {"field": field_name},
        )
    normalized = str(value).strip()
    if not normalized:
        raise DocumentManifestError(
            "document_manifest_required_field_missing",
            {"field": field_name},
        )
    return normalized


def _nonnegative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise DocumentManifestError(
            "document_manifest_nonnegative_integer_required",
            {"field": field_name, "value": value},
        )
    return value


def _optional_nonnegative_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _nonnegative_int(value, field_name)


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
    "DOCUMENT_MANIFEST_ACTIVATION_POSTURE",
    "DOCUMENT_MANIFEST_ARTIFACT_KIND",
    "DOCUMENT_MANIFEST_ARTIFACT_ROLE",
    "DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION",
    "DOCUMENT_MANIFEST_SCHEMA_VERSION",
    "EXTRACTION_STATE_REGISTER_ARTIFACT_KIND",
    "EXTRACTION_STATE_REGISTER_SCHEMA_VERSION",
    "EXTRACTION_STATUSES",
    "DocumentManifestError",
    "build_document_manifest_outputs",
    "canonical_document_manifest_bytes",
    "document_manifest_digest",
]
