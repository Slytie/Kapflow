from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.source_refs import (
    SourceRefResolutionError,
    require_meaningful_source_refs,
    resolve_source_ref,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project
from onetruth.infrastructure.repositories.capex_source_occurrences import (
    create_source_occurrence,
    source_ref_for_occurrence,
    upsert_content_identity,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-alpha"
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
        project_key="CAPEX-A",
        name="CAPEX A",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def _source_occurrence(
    connection: sqlite3.Connection,
    *,
    source_occurrence_id: str = "so-alpha",
    project_id: str | None = PROJECT_ID,
    status: str = "available",
) -> str:
    content_identity_id = upsert_content_identity(
        connection,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        digest_algorithm="sha256",
        content_digest=f"digest-{source_occurrence_id}",
        byte_size=128,
        media_type="application/pdf",
        canonicalization_profile="sanitized-fixture-manifest-v1",
        metadata_json={"fixture_role": "sanitized"},
        created_at=NOW,
    )
    create_source_occurrence(
        connection,
        source_occurrence_id=source_occurrence_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=project_id,
        content_identity_id=content_identity_id,
        occurrence_kind="sanitized_fixture_manifest_entry",
        status=status,
        locator_json={"manifest_ref": "fixture-manifest:alpha", "entry_ref": source_occurrence_id},
        metadata_json={"raw_corpus_material": False},
        registered_by_actor_id="human:admin",
        registered_by_actor_type="human",
        created_at=NOW,
    )
    return source_ref_for_occurrence(source_occurrence_id)


def test_source_ref_resolver_returns_scope_status_and_content_identity() -> None:
    connection = _connection()
    try:
        source_ref = _source_occurrence(connection)

        resolution = resolve_source_ref(
            connection,
            source_ref,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
        )

        assert resolution.resolved is True
        assert resolution.denial_reason is None
        assert resolution.source_occurrence_id == "so-alpha"
        assert resolution.tenant_id == TENANT_ID
        assert resolution.domain_id == DOMAIN_ID
        assert resolution.project_id == PROJECT_ID
        assert resolution.occurrence_status == "available"
        assert resolution.content_digest_algorithm == "sha256"
        assert resolution.content_digest == "digest-so-alpha"
        assert resolution.to_dict()["content_identity"]["media_type"] == "application/pdf"
    finally:
        connection.close()


def test_meaningful_source_refs_reject_empty_and_malformed_refs() -> None:
    connection = _connection()
    try:
        with pytest.raises(SourceRefResolutionError, match="must not be empty"):
            require_meaningful_source_refs(
                connection,
                [],
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
            )

        with pytest.raises(SourceRefResolutionError) as exc_info:
            require_meaningful_source_refs(
                connection,
                ["artifact_version:av-1"],
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
            )

        assert exc_info.value.resolutions[0].denial_reason == "malformed_source_ref"
    finally:
        connection.close()


def test_meaningful_source_refs_reject_unresolved_cross_scope_and_non_resolvable_status() -> None:
    connection = _connection()
    try:
        available_ref = _source_occurrence(connection, source_occurrence_id="so-available")
        quarantined_ref = _source_occurrence(
            connection,
            source_occurrence_id="so-quarantined",
            status="quarantined",
        )

        assert require_meaningful_source_refs(
            connection,
            [available_ref],
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
        )[0].resolved

        cases = [
            ("source_occurrence:missing", "source_occurrence_not_found"),
            (available_ref, "source_occurrence_scope_mismatch"),
            (quarantined_ref, "source_occurrence_status_not_resolvable:quarantined"),
        ]
        for source_ref, expected_reason in cases:
            with pytest.raises(SourceRefResolutionError) as exc_info:
                require_meaningful_source_refs(
                    connection,
                    [source_ref],
                    tenant_id=TENANT_ID,
                    domain_id=DOMAIN_ID,
                    project_id=None if expected_reason == "source_occurrence_scope_mismatch" else PROJECT_ID,
                )
            assert exc_info.value.resolutions[0].denial_reason == expected_reason
    finally:
        connection.close()
