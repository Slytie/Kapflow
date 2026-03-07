from __future__ import annotations

import sqlite3

from onetruth.domain.pointer_address import PartitionRef, PointerAddress, PointerId
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_pointers import (
    get_pointer,
    get_pointer_by_address,
    get_pointer_by_id,
    list_pointers_by_canonical_scope,
    list_pointers_for_workflow_run,
    promote_pointer,
)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _seed_workflow(connection: sqlite3.Connection, *, workflow_run_id: str, activation_key: str) -> None:
    connection.execute(
        """
        INSERT INTO workflow_runs (
            workflow_run_id,
            workflow_id,
            workflow_version,
            tenant_id,
            domain_id,
            partition_key,
            logical_date,
            activation_key,
            state,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workflow_run_id,
            "schedule_planning.v1",
            "v1",
            "tenant-a",
            "domain-ops",
            "SD-2026-03-04",
            "2026-03-04",
            activation_key,
            "OPEN",
            "2026-03-07T10:00:00Z",
            "2026-03-07T10:00:00Z",
        ),
    )


def _seed_artifact(connection: sqlite3.Connection, *, workflow_run_id: str, artifact_version_id: str) -> None:
    connection.execute(
        """
        INSERT INTO artifact_versions (
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            dataset_key,
            partition_kind,
            partition_key,
            task_run_id,
            artifact_kind,
            artifact_role,
            media_type,
            storage_uri,
            content_digest,
            byte_size,
            metadata_json,
            parent_artifact_version_id,
            supersedes_artifact_version_id,
            lineage_note,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            workflow_run_id,
            "tenant-a",
            "domain-ops",
            "schedule.published_schedule.workbook",
            "ScheduleDateID",
            "SD-2026-03-04",
            None,
            "schedule.published_schedule.workbook",
            "official_output",
            "application/json",
            f"s3://runtime/{artifact_version_id}.json",
            f"sha256:{artifact_version_id}",
            128,
            "{}",
            None,
            None,
            None,
            "2026-03-07T10:00:00Z",
        ),
    )


def test_repository_uses_canonical_pointer_identity_with_run_compatibility_adapters() -> None:
    connection = _connection()
    try:
        _seed_workflow(connection, workflow_run_id="wr-001", activation_key="seed-a")
        _seed_workflow(connection, workflow_run_id="wr-002", activation_key="seed-b")
        _seed_artifact(connection, workflow_run_id="wr-001", artifact_version_id="av-001")
        _seed_artifact(connection, workflow_run_id="wr-002", artifact_version_id="av-002")

        address = PointerAddress(
            tenant_id="tenant-a",
            domain_id="domain-ops",
            dataset_key="schedule.published_schedule.workbook",
            partition_ref=PartitionRef(key="ScheduleDateID", value="SD-2026-03-04"),
            stream_key=None,
        )
        pointer_id = str(PointerId.from_address(address))

        first, first_changed = promote_pointer(
            connection,
            workflow_run_id="wr-001",
            pointer_key="official:schedule.published_schedule.workbook",
            scope_kind="stage",
            scope_ref="Stage06",
            artifact_kind="schedule.published_schedule.workbook",
            artifact_version_id="av-001",
            promotion_reason="manual_promote",
            promoted_by_task_run_id=None,
            approved_by_approval_id=None,
            updated_at="2026-03-07T10:10:00Z",
            expected_generation=None,
            pointer_id=pointer_id,
            tenant_id="tenant-a",
            domain_id="domain-ops",
            dataset_key="schedule.published_schedule.workbook",
            partition_kind="ScheduleDateID",
            partition_key="SD-2026-03-04",
            stream_key=None,
            registry_kind="singleton",
        )
        assert first_changed is True
        assert first["pointer_id"] == pointer_id
        assert int(first["generation"]) == 0

        by_id = get_pointer_by_id(connection, pointer_id=pointer_id)
        assert by_id is not None
        assert by_id["artifact_version_id"] == "av-001"

        by_address = get_pointer_by_address(
            connection,
            tenant_id="tenant-a",
            domain_id="domain-ops",
            dataset_key="schedule.published_schedule.workbook",
            partition_kind="ScheduleDateID",
            partition_key="SD-2026-03-04",
            stream_key=None,
            registry_kind="singleton",
        )
        assert by_address is not None
        assert by_address["pointer_id"] == pointer_id

        listed_canonical = list_pointers_by_canonical_scope(
            connection,
            tenant_id="tenant-a",
            domain_id="domain-ops",
            dataset_key="schedule.published_schedule.workbook",
            partition_kind="ScheduleDateID",
            partition_key="SD-2026-03-04",
            stream_key=None,
            registry_kind="singleton",
        )
        assert len(listed_canonical) == 1
        assert listed_canonical[0]["pointer_id"] == pointer_id

        second, second_changed = promote_pointer(
            connection,
            workflow_run_id="wr-002",
            pointer_key="official:schedule.published_schedule.workbook",
            scope_kind="stage",
            scope_ref="Stage06",
            artifact_kind="schedule.published_schedule.workbook",
            artifact_version_id="av-002",
            promotion_reason="manual_promote",
            promoted_by_task_run_id=None,
            approved_by_approval_id=None,
            updated_at="2026-03-07T10:11:00Z",
            expected_generation=0,
            pointer_id=pointer_id,
            tenant_id="tenant-a",
            domain_id="domain-ops",
            dataset_key="schedule.published_schedule.workbook",
            partition_kind="ScheduleDateID",
            partition_key="SD-2026-03-04",
            stream_key=None,
            registry_kind="singleton",
        )
        assert second_changed is True
        assert second["pointer_id"] == pointer_id
        assert second["artifact_version_id"] == "av-002"
        assert int(second["generation"]) == 1

        compat = get_pointer(
            connection,
            workflow_run_id="wr-001",
            pointer_key="official:schedule.published_schedule.workbook",
        )
        assert compat is not None
        assert compat["pointer_id"] == pointer_id
        assert compat["artifact_version_id"] == "av-002"

        compat_list = list_pointers_for_workflow_run(connection, "wr-001")
        assert len(compat_list) == 1
        assert compat_list[0]["pointer_id"] == pointer_id
        assert compat_list[0]["artifact_version_id"] == "av-002"
    finally:
        connection.close()
