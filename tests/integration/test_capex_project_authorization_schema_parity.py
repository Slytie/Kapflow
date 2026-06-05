from __future__ import annotations

from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config

from onetruth.infrastructure.events.event_store import create_sqlite_substrate


CAPEX_AUTHORIZATION_TABLES = [
    "capex_project_authorization",
    "capex_project_feature",
    "capex_user_project_view",
]


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


def test_capex_authorization_projection_schema_parity(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap.db"
    migrated_path = tmp_path / "migrated.db"
    _init_bootstrap(bootstrap_path)
    _init_migrated(migrated_path)

    bootstrap = _open_connection(bootstrap_path)
    migrated = _open_connection(migrated_path)
    try:
        for table_name in CAPEX_AUTHORIZATION_TABLES:
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


def test_capex_authorization_projection_migration_backfills_existing_rows(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "backfill.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "20260604_0011")

    connection = _open_connection(database_path)
    try:
        connection.execute(
            """
            INSERT INTO capex_projects (
                project_id,
                tenant_id,
                domain_id,
                project_key,
                name,
                state,
                metadata_json,
                created_by_actor_id,
                created_by_actor_type,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cp-existing",
                "tenant-a",
                "domain-x",
                "CAPEX-EXISTING",
                "Existing project",
                "active",
                "{}",
                "human:admin",
                "human",
                "2026-06-05T00:00:00Z",
                "2026-06-05T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO project_memberships (
                project_membership_id,
                project_id,
                tenant_id,
                domain_id,
                actor_type,
                actor_id,
                role,
                state,
                granted_by_actor_id,
                granted_by_actor_type,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "pm-existing",
                "cp-existing",
                "tenant-a",
                "domain-x",
                "human",
                "human:admin",
                "project_admin",
                "active",
                "human:admin",
                "human",
                "2026-06-05T00:00:00Z",
                "2026-06-05T00:00:00Z",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    command.upgrade(config, "head")

    migrated = _open_connection(database_path)
    try:
        authorization = migrated.execute(
            """
            SELECT *
            FROM capex_project_authorization
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-existing", "human", "human:admin"),
        ).fetchone()
        feature = migrated.execute(
            """
            SELECT *
            FROM capex_project_feature
            WHERE project_id = ? AND feature_key = ?
            """,
            ("cp-existing", "capex.runtime_activation"),
        ).fetchone()
        user_view = migrated.execute(
            """
            SELECT *
            FROM capex_user_project_view
            WHERE project_id = ? AND actor_type = ? AND actor_id = ?
            """,
            ("cp-existing", "human", "human:admin"),
        ).fetchone()

        assert authorization is not None
        assert authorization["direct_role"] == "project_admin"
        assert authorization["effective_role"] == "project_admin"
        assert authorization["source_membership_id"] == "pm-existing"
        assert feature is not None
        assert feature["state"] == "disabled"
        assert (
            feature["blocked_reason"]
            == "capex_runtime_activation_blocked_by_future_gates"
        )
        assert user_view is not None
        assert user_view["caller_role"] == "project_admin"
        assert user_view["project_key"] == "CAPEX-EXISTING"
    finally:
        migrated.close()

