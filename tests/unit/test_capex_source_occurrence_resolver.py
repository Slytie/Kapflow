from __future__ import annotations

import sqlite3
from pathlib import Path

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
OTHER_PROJECT_ID = "cp-beta"
NOW = "2026-06-08T00:00:00Z"
REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _create_project(connection: sqlite3.Connection, project_id: str) -> None:
    create_capex_project(
        connection,
        project_id=project_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key=project_id.upper(),
        name=project_id,
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )


def _source_occurrence(
    connection: sqlite3.Connection,
    *,
    source_occurrence_id: str = "so-alpha",
    project_id: str | None = PROJECT_ID,
    status: str = "available",
    content_digest: str | None = None,
) -> str:
    content_identity_id = upsert_content_identity(
        connection,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        digest_algorithm="sha256",
        content_digest=content_digest or f"digest-{source_occurrence_id}",
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


def test_same_digest_in_two_projects_creates_distinct_project_scoped_occurrences() -> None:
    connection = _connection()
    try:
        _create_project(connection, OTHER_PROJECT_ID)
        first_ref = _source_occurrence(
            connection,
            source_occurrence_id="so-shared-digest-a",
            project_id=PROJECT_ID,
            content_digest="digest-shared",
        )
        second_ref = _source_occurrence(
            connection,
            source_occurrence_id="so-shared-digest-b",
            project_id=OTHER_PROJECT_ID,
            content_digest="digest-shared",
        )

        first = resolve_source_ref(
            connection,
            first_ref,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
        )
        second = resolve_source_ref(
            connection,
            second_ref,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=OTHER_PROJECT_ID,
        )
        cross_scope = resolve_source_ref(
            connection,
            second_ref,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
        )

        assert first.resolved is True
        assert first.source_occurrence_id == "so-shared-digest-a"
        assert second.resolved is True
        assert second.source_occurrence_id == "so-shared-digest-b"
        assert first.content_digest == second.content_digest == "digest-shared"
        assert cross_scope.resolved is False
        assert cross_scope.denial_reason == "source_occurrence_scope_mismatch"
    finally:
        connection.close()


def test_source_occurrence_relations_remain_inactive_until_same_project_policy_exists() -> None:
    guardrails = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "CAPEX_SOURCE_REF_AND_CLOSURE_GUARDRAILS.md"
    ).read_text(encoding="utf-8")

    assert "Source occurrence relations are now internal runtime state only" in guardrails
    assert "same tenant/domain/project duplicate, archive, derivative, and redaction" in guardrails
    assert "Public relation commands, locator-union commands" in guardrails
