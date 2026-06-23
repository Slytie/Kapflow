from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project
from onetruth.infrastructure.repositories.capex_source_roots import (
    create_folder_tree_snapshot,
    create_source_root_binding,
    create_source_root_sync_run,
    get_source_root_binding,
    transition_source_root_sync_run_status,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-source-root"
OTHER_PROJECT_ID = "cp-other"
NOW = "2026-06-17T00:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    create_capex_project(
        connection,
        project_id=PROJECT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key="CAPEX-SOURCE-ROOT",
        name="Source root project",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    create_capex_project(
        connection,
        project_id=OTHER_PROJECT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key="CAPEX-OTHER",
        name="Other project",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def _create_binding(connection: sqlite3.Connection, source_root_id: str = "sr-001") -> None:
    create_source_root_binding(
        connection,
        source_root_id=source_root_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        observer_mode="browser_folder_selection",
        display_label="PM selected folder",
        redacted_path_hint="~/Client/...",
        permission_basis="operator_selected_folder",
        sync_health="healthy",
        status="active",
        root_marker="opaque-root-marker",
        metadata_json={"activation": "planning_only"},
        owner_actor_id="human:pm",
        owner_actor_type="human",
        created_by_actor_id="human:pm",
        created_by_actor_type="human",
        created_at=NOW,
    )


def _create_sync_run(connection: sqlite3.Connection, sync_run_id: str = "sync-001") -> None:
    create_source_root_sync_run(
        connection,
        sync_run_id=sync_run_id,
        source_root_id="sr-001",
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        observer_mode="browser_folder_selection",
        observation_basis="browser_folder_manifest_v1",
        status="pending",
        metadata_json={"phase": "manifest"},
        started_by_actor_id="human:pm",
        started_by_actor_type="human",
        created_at=NOW,
    )


def test_create_source_root_binding_records_project_scope_and_redacted_hint() -> None:
    connection = _connection()
    try:
        _create_binding(connection)

        binding = get_source_root_binding(connection, "sr-001")

        assert binding is not None
        assert binding["project_id"] == PROJECT_ID
        assert binding["observer_mode"] == "browser_folder_selection"
        assert binding["redacted_path_hint"] == "~/Client/..."
        assert binding["latest_snapshot_id"] is None
        assert binding["metadata_json"] == {"activation": "planning_only"}
    finally:
        connection.close()


def test_source_root_binding_rejects_invalid_values_and_raw_absolute_paths() -> None:
    connection = _connection()
    try:
        with pytest.raises(ValueError, match="invalid observer mode"):
            create_source_root_binding(
                connection,
                source_root_id="sr-invalid-mode",
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                observer_mode="background_desktop_sync",
                display_label=None,
                redacted_path_hint="~/Client/...",
                permission_basis="operator_selected_folder",
                sync_health="healthy",
                status="active",
                root_marker=None,
                metadata_json={},
                owner_actor_id="human:pm",
                owner_actor_type="human",
                created_by_actor_id="human:pm",
                created_by_actor_type="human",
                created_at=NOW,
            )
        with pytest.raises(ValueError, match="raw absolute path"):
            create_source_root_binding(
                connection,
                source_root_id="sr-raw-path",
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                observer_mode="browser_folder_selection",
                display_label=None,
                redacted_path_hint="/Users/pm/Client/Raw Folder",
                permission_basis="operator_selected_folder",
                sync_health="healthy",
                status="active",
                root_marker=None,
                metadata_json={},
                owner_actor_id="human:pm",
                owner_actor_type="human",
                created_by_actor_id="human:pm",
                created_by_actor_type="human",
                created_at=NOW,
            )
    finally:
        connection.close()


def test_sync_run_lifecycle_allows_valid_transition_and_blocks_terminal_advance() -> None:
    connection = _connection()
    try:
        _create_binding(connection)
        _create_sync_run(connection)

        received = transition_source_root_sync_run_status(
            connection,
            sync_run_id="sync-001",
            status="manifest_received",
            updated_at="2026-06-17T00:01:00Z",
        )
        finalized = transition_source_root_sync_run_status(
            connection,
            sync_run_id="sync-001",
            status="finalized",
            updated_at="2026-06-17T00:02:00Z",
        )

        assert received["status"] == "manifest_received"
        assert finalized["status"] == "finalized"
        assert finalized["finalized_at"] == "2026-06-17T00:02:00Z"
        with pytest.raises(ValueError, match="terminal sync run status"):
            transition_source_root_sync_run_status(
                connection,
                sync_run_id="sync-001",
                status="uploading",
                updated_at="2026-06-17T00:03:00Z",
            )
    finally:
        connection.close()


def test_folder_snapshot_enforces_scope_and_updates_latest_only_when_requested() -> None:
    connection = _connection()
    try:
        _create_binding(connection)
        _create_sync_run(connection)

        with pytest.raises(ValueError, match="source root scope mismatch"):
            create_folder_tree_snapshot(
                connection,
                folder_tree_snapshot_id="snap-wrong-project",
                source_root_id="sr-001",
                sync_run_id="sync-001",
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=OTHER_PROJECT_ID,
                observation_basis="browser_folder_manifest_v1",
                path_scope="full",
                status="complete",
                manifest_digest="sha256:manifest",
                file_count=2,
                metadata_json={},
                created_by_actor_id="human:pm",
                created_by_actor_type="human",
                observed_at="2026-06-17T00:04:00Z",
                created_at="2026-06-17T00:04:01Z",
            )

        create_folder_tree_snapshot(
            connection,
            folder_tree_snapshot_id="snap-001",
            source_root_id="sr-001",
            sync_run_id="sync-001",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            observation_basis="browser_folder_manifest_v1",
            path_scope="full",
            status="complete",
            manifest_digest="sha256:manifest-1",
            file_count=2,
            metadata_json={"creates_reviewed_truth": False},
            created_by_actor_id="human:pm",
            created_by_actor_type="human",
            observed_at="2026-06-17T00:04:00Z",
            created_at="2026-06-17T00:04:01Z",
        )
        assert get_source_root_binding(connection, "sr-001")["latest_snapshot_id"] is None

        create_folder_tree_snapshot(
            connection,
            folder_tree_snapshot_id="snap-002",
            source_root_id="sr-001",
            sync_run_id="sync-001",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            observation_basis="browser_folder_manifest_v1",
            path_scope="full",
            status="complete",
            manifest_digest="sha256:manifest-2",
            file_count=3,
            metadata_json={"creates_reviewed_truth": False},
            created_by_actor_id="human:pm",
            created_by_actor_type="human",
            observed_at="2026-06-17T00:05:00Z",
            created_at="2026-06-17T00:05:01Z",
            record_as_latest=True,
        )

        binding = get_source_root_binding(connection, "sr-001")
        assert binding["latest_snapshot_id"] == "snap-002"
        assert binding["last_observed_at"] == "2026-06-17T00:05:00Z"
        assert {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name IN ('reviewed_corpus_baselines', 'official_evidence_bindings')
                """
            ).fetchall()
        } == set()
    finally:
        connection.close()
