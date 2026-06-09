from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.closure_governance import (
    ClosureDimensionInput,
    create_closure_snapshot_from_evaluation,
    evaluate_closure_gate,
)
from onetruth.capex_platform.workflow_handoffs import (
    HandoffManifestValidationError,
    require_valid_handoff_manifest,
    validate_handoff_manifest,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_pointers import promote_pointer
from onetruth.infrastructure.repositories.artifact_versions import create_artifact_version
from onetruth.infrastructure.repositories.capex_closure_governance import mark_closure_snapshot_stale
from onetruth.infrastructure.repositories.capex_projects import create_capex_project
from onetruth.infrastructure.repositories.capex_source_occurrences import (
    create_source_occurrence,
    source_ref_for_occurrence,
    upsert_content_identity,
)
from onetruth.infrastructure.repositories.workflow_runs import create_workflow_run


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-handoff"
WORKFLOW_RUN_ID = "wr-handoff-source"
NOW = "2026-06-08T00:00:00Z"


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
        project_key="CAPEX-HANDOFF",
        name="Handoff project",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    create_workflow_run(
        connection,
        workflow_run_id=WORKFLOW_RUN_ID,
        workflow_id="capex.source_review.v1",
        workflow_version="v1",
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        partition_key="project:cp-handoff",
        logical_date="2026-06-08",
        activation_key="source-review",
        state="active",
        created_at=NOW,
    )
    return connection


def _seed_source_ref(connection: sqlite3.Connection) -> str:
    content_identity_id = upsert_content_identity(
        connection,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        digest_algorithm="sha256",
        content_digest="digest-source",
        byte_size=512,
        media_type="application/json",
        canonicalization_profile="sanitized-fixture-manifest-v1",
        metadata_json={},
        created_at=NOW,
    )
    create_source_occurrence(
        connection,
        source_occurrence_id="so-handoff",
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        content_identity_id=content_identity_id,
        occurrence_kind="sanitized_fixture_manifest_entry",
        status="available",
        locator_json={"manifest_ref": "fixture-manifest:handoff", "entry_ref": "so-handoff"},
        metadata_json={"raw_corpus_material": False},
        registered_by_actor_id="human:admin",
        registered_by_actor_type="human",
        created_at=NOW,
    )
    return source_ref_for_occurrence("so-handoff")


def _seed_artifact_and_pointer(connection: sqlite3.Connection) -> None:
    create_artifact_version(
        connection,
        artifact_version_id="av-handoff",
        workflow_run_id=WORKFLOW_RUN_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        artifact_kind="capex.source.validation.packet",
        artifact_role="handoff_basis",
        media_type="application/json",
        storage_uri="memory://handoff",
        content_digest="digest-artifact",
        byte_size=64,
        metadata_json={},
        task_run_id=None,
        dataset_key="capex_project",
        partition_kind="CapexProjectID",
        partition_key=PROJECT_ID,
        parent_artifact_version_id=None,
        supersedes_artifact_version_id=None,
        lineage_note=None,
        created_at=NOW,
    )
    promote_pointer(
        connection,
        pointer_id="ptr-handoff",
        workflow_run_id=WORKFLOW_RUN_ID,
        pointer_key="official:source-validation",
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        dataset_key="capex_project",
        partition_kind="CapexProjectID",
        partition_key=PROJECT_ID,
        stream_key="capex-project:cp-handoff:source-validation",
        registry_kind="singleton",
        scope_kind="capex_project",
        scope_ref=PROJECT_ID,
        artifact_kind="capex.source.validation.packet",
        artifact_version_id="av-handoff",
        promotion_reason="handoff basis",
        promoted_by_task_run_id=None,
        approved_by_approval_id=None,
        expected_generation=None,
        updated_at=NOW,
    )


def _seed_closure(connection: sqlite3.Connection, source_ref: str) -> None:
    evaluate_closure_gate(
        connection,
        closure_gate_evaluation_id="cge-handoff",
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        closure_target_kind="workflow_handoff",
        closure_target_ref="hm-handoff",
        dimensions=(ClosureDimensionInput("source_basis", (source_ref,)),),
        created_by_actor_id="human:reviewer",
        created_by_actor_type="human",
        now_iso=NOW,
    )
    create_closure_snapshot_from_evaluation(
        connection,
        closure_snapshot_id="cs-handoff",
        closure_gate_evaluation_id="cge-handoff",
        created_by_actor_id="human:reviewer",
        created_by_actor_type="human",
        now_iso=NOW,
    )


def _manifest(source_ref: str) -> dict[str, object]:
    return {
        "manifest_id": "hm-handoff",
        "schema_version": "capex.workflow_handoff_manifest.v1",
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "project_id": PROJECT_ID,
        "source_workflow_run_id": WORKFLOW_RUN_ID,
        "target_workflow_id": "capex.assumption_closure.v1",
        "target_workflow_version": "v1",
        "target_partition_key": "project:cp-handoff",
        "artifact_versions": [
            {
                "artifact_version_id": "av-handoff",
                "artifact_kind": "capex.source.validation.packet",
                "content_digest": "digest-artifact",
            }
        ],
        "pointers": [
            {
                "pointer_id": "ptr-handoff",
                "pointer_key": "official:source-validation",
                "artifact_version_id": "av-handoff",
                "generation": 0,
            }
        ],
        "source_refs": [source_ref],
        "validation_summaries": [
            {
                "validation_id": "validation-source-basis",
                "result": "pass",
                "summary": "Sanitized source basis is present.",
            }
        ],
        "closure_gate_evaluation_ids": ["cge-handoff"],
        "closure_snapshot_ids": ["cs-handoff"],
        "task_handoff_bindings": [
            {
                "binding_id": "task-binding-1",
                "task_kind": "capex.review_source_basis",
                "basis_ref": "av-handoff",
            }
        ],
        "workpage_handoff_bindings": [
            {
                "binding_id": "workpage-binding-1",
                "workpage_kind": "capex-source-review-v0",
                "basis_ref": "ptr-handoff",
            }
        ],
        "basis_version_vector_json": {
            "basis_refs": [source_ref, "artifact_version:av-handoff", "pointer:ptr-handoff:0"]
        },
        "metadata_json": {"activation_allowed": False},
    }


def _seed_valid_manifest_basis(connection: sqlite3.Connection) -> tuple[str, dict[str, object]]:
    source_ref = _seed_source_ref(connection)
    _seed_artifact_and_pointer(connection)
    _seed_closure(connection, source_ref)
    return source_ref, _manifest(source_ref)


def test_handoff_manifest_validation_accepts_exact_current_basis() -> None:
    connection = _connection()
    try:
        _source_ref, manifest = _seed_valid_manifest_basis(connection)

        validated = require_valid_handoff_manifest(connection, manifest)
        result = validate_handoff_manifest(connection, manifest)

        assert validated.manifest_id == "hm-handoff"
        assert result.valid is True
        assert result.error_codes == ()
    finally:
        connection.close()


def test_handoff_manifest_validation_rejects_missing_manifest() -> None:
    connection = _connection()
    try:
        with pytest.raises(HandoffManifestValidationError) as exc_info:
            require_valid_handoff_manifest(connection, None)

        assert exc_info.value.result.error_codes == ("missing_handoff_manifest",)
    finally:
        connection.close()


def test_handoff_manifest_validation_rejects_pointer_generation_drift() -> None:
    connection = _connection()
    try:
        _source_ref, manifest = _seed_valid_manifest_basis(connection)
        manifest["pointers"][0]["generation"] = 1

        result = validate_handoff_manifest(connection, manifest)

        assert result.valid is False
        assert "pointer_generation_drift" in result.error_codes
    finally:
        connection.close()


def test_handoff_manifest_validation_rejects_stale_closure_snapshot() -> None:
    connection = _connection()
    try:
        _source_ref, manifest = _seed_valid_manifest_basis(connection)
        mark_closure_snapshot_stale(
            connection,
            closure_snapshot_id="cs-handoff",
            stale_reason="basis_ref_changed:source_occurrence:so-handoff",
            stale_at="2026-06-08T01:00:00Z",
        )

        result = validate_handoff_manifest(connection, manifest)

        assert result.valid is False
        assert "closure_snapshot_not_current" in result.error_codes
    finally:
        connection.close()


def test_handoff_manifest_validation_rejects_unresolved_source_and_missing_validation() -> None:
    connection = _connection()
    try:
        source_ref, manifest = _seed_valid_manifest_basis(connection)
        manifest["source_refs"] = [source_ref.replace("so-handoff", "missing")]
        manifest["validation_summaries"] = []

        result = validate_handoff_manifest(connection, manifest)

        assert result.valid is False
        assert "source_refs_not_meaningful" in result.error_codes
        assert "missing_validation_summary" in result.error_codes
    finally:
        connection.close()
