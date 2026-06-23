from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_source_occurrences import (
    create_content_identity,
    create_source_occurrence,
)


SOURCE_OCCURRENCE_TABLES = [
    "capex_content_identities",
    "capex_source_occurrences",
]
PROHIBITED_RAW_COLUMNS = {
    "absolute_path",
    "base64_content",
    "blob_bytes",
    "content_base64",
    "document_text",
    "file_name",
    "filename",
    "local_path",
    "ocr_text",
    "raw_bytes",
    "raw_content",
    "raw_filename",
    "source_path",
}


def _open_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def _alembic_config(path: Path) -> Config:
    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return config


def _init_bootstrap(path: Path) -> None:
    connection = _open_connection(path)
    try:
        create_sqlite_substrate(connection)
    finally:
        connection.close()


def _init_migrated(path: Path) -> None:
    command.upgrade(_alembic_config(path), "head")


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {str(row["name"]) for row in rows}


def _index_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'index' AND tbl_name = ?
        """,
        (table_name,),
    ).fetchall()
    return {
        str(row["name"])
        for row in rows
        if not str(row["name"]).startswith("sqlite_autoindex")
    }


def _primary_key_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {str(row["name"]) for row in rows if int(row["pk"]) > 0}


def _unique_column_sets(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[tuple[str, ...]]:
    rows = connection.execute(f"PRAGMA index_list('{table_name}')").fetchall()
    column_sets: set[tuple[str, ...]] = set()
    for row in rows:
        if not bool(row["unique"]):
            continue
        index_name = str(row["name"])
        columns = connection.execute(f"PRAGMA index_info('{index_name}')").fetchall()
        column_sets.add(tuple(str(column["name"]) for column in columns))
    return column_sets


def _table_names_like(connection: sqlite3.Connection, pattern: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name LIKE ?
        """,
        (pattern,),
    ).fetchall()
    return {str(row["name"]) for row in rows}


def test_capex_source_occurrence_schema_parity(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap.db"
    migrated_path = tmp_path / "migrated.db"
    _init_bootstrap(bootstrap_path)
    _init_migrated(migrated_path)

    bootstrap = _open_connection(bootstrap_path)
    migrated = _open_connection(migrated_path)
    try:
        for table_name in SOURCE_OCCURRENCE_TABLES:
            assert _column_names(bootstrap, table_name) == _column_names(
                migrated,
                table_name,
            )
            assert _index_names(bootstrap, table_name) == _index_names(
                migrated,
                table_name,
            )
            assert _primary_key_columns(bootstrap, table_name) == _primary_key_columns(
                migrated,
                table_name,
            )
    finally:
        bootstrap.close()
        migrated.close()


def test_capex_source_occurrence_required_fields_indexes_and_raw_column_boundary(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bootstrap.db"
    _init_bootstrap(path)
    connection = _open_connection(path)
    try:
        assert {
            "content_identity_id",
            "tenant_id",
            "domain_id",
            "digest_algorithm",
            "content_digest",
            "metadata_json",
            "created_at",
        } <= _column_names(connection, "capex_content_identities")
        assert {
            "source_occurrence_id",
            "tenant_id",
            "domain_id",
            "content_identity_id",
            "occurrence_kind",
            "status",
            "source_ref",
            "locator_json",
            "metadata_json",
            "registered_by_actor_id",
            "registered_by_actor_type",
            "created_at",
            "updated_at",
        } <= _column_names(connection, "capex_source_occurrences")
        assert _primary_key_columns(connection, "capex_content_identities") == {
            "content_identity_id"
        }
        assert _primary_key_columns(connection, "capex_source_occurrences") == {
            "source_occurrence_id"
        }
        assert (
            "tenant_id",
            "domain_id",
            "digest_algorithm",
            "content_digest",
        ) in _unique_column_sets(connection, "capex_content_identities")
        assert (
            "tenant_id",
            "domain_id",
            "source_ref",
        ) in _unique_column_sets(connection, "capex_source_occurrences")
        assert {
            "ix_capex_content_identities_digest_lookup",
        } <= _index_names(connection, "capex_content_identities")
        assert {
            "ix_capex_source_occurrences_scope_status",
            "ix_capex_source_occurrences_content_identity",
        } <= _index_names(connection, "capex_source_occurrences")
        assert (
            PROHIBITED_RAW_COLUMNS
            & _column_names(connection, "capex_content_identities")
        ) == set()
        assert (
            PROHIBITED_RAW_COLUMNS
            & _column_names(connection, "capex_source_occurrences")
        ) == set()
        assert _table_names_like(connection, "capex%source%occurrence%") == {
            "capex_source_occurrences"
        }
    finally:
        connection.close()


def test_capex_source_occurrence_runtime_schemas_match_table_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    content_identity_schema = json.loads(
        (repo_root / "schemas/runtime/capex_content_identity.schema.json").read_text(
            encoding="utf-8"
        )
    )
    source_occurrence_schema = json.loads(
        (repo_root / "schemas/runtime/capex_source_occurrence.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert content_identity_schema["additionalProperties"] is False
    assert source_occurrence_schema["additionalProperties"] is False
    assert {
        "content_identity_id",
        "tenant_id",
        "domain_id",
        "digest_algorithm",
        "content_digest",
        "metadata_json",
        "created_at",
    } <= set(content_identity_schema["required"])
    assert {
        "source_occurrence_id",
        "tenant_id",
        "domain_id",
        "content_identity_id",
        "occurrence_kind",
        "status",
        "source_ref",
        "locator_json",
        "metadata_json",
        "registered_by_actor_id",
        "registered_by_actor_type",
        "created_at",
        "updated_at",
    } <= set(source_occurrence_schema["required"])
    assert (
        source_occurrence_schema["properties"]["source_ref"]["pattern"]
        == r"^source_occurrence:[^\s]+$"
    )
    assert PROHIBITED_RAW_COLUMNS & set(content_identity_schema["properties"]) == set()
    assert PROHIBITED_RAW_COLUMNS & set(source_occurrence_schema["properties"]) == set()


def test_scoped_content_identity_uniqueness_allows_same_digest_multiple_occurrences(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bootstrap.db"
    _init_bootstrap(path)
    connection = _open_connection(path)
    try:
        create_content_identity(
            connection,
            content_identity_id="cci-001",
            tenant_id="tenant-a",
            domain_id="domain-x",
            digest_algorithm="sha256",
            content_digest="a" * 64,
            byte_size=128,
            media_type="application/pdf",
            canonicalization_profile="observed-bytes-v1",
            metadata_json={"fixture": "schema-parity"},
            created_at="2026-06-23T00:00:00Z",
        )
        with pytest.raises(sqlite3.IntegrityError):
            create_content_identity(
                connection,
                content_identity_id="cci-duplicate",
                tenant_id="tenant-a",
                domain_id="domain-x",
                digest_algorithm="sha256",
                content_digest="a" * 64,
                byte_size=128,
                media_type="application/pdf",
                canonicalization_profile="observed-bytes-v1",
                metadata_json={"fixture": "schema-parity"},
                created_at="2026-06-23T00:00:00Z",
            )
        create_content_identity(
            connection,
            content_identity_id="cci-other-domain",
            tenant_id="tenant-a",
            domain_id="domain-y",
            digest_algorithm="sha256",
            content_digest="a" * 64,
            byte_size=128,
            media_type="application/pdf",
            canonicalization_profile="observed-bytes-v1",
            metadata_json={"fixture": "schema-parity"},
            created_at="2026-06-23T00:00:00Z",
        )

        create_source_occurrence(
            connection,
            source_occurrence_id="so-001",
            tenant_id="tenant-a",
            domain_id="domain-x",
            project_id=None,
            content_identity_id="cci-001",
            occurrence_kind="document",
            status="available",
            locator_json={"storage_ref": "object://staged/sanitized/001"},
            metadata_json={"fixture": "schema-parity"},
            registered_by_actor_id="human:pm",
            registered_by_actor_type="human",
            created_at="2026-06-23T00:00:00Z",
        )
        create_source_occurrence(
            connection,
            source_occurrence_id="so-002",
            tenant_id="tenant-a",
            domain_id="domain-x",
            project_id=None,
            content_identity_id="cci-001",
            occurrence_kind="document",
            status="available",
            locator_json={"storage_ref": "object://staged/sanitized/002"},
            metadata_json={"fixture": "schema-parity"},
            registered_by_actor_id="human:pm",
            registered_by_actor_type="human",
            created_at="2026-06-23T00:00:00Z",
        )

        assert connection.execute(
            "SELECT COUNT(*) FROM capex_source_occurrences WHERE content_identity_id = ?",
            ("cci-001",),
        ).fetchone()[0] == 2
    finally:
        connection.close()
