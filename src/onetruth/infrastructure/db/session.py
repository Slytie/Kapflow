from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

DEFAULT_DB_URL = "sqlite:///./onetruth.db"


@dataclass(frozen=True)
class SqliteDatabaseProbe:
    ready: bool
    exists: bool
    is_file: bool
    error_code: str | None = None


def sqlite_path_from_url(database_url: str = DEFAULT_DB_URL) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(
            "Only sqlite URLs are supported by the local smoke-test bootstrap: "
            f"{database_url!r}"
        )
    raw_path = database_url[len(prefix) :]
    if raw_path.startswith("/"):
        return Path(raw_path)
    return Path.cwd() / raw_path


def open_sqlite_connection(database_url: str = DEFAULT_DB_URL) -> sqlite3.Connection:
    db_path = sqlite_path_from_url(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def open_read_only_sqlite_connection(
    database_url: str = DEFAULT_DB_URL,
) -> sqlite3.Connection:
    db_path = sqlite_path_from_url(database_url).resolve()
    if not db_path.exists():
        raise FileNotFoundError(str(db_path))
    if not db_path.is_file():
        raise NotADirectoryError(str(db_path))
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def probe_sqlite_database(
    database_url: str = DEFAULT_DB_URL,
) -> SqliteDatabaseProbe:
    db_path = sqlite_path_from_url(database_url).resolve()
    if not db_path.exists():
        return SqliteDatabaseProbe(
            ready=False,
            exists=False,
            is_file=False,
            error_code="missing_db_file",
        )
    if not db_path.is_file():
        return SqliteDatabaseProbe(
            ready=False,
            exists=True,
            is_file=False,
            error_code="db_path_not_file",
        )

    try:
        connection = open_read_only_sqlite_connection(database_url)
    except sqlite3.Error:
        return SqliteDatabaseProbe(
            ready=False,
            exists=True,
            is_file=True,
            error_code="db_open_failed",
        )

    try:
        connection.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        return SqliteDatabaseProbe(
            ready=False,
            exists=True,
            is_file=True,
            error_code="db_query_failed",
        )
    finally:
        connection.close()

    return SqliteDatabaseProbe(
        ready=True,
        exists=True,
        is_file=True,
        error_code=None,
    )
