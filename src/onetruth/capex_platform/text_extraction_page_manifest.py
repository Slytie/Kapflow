from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.document_manifest import (
    DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION,
    DOCUMENT_MANIFEST_SCHEMA_VERSION,
)


TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION = (
    "capex.text_extraction_page_manifest.outputs.v1"
)
DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION = "capex.document_text_extract.v1"
DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION = "capex.document_page_manifest.v1"
TEXT_EXTRACTION_PAGE_MANIFEST_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)
DOCUMENT_TEXT_EXTRACT_ARTIFACT_KIND = "capex.document_text_extract"
DOCUMENT_PAGE_MANIFEST_ARTIFACT_KIND = "capex.document_page_manifest"
TEXT_EXTRACTION_PAGE_MANIFEST_ARTIFACT_ROLE = "evidence"

EXTRACTION_MODES = frozenset(
    {"digital_text", "ocr", "hybrid", "metadata_only", "unavailable"}
)
OCR_STATUSES = frozenset(
    {"not_applicable", "not_requested", "queued", "completed", "partial", "failed", "gated"}
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
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
    "full_text",
    "local_path",
    "ocr_text",
    "page_text",
    "path",
    "raw_bytes",
    "raw_content",
    "raw_error",
    "raw_file",
    "raw_filename",
    "raw_log",
    "source_filename",
    "source_text",
    "stack_trace",
    "stderr",
    "stdout",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class TextExtractionPageManifestError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_text_extraction_page_manifest_outputs(
    *,
    document_manifest_outputs: Mapping[str, Any],
    text_extract_rows: Sequence[Mapping[str, Any]],
    page_rows: Sequence[Mapping[str, Any]],
    extraction_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only text extract and page manifest outputs."""

    document_manifest = _require_document_manifest_outputs(document_manifest_outputs)
    tenant_id = _require_nonempty(document_manifest.get("tenant_id"), "tenant_id")
    domain_id = _require_nonempty(document_manifest.get("domain_id"), "domain_id")
    project_id = _require_nonempty(document_manifest.get("project_id"), "project_id")
    document_rows = _document_rows(document_manifest)
    if not text_extract_rows:
        raise TextExtractionPageManifestError(
            "text_extract_rows_required",
            {"field": "text_extract_rows"},
        )
    if not page_rows:
        raise TextExtractionPageManifestError(
            "page_manifest_rows_required",
            {"field": "page_rows"},
        )

    normalized_text_rows: list[dict[str, Any]] = []
    seen_text_ids: set[str] = set()
    for index, row in enumerate(text_extract_rows):
        if not isinstance(row, Mapping):
            raise TextExtractionPageManifestError(
                "text_extract_row_must_be_object",
                {"index": index},
            )
        normalized = _text_extract_row(
            index=index,
            row=row,
            document_rows=document_rows,
            extraction_id=extraction_id,
        )
        if normalized["text_extract_id"] in seen_text_ids:
            raise TextExtractionPageManifestError(
                "text_extract_duplicate_id",
                {"index": index, "text_extract_id": normalized["text_extract_id"]},
            )
        seen_text_ids.add(normalized["text_extract_id"])
        normalized_text_rows.append(normalized)

    normalized_page_rows: list[dict[str, Any]] = []
    seen_pages: set[tuple[str, int]] = set()
    for index, row in enumerate(page_rows):
        if not isinstance(row, Mapping):
            raise TextExtractionPageManifestError(
                "page_manifest_row_must_be_object",
                {"index": index},
            )
        normalized = _page_row(
            index=index,
            row=row,
            document_rows=document_rows,
            extraction_id=extraction_id,
        )
        page_key = (normalized["document_id"], normalized["page_number"])
        if page_key in seen_pages:
            raise TextExtractionPageManifestError(
                "page_manifest_duplicate_page",
                {
                    "index": index,
                    "document_id": normalized["document_id"],
                    "page_number": normalized["page_number"],
                },
            )
        seen_pages.add(page_key)
        normalized_page_rows.append(normalized)

    normalized_text_rows = sorted(
        normalized_text_rows,
        key=lambda row: (row["document_id"], row["page_span"]["start_page"], row["text_extract_id"]),
    )
    normalized_page_rows = sorted(
        normalized_page_rows,
        key=lambda row: (row["document_id"], row["page_number"], row["page_id"]),
    )
    actor = {
        "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
        "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
    }
    return {
        "schema_version": TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": TEXT_EXTRACTION_PAGE_MANIFEST_ACTIVATION_POSTURE,
        "extraction_id": _require_nonempty(extraction_id, "extraction_id"),
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "project_id": project_id,
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": actor,
        "basis": {
            "document_manifest_id": _require_nonempty(
                document_manifest.get("manifest_id"),
                "document_manifest.manifest_id",
            ),
            "document_manifest_snapshot_digest": _require_nonempty(
                document_manifest.get("snapshot_digest"),
                "document_manifest.snapshot_digest",
            ),
            "extraction_state_register_id": _require_nonempty(
                document_manifest_outputs.get("extraction_state_register", {}).get("register_id")
                if isinstance(document_manifest_outputs.get("extraction_state_register"), Mapping)
                else None,
                "extraction_state_register.register_id",
            ),
        },
        "document_text_extract": {
            "schema_version": DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION,
            "artifact_kind": DOCUMENT_TEXT_EXTRACT_ARTIFACT_KIND,
            "artifact_role": TEXT_EXTRACTION_PAGE_MANIFEST_ARTIFACT_ROLE,
            "rows": normalized_text_rows,
            "row_count": len(normalized_text_rows),
            "snapshot_digest": _digest(normalized_text_rows),
        },
        "document_page_manifest": {
            "schema_version": DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION,
            "artifact_kind": DOCUMENT_PAGE_MANIFEST_ARTIFACT_KIND,
            "artifact_role": TEXT_EXTRACTION_PAGE_MANIFEST_ARTIFACT_ROLE,
            "rows": normalized_page_rows,
            "row_count": len(normalized_page_rows),
            "snapshot_digest": _digest(normalized_page_rows),
        },
        "truth_effects": {
            "creates_extraction_jobs": False,
            "runs_parser_adapter": False,
            "creates_reviewed_evidence": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "parser_runtime_activation",
            "workflow_run_creation",
            "public_route_activation",
            "frontend_route_activation",
            "raw_corpus_import",
            "evidence_sufficiency_claim",
            "reviewed_baseline_creation",
            "official_pointer_creation",
            "capex_runtime_activation",
            "product_activation",
        ],
    }


def canonical_text_extraction_page_manifest_bytes(outputs: Mapping[str, Any]) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def text_extraction_page_manifest_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_text_extraction_page_manifest_bytes(outputs)
    ).hexdigest()


def _require_document_manifest_outputs(raw: Mapping[str, Any]) -> Mapping[str, Any]:
    if raw.get("schema_version") != DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION:
        raise TextExtractionPageManifestError(
            "text_extraction_requires_document_manifest_outputs",
            {
                "expected_schema_version": DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )
    document_manifest = raw.get("document_manifest")
    if not isinstance(document_manifest, Mapping):
        raise TextExtractionPageManifestError(
            "text_extraction_document_manifest_required",
            {"field": "document_manifest_outputs.document_manifest"},
        )
    if document_manifest.get("schema_version") != DOCUMENT_MANIFEST_SCHEMA_VERSION:
        raise TextExtractionPageManifestError(
            "text_extraction_document_manifest_schema_mismatch",
            {
                "expected_schema_version": DOCUMENT_MANIFEST_SCHEMA_VERSION,
                "actual_schema_version": document_manifest.get("schema_version"),
            },
        )
    return document_manifest


def _document_rows(document_manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = document_manifest.get("rows")
    if not isinstance(rows, list) or not rows:
        raise TextExtractionPageManifestError(
            "text_extraction_document_rows_required",
            {"field": "document_manifest.rows"},
        )
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise TextExtractionPageManifestError(
                "text_extraction_document_row_must_be_object",
                {"index": index},
            )
        document_id = _require_nonempty(
            row.get("document_id"),
            f"document_manifest.rows[{index}].document_id",
        )
        by_id[document_id] = row
    return by_id


def _text_extract_row(
    *,
    index: int,
    row: Mapping[str, Any],
    document_rows: Mapping[str, Mapping[str, Any]],
    extraction_id: str,
) -> dict[str, Any]:
    _reject_raw_material(row, path=f"text_extract_rows[{index}]")
    document_id, descriptor_id, document = _document_basis(row, document_rows, index, "text_extract_rows")
    page_span = _page_span(row.get("page_span"), index=index)
    return {
        "text_extract_id": str(
            row.get("text_extract_id")
            or f"{extraction_id}:text:{document_id}:{page_span['start_page']:04d}-{page_span['end_page']:04d}"
        ),
        "document_id": document_id,
        "descriptor_id": descriptor_id,
        "content_identity_id": _require_nonempty(
            document.get("content_identity_id"),
            f"document_manifest.rows[{document_id}].content_identity_id",
        ),
        "source_document_digest": _require_nonempty(
            document.get("content_digest"),
            f"document_manifest.rows[{document_id}].content_digest",
        ),
        "storage_ref": _require_nonempty(
            row.get("storage_ref"),
            f"text_extract_rows[{index}].storage_ref",
        ),
        "text_digest": _sha256(row.get("text_digest"), f"text_extract_rows[{index}].text_digest"),
        "parser_config_hash": _sha256(
            row.get("parser_config_hash"),
            f"text_extract_rows[{index}].parser_config_hash",
        ),
        "extraction_mode": _allowed(
            row.get("extraction_mode"),
            EXTRACTION_MODES,
            f"text_extract_rows[{index}].extraction_mode",
            "text_extraction_mode_invalid",
        ),
        "page_span": page_span,
        "character_count": _nonnegative_int(
            row.get("character_count"),
            f"text_extract_rows[{index}].character_count",
        ),
        "token_estimate": _optional_nonnegative_int(
            row.get("token_estimate"),
            f"text_extract_rows[{index}].token_estimate",
        ),
        "ocr_status": _allowed(
            row.get("ocr_status") or "not_applicable",
            OCR_STATUSES,
            f"text_extract_rows[{index}].ocr_status",
            "text_extraction_ocr_status_invalid",
        ),
        "source_refs": _source_refs(row.get("source_refs"), index=index, field_name="source_refs"),
    }


def _page_row(
    *,
    index: int,
    row: Mapping[str, Any],
    document_rows: Mapping[str, Mapping[str, Any]],
    extraction_id: str,
) -> dict[str, Any]:
    _reject_raw_material(row, path=f"page_rows[{index}]")
    document_id, descriptor_id, document = _document_basis(row, document_rows, index, "page_rows")
    page_number = _positive_int(row.get("page_number"), f"page_rows[{index}].page_number")
    text_span = _optional_text_span(row.get("text_span"), index=index)
    return {
        "page_id": str(row.get("page_id") or f"{extraction_id}:page:{document_id}:{page_number:04d}"),
        "document_id": document_id,
        "descriptor_id": descriptor_id,
        "content_identity_id": _require_nonempty(
            document.get("content_identity_id"),
            f"document_manifest.rows[{document_id}].content_identity_id",
        ),
        "source_document_digest": _require_nonempty(
            document.get("content_digest"),
            f"document_manifest.rows[{document_id}].content_digest",
        ),
        "page_number": page_number,
        "page_text_digest": _sha256(row.get("page_text_digest"), f"page_rows[{index}].page_text_digest"),
        "page_storage_ref": (
            _require_nonempty(row.get("page_storage_ref"), f"page_rows[{index}].page_storage_ref")
            if row.get("page_storage_ref") is not None
            else None
        ),
        "parser_config_hash": _sha256(
            row.get("parser_config_hash"),
            f"page_rows[{index}].parser_config_hash",
        ),
        "text_span": text_span,
        "ocr_status": _allowed(
            row.get("ocr_status") or "not_applicable",
            OCR_STATUSES,
            f"page_rows[{index}].ocr_status",
            "text_extraction_ocr_status_invalid",
        ),
        "source_refs": _source_refs(row.get("source_refs"), index=index, field_name="source_refs"),
    }


def _document_basis(
    row: Mapping[str, Any],
    document_rows: Mapping[str, Mapping[str, Any]],
    index: int,
    collection_name: str,
) -> tuple[str, str, Mapping[str, Any]]:
    document_id = _require_nonempty(
        row.get("document_id"),
        f"{collection_name}[{index}].document_id",
    )
    document = document_rows.get(document_id)
    if document is None:
        raise TextExtractionPageManifestError(
            "text_extraction_unknown_document_id",
            {"index": index, "document_id": document_id},
        )
    descriptor_id = _require_nonempty(
        row.get("descriptor_id"),
        f"{collection_name}[{index}].descriptor_id",
    )
    expected_descriptor_id = _require_nonempty(
        document.get("descriptor_id"),
        f"document_manifest.rows[{document_id}].descriptor_id",
    )
    if descriptor_id != expected_descriptor_id:
        raise TextExtractionPageManifestError(
            "text_extraction_descriptor_mismatch",
            {
                "index": index,
                "document_id": document_id,
                "descriptor_id": descriptor_id,
                "expected_descriptor_id": expected_descriptor_id,
            },
        )
    return document_id, descriptor_id, document


def _page_span(value: Any, *, index: int) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise TextExtractionPageManifestError(
            "text_extraction_page_span_required",
            {"index": index},
        )
    start_page = _positive_int(value.get("start_page"), f"text_extract_rows[{index}].page_span.start_page")
    end_page = _positive_int(value.get("end_page"), f"text_extract_rows[{index}].page_span.end_page")
    if end_page < start_page:
        raise TextExtractionPageManifestError(
            "text_extraction_page_span_invalid",
            {"index": index, "start_page": start_page, "end_page": end_page},
        )
    return {"start_page": start_page, "end_page": end_page}


def _optional_text_span(value: Any, *, index: int) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TextExtractionPageManifestError(
            "page_manifest_text_span_must_be_object",
            {"index": index},
        )
    start_char = _nonnegative_int(value.get("start_char"), f"page_rows[{index}].text_span.start_char")
    end_char = _nonnegative_int(value.get("end_char"), f"page_rows[{index}].text_span.end_char")
    if end_char < start_char:
        raise TextExtractionPageManifestError(
            "page_manifest_text_span_invalid",
            {"index": index, "start_char": start_char, "end_char": end_char},
        )
    return {"start_char": start_char, "end_char": end_char}


def _source_refs(value: Any, *, index: int, field_name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise TextExtractionPageManifestError(
            "text_extraction_source_refs_required",
            {"index": index, "field": field_name},
        )
    refs: list[str] = []
    for ref_index, raw_ref in enumerate(value):
        source_ref = _require_nonempty(raw_ref, f"{field_name}[{ref_index}]")
        if not _SOURCE_REF_RE.match(source_ref):
            raise TextExtractionPageManifestError(
                "text_extraction_source_ref_invalid",
                {"index": index, "source_ref": source_ref},
            )
        if source_ref in refs:
            raise TextExtractionPageManifestError(
                "text_extraction_duplicate_source_ref",
                {"index": index, "source_ref": source_ref},
            )
        refs.append(source_ref)
    return sorted(refs)


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field_name: str,
    error_code: str,
) -> str:
    normalized = _require_nonempty(value, field_name)
    if normalized not in allowed:
        raise TextExtractionPageManifestError(
            error_code,
            {"field": field_name, "value": normalized, "allowed": sorted(allowed)},
        )
    return normalized


def _sha256(value: Any, field_name: str) -> str:
    normalized = _require_nonempty(value, field_name)
    if not _SHA256_RE.match(normalized):
        raise TextExtractionPageManifestError(
            "text_extraction_sha256_invalid",
            {"field": field_name, "value": normalized},
        )
    return normalized


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_RAW_KEYS or key_text.startswith("raw_"):
                raise TextExtractionPageManifestError(
                    "text_extraction_raw_field_forbidden",
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
            raise TextExtractionPageManifestError(
                "text_extraction_inline_content_forbidden",
                {"path": path},
            )
        if _ABSOLUTE_PATH_RE.match(value) or any(marker in value for marker in _RAW_PATH_MARKERS):
            raise TextExtractionPageManifestError(
                "text_extraction_raw_value_forbidden",
                {"path": path},
            )
        if _RAW_FILENAME_RE.match(value):
            raise TextExtractionPageManifestError(
                "text_extraction_raw_value_forbidden",
                {"path": path},
            )


def _require_nonempty(value: Any, field_name: str) -> str:
    if value is None:
        raise TextExtractionPageManifestError(
            "text_extraction_required_field_missing",
            {"field": field_name},
        )
    normalized = str(value).strip()
    if not normalized:
        raise TextExtractionPageManifestError(
            "text_extraction_required_field_missing",
            {"field": field_name},
        )
    return normalized


def _positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise TextExtractionPageManifestError(
            "text_extraction_positive_integer_required",
            {"field": field_name, "value": value},
        )
    return value


def _nonnegative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise TextExtractionPageManifestError(
            "text_extraction_nonnegative_integer_required",
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
    "DOCUMENT_PAGE_MANIFEST_ARTIFACT_KIND",
    "DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION",
    "DOCUMENT_TEXT_EXTRACT_ARTIFACT_KIND",
    "DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION",
    "EXTRACTION_MODES",
    "OCR_STATUSES",
    "TEXT_EXTRACTION_PAGE_MANIFEST_ACTIVATION_POSTURE",
    "TEXT_EXTRACTION_PAGE_MANIFEST_ARTIFACT_ROLE",
    "TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION",
    "TextExtractionPageManifestError",
    "build_text_extraction_page_manifest_outputs",
    "canonical_text_extraction_page_manifest_bytes",
    "text_extraction_page_manifest_digest",
]
