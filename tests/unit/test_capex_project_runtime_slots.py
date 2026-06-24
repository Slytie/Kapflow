from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_project_runtime_slots import (
    ProjectRuntimeSlotError,
    acquire_project_runtime_slot,
    ensure_project_concurrency_policy,
    get_active_project_runtime_slot,
    get_project_concurrency_policy,
    get_project_runtime_slot,
    release_project_runtime_slot,
)
from onetruth.infrastructure.repositories.capex_projects import create_capex_project


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-alpha"
NOW = "2026-06-23T00:00:00Z"
LATER = "2026-06-23T00:10:00Z"
EARLIER = "2026-06-22T23:59:00Z"


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
        project_key="CP-ALPHA",
        name="CAPEX Alpha",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def _acquire(
    connection: sqlite3.Connection,
    *,
    slot_id: str = "slot-ingest-001",
    lock_family: str = "ingest",
    slot_key: str = "ingest:batch-001",
    holder_ref: str = "ingest_job:job-001",
    lease_token: str = "lease:ingest:001",
    acquired_at: str = NOW,
    expires_at: str | None = None,
    metadata_json: dict[str, object] | None = None,
) -> dict[str, object]:
    return acquire_project_runtime_slot(
        connection,
        project_runtime_slot_id=slot_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        lock_family=lock_family,
        slot_key=slot_key,
        holder_ref=holder_ref,
        lease_token=lease_token,
        acquired_at=acquired_at,
        expires_at=expires_at,
        metadata_json=metadata_json,
    )


def test_acquire_ingest_slot_creates_default_policy_and_replays_matching_holder() -> None:
    connection = _connection()
    try:
        slot = _acquire(connection, metadata_json={"request_ref": "ingest:batch-001"})
        replay = _acquire(
            connection,
            slot_id="slot-ingest-replay",
            metadata_json={"request_ref": "ingest:batch-001"},
        )

        policy = get_project_concurrency_policy(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            lock_family="ingest",
        )
        assert policy is not None
        assert policy["max_active_slots"] == 1
        assert policy["state"] == "active"
        assert slot["project_runtime_slot_id"] == "slot-ingest-001"
        assert replay["project_runtime_slot_id"] == slot["project_runtime_slot_id"]
        assert replay["state"] == "active"
    finally:
        connection.close()


def test_conflicting_active_slot_and_stale_release_fail_closed() -> None:
    connection = _connection()
    try:
        slot = _acquire(
            connection,
            slot_id="slot-pointer-001",
            lock_family="pointer",
            slot_key="pointer:official:source-baseline",
            holder_ref="pointer_command:cmd-001",
            lease_token="lease:pointer:001",
        )

        with pytest.raises(ProjectRuntimeSlotError) as conflict:
            _acquire(
                connection,
                slot_id="slot-pointer-002",
                lock_family="pointer",
                slot_key="pointer:official:closure",
                holder_ref="pointer_command:cmd-002",
                lease_token="lease:pointer:002",
            )
        assert conflict.value.code == "project_runtime_slot_conflict"

        with pytest.raises(ProjectRuntimeSlotError) as stale_release:
            release_project_runtime_slot(
                connection,
                project_runtime_slot_id=str(slot["project_runtime_slot_id"]),
                lease_token="lease:pointer:stale",
                released_at=LATER,
            )
        assert stale_release.value.code == "project_runtime_slot_stale_release"

        released = release_project_runtime_slot(
            connection,
            project_runtime_slot_id=str(slot["project_runtime_slot_id"]),
            lease_token="lease:pointer:001",
            released_at=LATER,
        )
        assert released["state"] == "released"
        assert released["active_family_key"] is None
        assert (
            get_active_project_runtime_slot(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                lock_family="pointer",
            )
            is None
        )
    finally:
        connection.close()


def test_expired_slot_can_be_reclaimed_by_new_holder() -> None:
    connection = _connection()
    try:
        first = _acquire(
            connection,
            slot_id="slot-ingest-expired",
            slot_key="ingest:batch-expired",
            holder_ref="ingest_job:expired",
            lease_token="lease:ingest:expired",
            expires_at=EARLIER,
        )
        second = _acquire(
            connection,
            slot_id="slot-ingest-new",
            slot_key="ingest:batch-new",
            holder_ref="ingest_job:new",
            lease_token="lease:ingest:new",
            acquired_at=LATER,
        )

        expired = get_project_runtime_slot(connection, str(first["project_runtime_slot_id"]))
        assert expired is not None
        assert expired["state"] == "expired"
        assert expired["active_family_key"] is None
        assert second["state"] == "active"
        assert second["project_runtime_slot_id"] == "slot-ingest-new"
    finally:
        connection.close()


def test_ingest_and_pointer_lock_families_are_independent() -> None:
    connection = _connection()
    try:
        ingest = _acquire(connection)
        pointer = _acquire(
            connection,
            slot_id="slot-pointer-001",
            lock_family="pointer",
            slot_key="pointer:official:source-baseline",
            holder_ref="pointer_command:cmd-001",
            lease_token="lease:pointer:001",
        )

        assert ingest["state"] == "active"
        assert pointer["state"] == "active"
        assert ingest["active_family_key"] != pointer["active_family_key"]
    finally:
        connection.close()


def test_slot_validation_fails_closed_for_scope_family_keys_and_raw_material() -> None:
    connection = _connection()
    try:
        with pytest.raises(ProjectRuntimeSlotError) as scope:
            acquire_project_runtime_slot(
                connection,
                project_runtime_slot_id="slot-bad-scope",
                tenant_id="tenant-b",
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                lock_family="ingest",
                slot_key="ingest:batch-001",
                holder_ref="ingest_job:job-001",
                lease_token="lease:ingest:001",
                acquired_at=NOW,
                expires_at=None,
            )
        assert scope.value.code == "project_runtime_slot_scope_invalid"

        with pytest.raises(ProjectRuntimeSlotError) as family:
            _acquire(connection, lock_family="search", slot_key="search:index-001")
        assert family.value.code == "project_runtime_slot_family_unsupported"

        with pytest.raises(ProjectRuntimeSlotError) as slot_key:
            _acquire(connection, lock_family="ingest", slot_key="pointer:official")
        assert slot_key.value.code == "project_runtime_slot_key_invalid"

        with pytest.raises(ProjectRuntimeSlotError) as raw_material:
            _acquire(
                connection,
                metadata_json={"source_path": "/Users/tylerclark/raw/corpus.pdf"},
            )
        assert raw_material.value.code == "project_runtime_slot_raw_material"

        with pytest.raises(ProjectRuntimeSlotError) as policy:
            ensure_project_concurrency_policy(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                lock_family="ingest",
                created_at=NOW,
                max_active_slots=2,
            )
        assert policy.value.code == "project_runtime_slot_policy_invalid"
    finally:
        connection.close()
