from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any


PROJECTION_SNAPSHOT_STATES = ("current", "stale", "superseded")

SNAPSHOT_COLUMNS = """
    projection_snapshot_id,
    tenant_id,
    domain_id,
    project_id,
    workpage_kind,
    projection_kind,
    renderer_version,
    basis_version_vector_json,
    basis_hash,
    state,
    payload_metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    stale_reason,
    stale_at,
    superseded_at,
    created_at,
    updated_at
"""

ROW_COLUMNS = """
    projection_row_id,
    projection_snapshot_id,
    row_key,
    row_order,
    subject_kind,
    subject_ref,
    row_payload_json,
    created_at
"""


def projection_basis_hash(basis_version_vector_json: dict[str, Any]) -> str:
    canonical = json.dumps(
        basis_version_vector_json,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_projection_snapshot(
    connection: sqlite3.Connection,
    *,
    projection_snapshot_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    workpage_kind: str,
    projection_kind: str,
    renderer_version: str,
    basis_version_vector_json: dict[str, Any],
    state: str,
    payload_metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
) -> dict[str, Any]:
    if state not in PROJECTION_SNAPSHOT_STATES:
        raise ValueError(f"invalid projection snapshot state: {state}")
    basis_hash = projection_basis_hash(basis_version_vector_json)
    connection.execute(
        """
        INSERT INTO capex_workpage_projection_snapshots (
            projection_snapshot_id,
            tenant_id,
            domain_id,
            project_id,
            workpage_kind,
            projection_kind,
            renderer_version,
            basis_version_vector_json,
            basis_hash,
            state,
            payload_metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            projection_snapshot_id,
            tenant_id,
            domain_id,
            project_id,
            workpage_kind,
            projection_kind,
            renderer_version,
            json.dumps(basis_version_vector_json, separators=(",", ":"), sort_keys=True),
            basis_hash,
            state,
            json.dumps(payload_metadata_json, separators=(",", ":"), sort_keys=True),
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            created_at,
        ),
    )
    snapshot = get_projection_snapshot(connection, projection_snapshot_id)
    if snapshot is None:
        raise RuntimeError("projection snapshot create failed")
    return snapshot


def create_projection_row(
    connection: sqlite3.Connection,
    *,
    projection_row_id: str,
    projection_snapshot_id: str,
    row_key: str,
    row_order: int,
    subject_kind: str,
    subject_ref: str,
    row_payload_json: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    connection.execute(
        """
        INSERT INTO capex_workpage_projection_rows (
            projection_row_id,
            projection_snapshot_id,
            row_key,
            row_order,
            subject_kind,
            subject_ref,
            row_payload_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            projection_row_id,
            projection_snapshot_id,
            row_key,
            row_order,
            subject_kind,
            subject_ref,
            json.dumps(row_payload_json, separators=(",", ":"), sort_keys=True),
            created_at,
        ),
    )
    row = get_projection_row(connection, projection_row_id)
    if row is None:
        raise RuntimeError("projection row create failed")
    return row


def get_projection_snapshot(
    connection: sqlite3.Connection,
    projection_snapshot_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SNAPSHOT_COLUMNS}
        FROM capex_workpage_projection_snapshots
        WHERE projection_snapshot_id = ?
        """,
        (projection_snapshot_id,),
    ).fetchone()
    return _snapshot_row(row)


def get_projection_row(
    connection: sqlite3.Connection,
    projection_row_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {ROW_COLUMNS}
        FROM capex_workpage_projection_rows
        WHERE projection_row_id = ?
        """,
        (projection_row_id,),
    ).fetchone()
    return _projection_row(row)


def list_projection_rows(
    connection: sqlite3.Connection,
    projection_snapshot_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {ROW_COLUMNS}
        FROM capex_workpage_projection_rows
        WHERE projection_snapshot_id = ?
        ORDER BY row_order ASC, row_key ASC
        """,
        (projection_snapshot_id,),
    ).fetchall()
    return [_projection_row(row) for row in rows if row is not None]


def mark_projection_snapshot_stale(
    connection: sqlite3.Connection,
    *,
    projection_snapshot_id: str,
    stale_reason: str,
    stale_at: str,
) -> None:
    connection.execute(
        """
        UPDATE capex_workpage_projection_snapshots
        SET state = 'stale',
            stale_reason = ?,
            stale_at = ?,
            updated_at = ?
        WHERE projection_snapshot_id = ?
          AND state = 'current'
        """,
        (stale_reason, stale_at, stale_at, projection_snapshot_id),
    )


def mark_projection_snapshot_superseded(
    connection: sqlite3.Connection,
    *,
    projection_snapshot_id: str,
    superseded_at: str,
) -> None:
    connection.execute(
        """
        UPDATE capex_workpage_projection_snapshots
        SET state = 'superseded',
            superseded_at = ?,
            updated_at = ?
        WHERE projection_snapshot_id = ?
          AND state = 'current'
        """,
        (superseded_at, superseded_at, projection_snapshot_id),
    )


def _snapshot_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["basis_version_vector_json"] = json.loads(str(item["basis_version_vector_json"]))
    item["payload_metadata_json"] = json.loads(str(item["payload_metadata_json"]))
    return item


def _projection_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["row_payload_json"] = json.loads(str(item["row_payload_json"]))
    return item
