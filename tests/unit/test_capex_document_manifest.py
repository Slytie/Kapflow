from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.document_manifest import (
    DOCUMENT_MANIFEST_ACTIVATION_POSTURE,
    DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION,
    DOCUMENT_MANIFEST_SCHEMA_VERSION,
    EXTRACTION_STATE_REGISTER_SCHEMA_VERSION,
    DocumentManifestError,
    build_document_manifest_outputs,
    document_manifest_digest,
)
from onetruth.capex_platform.source_inventory import build_source_inventory
from onetruth.capex_platform.staged_corpus_ingest import plan_staged_corpus_ingest
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-document-manifest"
NOW = "2026-06-17T00:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    create_capex_project(
        connection,
        project_id=PROJECT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key="CP-DOCS",
        name="Document Manifest Fixture",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def _descriptor(index: int) -> dict[str, object]:
    return {
        "descriptor_id": f"desc-{index:04d}",
        "mode": "object_store_manifest",
        "manifest_ref": f"manifest:documents:{index:04d}",
        "manifest_digest": "sha256:" + f"{index:064x}",
        "object_ref": f"object://staged/capex/{PROJECT_ID}/{index:04d}",
        "content_digest": "sha256:" + f"{index + 200:064x}",
        "content_byte_size": 2048 + index,
        "content_media_type": "application/pdf",
        "canonicalization_profile": "staged-observed-bytes-v1",
    }


def _inventory(connection: sqlite3.Connection) -> dict[str, object]:
    plan = plan_staged_corpus_ingest(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        ingest_batch_id="ingest-document-manifest",
        idempotency_key="idem-document-manifest",
        requested_by_actor_id="human:pm",
        requested_by_actor_type="human",
        created_at=NOW,
        descriptors=[_descriptor(index) for index in range(1, 7)],
    )
    return build_source_inventory(
        connection,
        ingest_plan=plan,
        inventory_id="inventory-document-manifest",
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
    )


def _documents() -> list[dict[str, object]]:
    statuses = [
        ("pending", 0),
        ("retry_pending", 25),
        ("partial", 60),
        ("completed", 100),
        ("failed", 80),
        ("skipped", 0),
    ]
    rows: list[dict[str, object]] = []
    for index, (status, progress) in enumerate(statuses, start=1):
        row: dict[str, object] = {
            "document_id": f"doc-{index:04d}",
            "descriptor_id": f"desc-{index:04d}",
            "storage_ref": f"object://staged/capex/{PROJECT_ID}/doc-{index:04d}",
            "extraction_status": status,
            "extraction_progress": progress,
            "retry_count": 1 if status == "retry_pending" else 0,
        }
        if status == "failed":
            row["failure_code"] = "parser_timeout"
            row["failure_summary"] = "Parser timed out before completion."
        rows.append(row)
    return rows


def _outputs(connection: sqlite3.Connection) -> dict[str, object]:
    return build_document_manifest_outputs(
        source_inventory=_inventory(connection),
        documents=_documents(),
        manifest_id="document-manifest-001",
        created_at=NOW,
        prepared_by_actor_id="human:pm",
        prepared_by_actor_type="human",
    )


def test_document_manifest_outputs_track_sanitized_storage_and_extraction_state() -> None:
    connection = _connection()
    try:
        outputs = _outputs(connection)

        assert outputs["schema_version"] == DOCUMENT_MANIFEST_OUTPUTS_SCHEMA_VERSION
        assert outputs["activation_posture"] == DOCUMENT_MANIFEST_ACTIVATION_POSTURE
        manifest = outputs["document_manifest"]  # type: ignore[index]
        states = outputs["extraction_state_register"]  # type: ignore[index]
        assert manifest["schema_version"] == DOCUMENT_MANIFEST_SCHEMA_VERSION
        assert states["schema_version"] == EXTRACTION_STATE_REGISTER_SCHEMA_VERSION
        assert manifest["document_count"] == 6
        assert states["row_count"] == 6
        assert {row["extraction_status"] for row in states["rows"]} == {  # type: ignore[index]
            "pending",
            "retry_pending",
            "partial",
            "completed",
            "failed",
            "skipped",
        }
        assert document_manifest_digest(outputs).startswith("sha256:")
    finally:
        connection.close()


def test_document_manifest_rejects_unknown_duplicate_and_invalid_progress() -> None:
    connection = _connection()
    try:
        inventory = _inventory(connection)
        unknown = [_documents()[0] | {"descriptor_id": "missing"}]
        with pytest.raises(DocumentManifestError) as unknown_exc:
            build_document_manifest_outputs(
                source_inventory=inventory,
                documents=unknown,
                manifest_id="document-manifest-unknown",
                created_at=NOW,
                prepared_by_actor_id="human:pm",
                prepared_by_actor_type="human",
            )
        assert unknown_exc.value.code == "document_manifest_unknown_descriptor"

        duplicate = [_documents()[0], _documents()[0] | {"document_id": "doc-duplicate"}]
        with pytest.raises(DocumentManifestError) as duplicate_exc:
            build_document_manifest_outputs(
                source_inventory=inventory,
                documents=duplicate,
                manifest_id="document-manifest-duplicate",
                created_at=NOW,
                prepared_by_actor_id="human:pm",
                prepared_by_actor_type="human",
            )
        assert duplicate_exc.value.code == "document_manifest_duplicate_descriptor"

        invalid = [_documents()[0] | {"extraction_progress": 101}]
        with pytest.raises(DocumentManifestError) as invalid_exc:
            build_document_manifest_outputs(
                source_inventory=inventory,
                documents=invalid,
                manifest_id="document-manifest-invalid",
                created_at=NOW,
                prepared_by_actor_id="human:pm",
                prepared_by_actor_type="human",
            )
        assert invalid_exc.value.code == "document_manifest_progress_invalid"
    finally:
        connection.close()


def test_document_manifest_rejects_raw_paths_filenames_inline_content_and_logs() -> None:
    connection = _connection()
    try:
        inventory = _inventory(connection)
        raw_cases = [
            (_documents()[0] | {"storage_ref": "/Users/pm/raw/source.pdf"}, "document_manifest_raw_value_forbidden"),
            (_documents()[0] | {"storage_ref": "Real Client Budget.xlsx"}, "document_manifest_raw_value_forbidden"),
            (_documents()[0] | {"storage_ref": "data:application/pdf;base64,AAAA"}, "document_manifest_inline_content_forbidden"),
            (_documents()[0] | {"raw_log": "parser dumped raw text"}, "document_manifest_raw_field_forbidden"),
        ]
        for index, (document, expected_code) in enumerate(raw_cases, start=1):
            with pytest.raises(DocumentManifestError) as exc_info:
                build_document_manifest_outputs(
                    source_inventory=inventory,
                    documents=[document],
                    manifest_id=f"document-manifest-raw-{index}",
                    created_at=NOW,
                    prepared_by_actor_id="human:pm",
                    prepared_by_actor_type="human",
                )
            assert exc_info.value.code == expected_code
    finally:
        connection.close()


def test_document_manifest_outputs_have_no_runtime_or_official_effects() -> None:
    connection = _connection()
    try:
        outputs = _outputs(connection)

        assert outputs["truth_effects"] == {
            "creates_extraction_jobs": False,
            "creates_reviewed_evidence": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        }
    finally:
        connection.close()
