from __future__ import annotations

import pytest

from onetruth.capex_platform.text_extraction_page_manifest import (
    DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION,
    DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION,
    TEXT_EXTRACTION_PAGE_MANIFEST_ACTIVATION_POSTURE,
    TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION,
    TextExtractionPageManifestError,
    build_text_extraction_page_manifest_outputs,
    text_extraction_page_manifest_digest,
)


NOW = "2026-06-23T00:00:00Z"


def _sha256(index: int) -> str:
    return "sha256:" + f"{index:064x}"


def _document_manifest_outputs() -> dict[str, object]:
    return {
        "schema_version": "capex.document_manifest.outputs.v1",
        "activation_posture": "planning_only_no_capex_activation",
        "document_manifest": {
            "schema_version": "capex.document_manifest.v1",
            "activation_posture": "planning_only_no_capex_activation",
            "manifest_id": "document-manifest-text-001",
            "source_inventory_id": "source-inventory-text-001",
            "tenant_id": "tenant-a",
            "domain_id": "domain-x",
            "project_id": "cp-text",
            "created_at": NOW,
            "prepared_by_actor": {"id": "human:pm", "type": "human"},
            "document_count": 2,
            "rows": [
                {
                    "document_id": "doc-0001",
                    "descriptor_id": "desc-0001",
                    "storage_ref": "object://staged/capex/cp-text/doc-0001",
                    "content_identity_id": "ci-0001",
                    "content_digest": _sha256(1),
                    "media_type": "application/pdf",
                    "byte_size": 1000,
                    "canonicalization_profile": "staged-observed-bytes-v1",
                },
                {
                    "document_id": "doc-0002",
                    "descriptor_id": "desc-0002",
                    "storage_ref": "object://staged/capex/cp-text/doc-0002",
                    "content_identity_id": "ci-0002",
                    "content_digest": _sha256(2),
                    "media_type": "application/pdf",
                    "byte_size": 2000,
                    "canonicalization_profile": "staged-observed-bytes-v1",
                },
            ],
            "snapshot_digest": _sha256(90),
        },
        "extraction_state_register": {
            "schema_version": "capex.extraction_state_register.v1",
            "register_id": "document-manifest-text-001:extraction-state",
            "row_count": 2,
            "rows": [],
            "snapshot_digest": _sha256(91),
        },
        "truth_effects": {
            "creates_extraction_jobs": False,
            "creates_reviewed_evidence": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        },
    }


def _text_rows() -> list[dict[str, object]]:
    return [
        {
            "text_extract_id": "text-doc-0002",
            "document_id": "doc-0002",
            "descriptor_id": "desc-0002",
            "storage_ref": "object://derived/text/cp-text/doc-0002",
            "text_digest": _sha256(20),
            "parser_config_hash": _sha256(30),
            "extraction_mode": "ocr",
            "page_span": {"start_page": 1, "end_page": 1},
            "character_count": 450,
            "token_estimate": 80,
            "ocr_status": "completed",
            "source_refs": ["source_occurrence:so-text-0002"],
        },
        {
            "text_extract_id": "text-doc-0001",
            "document_id": "doc-0001",
            "descriptor_id": "desc-0001",
            "storage_ref": "object://derived/text/cp-text/doc-0001",
            "text_digest": _sha256(10),
            "parser_config_hash": _sha256(30),
            "extraction_mode": "digital_text",
            "page_span": {"start_page": 1, "end_page": 2},
            "character_count": 1200,
            "token_estimate": 210,
            "source_refs": ["source_occurrence:so-text-0001"],
        },
    ]


def _page_rows() -> list[dict[str, object]]:
    return [
        {
            "page_id": "page-doc-0001-0002",
            "document_id": "doc-0001",
            "descriptor_id": "desc-0001",
            "page_number": 2,
            "page_text_digest": _sha256(12),
            "page_storage_ref": "object://derived/pages/cp-text/doc-0001/page-0002",
            "parser_config_hash": _sha256(30),
            "text_span": {"start_char": 601, "end_char": 1200},
            "source_refs": ["source_occurrence:so-text-0001"],
        },
        {
            "page_id": "page-doc-0001-0001",
            "document_id": "doc-0001",
            "descriptor_id": "desc-0001",
            "page_number": 1,
            "page_text_digest": _sha256(11),
            "page_storage_ref": "object://derived/pages/cp-text/doc-0001/page-0001",
            "parser_config_hash": _sha256(30),
            "text_span": {"start_char": 0, "end_char": 600},
            "source_refs": ["source_occurrence:so-text-0001"],
        },
        {
            "page_id": "page-doc-0002-0001",
            "document_id": "doc-0002",
            "descriptor_id": "desc-0002",
            "page_number": 1,
            "page_text_digest": _sha256(21),
            "page_storage_ref": "object://derived/pages/cp-text/doc-0002/page-0001",
            "parser_config_hash": _sha256(30),
            "ocr_status": "completed",
            "text_span": {"start_char": 0, "end_char": 450},
            "source_refs": ["source_occurrence:so-text-0002"],
        },
    ]


def _outputs(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "document_manifest_outputs": _document_manifest_outputs(),
        "text_extract_rows": _text_rows(),
        "page_rows": _page_rows(),
        "extraction_id": "text-extraction-001",
        "created_at": NOW,
        "created_by_actor_id": "service:extractor-planner",
        "created_by_actor_type": "service",
    }
    payload.update(overrides)
    return build_text_extraction_page_manifest_outputs(**payload)  # type: ignore[arg-type]


def test_text_extraction_page_manifest_outputs_are_deterministic_and_sanitized() -> None:
    outputs = _outputs()

    assert outputs["schema_version"] == TEXT_EXTRACTION_PAGE_MANIFEST_OUTPUTS_SCHEMA_VERSION
    assert outputs["activation_posture"] == TEXT_EXTRACTION_PAGE_MANIFEST_ACTIVATION_POSTURE
    assert outputs["basis"] == {
        "document_manifest_id": "document-manifest-text-001",
        "document_manifest_snapshot_digest": _sha256(90),
        "extraction_state_register_id": "document-manifest-text-001:extraction-state",
    }

    text_extract = outputs["document_text_extract"]  # type: ignore[index]
    page_manifest = outputs["document_page_manifest"]  # type: ignore[index]
    assert text_extract["schema_version"] == DOCUMENT_TEXT_EXTRACT_SCHEMA_VERSION
    assert page_manifest["schema_version"] == DOCUMENT_PAGE_MANIFEST_SCHEMA_VERSION
    assert text_extract["row_count"] == 2
    assert page_manifest["row_count"] == 3
    assert [row["document_id"] for row in text_extract["rows"]] == [  # type: ignore[index]
        "doc-0001",
        "doc-0002",
    ]
    assert [
        (row["document_id"], row["page_number"])
        for row in page_manifest["rows"]  # type: ignore[index]
    ] == [("doc-0001", 1), ("doc-0001", 2), ("doc-0002", 1)]
    assert text_extraction_page_manifest_digest(outputs).startswith("sha256:")


def test_text_extraction_rejects_unknown_document_descriptor_mismatch_and_bad_source_ref() -> None:
    with pytest.raises(TextExtractionPageManifestError) as unknown_exc:
        _outputs(text_extract_rows=[_text_rows()[0] | {"document_id": "missing"}])
    assert unknown_exc.value.code == "text_extraction_unknown_document_id"

    with pytest.raises(TextExtractionPageManifestError) as descriptor_exc:
        _outputs(text_extract_rows=[_text_rows()[0] | {"descriptor_id": "wrong"}])
    assert descriptor_exc.value.code == "text_extraction_descriptor_mismatch"

    bad_source_ref = _text_rows()[0] | {"source_refs": ["artifact_version:av-1"]}
    with pytest.raises(TextExtractionPageManifestError) as source_ref_exc:
        _outputs(text_extract_rows=[bad_source_ref])
    assert source_ref_exc.value.code == "text_extraction_source_ref_invalid"


def test_text_extraction_rejects_duplicate_pages_bad_spans_and_invalid_hashes() -> None:
    duplicate_pages = [_page_rows()[0], _page_rows()[0] | {"page_id": "duplicate"}]
    with pytest.raises(TextExtractionPageManifestError) as duplicate_exc:
        _outputs(page_rows=duplicate_pages)
    assert duplicate_exc.value.code == "page_manifest_duplicate_page"

    bad_page_span = _text_rows()[0] | {"page_span": {"start_page": 3, "end_page": 2}}
    with pytest.raises(TextExtractionPageManifestError) as page_span_exc:
        _outputs(text_extract_rows=[bad_page_span])
    assert page_span_exc.value.code == "text_extraction_page_span_invalid"

    bad_hash = _page_rows()[0] | {"page_text_digest": "sha256:not-a-real-hash"}
    with pytest.raises(TextExtractionPageManifestError) as hash_exc:
        _outputs(page_rows=[bad_hash])
    assert hash_exc.value.code == "text_extraction_sha256_invalid"


def test_text_extraction_rejects_raw_paths_filenames_and_inline_text() -> None:
    raw_cases = [
        (_text_rows()[0] | {"storage_ref": "/Users/pm/raw/source.pdf"}, "text_extraction_raw_value_forbidden"),
        (_text_rows()[0] | {"storage_ref": "Real Client Budget.xlsx"}, "text_extraction_raw_value_forbidden"),
        (_text_rows()[0] | {"storage_ref": "data:application/pdf;base64,AAAA"}, "text_extraction_inline_content_forbidden"),
        (_text_rows()[0] | {"document_text": "copied raw page text"}, "text_extraction_raw_field_forbidden"),
    ]
    for text_row, expected_code in raw_cases:
        with pytest.raises(TextExtractionPageManifestError) as exc_info:
            _outputs(text_extract_rows=[text_row])
        assert exc_info.value.code == expected_code


def test_text_extraction_outputs_have_no_runtime_or_official_effects() -> None:
    outputs = _outputs()

    assert outputs["truth_effects"] == {
        "creates_extraction_jobs": False,
        "runs_parser_adapter": False,
        "creates_reviewed_evidence": False,
        "writes_artifacts": False,
        "promotes_official_pointers": False,
        "activates_workflow_pack": False,
    }
    assert set(outputs["cannot_be_used_for"]) >= {  # type: ignore[arg-type]
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
    }
