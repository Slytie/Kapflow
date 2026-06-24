from __future__ import annotations

import sqlite3

from onetruth.infrastructure.db.models import Base
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


REQUIRED_POINTER_COLUMNS = {
    "workflow_run_id",
    "pointer_key",
    "pointer_id",
    "tenant_id",
    "domain_id",
    "dataset_key",
    "partition_kind",
    "partition_key",
    "stream_key",
    "registry_kind",
}

REQUIRED_VERSION_COLUMNS = {
    "tenant_id",
    "domain_id",
    "project_id",
    "dataset_key",
    "partition_kind",
    "partition_key",
}

REQUIRED_PROVENANCE_COLUMNS = {
    "project_id",
}

REQUIRED_NEW_TABLES = {
    "command_receipts",
    "effect_ledger_entries",
    "artifact_provenance_edges",
    "workflow_run_inputs",
    "task_input_bindings",
    "capex_source_root_bindings",
    "capex_source_root_sync_runs",
    "capex_folder_tree_snapshots",
    "capex_source_occurrence_relations",
    "capex_ingest_batches",
    "capex_ingest_jobs",
    "capex_ingest_attempts",
    "capex_ingest_job_logs",
}

REQUIRED_COMMAND_RECEIPT_COLUMNS = {
    "request_fingerprint",
    "request_fingerprint_profile",
}

REQUIRED_EFFECT_LEDGER_COLUMNS = {
    "effect_ledger_entry_id",
    "tenant_id",
    "domain_id",
    "workflow_run_id",
    "command_name",
    "scope_key",
    "idempotency_key",
    "request_fingerprint",
    "request_fingerprint_profile",
    "effect_key",
    "effect_kind",
    "target_kind",
    "target_ref",
    "payload_hash",
    "payload_json",
    "status",
    "result_json",
    "metadata_json",
    "created_at",
    "applied_at",
}

REQUIRED_INDEXES_BY_TABLE = {
    "command_receipts": {
        "ix_command_receipts_workflow_run_id",
        "ix_command_receipts_scope_lookup",
    },
    "effect_ledger_entries": {
        "ix_effect_ledger_entries_scope_status",
        "ix_effect_ledger_entries_target",
        "ix_effect_ledger_entries_workflow_run_id",
    },
    "artifact_versions": {
        "ix_artifact_versions_canonical_address",
        "ix_artifact_versions_project_scope",
    },
    "artifact_pointers": {
        "ix_artifact_pointers_pointer_id",
        "ix_artifact_pointers_canonical_lookup",
        "ix_artifact_pointers_workflow_scope",
    },
    "artifact_provenance_edges": {
        "ix_artifact_provenance_edges_output",
        "ix_artifact_provenance_edges_input",
        "ix_artifact_provenance_edges_project",
    },
    "workflow_run_inputs": {
        "ix_workflow_run_inputs_workflow_run_id",
    },
    "task_input_bindings": {
        "ix_task_input_bindings_task_run_id",
    },
    "capex_source_root_bindings": {
        "ix_capex_source_root_bindings_scope_status",
        "ix_capex_source_root_bindings_observer",
    },
    "capex_source_root_sync_runs": {
        "ix_capex_source_root_sync_runs_root_status",
        "ix_capex_source_root_sync_runs_scope_status",
    },
    "capex_folder_tree_snapshots": {
        "ix_capex_folder_tree_snapshots_root_observed",
        "ix_capex_folder_tree_snapshots_scope_status",
    },
    "capex_source_occurrence_relations": {
        "ix_capex_source_occurrence_relations_source",
        "ix_capex_source_occurrence_relations_target",
        "ix_capex_source_occurrence_relations_scope_type",
    },
    "capex_ingest_batches": {
        "ix_capex_ingest_batches_scope_status",
    },
    "capex_ingest_jobs": {
        "ix_capex_ingest_jobs_batch_status",
        "ix_capex_ingest_jobs_scope_status",
    },
    "capex_ingest_attempts": {
        "ix_capex_ingest_attempts_job_status",
        "ix_capex_ingest_attempts_execution_session",
    },
    "capex_ingest_job_logs": {
        "ix_capex_ingest_job_logs_job_created",
        "ix_capex_ingest_job_logs_attempt_created",
        "ix_capex_ingest_job_logs_scope_kind",
    },
}

EXPECTED_POINTER_PK_COLUMNS = {"pointer_id"}


def _model_columns(table_name: str) -> set[str]:
    return {column.name for column in Base.metadata.tables[table_name].columns}


def _model_index_names(table_name: str) -> set[str]:
    return {
        index.name
        for index in Base.metadata.tables[table_name].indexes
        if index.name is not None
    }


def _sqlite_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _sqlite_table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {str(row["name"]) for row in rows}


def _sqlite_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {str(row["name"]) for row in rows}


def _sqlite_indexes(connection: sqlite3.Connection, table_name: str) -> set[str]:
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


def _model_primary_key_columns(table_name: str) -> set[str]:
    return {
        column.name
        for column in Base.metadata.tables[table_name].columns
        if column.primary_key
    }


def _sqlite_primary_key_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {
        str(row["name"])
        for row in rows
        if int(row["pk"]) > 0
    }


def test_models_include_strategy_a_expand_schema_surfaces() -> None:
    table_names = set(Base.metadata.tables)
    assert REQUIRED_NEW_TABLES <= table_names

    assert REQUIRED_POINTER_COLUMNS <= _model_columns("artifact_pointers")
    assert REQUIRED_VERSION_COLUMNS <= _model_columns("artifact_versions")
    assert REQUIRED_PROVENANCE_COLUMNS <= _model_columns("artifact_provenance_edges")
    assert REQUIRED_COMMAND_RECEIPT_COLUMNS <= _model_columns("command_receipts")
    assert REQUIRED_EFFECT_LEDGER_COLUMNS <= _model_columns("effect_ledger_entries")
    assert _model_primary_key_columns("artifact_pointers") == EXPECTED_POINTER_PK_COLUMNS

    for table_name, expected_indexes in REQUIRED_INDEXES_BY_TABLE.items():
        assert expected_indexes <= _model_index_names(table_name)


def test_bootstrap_schema_matches_strategy_a_expand_schema_surfaces() -> None:
    connection = _sqlite_connection()
    try:
        assert REQUIRED_NEW_TABLES <= _sqlite_table_names(connection)
        assert REQUIRED_POINTER_COLUMNS <= _sqlite_columns(connection, "artifact_pointers")
        assert REQUIRED_VERSION_COLUMNS <= _sqlite_columns(connection, "artifact_versions")
        assert REQUIRED_PROVENANCE_COLUMNS <= _sqlite_columns(
            connection,
            "artifact_provenance_edges",
        )
        assert REQUIRED_COMMAND_RECEIPT_COLUMNS <= _sqlite_columns(connection, "command_receipts")
        assert REQUIRED_EFFECT_LEDGER_COLUMNS <= _sqlite_columns(
            connection,
            "effect_ledger_entries",
        )
        assert _sqlite_primary_key_columns(connection, "artifact_pointers") == EXPECTED_POINTER_PK_COLUMNS
        for table_name, expected_indexes in REQUIRED_INDEXES_BY_TABLE.items():
            assert expected_indexes <= _sqlite_indexes(connection, table_name)
    finally:
        connection.close()
