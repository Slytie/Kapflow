from __future__ import annotations

import re
import sqlite3

import pytest

from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_versions import (
    ARTIFACT_VERSION_IDENTITY_PROFILE,
    ArtifactProjectIdentityError,
    artifact_version_identity_payload,
    build_artifact_version_identity_digest,
    create_artifact_version,
    get_artifact_version,
    require_artifact_project_identity,
)
from onetruth.infrastructure.repositories.capex_projects import create_capex_project


NOW = "2026-06-23T00:00:00Z"
TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _create_run(connection: sqlite3.Connection, workflow_run_id: str = "wr-artifact-identity") -> None:
    create_workflow_run_command(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "workflow_id": "weekly_schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "partition_key": "PW-2026-W26",
            "logical_date": "2026-06-23",
            "activation_key": f"artifact-identity:{workflow_run_id}",
        },
    )


def _create_project(connection: sqlite3.Connection, project_id: str) -> None:
    create_capex_project(
        connection,
        project_id=project_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key=project_id.upper(),
        name=project_id,
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )


def _create_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_version_id: str = "av-identity-001",
    workflow_run_id: str = "wr-artifact-identity",
    storage_uri: str = "s3://artifact-store/a.json",
    content_digest: str = "sha256:" + ("1" * 64),
    partition_key: str = "PW-2026-W26",
    project_id: str | None = None,
) -> None:
    create_artifact_version(
        connection,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        task_run_id=None,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=project_id,
        dataset_key="planning.schedule.workbook",
        partition_kind="planning_week",
        partition_key=partition_key,
        artifact_kind="planning.schedule.workbook",
        artifact_role="evidence",
        media_type="application/json",
        storage_uri=storage_uri,
        content_digest=content_digest,
        byte_size=128,
        metadata_json={"fixture": "artifact-identity"},
        parent_artifact_version_id=None,
        supersedes_artifact_version_id=None,
        lineage_note=None,
        created_at=NOW,
    )


def test_artifact_version_identity_digest_is_deterministic_on_create() -> None:
    connection = _connection()
    try:
        _create_run(connection)
        _create_artifact(connection)

        artifact = get_artifact_version(connection, "av-identity-001")
        assert artifact is not None
        expected_digest = build_artifact_version_identity_digest(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=None,
            workflow_run_id="wr-artifact-identity",
            dataset_key="planning.schedule.workbook",
            partition_kind="planning_week",
            partition_key="PW-2026-W26",
            artifact_kind="planning.schedule.workbook",
            media_type="application/json",
            content_digest="sha256:" + ("1" * 64),
            byte_size=128,
        )
        assert artifact["artifact_identity_profile"] == ARTIFACT_VERSION_IDENTITY_PROFILE
        assert artifact["artifact_identity_digest"] == expected_digest
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", expected_digest)
    finally:
        connection.close()


def test_artifact_identity_digest_changes_when_scope_or_content_identity_changes() -> None:
    base = {
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "project_id": None,
        "workflow_run_id": "wr-artifact-identity",
        "dataset_key": "planning.schedule.workbook",
        "partition_kind": "planning_week",
        "partition_key": "PW-2026-W26",
        "artifact_kind": "planning.schedule.workbook",
        "media_type": "application/json",
        "content_digest": "sha256:" + ("1" * 64),
        "byte_size": 128,
    }

    assert build_artifact_version_identity_digest(**base) != build_artifact_version_identity_digest(
        **{**base, "partition_key": "PW-2026-W27"}
    )
    assert build_artifact_version_identity_digest(**base) != build_artifact_version_identity_digest(
        **{**base, "content_digest": "sha256:" + ("2" * 64)}
    )


def test_same_identity_inputs_produce_same_digest_and_no_officialness_columns() -> None:
    connection = _connection()
    try:
        _create_run(connection)
        _create_artifact(connection, artifact_version_id="av-identity-a", storage_uri="s3://a")
        _create_artifact(connection, artifact_version_id="av-identity-b", storage_uri="s3://b")

        first = get_artifact_version(connection, "av-identity-a")
        second = get_artifact_version(connection, "av-identity-b")
        assert first is not None
        assert second is not None
        assert first["artifact_identity_digest"] == second["artifact_identity_digest"]

        payload = artifact_version_identity_payload(
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=None,
            workflow_run_id="wr-artifact-identity",
            dataset_key="planning.schedule.workbook",
            partition_kind="planning_week",
            partition_key="PW-2026-W26",
            artifact_kind="planning.schedule.workbook",
            media_type="application/json",
            content_digest="sha256:" + ("1" * 64),
            byte_size=128,
        )
        assert "storage_uri" not in payload
        assert "officialness" not in payload
        assert "artifact_version_id" not in payload

        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info('artifact_versions')").fetchall()
        }
        assert "officialness" not in columns
        assert "is_official" not in columns
        assert "official_status" not in columns
        assert "pointer_id" not in columns
    finally:
        connection.close()


def test_existing_project_identity_mismatch_still_fails_closed() -> None:
    connection = _connection()
    try:
        _create_project(connection, "cp-alpha")
        connection.execute(
            """
            INSERT INTO workflow_runs (
                workflow_run_id,
                workflow_id,
                workflow_version,
                tenant_id,
                domain_id,
                project_id,
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
                "wr-project-artifact",
                "capex.project_state.v1",
                "v1",
                TENANT_ID,
                DOMAIN_ID,
                "cp-alpha",
                "project:alpha",
                "2026-06-23",
                "project-artifact",
                "OPEN",
                NOW,
                NOW,
            ),
        )
        _create_artifact(
            connection,
            artifact_version_id="av-project-artifact",
            workflow_run_id="wr-project-artifact",
            project_id="cp-alpha",
        )

        assert require_artifact_project_identity(
            connection,
            artifact_version_id="av-project-artifact",
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id="cp-alpha",
        )["artifact_version_id"] == "av-project-artifact"
        with pytest.raises(ArtifactProjectIdentityError):
            require_artifact_project_identity(
                connection,
                artifact_version_id="av-project-artifact",
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id="cp-beta",
            )
    finally:
        connection.close()
