from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import (
    create_artifact_version_command,
    create_workflow_run_command,
    promote_pointer_command,
)
from onetruth.domain.pointer_address import PointerId
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _create_workflow_run(connection: sqlite3.Connection, *, run_suffix: str) -> dict[str, Any]:
    return create_workflow_run_command(
        connection,
        {
            "workflow_run_id": f"wr-{run_suffix}",
            "workflow_id": "schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": "tenant-a",
            "domain_id": "domain-ops",
            "partition_key": "SD-2026-03-04",
            "logical_date": "2026-03-04",
            "activation_key": f"activation-{run_suffix}",
            "idempotency_key": f"idem-run-{run_suffix}",
        },
    )


def _create_artifact(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    artifact_kind: str,
    suffix: str,
) -> dict[str, Any]:
    return create_artifact_version_command(
        connection,
        {
            "artifact_version_id": f"av-{suffix}",
            "workflow_run_id": workflow_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": "official_output",
            "media_type": "application/json",
            "storage_uri": f"s3://runtime/{suffix}.json",
            "content_digest": f"sha256:{suffix}",
            "byte_size": 128,
            "metadata_json": {"seed": suffix},
            "idempotency_key": f"idem-artifact-{suffix}",
        },
    )


def test_pointer_dual_write_keeps_legacy_and_canonical_identity_aligned() -> None:
    connection = _connection()
    try:
        cases = [
            {
                "suffix": "stage-shape",
                "scope_kind": "stage",
                "scope_ref": "Stage06",
                "pointer_key": "official:schedule.published_schedule.workbook",
                "artifact_kind": "schedule.published_schedule.workbook",
            },
            {
                "suffix": "workflow-partition-shape",
                "scope_kind": "workflow_partition",
                "scope_ref": "SD-2026-03-04",
                "pointer_key": "schedule.replan_delta.workbook:official:SD-2026-03-04",
                "artifact_kind": "schedule.replan_delta.workbook",
            },
        ]

        for case in cases:
            workflow_run = _create_workflow_run(connection, run_suffix=str(case["suffix"]))
            artifact = _create_artifact(
                connection,
                workflow_run_id=str(workflow_run["workflow_run_id"]),
                artifact_kind=str(case["artifact_kind"]),
                suffix=str(case["suffix"]),
            )

            promote_pointer_command(
                connection,
                {
                    "workflow_run_id": str(workflow_run["workflow_run_id"]),
                    "scope_kind": str(case["scope_kind"]),
                    "scope_ref": str(case["scope_ref"]),
                    "pointer_key": str(case["pointer_key"]),
                    "artifact_kind": str(case["artifact_kind"]),
                    "artifact_version_id": str(artifact["artifact_version_id"]),
                    "promotion_reason": "manual_promote",
                    "idempotency_key": f"idem-pointer-{case['suffix']}",
                },
            )

            row = connection.execute(
                """
                SELECT
                    workflow_run_id,
                    pointer_key,
                    pointer_id,
                    tenant_id,
                    domain_id,
                    dataset_key,
                    partition_kind,
                    partition_key,
                    artifact_version_id,
                    generation
                FROM artifact_pointers
                WHERE workflow_run_id = ? AND pointer_key = ?
                """,
                (
                    str(workflow_run["workflow_run_id"]),
                    str(case["pointer_key"]),
                ),
            ).fetchone()
            assert row is not None

            pointer_id = str(row["pointer_id"])
            assert pointer_id
            canonical = PointerId.parse(pointer_id).to_address()
            assert canonical.tenant_id == str(row["tenant_id"])
            assert canonical.domain_id == str(row["domain_id"])
            assert canonical.dataset_key == str(row["dataset_key"])
            assert canonical.partition_ref.key == str(row["partition_kind"])
            assert canonical.partition_ref.value == str(row["partition_key"])

            by_pointer_id = connection.execute(
                """
                SELECT workflow_run_id, pointer_key, artifact_version_id, generation
                FROM artifact_pointers
                WHERE pointer_id = ?
                """,
                (pointer_id,),
            ).fetchone()
            assert by_pointer_id is not None
            assert str(by_pointer_id["workflow_run_id"]) == str(row["workflow_run_id"])
            assert str(by_pointer_id["pointer_key"]) == str(row["pointer_key"])
            assert str(by_pointer_id["artifact_version_id"]) == str(row["artifact_version_id"])
            assert int(by_pointer_id["generation"]) == int(row["generation"])
    finally:
        connection.close()
