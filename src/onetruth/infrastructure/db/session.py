from __future__ import annotations

from pathlib import Path
import sqlite3

DEFAULT_DB_URL = "sqlite:///./onetruth.db"


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

