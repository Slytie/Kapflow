from __future__ import annotations

import pytest

from onetruth.capex_platform.chunk_search_evidence_binding_index import (
    CHUNK_SEARCH_EVIDENCE_BINDING_ACTIVATION_POSTURE,
    CHUNK_SEARCH_EVIDENCE_BINDING_OUTPUTS_SCHEMA_VERSION,
    DOCUMENT_CHUNK_INDEX_SCHEMA_VERSION,
    DOCUMENT_SEARCH_INDEX_SCHEMA_VERSION,
    EVIDENCE_BINDING_INDEX_SCHEMA_VERSION,
    ChunkSearchEvidenceBindingIndexError,
    build_chunk_search_evidence_binding_index_outputs,
    chunk_search_evidence_binding_index_digest,
)


NOW = "2026-06-23T00:00:00Z"


def _sha256(index: int) -> str:
    return "sha256:" + f"{index:064x}"


def _text_extraction_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.text_extraction_page_manifest.outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "extraction_id": "text-extraction-index-001",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "project_id": "cp-index",
        "document_text_extract": {
            "schema_version": "capex.document_text_extract.v1",
            "rows": [
                {
                    "text_extract_id": "text-doc-0001",
                    "document_id": "doc-0001",
                    "descriptor_id": "desc-0001",
                    "content_identity_id": "ci-0001",
                    "source_document_digest": _sha256(1),
                    "storage_ref": "object://derived/text/cp-index/doc-0001",
                    "text_digest": _sha256(10),
                    "parser_config_hash": _sha256(30),
                    "page_span": {"start_page": 1, "end_page": 2},
                    "character_count": 1200,
                    "source_refs": ["source_occurrence:so-index-0001"],
                },
                {
                    "text_extract_id": "text-doc-0002",
                    "document_id": "doc-0002",
                    "descriptor_id": "desc-0002",
                    "content_identity_id": "ci-0002",
                    "source_document_digest": _sha256(2),
                    "storage_ref": "object://derived/text/cp-index/doc-0002",
                    "text_digest": _sha256(20),
                    "parser_config_hash": _sha256(30),
                    "page_span": {"start_page": 1, "end_page": 1},
                    "character_count": 450,
                    "source_refs": ["source_occurrence:so-index-0002"],
                },
            ],
            "row_count": 2,
            "snapshot_digest": _sha256(90),
        },
        "document_page_manifest": {
            "schema_version": "capex.document_page_manifest.v1",
            "rows": [
                {
                    "page_id": "page-doc-0001-0001",
                    "document_id": "doc-0001",
                    "page_number": 1,
                    "source_refs": ["source_occurrence:so-index-0001"],
                },
                {
                    "page_id": "page-doc-0001-0002",
                    "document_id": "doc-0001",
                    "page_number": 2,
                    "source_refs": ["source_occurrence:so-index-0001"],
                },
                {
                    "page_id": "page-doc-0002-0001",
                    "document_id": "doc-0002",
                    "page_number": 1,
                    "source_refs": ["source_occurrence:so-index-0002"],
                },
            ],
            "row_count": 3,
            "snapshot_digest": _sha256(91),
        },
    }


def _chunk_rows() -> list[dict[str, object]]:
    return [
        {
            "chunk_id": "chunk-doc-0002-0001",
            "document_id": "doc-0002",
            "text_extract_id": "text-doc-0002",
            "page_ids": ["page-doc-0002-0001"],
            "chunk_storage_ref": "object://derived/chunks/cp-index/doc-0002/chunk-0001",
            "chunk_digest": _sha256(42),
            "parser_config_hash": _sha256(30),
            "text_span": {"start_char": 0, "end_char": 450},
            "page_span": {"start_page": 1, "end_page": 1},
            "token_estimate": 80,
            "source_refs": ["source_occurrence:so-index-0002"],
        },
        {
            "chunk_id": "chunk-doc-0001-0001",
            "document_id": "doc-0001",
            "text_extract_id": "text-doc-0001",
            "page_ids": ["page-doc-0001-0001"],
            "chunk_storage_ref": "object://derived/chunks/cp-index/doc-0001/chunk-0001",
            "chunk_digest": _sha256(40),
            "parser_config_hash": _sha256(30),
            "text_span": {"start_char": 0, "end_char": 600},
            "page_span": {"start_page": 1, "end_page": 1},
            "token_estimate": 100,
            "source_refs": ["source_occurrence:so-index-0001"],
        },
    ]


def _search_rows() -> list[dict[str, object]]:
    return [
        {
            "search_entry_id": "search-doc-0002-0001",
            "chunk_id": "chunk-doc-0002-0001",
            "document_id": "doc-0002",
            "search_storage_ref": "object://derived/search/cp-index/chunk-doc-0002-0001",
            "search_digest": _sha256(52),
            "projection_kind": "hybrid_metadata",
            "source_refs": ["source_occurrence:so-index-0002"],
        },
        {
            "search_entry_id": "search-doc-0001-0001",
            "chunk_id": "chunk-doc-0001-0001",
            "document_id": "doc-0001",
            "search_storage_ref": "object://derived/search/cp-index/chunk-doc-0001-0001",
            "search_digest": _sha256(50),
            "projection_kind": "lexical_metadata",
            "source_refs": ["source_occurrence:so-index-0001"],
        },
    ]


def _binding_rows() -> list[dict[str, object]]:
    return [
        {
            "binding_id": "binding-generated-0002",
            "generated_row_ref": "generated_row:capex.assumption_closure_matrix:assumption-0002",
            "chunk_id": "chunk-doc-0002-0001",
            "document_id": "doc-0002",
            "evidence_span": {"start_char": 10, "end_char": 100},
            "binding_status": "requires_review",
            "source_refs": ["source_occurrence:so-index-0002"],
        },
        {
            "binding_id": "binding-generated-0001",
            "generated_row_ref": "generated_row:capex.commitment_chain:commitment-0001",
            "chunk_id": "chunk-doc-0001-0001",
            "document_id": "doc-0001",
            "evidence_span": {"start_char": 100, "end_char": 180},
            "binding_status": "candidate",
            "source_refs": ["source_occurrence:so-index-0001"],
        },
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "text_extraction_page_manifest_outputs": _text_extraction_outputs(),
        "chunk_rows": _chunk_rows(),
        "search_rows": _search_rows(),
        "evidence_binding_rows": _binding_rows(),
        "index_id": "chunk-index-001",
        "created_at": NOW,
        "created_by_actor_id": "service:index-planner",
        "created_by_actor_type": "service",
    }
    payload.update(overrides)
    return build_chunk_search_evidence_binding_index_outputs(**payload)  # type: ignore[arg-type]


def test_chunk_search_binding_outputs_are_deterministic_and_sanitized() -> None:
    outputs = _outputs()

    assert outputs["schema_version"] == CHUNK_SEARCH_EVIDENCE_BINDING_OUTPUTS_SCHEMA_VERSION
    assert outputs["activation_posture"] == CHUNK_SEARCH_EVIDENCE_BINDING_ACTIVATION_POSTURE
    assert outputs["basis"] == {
        "text_extraction_id": "text-extraction-index-001",
        "document_text_extract_snapshot_digest": _sha256(90),
        "document_page_manifest_snapshot_digest": _sha256(91),
    }
    chunks = outputs["document_chunk_index"]  # type: ignore[index]
    search = outputs["document_search_index"]  # type: ignore[index]
    bindings = outputs["evidence_binding_index"]  # type: ignore[index]
    assert chunks["schema_version"] == DOCUMENT_CHUNK_INDEX_SCHEMA_VERSION
    assert search["schema_version"] == DOCUMENT_SEARCH_INDEX_SCHEMA_VERSION
    assert bindings["schema_version"] == EVIDENCE_BINDING_INDEX_SCHEMA_VERSION
    assert [row["chunk_id"] for row in chunks["rows"]] == [  # type: ignore[index]
        "chunk-doc-0001-0001",
        "chunk-doc-0002-0001",
    ]
    assert search["row_count"] == 2
    assert bindings["row_count"] == 2
    assert chunk_search_evidence_binding_index_digest(outputs).startswith("sha256:")


def test_chunk_index_rejects_unknown_document_text_page_and_bad_source_ref() -> None:
    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as doc_exc:
        _outputs(chunk_rows=[_chunk_rows()[0] | {"document_id": "missing"}])
    assert doc_exc.value.code == "chunk_index_unknown_document_id"

    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as text_exc:
        _outputs(chunk_rows=[_chunk_rows()[0] | {"text_extract_id": "missing"}])
    assert text_exc.value.code == "chunk_unknown_text_extract_id"

    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as page_exc:
        _outputs(chunk_rows=[_chunk_rows()[0] | {"page_ids": ["missing"]}])
    assert page_exc.value.code == "chunk_unknown_page_id"

    bad_source = _chunk_rows()[0] | {"source_refs": ["artifact_version:av-1"]}
    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as source_exc:
        _outputs(chunk_rows=[bad_source])
    assert source_exc.value.code == "chunk_source_ref_invalid"


def test_chunk_index_rejects_duplicate_ids_bad_spans_hashes_and_generated_row_refs() -> None:
    duplicate = [_chunk_rows()[0], _chunk_rows()[0] | {"document_id": "doc-0002"}]
    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as duplicate_exc:
        _outputs(chunk_rows=duplicate)
    assert duplicate_exc.value.code == "chunk_duplicate_id"

    bad_span = _chunk_rows()[0] | {"text_span": {"start_char": 500, "end_char": 450}}
    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as span_exc:
        _outputs(chunk_rows=[bad_span])
    assert span_exc.value.code == "chunk_text_span_invalid"

    bad_hash = _chunk_rows()[0] | {"chunk_digest": "sha256:not-a-real-hash"}
    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as hash_exc:
        _outputs(chunk_rows=[bad_hash])
    assert hash_exc.value.code == "chunk_sha256_invalid"

    bad_generated_row = _binding_rows()[0] | {"generated_row_ref": "artifact:bad"}
    with pytest.raises(ChunkSearchEvidenceBindingIndexError) as binding_exc:
        _outputs(evidence_binding_rows=[bad_generated_row])
    assert binding_exc.value.code == "evidence_binding_generated_row_ref_invalid"


def test_chunk_index_rejects_raw_paths_filenames_and_inline_text() -> None:
    raw_cases = [
        (_chunk_rows()[0] | {"chunk_storage_ref": "/Users/pm/raw/source.pdf"}, "chunk_raw_value_forbidden"),
        (_chunk_rows()[0] | {"chunk_storage_ref": "Real Client Budget.xlsx"}, "chunk_raw_value_forbidden"),
        (_chunk_rows()[0] | {"chunk_storage_ref": "data:application/pdf;base64,AAAA"}, "chunk_inline_content_forbidden"),
        (_chunk_rows()[0] | {"chunk_text": "copied raw chunk text"}, "chunk_raw_field_forbidden"),
    ]
    for chunk_row, expected_code in raw_cases:
        with pytest.raises(ChunkSearchEvidenceBindingIndexError) as exc_info:
            _outputs(chunk_rows=[chunk_row])
        assert exc_info.value.code == expected_code


def test_chunk_index_outputs_have_no_runtime_or_official_effects() -> None:
    outputs = _outputs()

    assert outputs["truth_effects"] == {
        "creates_search_service": False,
        "creates_vector_store": False,
        "creates_reviewed_evidence": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert set(outputs["cannot_be_used_for"]) >= {  # type: ignore[arg-type]
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
    }
