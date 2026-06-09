from __future__ import annotations

import sqlite3

from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import create_capex_project
from onetruth.infrastructure.repositories.capex_workpage_projections import (
    create_projection_row,
    create_projection_snapshot,
    get_projection_snapshot,
    list_projection_rows,
    mark_projection_snapshot_stale,
    projection_basis_hash,
)


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-projection"
NOW = "2026-06-08T00:00:00Z"


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
        project_key="CAPEX-PROJECTION",
        name="Projection project",
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    return connection


def test_projection_snapshot_stores_deterministic_basis_hash_and_ordered_rows() -> None:
    connection = _connection()
    try:
        basis = {
            "basis_refs": ["source_occurrence:so-a", "closure_snapshot:cs-a"],
            "policy_version": "capex.projection.v1",
        }
        snapshot = create_projection_snapshot(
            connection,
            projection_snapshot_id="wps-001",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            workpage_kind="capex-source-review-v0",
            projection_kind="capex.project_source_review",
            renderer_version="capex.projection.renderer.v1",
            basis_version_vector_json=basis,
            state="current",
            payload_metadata_json={"row_count": 2},
            created_by_actor_id="system:projection",
            created_by_actor_type="system",
            created_at=NOW,
        )
        create_projection_row(
            connection,
            projection_row_id="wpr-002",
            projection_snapshot_id="wps-001",
            row_key="row-b",
            row_order=20,
            subject_kind="artifact_version",
            subject_ref="av-b",
            row_payload_json={"label": "B"},
            created_at=NOW,
        )
        create_projection_row(
            connection,
            projection_row_id="wpr-001",
            projection_snapshot_id="wps-001",
            row_key="row-a",
            row_order=10,
            subject_kind="artifact_version",
            subject_ref="av-a",
            row_payload_json={"label": "A"},
            created_at=NOW,
        )

        rows = list_projection_rows(connection, "wps-001")

        assert snapshot["basis_hash"] == projection_basis_hash(basis)
        assert rows[0]["row_key"] == "row-a"
        assert rows[1]["row_key"] == "row-b"
    finally:
        connection.close()


def test_projection_snapshot_can_be_marked_stale_without_mutating_basis() -> None:
    connection = _connection()
    try:
        basis = {"basis_refs": ["source_occurrence:so-a"]}
        expected_hash = projection_basis_hash(basis)
        create_projection_snapshot(
            connection,
            projection_snapshot_id="wps-stale",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            workpage_kind="capex-source-review-v0",
            projection_kind="capex.project_source_review",
            renderer_version="capex.projection.renderer.v1",
            basis_version_vector_json=basis,
            state="current",
            payload_metadata_json={},
            created_by_actor_id="system:projection",
            created_by_actor_type="system",
            created_at=NOW,
        )

        mark_projection_snapshot_stale(
            connection,
            projection_snapshot_id="wps-stale",
            stale_reason="basis_ref_changed:source_occurrence:so-a",
            stale_at="2026-06-08T01:00:00Z",
        )

        snapshot = get_projection_snapshot(connection, "wps-stale")
        assert snapshot is not None
        assert snapshot["state"] == "stale"
        assert snapshot["basis_hash"] == expected_hash
        assert snapshot["stale_reason"] == "basis_ref_changed:source_occurrence:so-a"
    finally:
        connection.close()
