from __future__ import annotations

import json
import re
import sqlite3
from typing import Any


SOURCE_ROOT_OBSERVER_MODES = (
    "browser_folder_selection",
    "zip_import",
    "user_selected_folder_upload",
    "browser_manual_resync",
    "desktop_agent_manual_scan",
    "desktop_agent_watch",
    "cloud_connector",
    "server_mounted_folder",
    "archived_source",
)
SOURCE_ROOT_STATUSES = (
    "active",
    "needs_manual_resync",
    "permission_lost",
    "root_missing",
    "watcher_degraded",
    "archived",
)
SOURCE_ROOT_SYNC_HEALTH = (
    "unknown",
    "healthy",
    "needs_manual_resync",
    "permission_lost",
    "root_missing",
    "watcher_degraded",
    "degraded",
)
SYNC_RUN_STATUSES = (
    "pending",
    "manifest_received",
    "uploading",
    "finalized",
    "failed",
    "aborted",
)
TERMINAL_SYNC_RUN_STATUSES = frozenset({"finalized", "failed", "aborted"})
FOLDER_TREE_SNAPSHOT_STATUSES = ("complete", "partial", "failed", "degraded")

SOURCE_ROOT_COLUMNS = """
    source_root_id,
    tenant_id,
    domain_id,
    project_id,
    observer_mode,
    display_label,
    redacted_path_hint,
    permission_basis,
    sync_health,
    status,
    root_marker,
    latest_snapshot_id,
    metadata_json,
    owner_actor_id,
    owner_actor_type,
    created_by_actor_id,
    created_by_actor_type,
    last_observed_at,
    created_at,
    updated_at
"""

SYNC_RUN_COLUMNS = """
    sync_run_id,
    source_root_id,
    tenant_id,
    domain_id,
    project_id,
    observer_mode,
    observation_basis,
    status,
    failure_reason,
    metadata_json,
    started_by_actor_id,
    started_by_actor_type,
    finalized_at,
    created_at,
    updated_at
"""

FOLDER_TREE_SNAPSHOT_COLUMNS = """
    folder_tree_snapshot_id,
    source_root_id,
    sync_run_id,
    tenant_id,
    domain_id,
    project_id,
    observation_basis,
    path_scope,
    status,
    manifest_digest,
    file_count,
    metadata_json,
    created_by_actor_id,
    created_by_actor_type,
    observed_at,
    created_at
"""


def create_source_root_binding(
    connection: sqlite3.Connection,
    *,
    source_root_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    observer_mode: str,
    display_label: str | None,
    redacted_path_hint: str | None,
    permission_basis: str,
    sync_health: str,
    status: str,
    root_marker: str | None,
    metadata_json: dict[str, Any],
    owner_actor_id: str,
    owner_actor_type: str,
    created_by_actor_id: str,
    created_by_actor_type: str,
    created_at: str,
    last_observed_at: str | None = None,
) -> dict[str, Any]:
    _validate_member("observer mode", observer_mode, SOURCE_ROOT_OBSERVER_MODES)
    _validate_member("source root status", status, SOURCE_ROOT_STATUSES)
    _validate_member("source root sync health", sync_health, SOURCE_ROOT_SYNC_HEALTH)
    _validate_redacted_path_hint(redacted_path_hint)
    _assert_project_scope(
        connection,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    connection.execute(
        """
        INSERT INTO capex_source_root_bindings (
            source_root_id,
            tenant_id,
            domain_id,
            project_id,
            observer_mode,
            display_label,
            redacted_path_hint,
            permission_basis,
            sync_health,
            status,
            root_marker,
            latest_snapshot_id,
            metadata_json,
            owner_actor_id,
            owner_actor_type,
            created_by_actor_id,
            created_by_actor_type,
            last_observed_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_root_id,
            tenant_id,
            domain_id,
            project_id,
            observer_mode,
            display_label,
            redacted_path_hint,
            permission_basis,
            sync_health,
            status,
            root_marker,
            None,
            _dump_json(metadata_json),
            owner_actor_id,
            owner_actor_type,
            created_by_actor_id,
            created_by_actor_type,
            last_observed_at,
            created_at,
            created_at,
        ),
    )
    binding = get_source_root_binding(connection, source_root_id)
    if binding is None:
        raise RuntimeError("source root binding create failed")
    return binding


def get_source_root_binding(
    connection: sqlite3.Connection,
    source_root_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SOURCE_ROOT_COLUMNS}
        FROM capex_source_root_bindings
        WHERE source_root_id = ?
        """,
        (source_root_id,),
    ).fetchone()
    return _source_root_row(row)


def list_source_root_bindings_for_project(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        f"""
        SELECT {SOURCE_ROOT_COLUMNS}
        FROM capex_source_root_bindings
        WHERE tenant_id = ?
          AND domain_id = ?
          AND project_id = ?
        ORDER BY created_at ASC, source_root_id ASC
        """,
        (tenant_id, domain_id, project_id),
    ).fetchall()
    return [_source_root_row(row) for row in rows if row is not None]


def create_source_root_sync_run(
    connection: sqlite3.Connection,
    *,
    sync_run_id: str,
    source_root_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    observer_mode: str,
    observation_basis: str,
    status: str,
    metadata_json: dict[str, Any],
    started_by_actor_id: str,
    started_by_actor_type: str,
    created_at: str,
    failure_reason: str | None = None,
    finalized_at: str | None = None,
) -> dict[str, Any]:
    _validate_member("observer mode", observer_mode, SOURCE_ROOT_OBSERVER_MODES)
    _validate_member("sync run status", status, SYNC_RUN_STATUSES)
    if status not in TERMINAL_SYNC_RUN_STATUSES and finalized_at is not None:
        raise ValueError("non-terminal sync run cannot have finalized_at")
    binding = _assert_source_root_scope(
        connection,
        source_root_id=source_root_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    if str(binding["observer_mode"]) != observer_mode:
        raise ValueError("sync run observer mode does not match source root")
    connection.execute(
        """
        INSERT INTO capex_source_root_sync_runs (
            sync_run_id,
            source_root_id,
            tenant_id,
            domain_id,
            project_id,
            observer_mode,
            observation_basis,
            status,
            failure_reason,
            metadata_json,
            started_by_actor_id,
            started_by_actor_type,
            finalized_at,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sync_run_id,
            source_root_id,
            tenant_id,
            domain_id,
            project_id,
            observer_mode,
            observation_basis,
            status,
            failure_reason,
            _dump_json(metadata_json),
            started_by_actor_id,
            started_by_actor_type,
            finalized_at,
            created_at,
            created_at,
        ),
    )
    sync_run = get_source_root_sync_run(connection, sync_run_id)
    if sync_run is None:
        raise RuntimeError("source root sync run create failed")
    return sync_run


def get_source_root_sync_run(
    connection: sqlite3.Connection,
    sync_run_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {SYNC_RUN_COLUMNS}
        FROM capex_source_root_sync_runs
        WHERE sync_run_id = ?
        """,
        (sync_run_id,),
    ).fetchone()
    return _sync_run_row(row)


def transition_source_root_sync_run_status(
    connection: sqlite3.Connection,
    *,
    sync_run_id: str,
    status: str,
    updated_at: str,
    failure_reason: str | None = None,
    finalized_at: str | None = None,
) -> dict[str, Any]:
    _validate_member("sync run status", status, SYNC_RUN_STATUSES)
    existing = get_source_root_sync_run(connection, sync_run_id)
    if existing is None:
        raise ValueError(f"source root sync run not found: {sync_run_id}")
    if existing["status"] in TERMINAL_SYNC_RUN_STATUSES:
        raise ValueError("terminal sync run status cannot be advanced")
    resolved_finalized_at = (
        finalized_at or updated_at if status in TERMINAL_SYNC_RUN_STATUSES else None
    )
    connection.execute(
        """
        UPDATE capex_source_root_sync_runs
        SET status = ?,
            failure_reason = ?,
            finalized_at = ?,
            updated_at = ?
        WHERE sync_run_id = ?
        """,
        (
            status,
            failure_reason,
            resolved_finalized_at,
            updated_at,
            sync_run_id,
        ),
    )
    sync_run = get_source_root_sync_run(connection, sync_run_id)
    if sync_run is None:
        raise RuntimeError("source root sync run transition failed")
    return sync_run


def create_folder_tree_snapshot(
    connection: sqlite3.Connection,
    *,
    folder_tree_snapshot_id: str,
    source_root_id: str,
    sync_run_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
    observation_basis: str,
    path_scope: str,
    status: str,
    manifest_digest: str | None,
    file_count: int | None,
    metadata_json: dict[str, Any],
    created_by_actor_id: str,
    created_by_actor_type: str,
    observed_at: str,
    created_at: str,
    record_as_latest: bool = False,
) -> dict[str, Any]:
    _validate_member("folder tree snapshot status", status, FOLDER_TREE_SNAPSHOT_STATUSES)
    if file_count is not None and file_count < 0:
        raise ValueError("folder tree snapshot file_count cannot be negative")
    _assert_source_root_scope(
        connection,
        source_root_id=source_root_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    sync_run = _assert_sync_run_scope(
        connection,
        sync_run_id=sync_run_id,
        source_root_id=source_root_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        project_id=project_id,
    )
    if str(sync_run["observation_basis"]) != observation_basis:
        raise ValueError("snapshot observation basis does not match sync run")
    connection.execute(
        """
        INSERT INTO capex_folder_tree_snapshots (
            folder_tree_snapshot_id,
            source_root_id,
            sync_run_id,
            tenant_id,
            domain_id,
            project_id,
            observation_basis,
            path_scope,
            status,
            manifest_digest,
            file_count,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            observed_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            folder_tree_snapshot_id,
            source_root_id,
            sync_run_id,
            tenant_id,
            domain_id,
            project_id,
            observation_basis,
            path_scope,
            status,
            manifest_digest,
            file_count,
            _dump_json(metadata_json),
            created_by_actor_id,
            created_by_actor_type,
            observed_at,
            created_at,
        ),
    )
    if record_as_latest:
        connection.execute(
            """
            UPDATE capex_source_root_bindings
            SET latest_snapshot_id = ?,
                last_observed_at = ?,
                updated_at = ?
            WHERE source_root_id = ?
            """,
            (folder_tree_snapshot_id, observed_at, created_at, source_root_id),
        )
    snapshot = get_folder_tree_snapshot(connection, folder_tree_snapshot_id)
    if snapshot is None:
        raise RuntimeError("folder tree snapshot create failed")
    return snapshot


def get_folder_tree_snapshot(
    connection: sqlite3.Connection,
    folder_tree_snapshot_id: str,
) -> dict[str, Any] | None:
    row = connection.execute(
        f"""
        SELECT {FOLDER_TREE_SNAPSHOT_COLUMNS}
        FROM capex_folder_tree_snapshots
        WHERE folder_tree_snapshot_id = ?
        """,
        (folder_tree_snapshot_id,),
    ).fetchone()
    return _folder_tree_snapshot_row(row)


def _assert_project_scope(
    connection: sqlite3.Connection,
    *,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT tenant_id, domain_id
        FROM capex_projects
        WHERE project_id = ?
        """,
        (project_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"CAPEX project not found: {project_id}")
    if row["tenant_id"] != tenant_id or row["domain_id"] != domain_id:
        raise ValueError("CAPEX project scope mismatch")


def _assert_source_root_scope(
    connection: sqlite3.Connection,
    *,
    source_root_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> dict[str, Any]:
    binding = get_source_root_binding(connection, source_root_id)
    if binding is None:
        raise ValueError(f"source root binding not found: {source_root_id}")
    if (
        binding["tenant_id"] != tenant_id
        or binding["domain_id"] != domain_id
        or binding["project_id"] != project_id
    ):
        raise ValueError("source root scope mismatch")
    return binding


def _assert_sync_run_scope(
    connection: sqlite3.Connection,
    *,
    sync_run_id: str,
    source_root_id: str,
    tenant_id: str,
    domain_id: str,
    project_id: str,
) -> dict[str, Any]:
    sync_run = get_source_root_sync_run(connection, sync_run_id)
    if sync_run is None:
        raise ValueError(f"source root sync run not found: {sync_run_id}")
    if (
        sync_run["source_root_id"] != source_root_id
        or sync_run["tenant_id"] != tenant_id
        or sync_run["domain_id"] != domain_id
        or sync_run["project_id"] != project_id
    ):
        raise ValueError("source root sync run scope mismatch")
    return sync_run


def _validate_member(label: str, value: str, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        raise ValueError(f"invalid {label}: {value}")


def _validate_redacted_path_hint(value: str | None) -> None:
    if value is None:
        return
    stripped = value.strip()
    if (
        stripped.startswith("/")
        or stripped.startswith("\\\\")
        or re.match(r"^[A-Za-z]:[\\/]", stripped)
        or "/Users/" in stripped
        or "\\Users\\" in stripped
    ):
        raise ValueError("redacted_path_hint must not contain a raw absolute path")


def _dump_json(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _source_root_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _sync_run_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item


def _folder_tree_snapshot_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    item["metadata_json"] = json.loads(str(item["metadata_json"]))
    return item
