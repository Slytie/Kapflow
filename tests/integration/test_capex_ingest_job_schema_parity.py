from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config

from onetruth.infrastructure.events.event_store import create_sqlite_substrate


INGEST_JOB_TABLES = [
    "capex_ingest_batches",
    "capex_ingest_jobs",
    "capex_ingest_attempts",
    "capex_ingest_job_logs",
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


def test_capex_ingest_job_schema_parity(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap.db"
    migrated_path = tmp_path / "migrated.db"
    _init_bootstrap(bootstrap_path)
    _init_migrated(migrated_path)

    bootstrap = _open_connection(bootstrap_path)
    migrated = _open_connection(migrated_path)
    try:
        for table_name in INGEST_JOB_TABLES:
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


def test_capex_ingest_job_required_fields_indexes_and_raw_column_boundary(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bootstrap.db"
    _init_bootstrap(path)
    connection = _open_connection(path)
    try:
        assert {
            "ingest_batch_id",
            "tenant_id",
            "domain_id",
            "project_id",
            "intake_ref",
            "idempotency_key",
            "request_fingerprint",
            "status",
            "descriptor_count",
            "metadata_json",
            "created_by_actor_id",
            "created_by_actor_type",
            "created_at",
            "updated_at",
        } <= _column_names(connection, "capex_ingest_batches")
        assert {
            "ingest_job_id",
            "ingest_batch_id",
            "tenant_id",
            "domain_id",
            "project_id",
            "job_kind",
            "status",
            "priority",
            "idempotency_key",
            "request_fingerprint",
            "command_receipt_id",
            "planned_task_refs_json",
            "planned_artifact_refs_json",
            "metadata_json",
            "terminal_at",
        } <= _column_names(connection, "capex_ingest_jobs")
        assert {
            "ingest_attempt_id",
            "ingest_job_id",
            "tenant_id",
            "domain_id",
            "project_id",
            "attempt_no",
            "status",
            "execution_session_id",
            "command_receipt_id",
            "lease_token",
            "metadata_json",
            "started_at",
            "completed_at",
            "error_code",
        } <= _column_names(connection, "capex_ingest_attempts")
        assert {
            "ingest_job_log_id",
            "ingest_job_id",
            "ingest_attempt_id",
            "tenant_id",
            "domain_id",
            "project_id",
            "log_kind",
            "severity",
            "message_code",
            "message_summary",
            "metadata_json",
            "created_at",
        } <= _column_names(connection, "capex_ingest_job_logs")
        assert _primary_key_columns(connection, "capex_ingest_batches") == {
            "ingest_batch_id"
        }
        assert _primary_key_columns(connection, "capex_ingest_jobs") == {
            "ingest_job_id"
        }
        assert _primary_key_columns(connection, "capex_ingest_attempts") == {
            "ingest_attempt_id"
        }
        assert _primary_key_columns(connection, "capex_ingest_job_logs") == {
            "ingest_job_log_id"
        }
        assert (
            "tenant_id",
            "domain_id",
            "project_id",
            "idempotency_key",
        ) in _unique_column_sets(connection, "capex_ingest_batches")
        assert (
            "ingest_batch_id",
            "job_kind",
            "idempotency_key",
        ) in _unique_column_sets(connection, "capex_ingest_jobs")
        assert (
            "ingest_job_id",
            "attempt_no",
        ) in _unique_column_sets(connection, "capex_ingest_attempts")
        assert {
            "ix_capex_ingest_batches_scope_status",
        } <= _index_names(connection, "capex_ingest_batches")
        assert {
            "ix_capex_ingest_jobs_batch_status",
            "ix_capex_ingest_jobs_scope_status",
        } <= _index_names(connection, "capex_ingest_jobs")
        assert {
            "ix_capex_ingest_attempts_job_status",
            "ix_capex_ingest_attempts_execution_session",
        } <= _index_names(connection, "capex_ingest_attempts")
        assert {
            "ix_capex_ingest_job_logs_job_created",
            "ix_capex_ingest_job_logs_attempt_created",
            "ix_capex_ingest_job_logs_scope_kind",
        } <= _index_names(connection, "capex_ingest_job_logs")
        for table_name in INGEST_JOB_TABLES:
            assert PROHIBITED_RAW_COLUMNS & _column_names(connection, table_name) == set()
    finally:
        connection.close()


def test_capex_ingest_job_runtime_schemas_match_table_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    schemas = {
        "capex_ingest_batches": "capex_ingest_batch.schema.json",
        "capex_ingest_jobs": "capex_ingest_job.schema.json",
        "capex_ingest_attempts": "capex_ingest_attempt.schema.json",
        "capex_ingest_job_logs": "capex_ingest_job_log.schema.json",
    }
    loaded = {
        table_name: json.loads(
            (repo_root / "schemas/runtime" / file_name).read_text(encoding="utf-8")
        )
        for table_name, file_name in schemas.items()
    }

    for table_name, schema in loaded.items():
        assert schema["additionalProperties"] is False, table_name
        assert PROHIBITED_RAW_COLUMNS & set(schema["properties"]) == set()

    assert loaded["capex_ingest_batches"]["properties"]["request_fingerprint"][
        "pattern"
    ] == "^sha256:[0-9a-f]{64}$"
    assert loaded["capex_ingest_jobs"]["properties"]["request_fingerprint"][
        "pattern"
    ] == "^sha256:[0-9a-f]{64}$"
    assert "source_inventory" in loaded["capex_ingest_jobs"]["properties"]["job_kind"][
        "enum"
    ]
    assert "succeeded" in loaded["capex_ingest_attempts"]["properties"]["status"]["enum"]
