from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from onetruth.capex_platform.text_extraction_page_manifest import (
    DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION,
    DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION,
    TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION,
)


CHUNK_SEARCH_EVIDENCE_BINDING_OUTPUTS_SCHEMA_VERSION = (
    "capex.chunk_search_evidence_binding.outputs.v1"
)
DOCUMENT_CHUNK_INDEX_SCHEMA_VERSION = "capex.document_chunk_index.v1"
DOCUMENT_SEARCH_INDEX_SCHEMA_VERSION = "capex.document_search_index.v1"
EVIDENCE_BINDING_INDEX_SCHEMA_VERSION = "capex.evidence_binding_index.v1"
CHUNK_SEARCH_EVIDENCE_BINDING_ACTIVATION_POSTURE = (
    "planning_only_no_capex_activation"
)
DOCUMENT_CHUNK_INDEX_ARTIFACT_KIND = "capex.document_chunk_index"
DOCUMENT_SEARCH_INDEX_ARTIFACT_KIND = "capex.document_search_index"
EVIDENCE_BINDING_INDEX_ARTIFACT_KIND = "capex.evidence_binding_index"
CHUNK_SEARCH_EVIDENCE_BINDING_ARTIFACT_ROLE = "evidence"

PROJECTION_KINDS = frozenset(
    {"lexical_metadata", "semantic_metadata", "hybrid_metadata", "evidence_lookup"}
)
BINDING_STATUSES = frozenset(
    {"candidate", "requires_review", "insufficient", "rejected"}
)

_ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|\\\\)")
_RAW_FILENAME_RE = re.compile(
    r"(?i)^[A-Za-z0-9 _.-]+\.(pdf|docx|xlsx|pptx|png|jpg|jpeg|zip|txt|csv)$"
)
_SOURCE_REF_RE = re.compile(r"^source_occurrence:[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GENERATED_ROW_REF_RE = re.compile(
    r"^generated_row:[A-Za-z0-9_.:-]+:[A-Za-z0-9_.:-]+$"
)
_RAW_PATH_MARKERS = ("/Users/", "\\Users\\")
_FORBIDDEN_RAW_KEYS = {
    "absolute_path",
    "base64",
    "base64_content",
    "blob_bytes",
    "chunk_text",
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
    "page_text",
    "path",
    "raw_bytes",
    "raw_chunk",
    "raw_content",
    "raw_error",
    "raw_file",
    "raw_filename",
    "raw_log",
    "search_text",
    "source_filename",
    "source_text",
    "stack_trace",
    "stderr",
    "stdout",
    "text",
    "text_excerpt",
}


@dataclass(frozen=True)
class ChunkSearchEvidenceBindingIndexError(ValueError):
    code: str
    details: dict[str, Any]

    def __str__(self) -> str:
        return self.code


def build_chunk_search_evidence_binding_index_outputs(
    *,
    text_extraction_page_manifest_outputs: Mapping[str, Any],
    chunk_rows: Sequence[Mapping[str, Any]],
    search_rows: Sequence[Mapping[str, Any]],
    evidence_binding_rows: Sequence[Mapping[str, Any]],
    index_id: str,
    created_at: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
) -> dict[str, Any]:
    """Build planning-only chunk/search/evidence-binding index outputs."""

    basis = _require_text_extraction_outputs(text_extraction_page_manifest_outputs)
    if not chunk_rows:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_rows_required",
            {"field": "chunk_rows"},
        )
    if not search_rows:
        raise ChunkSearchEvidenceBindingIndexError(
            "search_rows_required",
            {"field": "search_rows"},
        )
    if not evidence_binding_rows:
        raise ChunkSearchEvidenceBindingIndexError(
            "evidence_binding_rows_required",
            {"field": "evidence_binding_rows"},
        )

    normalized_chunks: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for index, row in enumerate(chunk_rows):
        if not isinstance(row, Mapping):
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_row_must_be_object",
                {"index": index},
            )
        normalized = _chunk_row(index=index, row=row, basis=basis, index_id=index_id)
        if normalized["chunk_id"] in seen_chunk_ids:
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_duplicate_id",
                {"index": index, "chunk_id": normalized["chunk_id"]},
            )
        seen_chunk_ids.add(normalized["chunk_id"])
        normalized_chunks.append(normalized)

    chunk_ids = {row["chunk_id"] for row in normalized_chunks}
    normalized_search_rows: list[dict[str, Any]] = []
    seen_search_ids: set[str] = set()
    for index, row in enumerate(search_rows):
        if not isinstance(row, Mapping):
            raise ChunkSearchEvidenceBindingIndexError(
                "search_row_must_be_object",
                {"index": index},
            )
        normalized = _search_row(
            index=index,
            row=row,
            basis=basis,
            chunk_ids=chunk_ids,
            index_id=index_id,
        )
        if normalized["search_entry_id"] in seen_search_ids:
            raise ChunkSearchEvidenceBindingIndexError(
                "search_duplicate_id",
                {"index": index, "search_entry_id": normalized["search_entry_id"]},
            )
        seen_search_ids.add(normalized["search_entry_id"])
        normalized_search_rows.append(normalized)

    normalized_bindings: list[dict[str, Any]] = []
    seen_binding_ids: set[str] = set()
    for index, row in enumerate(evidence_binding_rows):
        if not isinstance(row, Mapping):
            raise ChunkSearchEvidenceBindingIndexError(
                "evidence_binding_row_must_be_object",
                {"index": index},
            )
        normalized = _binding_row(
            index=index,
            row=row,
            basis=basis,
            chunk_ids=chunk_ids,
            index_id=index_id,
        )
        if normalized["binding_id"] in seen_binding_ids:
            raise ChunkSearchEvidenceBindingIndexError(
                "evidence_binding_duplicate_id",
                {"index": index, "binding_id": normalized["binding_id"]},
            )
        seen_binding_ids.add(normalized["binding_id"])
        normalized_bindings.append(normalized)

    normalized_chunks = sorted(
        normalized_chunks,
        key=lambda row: (row["document_id"], row["text_span"]["start_char"], row["chunk_id"]),
    )
    normalized_search_rows = sorted(
        normalized_search_rows,
        key=lambda row: (row["document_id"], row["chunk_id"], row["search_entry_id"]),
    )
    normalized_bindings = sorted(
        normalized_bindings,
        key=lambda row: (row["generated_row_ref"], row["chunk_id"], row["binding_id"]),
    )
    return {
        "schema_version": CHUNK_SEARCH_EVIDENCE_BINDING_OUTPUTS_SCHEMA_VERSION,
        "activation_posture": CHUNK_SEARCH_EVIDENCE_BINDING_ACTIVATION_POSTURE,
        "index_id": _require_nonempty(index_id, "index_id"),
        "tenant_id": basis["tenant_id"],
        "domain_id": basis["domain_id"],
        "project_id": basis["project_id"],
        "created_at": _require_nonempty(created_at, "created_at"),
        "created_by_actor": {
            "id": _require_nonempty(created_by_actor_id, "created_by_actor_id"),
            "type": _require_nonempty(created_by_actor_type, "created_by_actor_type"),
        },
        "basis": {
            "text_extraction_id": basis["extraction_id"],
            "document_text_extract_snapshot_digest": basis[
                "document_text_extract_snapshot_digest"
            ],
            "document_page_manifest_snapshot_digest": basis[
                "document_page_manifest_snapshot_digest"
            ],
        },
        "document_chunk_index": {
            "schema_version": DOCUMENT_CHUNK_INDEX_SCHEMA_VERSION,
            "artifact_kind": DOCUMENT_CHUNK_INDEX_ARTIFACT_KIND,
            "artifact_role": CHUNK_SEARCH_EVIDENCE_BINDING_ARTIFACT_ROLE,
            "rows": normalized_chunks,
            "row_count": len(normalized_chunks),
            "snapshot_digest": _digest(normalized_chunks),
        },
        "document_search_index": {
            "schema_version": DOCUMENT_SEARCH_INDEX_SCHEMA_VERSION,
            "artifact_kind": DOCUMENT_SEARCH_INDEX_ARTIFACT_KIND,
            "artifact_role": CHUNK_SEARCH_EVIDENCE_BINDING_ARTIFACT_ROLE,
            "rows": normalized_search_rows,
            "row_count": len(normalized_search_rows),
            "snapshot_digest": _digest(normalized_search_rows),
        },
        "evidence_binding_index": {
            "schema_version": EVIDENCE_BINDING_INDEX_SCHEMA_VERSION,
            "artifact_kind": EVIDENCE_BINDING_INDEX_ARTIFACT_KIND,
            "artifact_role": CHUNK_SEARCH_EVIDENCE_BINDING_ARTIFACT_ROLE,
            "rows": normalized_bindings,
            "row_count": len(normalized_bindings),
            "snapshot_digest": _digest(normalized_bindings),
        },
        "truth_effects": {
            "creates_search_service": False,
            "creates_vector_store": False,
            "creates_reviewed_evidence": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
        "cannot_be_used_for": [
            "search_runtime_activation",
            "vector_store_activation",
            "retrieval_runtime_activation",
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


def canonical_chunk_search_evidence_binding_index_bytes(
    outputs: Mapping[str, Any],
) -> bytes:
    return json.dumps(
        outputs,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def chunk_search_evidence_binding_index_digest(outputs: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_chunk_search_evidence_binding_index_bytes(outputs)
    ).hexdigest()


def _require_text_extraction_outputs(raw: Mapping[str, Any]) -> dict[str, Any]:
    if raw.get("schema_version") != TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_requires_text_extraction_outputs",
            {
                "expected_schema_version": TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION,
                "actual_schema_version": raw.get("schema_version"),
            },
        )
    text_extract = raw.get("document_text_extract")
    page_manifest = raw.get("document_page_manifest")
    if not isinstance(text_extract, Mapping):
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_text_extract_required",
            {"field": "document_text_extract"},
        )
    if text_extract.get("schema_version") != DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_text_extract_schema_mismatch",
            {
                "expected_schema_version": DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION,
                "actual_schema_version": text_extract.get("schema_version"),
            },
        )
    if not isinstance(page_manifest, Mapping):
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_page_manifest_required",
            {"field": "document_page_manifest"},
        )
    if page_manifest.get("schema_version") != DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_page_manifest_schema_mismatch",
            {
                "expected_schema_version": DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION,
                "actual_schema_version": page_manifest.get("schema_version"),
            },
        )

    text_rows = _rows(text_extract, "document_text_extract.rows")
    page_rows = _rows(page_manifest, "document_page_manifest.rows")
    text_by_id: dict[str, Mapping[str, Any]] = {}
    document_ids: set[str] = set()
    available_source_refs: set[str] = set()
    for index, row in enumerate(text_rows):
        text_extract_id = _require_nonempty(
            row.get("text_extract_id"),
            f"document_text_extract.rows[{index}].text_extract_id",
        )
        text_by_id[text_extract_id] = row
        document_ids.add(
            _require_nonempty(
                row.get("document_id"),
                f"document_text_extract.rows[{index}].document_id",
            )
        )
        available_source_refs.update(
            _source_refs(
                row.get("source_refs"),
                available_source_refs=None,
                index=index,
                field_name="document_text_extract.rows[].source_refs",
                required=True,
            )
        )
    pages_by_id: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(page_rows):
        page_id = _require_nonempty(
            row.get("page_id"),
            f"document_page_manifest.rows[{index}].page_id",
        )
        pages_by_id[page_id] = row
        document_ids.add(
            _require_nonempty(
                row.get("document_id"),
                f"document_page_manifest.rows[{index}].document_id",
            )
        )
        available_source_refs.update(
            _source_refs(
                row.get("source_refs"),
                available_source_refs=None,
                index=index,
                field_name="document_page_manifest.rows[].source_refs",
                required=True,
            )
        )
    if not text_by_id or not pages_by_id or not available_source_refs:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_text_page_basis_required",
            {"field": "text_extraction_page_manifest_outputs"},
        )
    return {
        "tenant_id": _require_nonempty(raw.get("tenant_id"), "tenant_id"),
        "domain_id": _require_nonempty(raw.get("domain_id"), "domain_id"),
        "project_id": _require_nonempty(raw.get("project_id"), "project_id"),
        "extraction_id": _require_nonempty(raw.get("extraction_id"), "extraction_id"),
        "document_text_extract_snapshot_digest": _require_nonempty(
            text_extract.get("snapshot_digest"),
            "document_text_extract.snapshot_digest",
        ),
        "document_page_manifest_snapshot_digest": _require_nonempty(
            page_manifest.get("snapshot_digest"),
            "document_page_manifest.snapshot_digest",
        ),
        "document_ids": document_ids,
        "text_by_id": text_by_id,
        "pages_by_id": pages_by_id,
        "available_source_refs": available_source_refs,
    }


def _chunk_row(
    *,
    index: int,
    row: Mapping[str, Any],
    basis: Mapping[str, Any],
    index_id: str,
) -> dict[str, Any]:
    _reject_raw_material(row, path=f"chunk_rows[{index}]")
    text_row = _text_row(row, basis, index=index)
    document_id = _document_id(row, basis, index=index, collection_name="chunk_rows")
    if document_id != text_row["document_id"]:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_text_document_mismatch",
            {
                "index": index,
                "document_id": document_id,
                "text_extract_document_id": text_row["document_id"],
            },
        )
    text_span = _text_span(
        row.get("text_span"),
        index=index,
        field_name="text_span",
        max_end=int(text_row.get("character_count") or 0),
    )
    page_span = _page_span(
        row.get("page_span"),
        index=index,
        field_name="page_span",
        basis_text_row=text_row,
    )
    page_ids = _page_ids(row.get("page_ids"), basis, document_id=document_id, page_span=page_span, index=index)
    return {
        "chunk_id": str(
            row.get("chunk_id")
            or f"{index_id}:chunk:{document_id}:{text_span['start_char']:08d}-{text_span['end_char']:08d}"
        ),
        "document_id": document_id,
        "text_extract_id": text_row["text_extract_id"],
        "page_ids": page_ids,
        "chunk_storage_ref": _sanitized_storage_ref(
            row.get("chunk_storage_ref"),
            f"chunk_rows[{index}].chunk_storage_ref",
        ),
        "chunk_digest": _sha256(row.get("chunk_digest"), f"chunk_rows[{index}].chunk_digest"),
        "parser_config_hash": _sha256(
            row.get("parser_config_hash"),
            f"chunk_rows[{index}].parser_config_hash",
        ),
        "text_span": text_span,
        "page_span": page_span,
        "character_count": text_span["end_char"] - text_span["start_char"],
        "token_estimate": _optional_nonnegative_int(
            row.get("token_estimate"),
            f"chunk_rows[{index}].token_estimate",
        ),
        "source_refs": _source_refs(
            row.get("source_refs"),
            basis["available_source_refs"],
            index=index,
            field_name="source_refs",
            required=True,
        ),
    }


def _search_row(
    *,
    index: int,
    row: Mapping[str, Any],
    basis: Mapping[str, Any],
    chunk_ids: set[str],
    index_id: str,
) -> dict[str, Any]:
    _reject_raw_material(row, path=f"search_rows[{index}]")
    chunk_id = _require_nonempty(row.get("chunk_id"), f"search_rows[{index}].chunk_id")
    if chunk_id not in chunk_ids:
        raise ChunkSearchEvidenceBindingIndexError(
            "search_unknown_chunk_id",
            {"index": index, "chunk_id": chunk_id},
        )
    document_id = _document_id(row, basis, index=index, collection_name="search_rows")
    projection_kind = _allowed(
        row.get("projection_kind"),
        PROJECTION_KINDS,
        f"search_rows[{index}].projection_kind",
        "search_projection_kind_invalid",
    )
    return {
        "search_entry_id": str(
            row.get("search_entry_id")
            or f"{index_id}:search:{chunk_id}:{projection_kind}"
        ),
        "chunk_id": chunk_id,
        "document_id": document_id,
        "search_storage_ref": _sanitized_storage_ref(
            row.get("search_storage_ref"),
            f"search_rows[{index}].search_storage_ref",
        ),
        "search_digest": _sha256(row.get("search_digest"), f"search_rows[{index}].search_digest"),
        "projection_kind": projection_kind,
        "source_refs": _source_refs(
            row.get("source_refs"),
            basis["available_source_refs"],
            index=index,
            field_name="source_refs",
            required=True,
        ),
        "runtime_indexed": False,
    }


def _binding_row(
    *,
    index: int,
    row: Mapping[str, Any],
    basis: Mapping[str, Any],
    chunk_ids: set[str],
    index_id: str,
) -> dict[str, Any]:
    _reject_raw_material(row, path=f"evidence_binding_rows[{index}]")
    chunk_id = _require_nonempty(
        row.get("chunk_id"),
        f"evidence_binding_rows[{index}].chunk_id",
    )
    if chunk_id not in chunk_ids:
        raise ChunkSearchEvidenceBindingIndexError(
            "evidence_binding_unknown_chunk_id",
            {"index": index, "chunk_id": chunk_id},
        )
    document_id = _document_id(
        row,
        basis,
        index=index,
        collection_name="evidence_binding_rows",
    )
    generated_row_ref = _generated_row_ref(
        row.get("generated_row_ref"),
        f"evidence_binding_rows[{index}].generated_row_ref",
    )
    binding_status = _allowed(
        row.get("binding_status"),
        BINDING_STATUSES,
        f"evidence_binding_rows[{index}].binding_status",
        "evidence_binding_status_invalid",
    )
    evidence_span = _text_span(
        row.get("evidence_span"),
        index=index,
        field_name="evidence_span",
        max_end=None,
    )
    return {
        "binding_id": str(
            row.get("binding_id")
            or f"{index_id}:binding:{generated_row_ref}:{chunk_id}"
        ),
        "generated_row_ref": generated_row_ref,
        "chunk_id": chunk_id,
        "document_id": document_id,
        "evidence_span": evidence_span,
        "binding_status": binding_status,
        "source_refs": _source_refs(
            row.get("source_refs"),
            basis["available_source_refs"],
            index=index,
            field_name="source_refs",
            required=True,
        ),
        "reviewed_evidence": False,
    }


def _rows(raw: Mapping[str, Any], field: str) -> list[Mapping[str, Any]]:
    rows = raw.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_rows_required",
            {"field": field},
        )
    normalized: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_index_row_must_be_object",
                {"field": field, "index": index},
            )
        normalized.append(row)
    return normalized


def _text_row(row: Mapping[str, Any], basis: Mapping[str, Any], *, index: int) -> Mapping[str, Any]:
    text_extract_id = _require_nonempty(
        row.get("text_extract_id"),
        f"chunk_rows[{index}].text_extract_id",
    )
    text_row = basis["text_by_id"].get(text_extract_id)
    if text_row is None:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_unknown_text_extract_id",
            {"index": index, "text_extract_id": text_extract_id},
        )
    return text_row


def _document_id(
    row: Mapping[str, Any],
    basis: Mapping[str, Any],
    *,
    index: int,
    collection_name: str,
) -> str:
    document_id = _require_nonempty(
        row.get("document_id"),
        f"{collection_name}[{index}].document_id",
    )
    if document_id not in basis["document_ids"]:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_index_unknown_document_id",
            {"index": index, "document_id": document_id},
        )
    return document_id


def _page_ids(
    value: Any,
    basis: Mapping[str, Any],
    *,
    document_id: str,
    page_span: Mapping[str, int],
    index: int,
) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_page_ids_required",
            {"index": index},
        )
    page_ids: list[str] = []
    seen: set[str] = set()
    for page_id in value:
        page_id_text = _require_nonempty(page_id, f"chunk_rows[{index}].page_ids[]")
        page = basis["pages_by_id"].get(page_id_text)
        if page is None:
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_unknown_page_id",
                {"index": index, "page_id": page_id_text},
            )
        if page.get("document_id") != document_id:
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_page_document_mismatch",
                {"index": index, "page_id": page_id_text, "document_id": document_id},
            )
        page_number = int(page.get("page_number") or 0)
        if page_number < page_span["start_page"] or page_number > page_span["end_page"]:
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_page_outside_span",
                {"index": index, "page_id": page_id_text, "page_span": dict(page_span)},
            )
        if page_id_text in seen:
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_duplicate_page_id",
                {"index": index, "page_id": page_id_text},
            )
        seen.add(page_id_text)
        page_ids.append(page_id_text)
    return sorted(page_ids)


def _page_span(
    value: Any,
    *,
    index: int,
    field_name: str,
    basis_text_row: Mapping[str, Any],
) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_page_span_required",
            {"index": index, "field": field_name},
        )
    start = _positive_int(value.get("start_page"), f"{field_name}.start_page", index)
    end = _positive_int(value.get("end_page"), f"{field_name}.end_page", index)
    if start > end:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_page_span_invalid",
            {"index": index, "start_page": start, "end_page": end},
        )
    text_page_span = basis_text_row.get("page_span")
    if isinstance(text_page_span, Mapping):
        text_start = int(text_page_span.get("start_page") or 0)
        text_end = int(text_page_span.get("end_page") or 0)
        if start < text_start or end > text_end:
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_page_span_outside_text_extract",
                {
                    "index": index,
                    "chunk_page_span": {"start_page": start, "end_page": end},
                    "text_page_span": {"start_page": text_start, "end_page": text_end},
                },
            )
    return {"start_page": start, "end_page": end}


def _text_span(
    value: Any,
    *,
    index: int,
    field_name: str,
    max_end: int | None,
) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_text_span_required",
            {"index": index, "field": field_name},
        )
    start = _nonnegative_int(value.get("start_char"), f"{field_name}.start_char", index)
    end = _nonnegative_int(value.get("end_char"), f"{field_name}.end_char", index)
    if start >= end:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_text_span_invalid",
            {"index": index, "start_char": start, "end_char": end},
        )
    if max_end is not None and end > max_end:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_text_span_outside_extract",
            {"index": index, "end_char": end, "max_end": max_end},
        )
    return {"start_char": start, "end_char": end}


def _source_refs(
    value: Any,
    available_source_refs: set[str] | None,
    *,
    index: int,
    field_name: str,
    required: bool,
) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list) or (required and not value):
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_source_refs_required",
            {"index": index, "field": field_name},
        )
    refs: list[str] = []
    for source_ref in value:
        source_ref_text = _require_nonempty(source_ref, field_name)
        if not _SOURCE_REF_RE.match(source_ref_text):
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_source_ref_invalid",
                {"index": index, "source_ref": source_ref_text},
            )
        if available_source_refs is not None and source_ref_text not in available_source_refs:
            raise ChunkSearchEvidenceBindingIndexError(
                "chunk_source_ref_not_in_text_extraction_basis",
                {"index": index, "source_ref": source_ref_text},
            )
        refs.append(source_ref_text)
    return sorted(set(refs))


def _generated_row_ref(value: Any, field: str) -> str:
    text = _require_nonempty(value, field)
    if not _GENERATED_ROW_REF_RE.match(text):
        raise ChunkSearchEvidenceBindingIndexError(
            "evidence_binding_generated_row_ref_invalid",
            {"field": field, "generated_row_ref": text},
        )
    return text


def _sha256(value: Any, field: str) -> str:
    text = _require_nonempty(value, field)
    if not _SHA256_RE.match(text):
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_sha256_invalid",
            {"field": field, "value": text},
        )
    return text


def _sanitized_storage_ref(value: Any, field: str) -> str:
    text = _require_nonempty(value, field)
    _reject_raw_value(text, path=field)
    return text


def _allowed(
    value: Any,
    allowed: frozenset[str],
    field: str,
    error_code: str,
) -> str:
    text = _require_nonempty(value, field)
    if text not in allowed:
        raise ChunkSearchEvidenceBindingIndexError(
            error_code,
            {"field": field, "value": text, "allowed": sorted(allowed)},
        )
    return text


def _positive_int(value: Any, field: str, index: int) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_positive_int_required",
            {"index": index, "field": field, "value": value},
        )
    return value


def _nonnegative_int(value: Any, field: str, index: int) -> int:
    if not isinstance(value, int) or value < 0:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_nonnegative_int_required",
            {"index": index, "field": field, "value": value},
        )
    return value


def _optional_nonnegative_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_nonnegative_int_required",
            {"field": field, "value": value},
        )
    return value


def _require_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_nonempty_string_required",
            {"field": field},
        )
    text = value.strip()
    _reject_raw_value(text, path=field)
    return text


def _reject_raw_material(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in _FORBIDDEN_RAW_KEYS:
                raise ChunkSearchEvidenceBindingIndexError(
                    "chunk_raw_field_forbidden",
                    {"path": f"{path}.{key_text}"},
                )
            _reject_raw_material(nested, path=f"{path}.{key_text}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_raw_material(nested, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        _reject_raw_value(value, path=path)


def _reject_raw_value(value: str, *, path: str) -> None:
    if value.startswith("data:") or "base64," in value:
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_inline_content_forbidden",
            {"path": path},
        )
    if (
        _ABSOLUTE_PATH_RE.match(value)
        or _RAW_FILENAME_RE.match(value)
        or any(marker in value for marker in _RAW_PATH_MARKERS)
    ):
        raise ChunkSearchEvidenceBindingIndexError(
            "chunk_raw_value_forbidden",
            {"path": path},
        )


def _digest(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(
        list(rows),
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
