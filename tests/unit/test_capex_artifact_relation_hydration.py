from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_relation_hydration import (
    ArtifactRelationHydrationError,
    hydrate_artifact_relations_for_versions,
    list_artifact_versions_page_with_relations,
)


NOW = "2026-06-23T00:00:00Z"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _seed_project(connection: sqlite3.Connection, project_id: str = "cp-hydration") -> None:
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
            "domain-x",
            project_id.upper(),
            project_id,
            "active",
            "{}",
            "human:admin",
            "human",
            NOW,
            NOW,
        ),
    )


def _seed_workflow(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str = "wr-hydration",
    project_id: str = "cp-hydration",
    tenant_id: str = "tenant-a",
    domain_id: str = "domain-x",
) -> None:
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
            "capex.corpus_baseline.v1",
            "v1",
            tenant_id,
            domain_id,
            "cp-hydration",
            "2026-06-23",
            f"activation-{workflow_run_id}",
            "ACTIVE",
            NOW,
            NOW,
        ),
    )


def _seed_artifact(
    connection: sqlite3.Connection,
    artifact_version_id: str,
    *,
    workflow_run_id: str = "wr-hydration",
    project_id: str = "cp-hydration",
    created_at: str = NOW,
) -> None:
    connection.execute(
        """
        INSERT INTO artifact_versions (
            artifact_version_id,
            workflow_run_id,
            tenant_id,
            domain_id,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            workflow_run_id,
            "tenant-a",
            "domain-x",
            project_id,
            None,
            "capex.generated_artifact",
            "evidence",
            "application/json",
            f"object://artifact/{artifact_version_id}",
            f"sha256:{artifact_version_id:0<64}"[:71],
            128,
            "{}",
            None,
            None,
            None,
            created_at,
        ),
    )


def _seed_link(connection: sqlite3.Connection, artifact_version_id: str, index: int) -> None:
    connection.execute(
        """
        INSERT INTO artifact_links (
            artifact_version_id,
            workflow_run_id,
            subject_kind,
            subject_id,
            relation_kind,
            created_at,
            created_by_actor_id,
            created_by_actor_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_version_id,
            "wr-hydration",
            "human_task",
            f"ht-{index:04d}",
            "input",
            f"2026-06-23T00:00:{index % 60:02d}Z",
            "human:pm",
            "human",
        ),
    )


def _seed_provenance(
    connection: sqlite3.Connection,
    *,
    output_artifact_version_id: str,
    input_artifact_version_id: str,
    edge_order: int,
) -> None:
    connection.execute(
        """
        INSERT INTO artifact_provenance_edges (
            edge_id,
            workflow_run_id,
            project_id,
            output_artifact_version_id,
            input_artifact_version_id,
            edge_type,
            edge_order,
            metadata_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"ape-{output_artifact_version_id}-{input_artifact_version_id}",
            "wr-hydration",
            "cp-hydration",
            output_artifact_version_id,
            input_artifact_version_id,
            "derives_from",
            edge_order,
            '{"source":"unit"}',
            NOW,
        ),
    )


def test_project_page_hydrates_links_and_provenance_deterministically() -> None:
    connection = _connection()
    _seed_project(connection)
    _seed_workflow(connection)
    for index, artifact_id in enumerate(("av-001", "av-002", "av-003"), start=1):
        _seed_artifact(
            connection,
            artifact_id,
            created_at=f"2026-06-23T00:0{index}:00Z",
        )
        _seed_link(connection, artifact_id, index)
    _seed_provenance(
        connection,
        output_artifact_version_id="av-003",
        input_artifact_version_id="av-001",
        edge_order=1,
    )

    selects: list[str] = []
    connection.set_trace_callback(
        lambda sql: selects.append(sql)
        if sql.lstrip().upper().startswith("SELECT")
        else None
    )
    rows = list_artifact_versions_page_with_relations(
        connection,
        tenant_id="tenant-a",
        domain_id="domain-x",
        project_id="cp-hydration",
        limit=3,
    )
    connection.set_trace_callback(None)

    assert [row["artifact_version_id"] for row in rows] == ["av-003", "av-002", "av-001"]
    assert rows[0]["links"][0]["subject_id"] == "ht-0003"
    assert rows[0]["provenance_edges"][0]["input_artifact_version_id"] == "av-001"
    assert rows[0]["provenance_edges"][0]["metadata_json"] == {"source": "unit"}
    assert len(selects) == 4


def test_hydration_rejects_scope_mismatch_and_duplicate_ids() -> None:
    connection = _connection()
    _seed_project(connection)
    _seed_project(connection, "cp-other")
    _seed_workflow(connection)
    _seed_workflow(connection, workflow_run_id="wr-other", project_id="cp-other")
    _seed_artifact(connection, "av-001")
    _seed_artifact(
        connection,
        "av-other",
        workflow_run_id="wr-other",
        project_id="cp-other",
    )

    with pytest.raises(ArtifactRelationHydrationError) as duplicate:
        hydrate_artifact_relations_for_versions(connection, ["av-001", "av-001"])
    assert duplicate.value.code == "artifact_relation_duplicate_artifact_id"

    with pytest.raises(ArtifactRelationHydrationError) as scope:
        hydrate_artifact_relations_for_versions(
            connection,
            ["av-001", "av-other"],
            tenant_id="tenant-a",
            domain_id="domain-x",
            project_id="cp-hydration",
        )
    assert scope.value.code == "artifact_relation_scope_mismatch"
    assert scope.value.details["missing_or_out_of_scope"] == ["av-other"]


def test_five_thousand_artifacts_use_chunked_batch_queries_not_n_plus_one() -> None:
    connection = _connection()
    _seed_project(connection)
    _seed_workflow(connection)
    artifact_ids = [f"av-scale-{index:04d}" for index in range(5000)]
    for artifact_id in artifact_ids:
        _seed_artifact(connection, artifact_id)

    selects: list[str] = []
    connection.set_trace_callback(
        lambda sql: selects.append(sql)
        if sql.lstrip().upper().startswith("SELECT")
        else None
    )
    relations = hydrate_artifact_relations_for_versions(
        connection,
        artifact_ids,
        tenant_id="tenant-a",
        domain_id="domain-x",
        project_id="cp-hydration",
        include_provenance=False,
    )
    connection.set_trace_callback(None)

    assert len(relations) == 5000
    assert all(value["link_count"] == 0 for value in relations.values())
    assert len(selects) == 20


def test_hydration_rejects_unbounded_id_lists() -> None:
    connection = _connection()

    with pytest.raises(ArtifactRelationHydrationError) as exc:
        hydrate_artifact_relations_for_versions(
            connection,
            [f"av-{index:04d}" for index in range(5001)],
        )

    assert exc.value.code == "artifact_relation_hydration_id_limit_exceeded"
