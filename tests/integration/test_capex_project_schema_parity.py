from __future__ import annotations

from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config

from onetruth.infrastructure.events.event_store import create_sqlite_substrate


CAPEX_TABLES = ["capex_projects", "project_memberships"]


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


def _init_migrated(path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "head")


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


def _index_column_sets(connection: sqlite3.Connection, table_name: str) -> set[tuple[str, ...]]:
    column_sets: set[tuple[str, ...]] = set()
    for index in connection.execute(f"PRAGMA index_list('{table_name}')").fetchall():
        columns = connection.execute(f"PRAGMA index_info('{index['name']}')").fetchall()
        column_sets.add(tuple(str(column["name"]) for column in columns))
    return column_sets


def _primary_key_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {str(row["name"]) for row in rows if int(row["pk"]) > 0}


def test_capex_project_bootstrap_and_migration_schema_parity(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap.db"
    migrated_path = tmp_path / "migrated.db"
    _init_bootstrap(bootstrap_path)
    _init_migrated(migrated_path)

    bootstrap = _open_connection(bootstrap_path)
    migrated = _open_connection(migrated_path)
    try:
        for table_name in CAPEX_TABLES:
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

        for table_name, index_name in [
            ("workflow_runs", "ix_workflow_runs_project_scope"),
            ("timeline_events", "ix_timeline_events_project_id"),
        ]:
            assert "project_id" in _column_names(bootstrap, table_name)
            assert "project_id" in _column_names(migrated, table_name)
            assert index_name in _index_names(bootstrap, table_name)
            assert index_name in _index_names(migrated, table_name)

        for table_name in [
            "human_tasks",
            "approvals",
            "flags",
            "artifact_versions",
            "artifact_links",
            "artifact_pointers",
        ]:
            assert any(
                columns and columns[0] == "workflow_run_id"
                for columns in _index_column_sets(bootstrap, table_name)
            )
            assert any(
                columns and columns[0] == "workflow_run_id"
                for columns in _index_column_sets(migrated, table_name)
            )
    finally:
        bootstrap.close()
        migrated.close()
