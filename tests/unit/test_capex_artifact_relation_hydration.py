from __future__ import annotations

import sqlite3

import pytest

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_relation_hydration import (
    ArtifactRelationHydrationError,
    hydrate_artifact_relations_for_versions,
    list_artifact_versions_page_for_subject_with_relations,
    list_artifact_versions_page_for_workflow_run,
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
    artifact_kind: str = "capex.generated_artifact",
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
            artifact_kind,
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


def _seed_link(
    connection: sqlite3.Connection,
    artifact_version_id: str,
    index: int,
    *,
    workflow_run_id: str = "wr-hydration",
    subject_kind: str = "human_task",
    subject_id: str | None = None,
) -> None:
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
            workflow_run_id,
            subject_kind,
            subject_id if subject_id is not None else f"ht-{index:04d}",
            "input",
            f"2026-06-23T00:00:{index % 60:02d}Z",
            "human:pm",
            "human",
        ),
    )


def _seed_task_run(connection: sqlite3.Connection, task_run_id: str) -> None:
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
            task_run_id,
            "wr-hydration",
            "stage-review",
            "review",
            "ACTIVE",
            0,
            f"activation-{task_run_id}",
            NOW,
            NOW,
        ),
    )


def _seed_human_task(connection: sqlite3.Connection, human_task_id: str) -> None:
    task_run_id = f"tr-{human_task_id}"
    _seed_task_run(connection, task_run_id)
    connection.execute(
        """
        INSERT INTO human_tasks (
            human_task_id,
            workflow_run_id,
            task_run_id,
            task_kind,
            state,
            candidate_roles,
            owner_role,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            human_task_id,
            "wr-hydration",
            task_run_id,
            "review",
            "READY",
            '["project_manager"]',
            "project_manager",
            NOW,
            NOW,
        ),
    )


def _seed_flag(connection: sqlite3.Connection, flag_id: str) -> None:
    connection.execute(
        """
        INSERT INTO flags (
            flag_id,
            workflow_run_id,
            tenant_id,
            domain_id,
            workflow_id,
            partition_key,
            kind,
            severity,
            state,
            summary,
            details_json,
            assigned_group,
            created_at,
            created_by_actor_id,
            created_by_actor_type,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            flag_id,
            "wr-hydration",
            "tenant-a",
            "domain-x",
            "capex.corpus_baseline.v1",
            "cp-hydration",
            "missing_evidence",
            "high",
            "OPEN",
            "not exposed in hydration summary",
            "{}",
            "project_controls",
            NOW,
            "human:pm",
            "human",
            NOW,
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


def test_workflow_run_page_filters_kind_and_preserves_sql_ordering() -> None:
    connection = _connection()
    _seed_project(connection)
    _seed_workflow(connection)
    _seed_artifact(
        connection,
        "av-001",
        artifact_kind="capex.alpha",
        created_at="2026-06-23T00:01:00Z",
    )
    _seed_artifact(
        connection,
        "av-002",
        artifact_kind="capex.beta",
        created_at="2026-06-23T00:02:00Z",
    )
    _seed_artifact(
        connection,
        "av-003",
        artifact_kind="capex.alpha",
        created_at="2026-06-23T00:03:00Z",
    )

    selects: list[str] = []
    connection.set_trace_callback(
        lambda sql: selects.append(sql)
        if sql.lstrip().upper().startswith("SELECT")
        else None
    )
    rows = list_artifact_versions_page_for_workflow_run(
        connection,
        workflow_run_id="wr-hydration",
        artifact_kind="capex.alpha",
        tenant_id="tenant-a",
        domain_id="domain-x",
        project_id="cp-hydration",
        limit=1,
        offset=1,
    )
    connection.set_trace_callback(None)

    assert [row["artifact_version_id"] for row in rows] == ["av-003"]
    assert rows[0]["tenant_id"] == "tenant-a"
    assert rows[0]["project_id"] == "cp-hydration"
    assert len(selects) == 2


def test_subject_page_hydrates_relations_and_fails_closed_on_scope_mismatch() -> None:
    connection = _connection()
    _seed_project(connection)
    _seed_project(connection, "cp-other")
    _seed_workflow(connection)
    _seed_workflow(connection, workflow_run_id="wr-cross-same-project")
    for index, artifact_id in enumerate(("av-001", "av-002", "av-003"), start=1):
        _seed_artifact(
            connection,
            artifact_id,
            artifact_kind="capex.alpha" if artifact_id != "av-002" else "capex.beta",
            created_at=f"2026-06-23T00:0{index}:00Z",
        )
        _seed_link(connection, artifact_id, index, subject_id="ht-review")
    _seed_artifact(
        connection,
        "av-cross-run",
        workflow_run_id="wr-cross-same-project",
        artifact_kind="capex.alpha",
        created_at="2026-06-23T00:01:30Z",
    )
    _seed_link(
        connection,
        "av-cross-run",
        99,
        workflow_run_id="wr-hydration",
        subject_id="ht-review",
    )

    rows = list_artifact_versions_page_for_subject_with_relations(
        connection,
        workflow_run_id="wr-hydration",
        subject_kind="human_task",
        subject_id="ht-review",
        artifact_kind="capex.alpha",
        tenant_id="tenant-a",
        domain_id="domain-x",
        project_id="cp-hydration",
        limit=1,
        offset=1,
        include_provenance=False,
    )

    assert [row["artifact_version_id"] for row in rows] == ["av-003"]
    assert rows[0]["links"][0]["subject_id"] == "ht-review"
    with pytest.raises(ArtifactRelationHydrationError) as exc:
        list_artifact_versions_page_for_subject_with_relations(
            connection,
            workflow_run_id="wr-hydration",
            subject_kind="human_task",
            subject_id="ht-review",
            tenant_id="tenant-a",
            domain_id="domain-x",
            project_id="cp-other",
            limit=1,
        )
    assert exc.value.code == "artifact_relation_scope_mismatch"


def test_page_adapters_reject_invalid_bounds() -> None:
    connection = _connection()
    _seed_project(connection)
    _seed_workflow(connection)

    with pytest.raises(ArtifactRelationHydrationError) as limit:
        list_artifact_versions_page_for_workflow_run(
            connection,
            workflow_run_id="wr-hydration",
            limit=501,
        )
    assert limit.value.code == "artifact_relation_page_limit_invalid"

    with pytest.raises(ArtifactRelationHydrationError) as offset:
        list_artifact_versions_page_for_workflow_run(
            connection,
            workflow_run_id="wr-hydration",
            limit=1,
            offset=-1,
        )
    assert offset.value.code == "artifact_relation_page_offset_invalid"


def test_optional_subject_summary_hydration_batches_human_tasks_and_flags() -> None:
    connection = _connection()
    _seed_project(connection)
    _seed_workflow(connection)
    _seed_human_task(connection, "ht-summary")
    _seed_flag(connection, "flag-summary")
    _seed_artifact(connection, "av-task")
    _seed_artifact(connection, "av-flag")
    _seed_link(connection, "av-task", 1, subject_id="ht-summary")
    _seed_link(
        connection,
        "av-flag",
        2,
        subject_kind="flag",
        subject_id="flag-summary",
    )

    relations = hydrate_artifact_relations_for_versions(
        connection,
        ["av-task", "av-flag"],
        tenant_id="tenant-a",
        domain_id="domain-x",
        project_id="cp-hydration",
        include_provenance=False,
        include_subject_summaries=True,
    )

    task_summary = relations["av-task"]["links"][0]["subject_summary"]
    flag_summary = relations["av-flag"]["links"][0]["subject_summary"]
    assert task_summary == {
        "workflow_run_id": "wr-hydration",
        "task_run_id": "tr-ht-summary",
        "task_kind": "review",
        "state": "READY",
        "owner_role": "project_manager",
        "assignee_actor_id": None,
        "assignee_actor_type": None,
        "due_at": None,
        "escalation_at": None,
        "linked_approval_id": None,
        "created_at": NOW,
        "updated_at": NOW,
        "subject_kind": "human_task",
        "subject_id": "ht-summary",
    }
    assert flag_summary == {
        "workflow_run_id": "wr-hydration",
        "kind": "missing_evidence",
        "severity": "high",
        "state": "OPEN",
        "assigned_group": "project_controls",
        "created_at": NOW,
        "closed_at": None,
        "updated_at": NOW,
        "subject_kind": "flag",
        "subject_id": "flag-summary",
    }
    assert "summary" not in flag_summary


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
