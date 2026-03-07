from __future__ import annotations

from itertools import permutations
import sqlite3

from onetruth.application.handlers.workflow_task_lifecycle import (
    create_artifact_version_command,
    create_workflow_run_command,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_provenance import (
    project_legacy_lineage_fields,
    project_legacy_lineage_from_edge_rows,
)


def test_projection_is_deterministic_for_edge_row_order() -> None:
    edge_rows = [
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-parent-b",
            "edge_type": "derives_from",
            "edge_order": 2,
        },
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-parent-a",
            "edge_type": "derives_from",
            "edge_order": 1,
        },
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-superseded-a",
            "edge_type": "supersedes",
            "edge_order": 1,
        },
        {
            "output_artifact_version_id": "av-out",
            "input_artifact_version_id": "av-reviewed",
            "edge_type": "reviewed_against",
            "edge_order": 1,
        },
    ]

    expected = {
        "parent_artifact_version_id": "av-parent-a",
        "supersedes_artifact_version_id": "av-superseded-a",
    }
    for permutation in permutations(edge_rows):
        assert project_legacy_lineage_from_edge_rows(list(permutation)) == expected


def test_authoritative_create_version_dual_writes_provenance_compatibility_projection() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    try:
        workflow_run = create_workflow_run_command(
            connection,
            {
                "workflow_run_id": "wr-provenance-001",
                "workflow_id": "schedule_planning.v1",
                "workflow_version": "v1",
                "tenant_id": "tenant-a",
                "domain_id": "domain-ops",
                "partition_key": "SD-2026-03-04",
                "logical_date": "2026-03-04",
                "activation_key": "activation-provenance-001",
                "idempotency_key": "idem-run-provenance-001",
            },
        )
        base = create_artifact_version_command(
            connection,
            {
                "artifact_version_id": "av-provenance-base",
                "workflow_run_id": str(workflow_run["workflow_run_id"]),
                "artifact_kind": "schedule.published_schedule.workbook",
                "artifact_role": "official_output",
                "media_type": "application/json",
                "storage_uri": "s3://runtime/av-provenance-base.json",
                "content_digest": "sha256:av-provenance-base",
                "byte_size": 64,
                "metadata_json": {"seed": "base"},
                "idempotency_key": "idem-artifact-provenance-base",
            },
        )
        derived = create_artifact_version_command(
            connection,
            {
                "artifact_version_id": "av-provenance-derived",
                "workflow_run_id": str(workflow_run["workflow_run_id"]),
                "artifact_kind": "schedule.replan_delta.workbook",
                "artifact_role": "official_output",
                "media_type": "application/json",
                "storage_uri": "s3://runtime/av-provenance-derived.json",
                "content_digest": "sha256:av-provenance-derived",
                "byte_size": 64,
                "metadata_json": {"seed": "derived"},
                "parent_artifact_version_id": str(base["artifact_version_id"]),
                "supersedes_artifact_version_id": str(base["artifact_version_id"]),
                "idempotency_key": "idem-artifact-provenance-derived",
            },
        )

        projection = project_legacy_lineage_fields(connection, str(derived["artifact_version_id"]))
        assert projection == {
            "parent_artifact_version_id": str(base["artifact_version_id"]),
            "supersedes_artifact_version_id": str(base["artifact_version_id"]),
        }

        version_row = connection.execute(
            """
            SELECT parent_artifact_version_id, supersedes_artifact_version_id
            FROM artifact_versions
            WHERE artifact_version_id = ?
            """,
            (str(derived["artifact_version_id"]),),
        ).fetchone()
        assert version_row is not None
        assert str(version_row["parent_artifact_version_id"]) == projection["parent_artifact_version_id"]
        assert str(version_row["supersedes_artifact_version_id"]) == projection["supersedes_artifact_version_id"]
    finally:
        connection.close()
