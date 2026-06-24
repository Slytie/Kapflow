from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project
from onetruth.infrastructure.repositories.capex_source_occurrence_relations import (
    SOURCE_OCCURRENCE_RELATION_TYPES,
    SourceOccurrenceRelationError,
    create_source_occurrence_relation,
    list_source_occurrence_relations_for_occurrence,
    transition_source_occurrence_relation_status,
)
from onetruth.infrastructure.repositories.capex_source_occurrences import (
    create_source_occurrence,
    upsert_content_identity,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-alpha"
OTHER_PROJECT_ID = "cp-beta"
NOW = "2026-06-23T00:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    _project(connection, PROJECT_ID)
    return connection


def _project(connection: sqlite3.Connection, project_id: str) -> None:
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
    source_occurrence_id: str,
    *,
    project_id: str | None = PROJECT_ID,
) -> None:
    content_identity_id = upsert_content_identity(
        connection,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        digest_algorithm="sha256",
        content_digest=f"{len(source_occurrence_id):064x}",
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
        status="available",
        locator_json={"manifest_ref": "fixture-manifest:alpha", "entry_ref": source_occurrence_id},
        metadata_json={"raw_corpus_material": False},
        registered_by_actor_id="human:admin",
        registered_by_actor_type="human",
        created_at=NOW,
    )


def _relation(
    connection: sqlite3.Connection,
    *,
    relation_id: str = "sor-001",
    relation_type: str = "duplicate_of",
    source_occurrence_id: str = "so-a",
    target_source_occurrence_id: str = "so-b",
    project_id: str = PROJECT_ID,
    metadata_json: dict[str, object] | None = None,
) -> dict[str, object]:
    return create_source_occurrence_relation(
        connection,
        source_occurrence_relation_id=relation_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=project_id,
        relation_type=relation_type,
        source_occurrence_id=source_occurrence_id,
        target_source_occurrence_id=target_source_occurrence_id,
        basis_ref=f"source_occurrence:{source_occurrence_id}",
        policy_version="capex-source-relation-policy-v1",
        metadata_json=metadata_json or {"fixture": "synthetic", "material_committed": False},
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
        created_at=NOW,
    )


def test_source_occurrence_relations_record_all_allowed_relation_types() -> None:
    connection = _connection()
    try:
        for index, relation_type in enumerate(SOURCE_OCCURRENCE_RELATION_TYPES, start=1):
            _source_occurrence(connection, f"so-{index}-a")
            _source_occurrence(connection, f"so-{index}-b")

            row = _relation(
                connection,
                relation_id=f"sor-{index:03d}",
                relation_type=relation_type,
                source_occurrence_id=f"so-{index}-a",
                target_source_occurrence_id=f"so-{index}-b",
            )

            assert row["relation_type"] == relation_type
            assert row["status"] == "active"
            assert row["tenant_id"] == TENANT_ID
            assert row["project_id"] == PROJECT_ID

        relations = list_source_occurrence_relations_for_occurrence(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            source_occurrence_id="so-1-a",
        )
        assert [row["source_occurrence_relation_id"] for row in relations] == ["sor-001"]
    finally:
        connection.close()


def test_duplicate_inverse_self_and_invalid_values_fail_closed() -> None:
    connection = _connection()
    try:
        _source_occurrence(connection, "so-a")
        _source_occurrence(connection, "so-b")
        _relation(connection)

        with pytest.raises(SourceOccurrenceRelationError) as exc_info:
            _relation(
                connection,
                relation_id="sor-inverse",
                source_occurrence_id="so-b",
                target_source_occurrence_id="so-a",
            )
        assert exc_info.value.code == "source_occurrence_relation_duplicate_inverse_exists"

        cases = [
            {"relation_id": "sor-bad-type", "relation_type": "related_to"},
            {"relation_id": "sor-self", "target_source_occurrence_id": "so-a"},
        ]
        for kwargs in cases:
            with pytest.raises(SourceOccurrenceRelationError):
                _relation(connection, **kwargs)

        with pytest.raises(SourceOccurrenceRelationError) as status_exc:
            create_source_occurrence_relation(
                connection,
                source_occurrence_relation_id="sor-bad-status",
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                relation_type="derivative_of",
                source_occurrence_id="so-a",
                target_source_occurrence_id="so-b",
                status="published",
                basis_ref="source_occurrence:so-a",
                policy_version="capex-source-relation-policy-v1",
                metadata_json={},
                created_by_actor_id="human:pm",
                created_by_actor_type="human",
                created_at=NOW,
            )
        assert status_exc.value.code == "source_occurrence_relation_status_invalid"
    finally:
        connection.close()


def test_source_occurrence_relations_require_same_project_scoped_occurrences() -> None:
    connection = _connection()
    try:
        _project(connection, OTHER_PROJECT_ID)
        _source_occurrence(connection, "so-a")
        _source_occurrence(connection, "so-other", project_id=OTHER_PROJECT_ID)
        _source_occurrence(connection, "so-projectless", project_id=None)

        with pytest.raises(SourceOccurrenceRelationError) as cross_exc:
            _relation(
                connection,
                relation_id="sor-cross",
                target_source_occurrence_id="so-other",
            )
        assert cross_exc.value.code == "source_occurrence_relation_occurrence_scope_mismatch"

        with pytest.raises(SourceOccurrenceRelationError) as projectless_exc:
            _relation(
                connection,
                relation_id="sor-projectless",
                target_source_occurrence_id="so-projectless",
            )
        assert projectless_exc.value.code == "source_occurrence_relation_project_required"
    finally:
        connection.close()


def test_source_occurrence_relations_reject_raw_material_and_do_not_create_other_state() -> None:
    connection = _connection()
    try:
        _source_occurrence(connection, "so-a")
        _source_occurrence(connection, "so-b")
        before_occurrences = connection.execute(
            "SELECT COUNT(*) FROM capex_source_occurrences"
        ).fetchone()[0]
        before_artifacts = connection.execute(
            "SELECT COUNT(*) FROM artifact_versions"
        ).fetchone()[0]

        raw_cases = [
            {"metadata_json": {"source_path": "/Users/pm/client.pdf"}},
            {"metadata_json": {"preview": "data:application/pdf;base64,AAAA"}},
            {"metadata_json": {"display": "client-source.pdf"}},
        ]
        for index, kwargs in enumerate(raw_cases, start=1):
            with pytest.raises(SourceOccurrenceRelationError):
                _relation(connection, relation_id=f"sor-raw-{index}", **kwargs)

        _relation(connection)
        assert connection.execute(
            "SELECT COUNT(*) FROM capex_source_occurrences"
        ).fetchone()[0] == before_occurrences
        assert connection.execute("SELECT COUNT(*) FROM artifact_versions").fetchone()[0] == (
            before_artifacts
        )
    finally:
        connection.close()


def test_source_occurrence_relation_terminal_status_guard() -> None:
    connection = _connection()
    try:
        _source_occurrence(connection, "so-a")
        _source_occurrence(connection, "so-b")
        relation = _relation(connection)

        updated = transition_source_occurrence_relation_status(
            connection,
            source_occurrence_relation_id=str(relation["source_occurrence_relation_id"]),
            status="superseded",
            updated_at="2026-06-23T00:05:00Z",
        )

        assert updated["status"] == "superseded"
        with pytest.raises(SourceOccurrenceRelationError) as exc_info:
            transition_source_occurrence_relation_status(
                connection,
                source_occurrence_relation_id=str(relation["source_occurrence_relation_id"]),
                status="active",
                updated_at="2026-06-23T00:06:00Z",
            )
        assert exc_info.value.code == "source_occurrence_relation_terminal_status"
    finally:
        connection.close()
