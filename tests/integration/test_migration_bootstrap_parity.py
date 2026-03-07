from __future__ import annotations

from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config

from onetruth.infrastructure.events.event_store import create_sqlite_substrate


TABLES = [
    "artifact_versions",
    "artifact_pointers",
    "artifact_provenance_edges",
    "workflow_run_inputs",
    "task_input_bindings",
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


def _init_migrated(path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
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
            assert _column_names(bootstrap, table_name) == _column_names(migrated, table_name)
            assert _index_names(bootstrap, table_name) == _index_names(migrated, table_name)
    finally:
        bootstrap.close()
        migrated.close()
