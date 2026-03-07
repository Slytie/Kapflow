from __future__ import annotations

import sqlite3

import pytest

from onetruth.domain.pointer_address import PartitionRef, PointerAddress, PointerId
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_pointers import promote_pointer
from onetruth.infrastructure.repositories.input_bindings import (
    InputBindingConflictError,
    capture_task_pointer_input,
    create_workflow_run_artifact_input,
    is_task_input_binding_stale,
)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _seed_workflow_and_task(connection: sqlite3.Connection) -> None:
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
            "wr-001",
            "schedule_planning.v1",
            "v1",
            "tenant-a",
            "domain-ops",
            "SD-2026-03-04",
            "2026-03-04",
            "seed-activation",
            "ACTIVE",
            "2026-03-07T10:00:00Z",
            "2026-03-07T10:00:00Z",
        ),
    )
    connection.execute(
        """
        INSERT INTO task_runs (
            task_run_id,
            workflow_run_id,
            stage_id,
            task_kind,
            state,
            generation,
            activation_key,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "tr-001",
            "wr-001",
            "Stage06",
            "review_packet",
            "ACTIVE",
            0,
            "task-seed-activation",
            "2026-03-07T10:00:00Z",
            "2026-03-07T10:00:00Z",
        ),
    )


def _seed_artifact(connection: sqlite3.Connection, artifact_version_id: str) -> None:
    connection.execute(
        """
        INSERT INTO artifact_versions (
            artifact_version_id,
            workflow_run_id,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            "wr-001",
            "tr-001",
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


def _pointer_identity(pointer_key: str) -> dict[str, str]:
    pointer_id = str(
        PointerId.from_address(
            PointerAddress(
                tenant_id="tenant-a",
                domain_id="domain-ops",
                dataset_key="schedule.published_schedule.workbook",
                partition_ref=PartitionRef(key="ScheduleDateID", value="SD-2026-03-04"),
            )
        )
    )
    return {
        "pointer_key": pointer_key,
        "pointer_id": pointer_id,
        "tenant_id": "tenant-a",
        "domain_id": "domain-ops",
        "dataset_key": "schedule.published_schedule.workbook",
        "partition_kind": "ScheduleDateID",
        "partition_key": "SD-2026-03-04",
        "registry_kind": "singleton",
    }


def test_workflow_run_inputs_are_immutable_per_binding_key() -> None:
    connection = _connection()
    try:
        _seed_workflow_and_task(connection)
        _seed_artifact(connection, "av-001")
        _seed_artifact(connection, "av-002")

        create_workflow_run_artifact_input(
            connection,
            workflow_run_id="wr-001",
            binding_key="schedule_base",
            artifact_version_id="av-001",
            captured_by_task_run_id="tr-001",
            captured_at="2026-03-07T10:05:00Z",
        )

        with pytest.raises(InputBindingConflictError):
            create_workflow_run_artifact_input(
                connection,
                workflow_run_id="wr-001",
                binding_key="schedule_base",
                artifact_version_id="av-002",
                captured_by_task_run_id="tr-001",
                captured_at="2026-03-07T10:06:00Z",
            )
    finally:
        connection.close()


def test_task_binding_captures_pointer_generation_and_detects_stale_baseline() -> None:
    connection = _connection()
    try:
        _seed_workflow_and_task(connection)
        _seed_artifact(connection, "av-001")
        _seed_artifact(connection, "av-002")

        pointer_key = "official:schedule.published_schedule.workbook"
        pointer_identity = _pointer_identity(pointer_key)
        promote_pointer(
            connection,
            workflow_run_id="wr-001",
            pointer_key=pointer_identity["pointer_key"],
            scope_kind="stage",
            scope_ref="Stage06",
            artifact_kind="schedule.published_schedule.workbook",
            artifact_version_id="av-001",
            promotion_reason="official_publish",
            promoted_by_task_run_id="tr-001",
            approved_by_approval_id=None,
            updated_at="2026-03-07T10:10:00Z",
            expected_generation=None,
            pointer_id=pointer_identity["pointer_id"],
            tenant_id=pointer_identity["tenant_id"],
            domain_id=pointer_identity["domain_id"],
            dataset_key=pointer_identity["dataset_key"],
            partition_kind=pointer_identity["partition_kind"],
            partition_key=pointer_identity["partition_key"],
            stream_key=None,
            registry_kind=pointer_identity["registry_kind"],
        )

        capture_task_pointer_input(
            connection,
            task_run_id="tr-001",
            workflow_run_id="wr-001",
            binding_key="reviewed_base_pointer",
            pointer_key=pointer_key,
            captured_at="2026-03-07T10:11:00Z",
        )
        assert not is_task_input_binding_stale(
            connection,
            task_run_id="tr-001",
            binding_key="reviewed_base_pointer",
        )

        promote_pointer(
            connection,
            workflow_run_id="wr-001",
            pointer_key=pointer_identity["pointer_key"],
            scope_kind="stage",
            scope_ref="Stage06",
            artifact_kind="schedule.published_schedule.workbook",
            artifact_version_id="av-002",
            promotion_reason="official_publish",
            promoted_by_task_run_id="tr-001",
            approved_by_approval_id=None,
            updated_at="2026-03-07T10:12:00Z",
            expected_generation=0,
            pointer_id=pointer_identity["pointer_id"],
            tenant_id=pointer_identity["tenant_id"],
            domain_id=pointer_identity["domain_id"],
            dataset_key=pointer_identity["dataset_key"],
            partition_kind=pointer_identity["partition_kind"],
            partition_key=pointer_identity["partition_key"],
            stream_key=None,
            registry_kind=pointer_identity["registry_kind"],
        )
        assert is_task_input_binding_stale(
            connection,
            task_run_id="tr-001",
            binding_key="reviewed_base_pointer",
        )
    finally:
        connection.close()
