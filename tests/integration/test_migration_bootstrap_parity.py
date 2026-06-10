from __future__ import annotations

from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
import pytest

from onetruth.infrastructure.events.event_store import (
    SQLiteSchemaRepairError,
    create_sqlite_substrate,
)


TABLES = [
    "artifact_versions",
    "artifact_pointers",
    "artifact_provenance_edges",
    "workflow_run_inputs",
    "task_input_bindings",
]

CAPEX_RUNTIME_TABLES = [
    "capex_projects",
    "project_memberships",
    "capex_project_authorization",
    "capex_project_feature",
    "capex_user_project_view",
    "capex_content_identities",
    "capex_source_occurrences",
    "capex_waivers",
    "capex_closure_gate_evaluations",
    "capex_closure_snapshots",
    "capex_workpage_projection_snapshots",
    "capex_workpage_projection_rows",
]


def _open_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def _init_bootstrap(path: Path) -> None:
    connection = _open_connection(path)
    try:
        create_sqlite_substrate(connection)
    finally:
        connection.close()


def _alembic_config(path: Path) -> Config:
    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    return config


def _init_migrated(path: Path) -> None:
    config = _alembic_config(path)
    command.upgrade(config, "head")


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


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
    return {
        str(row["name"])
        for row in rows
        if int(row["pk"]) > 0
    }


def test_bootstrap_and_migration_schema_parity_for_strategy_a_tables(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap.db"
    migrated_path = tmp_path / "migrated.db"
    _init_bootstrap(bootstrap_path)
    _init_migrated(migrated_path)

    bootstrap = _open_connection(bootstrap_path)
    migrated = _open_connection(migrated_path)
    try:
        for table_name in TABLES:
            assert _table_exists(bootstrap, table_name), table_name
            assert _table_exists(migrated, table_name), table_name
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


def test_capex_alembic_upgrade_from_pre_capex_revision_is_idempotent(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "capex-upgrade.db"
    config = _alembic_config(database_path)

    command.upgrade(config, "20260313_0010")
    command.upgrade(config, "head")
    command.upgrade(config, "head")

    connection = _open_connection(database_path)
    try:
        for table_name in CAPEX_RUNTIME_TABLES:
            assert _table_exists(connection, table_name), table_name
            assert _primary_key_columns(connection, table_name), table_name
        assert "project_id" in _column_names(connection, "workflow_runs")
        assert "project_id" in _column_names(connection, "timeline_events")
        assert "ix_workflow_runs_project_scope" in _index_names(
            connection,
            "workflow_runs",
        )
        assert "ix_timeline_events_project_id" in _index_names(
            connection,
            "timeline_events",
        )
    finally:
        connection.close()


def test_sqlite_bootstrap_repairs_missing_project_scope_columns(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "missing-project-columns.db"
    connection = _open_connection(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE timeline_events (
                sequence_no INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                domain_id TEXT NOT NULL,
                workflow_run_id TEXT,
                actor TEXT NOT NULL,
                links TEXT NOT NULL,
                payload TEXT NOT NULL,
                correlation_id TEXT,
                causation_id TEXT,
                idempotency_key TEXT UNIQUE,
                integrity TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE workflow_runs (
                workflow_run_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                workflow_version TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                domain_id TEXT NOT NULL,
                partition_key TEXT NOT NULL,
                logical_date TEXT,
                activation_key TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (
                    tenant_id,
                    domain_id,
                    workflow_id,
                    partition_key,
                    activation_key
                )
            );
            """
        )

        create_sqlite_substrate(connection)

        assert "project_id" in _column_names(connection, "timeline_events")
        assert "project_id" in _column_names(connection, "workflow_runs")
        assert "ix_timeline_events_project_id" in _index_names(
            connection,
            "timeline_events",
        )
        assert "ix_workflow_runs_project_scope" in _index_names(
            connection,
            "workflow_runs",
        )
    finally:
        connection.close()


def test_sqlite_bootstrap_recreates_empty_malformed_capex_shell(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "empty-malformed-capex.db"
    connection = _open_connection(database_path)
    try:
        connection.execute(
            "CREATE TABLE capex_projects (project_id TEXT PRIMARY KEY)"
        )

        create_sqlite_substrate(connection)

        assert {
            "project_id",
            "tenant_id",
            "domain_id",
            "project_key",
            "state",
        } <= _column_names(connection, "capex_projects")
        assert "ix_capex_projects_scope_lookup" in _index_names(
            connection,
            "capex_projects",
        )
    finally:
        connection.close()


def test_sqlite_bootstrap_refuses_nonempty_malformed_capex_shell(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nonempty-malformed-capex.db"
    connection = _open_connection(database_path)
    try:
        connection.execute(
            "CREATE TABLE capex_projects (project_id TEXT PRIMARY KEY)"
        )
        connection.execute(
            "INSERT INTO capex_projects (project_id) VALUES (?)",
            ("cp-1",),
        )

        with pytest.raises(SQLiteSchemaRepairError) as excinfo:
            create_sqlite_substrate(connection)

        assert "non-empty malformed CAPEX table capex_projects" in str(
            excinfo.value
        )
        assert "tenant_id" in str(excinfo.value)
    finally:
        connection.close()
