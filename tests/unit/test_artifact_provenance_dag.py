from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_provenance import (
    ProvenanceCycleError,
    ProvenanceProjectScopeError,
    create_artifact_provenance_edge,
    list_artifact_provenance_edges_for_output,
    project_legacy_lineage_fields,
)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _seed_project(connection: sqlite3.Connection, project_id: str) -> None:
    connection.execute(
        """
        INSERT INTO capex_projects (
            project_id,
            tenant_id,
            domain_id,
            project_key,
            name,
            state,
            metadata_json,
            created_by_actor_id,
            created_by_actor_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            "tenant-a",
            "domain-ops",
            project_id.upper(),
            project_id,
            "active",
            "{}",
            "human:admin",
            "human",
            "2026-03-07T10:00:00Z",
            "2026-03-07T10:00:00Z",
        ),
    )


def _seed_workflow(
    connection: sqlite3.Connection,
    workflow_run_id: str = "wr-001",
    *,
    project_id: str | None = None,
) -> str:
    connection.execute(
        """
        INSERT INTO workflow_runs (
            workflow_run_id,
            project_id,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workflow_run_id,
            project_id,
            "schedule_planning.v1",
            "v1",
            "tenant-a",
            "domain-ops",
            "SD-2026-03-04",
            "2026-03-04",
            f"activation-{workflow_run_id}",
            "ACTIVE",
            "2026-03-07T10:00:00Z",
            "2026-03-07T10:00:00Z",
        ),
    )
    return workflow_run_id


def _seed_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str,
    workflow_run_id: str = "wr-001",
    project_id: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO artifact_versions (
            artifact_version_id,
            workflow_run_id,
            project_id,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            workflow_run_id,
            project_id,
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


def test_provenance_edges_persist_edge_typing() -> None:
    connection = _connection()
    try:
        _seed_workflow(connection)
        _seed_artifact(connection, artifact_version_id="av-output")
        _seed_artifact(connection, artifact_version_id="av-input")
        _seed_artifact(connection, artifact_version_id="av-reviewed")

        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id="av-output",
            input_artifact_version_id="av-input",
            edge_type="derives_from",
            workflow_run_id="wr-001",
            edge_order=1,
            created_at="2026-03-07T10:05:00Z",
        )
        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id="av-output",
            input_artifact_version_id="av-reviewed",
            edge_type="reviewed_against",
            workflow_run_id="wr-001",
            edge_order=2,
            created_at="2026-03-07T10:05:01Z",
        )

        rows = list_artifact_provenance_edges_for_output(connection, "av-output")
        assert [(row["edge_type"], row["input_artifact_version_id"]) for row in rows] == [
            ("derives_from", "av-input"),
            ("reviewed_against", "av-reviewed"),
        ]
        assert [row["project_id"] for row in rows] == [None, None]
    finally:
        connection.close()


def test_provenance_edges_persist_same_project_identity() -> None:
    connection = _connection()
    try:
        _seed_project(connection, "cp-a")
        _seed_workflow(connection, project_id="cp-a")
        _seed_artifact(
            connection,
            artifact_version_id="av-output",
            project_id="cp-a",
        )
        _seed_artifact(connection, artifact_version_id="av-input", project_id="cp-a")

        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id="av-output",
            input_artifact_version_id="av-input",
            edge_type="derives_from",
            workflow_run_id="wr-001",
            edge_order=1,
            created_at="2026-03-07T10:05:00Z",
        )

        rows = list_artifact_provenance_edges_for_output(connection, "av-output")
        assert rows[0]["project_id"] == "cp-a"
    finally:
        connection.close()


def test_provenance_edges_reject_cross_project_and_project_to_null_edges() -> None:
    connection = _connection()
    try:
        _seed_project(connection, "cp-a")
        _seed_project(connection, "cp-b")
        _seed_workflow(connection, project_id="cp-a")
        _seed_workflow(connection, workflow_run_id="wr-b", project_id="cp-b")
        _seed_artifact(
            connection,
            artifact_version_id="av-output",
            project_id="cp-a",
        )
        _seed_artifact(
            connection,
            artifact_version_id="av-other-project",
            workflow_run_id="wr-b",
            project_id="cp-b",
        )
        _seed_artifact(connection, artifact_version_id="av-null-project")

        with pytest.raises(ProvenanceProjectScopeError):
            create_artifact_provenance_edge(
                connection,
                output_artifact_version_id="av-output",
                input_artifact_version_id="av-other-project",
                edge_type="derives_from",
                workflow_run_id="wr-001",
                edge_order=1,
                created_at="2026-03-07T10:05:00Z",
            )

        with pytest.raises(ProvenanceProjectScopeError):
            create_artifact_provenance_edge(
                connection,
                output_artifact_version_id="av-output",
                input_artifact_version_id="av-null-project",
                edge_type="derives_from",
                workflow_run_id="wr-001",
                edge_order=1,
                created_at="2026-03-07T10:06:00Z",
            )
    finally:
        connection.close()


def test_provenance_edges_reject_cycles() -> None:
    connection = _connection()
    try:
        _seed_workflow(connection)
        _seed_artifact(connection, artifact_version_id="av-1")
        _seed_artifact(connection, artifact_version_id="av-2")

        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id="av-2",
            input_artifact_version_id="av-1",
            edge_type="derives_from",
            workflow_run_id="wr-001",
            edge_order=1,
            created_at="2026-03-07T10:05:00Z",
        )

        with pytest.raises(ProvenanceCycleError):
            create_artifact_provenance_edge(
                connection,
                output_artifact_version_id="av-1",
                input_artifact_version_id="av-2",
                edge_type="derives_from",
                workflow_run_id="wr-001",
                edge_order=1,
                created_at="2026-03-07T10:06:00Z",
            )
    finally:
        connection.close()


def test_provenance_compatibility_projection_derives_legacy_fields() -> None:
    connection = _connection()
    try:
        _seed_workflow(connection)
        _seed_artifact(connection, artifact_version_id="av-out")
        _seed_artifact(connection, artifact_version_id="av-parent-a")
        _seed_artifact(connection, artifact_version_id="av-parent-b")
        _seed_artifact(connection, artifact_version_id="av-superseded")

        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id="av-out",
            input_artifact_version_id="av-parent-a",
            edge_type="derives_from",
            workflow_run_id="wr-001",
            edge_order=1,
            created_at="2026-03-07T10:05:00Z",
        )
        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id="av-out",
            input_artifact_version_id="av-parent-b",
            edge_type="derives_from",
            workflow_run_id="wr-001",
            edge_order=2,
            created_at="2026-03-07T10:05:01Z",
        )
        create_artifact_provenance_edge(
            connection,
            output_artifact_version_id="av-out",
            input_artifact_version_id="av-superseded",
            edge_type="supersedes",
            workflow_run_id="wr-001",
            edge_order=1,
            created_at="2026-03-07T10:05:02Z",
        )

        projection = project_legacy_lineage_fields(connection, "av-out")
        assert projection == {
            "parent_artifact_version_id": "av-parent-a",
            "supersedes_artifact_version_id": "av-superseded",
        }
    finally:
        connection.close()
