from __future__ import annotations

import sqlite3

import pytest

from onetruth.capex_platform.source_inventory import build_source_inventory
from onetruth.capex_platform.source_occurrence_register import (
    SOURCE_OCCURRENCE_REGISTER_ACTIVATION_POSTURE,
    SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION,
    SourceOccurrenceRegisterError,
    build_source_occurrence_register,
    source_occurrence_register_digest,
    source_occurrence_register_snapshot_digest,
)
from onetruth.capex_platform.source_refs import resolve_source_ref
from onetruth.capex_platform.staged_corpus_ingest import plan_staged_corpus_ingest
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-occurrence-a"
OTHER_PROJECT_ID = "cp-occurrence-b"
NOW = "2026-06-17T00:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    for project_id in (PROJECT_ID, OTHER_PROJECT_ID):
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
    return connection


def _descriptor(index: int, *, project_id: str, digest_index: int) -> dict[str, object]:
    return {
        "descriptor_id": f"{project_id}-desc-{index:04d}",
        "mode": "object_store_manifest",
        "manifest_ref": f"manifest:{project_id}:{index:04d}",
        "manifest_digest": "sha256:" + f"{index:064x}",
        "object_ref": f"object://staged/capex/{project_id}/{index:04d}",
        "content_digest": "sha256:" + f"{digest_index:064x}",
        "content_byte_size": 1024 + digest_index,
        "content_media_type": "application/pdf",
        "canonicalization_profile": "staged-observed-bytes-v1",
        "metadata_json": {"fixture": "synthetic", "raw_material_committed": False},
    }


def _inventory(
    connection: sqlite3.Connection,
    *,
    project_id: str = PROJECT_ID,
    digest_indexes: tuple[int, ...] = (7, 7),
) -> dict[str, object]:
    plan = plan_staged_corpus_ingest(
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=project_id,
        ingest_batch_id=f"ingest-{project_id}",
        idempotency_key=f"ingest-{project_id}",
        requested_by_actor_id="human:pm",
        requested_by_actor_type="human",
        created_at=NOW,
        descriptors=[
            _descriptor(index, project_id=project_id, digest_index=digest_index)
            for index, digest_index in enumerate(digest_indexes, start=1)
        ],
    )
    return build_source_inventory(
        connection,
        ingest_plan=plan,
        inventory_id=f"inventory-{project_id}",
        created_at=NOW,
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
    )


def _contexts(project_id: str = PROJECT_ID) -> list[dict[str, object]]:
    return [
        {
            "source_occurrence_id": f"so-{project_id}-folder",
            "descriptor_id": f"{project_id}-desc-0001",
            "occurrence_kind": "sanitized_folder_manifest_entry",
            "locator_json": {
                "manifest_ref": f"manifest:{project_id}:0001",
                "container_ref": "folder:design-package",
                "entry_ref": "entry:001",
            },
            "metadata_json": {"context_profile": "folder"},
        },
        {
            "source_occurrence_id": f"so-{project_id}-archive",
            "descriptor_id": f"{project_id}-desc-0002",
            "occurrence_kind": "sanitized_archive_member",
            "locator_json": {
                "manifest_ref": f"manifest:{project_id}:0002",
                "container_ref": "archive:procurement-pack",
                "entry_ref": "entry:002",
            },
            "metadata_json": {"context_profile": "archive"},
        },
    ]


def _register(
    connection: sqlite3.Connection,
    inventory: dict[str, object],
    contexts: list[dict[str, object]],
    *,
    register_id: str = "register-001",
) -> dict[str, object]:
    return build_source_occurrence_register(
        connection,
        source_inventory=inventory,
        occurrence_contexts=contexts,
        register_id=register_id,
        created_at=NOW,
        registered_by_actor_id="human:pm",
        registered_by_actor_type="human",
    )


def test_same_digest_multiple_contexts_create_distinct_occurrences() -> None:
    connection = _connection()
    try:
        register = _register(connection, _inventory(connection), _contexts())

        assert register["schema_version"] == SOURCE_OCCURRENCE_REGISTER_SCHEMA_VERSION
        assert register["activation_posture"] == SOURCE_OCCURRENCE_REGISTER_ACTIVATION_POSTURE
        assert register["row_count"] == 2
        assert register["physical_row_count"] == 2
        rows = register["rows"]  # type: ignore[index]
        assert len({row["source_occurrence_id"] for row in rows}) == 2
        assert len({row["content_identity_id"] for row in rows}) == 1
        assert {row["occurrence_kind"] for row in rows} == {
            "sanitized_folder_manifest_entry",
            "sanitized_archive_member",
        }
        assert source_occurrence_register_digest(register).startswith("sha256:")
    finally:
        connection.close()


def test_source_occurrence_register_rows_match_physical_snapshot_digest() -> None:
    connection = _connection()
    try:
        register = _register(connection, _inventory(connection), _contexts())

        physical_rows = []
        for row in register["rows"]:  # type: ignore[index]
            stored = connection.execute(
                """
                SELECT source_occurrence_id
                FROM capex_source_occurrences
                WHERE source_occurrence_id = ?
                """,
                (row["source_occurrence_id"],),
            ).fetchone()
            assert stored is not None
            physical_rows.append(row)

        assert register["snapshot_digest"] == source_occurrence_register_snapshot_digest(
            physical_rows
        )
    finally:
        connection.close()


def test_same_digest_across_projects_resolves_only_in_matching_project() -> None:
    connection = _connection()
    try:
        first_register = _register(
            connection,
            _inventory(connection, project_id=PROJECT_ID, digest_indexes=(9,)),
            [_contexts(PROJECT_ID)[0]],
            register_id="register-a",
        )
        second_register = _register(
            connection,
            _inventory(connection, project_id=OTHER_PROJECT_ID, digest_indexes=(9,)),
            [_contexts(OTHER_PROJECT_ID)[0]],
            register_id="register-b",
        )
        first_ref = first_register["rows"][0]["source_ref"]  # type: ignore[index]
        second_ref = second_register["rows"][0]["source_ref"]  # type: ignore[index]

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
        wrong_project = resolve_source_ref(
            connection,
            first_ref,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=OTHER_PROJECT_ID,
        )

        assert first.resolved is True
        assert second.resolved is True
        assert first.content_identity_id == second.content_identity_id
        assert wrong_project.resolved is False
        assert wrong_project.denial_reason == "source_occurrence_scope_mismatch"
    finally:
        connection.close()


def test_source_occurrence_register_rejects_raw_locator_material() -> None:
    connection = _connection()
    try:
        inventory = _inventory(connection)
        for locator in (
            {"manifest_ref": "/Users/pm/raw/real-file.pdf"},
            {"file_name": "Real Client Budget.xlsx"},
            {"manifest_ref": "data:application/pdf;base64,AAAA"},
        ):
            context = _contexts()[0]
            context["source_occurrence_id"] = f"so-raw-{len(str(locator))}"
            context["locator_json"] = locator
            with pytest.raises(SourceOccurrenceRegisterError) as exc_info:
                _register(connection, inventory, [context], register_id=f"register-{len(str(locator))}")
            assert exc_info.value.code in {
                "source_occurrence_raw_locator_value_forbidden",
                "source_occurrence_raw_locator_field_forbidden",
                "source_occurrence_inline_content_forbidden",
            }
    finally:
        connection.close()


def test_source_occurrence_register_has_no_role_packet_or_pointer_effects() -> None:
    connection = _connection()
    try:
        register = _register(connection, _inventory(connection), _contexts())

        assert register["truth_effects"] == {
            "creates_source_occurrences": True,
            "creates_role_assignments": False,
            "creates_packet_register": False,
            "writes_artifacts": False,
            "promotes_official_pointers": False,
            "activates_workflow_pack": False,
        }
        assert connection.execute("SELECT COUNT(*) FROM artifact_versions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM artifact_pointers").fetchone()[0] == 0
    finally:
        connection.close()
