from __future__ import annotations

import sqlite3

import pytest

from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.infrastructure.events.event_store import create_sqlite_substrate, list_events
from onetruth.infrastructure.repositories.artifact_pointer_events import (
    ArtifactPointerFoundationError,
    get_artifact_pointer_family_policy,
    list_artifact_pointer_events,
    record_artifact_pointer_event,
    register_artifact_pointer_family_policy,
)
from onetruth.infrastructure.repositories.artifact_versions import create_artifact_version
from onetruth.infrastructure.repositories.capex_projects import (
    create_capex_project,
    create_project_membership,
)


NOW = "2026-06-23T00:00:00Z"
TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-pointer"
BASIS_DIGEST = "sha256:" + ("1" * 64)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _create_project(connection: sqlite3.Connection, project_id: str = PROJECT_ID) -> None:
    membership_id = f"pm-{project_id}-system-tests"
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
    create_project_membership(
        connection,
        project_membership_id=membership_id,
        project_id=project_id,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_type="system",
        actor_id="system:tests",
        role="project_admin",
        state="active",
        granted_by_actor_id="human:admin",
        granted_by_actor_type="human",
        created_at=NOW,
    )
    connection.execute(
        """
        INSERT INTO capex_project_authorization (
            project_authorization_id,
            project_id,
            tenant_id,
            domain_id,
            actor_type,
            actor_id,
            direct_role,
            effective_role,
            source_membership_id,
            state,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"cpa-{project_id}-system-tests",
            project_id,
            TENANT_ID,
            DOMAIN_ID,
            "system",
            "system:tests",
            "project_admin",
            "project_admin",
            membership_id,
            "active",
            NOW,
            NOW,
        ),
    )


def _create_run(
    connection: sqlite3.Connection,
    workflow_run_id: str = "wr-pointer",
    *,
    project_id: str = PROJECT_ID,
) -> None:
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
            "activation_key": f"pointer-events:{workflow_run_id}",
            "project_id": project_id,
            "actor_id": "system:tests",
            "actor_type": "system",
        },
    )


def _create_artifact(
    connection: sqlite3.Connection,
    artifact_version_id: str = "av-pointer-current",
    *,
    workflow_run_id: str = "wr-pointer",
    project_id: str = PROJECT_ID,
) -> None:
    create_artifact_version(
        connection,
        artifact_version_id=artifact_version_id,
        workflow_run_id=workflow_run_id,
        task_run_id=None,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=project_id,
        dataset_key="capex.pointer.current",
        partition_kind="capex_project",
        partition_key=project_id,
        artifact_kind="capex.pointer.current",
        artifact_role="evidence",
        media_type="application/json",
        storage_uri=f"s3://artifact-store/{artifact_version_id}.json",
        content_digest="sha256:" + ("2" * 64),
        byte_size=128,
        metadata_json={"fixture": "pointer-event"},
        parent_artifact_version_id=None,
        supersedes_artifact_version_id=None,
        lineage_note=None,
        created_at=NOW,
    )


def test_pointer_family_policy_registers_replays_and_conflicts() -> None:
    connection = _connection()
    try:
        _create_project(connection)

        policy = register_artifact_pointer_family_policy(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            pointer_family="reviewed_baseline",
            registry_kind="singleton",
            policy_version="artifact_pointer_family_policy.v1",
            basis_digest=BASIS_DIGEST,
            policy_json={
                "allowed_artifact_kinds": ["capex.pointer.current"],
                "requires_review": True,
            },
            created_at=NOW,
        )
        replay = register_artifact_pointer_family_policy(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            pointer_family="reviewed_baseline",
            registry_kind="singleton",
            policy_version="artifact_pointer_family_policy.v1",
            basis_digest=BASIS_DIGEST,
            policy_json={
                "allowed_artifact_kinds": ["capex.pointer.current"],
                "requires_review": True,
            },
            created_at=NOW,
        )

        assert policy == replay
        assert policy["artifact_pointer_family_policy_id"].startswith(
            "artifact-pointer-family-policy:",
        )
        assert policy["policy_digest"].startswith("sha256:")
        assert get_artifact_pointer_family_policy(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            pointer_family="reviewed_baseline",
        ) == policy

        with pytest.raises(ArtifactPointerFoundationError) as exc_info:
            register_artifact_pointer_family_policy(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                pointer_family="reviewed_baseline",
                registry_kind="singleton",
                policy_version="artifact_pointer_family_policy.v1",
                basis_digest=BASIS_DIGEST,
                policy_json={"allowed_artifact_kinds": ["capex.other"]},
                created_at=NOW,
            )
        assert exc_info.value.code == "artifact_pointer_family_policy_conflict"
    finally:
        connection.close()


def test_pointer_event_appends_replays_and_does_not_mutate_current_pointer_or_timeline() -> None:
    connection = _connection()
    try:
        _create_project(connection)
        _create_run(connection)
        _create_artifact(connection)
        timeline_before = list_events(connection, run_id="wr-pointer", limit=100)

        event = record_artifact_pointer_event(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            pointer_id="pointer:reviewed-baseline",
            pointer_family="reviewed_baseline",
            event_kind="promoted",
            to_generation=0,
            artifact_version_id="av-pointer-current",
            basis_digest=BASIS_DIGEST,
            payload_json={"artifact_version_id": "av-pointer-current", "reason": "reviewed"},
            metadata_json={"policy": "artifact_pointer_family_policy.v1"},
            recorded_at=NOW,
            recorded_by_actor_ref="system:tests",
        )
        replay = record_artifact_pointer_event(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            pointer_id="pointer:reviewed-baseline",
            pointer_family="reviewed_baseline",
            event_kind="promoted",
            to_generation=0,
            artifact_version_id="av-pointer-current",
            basis_digest=BASIS_DIGEST,
            payload_json={"artifact_version_id": "av-pointer-current", "reason": "reviewed"},
            metadata_json={"policy": "artifact_pointer_family_policy.v1"},
            recorded_at=NOW,
            recorded_by_actor_ref="system:tests",
        )

        assert event == replay
        assert event["artifact_pointer_event_id"].startswith("artifact-pointer-event:")
        assert event["payload_digest"].startswith("sha256:")
        assert list_artifact_pointer_events(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
        ) == [event]
        assert connection.execute("SELECT COUNT(*) FROM artifact_pointers").fetchone()[0] == 0
        assert list_events(connection, run_id="wr-pointer", limit=100) == timeline_before
    finally:
        connection.close()


def test_pointer_event_rejects_conflict_generation_scope_bad_digest_and_raw_material() -> None:
    connection = _connection()
    try:
        _create_project(connection)
        _create_project(connection, project_id="cp-other")
        _create_run(connection)
        _create_run(connection, workflow_run_id="wr-pointer-other", project_id="cp-other")
        _create_artifact(connection)
        _create_artifact(
            connection,
            artifact_version_id="av-pointer-other",
            workflow_run_id="wr-pointer-other",
            project_id="cp-other",
        )

        record_artifact_pointer_event(
            connection,
            tenant_id=TENANT_ID,
            domain_id=DOMAIN_ID,
            project_id=PROJECT_ID,
            pointer_id="pointer:reviewed-baseline",
            pointer_family="reviewed_baseline",
            event_kind="promoted",
            to_generation=0,
            artifact_version_id="av-pointer-current",
            basis_digest=BASIS_DIGEST,
            payload_json={"artifact_version_id": "av-pointer-current"},
            recorded_at=NOW,
            recorded_by_actor_ref="system:tests",
        )

        with pytest.raises(ArtifactPointerFoundationError) as conflict:
            record_artifact_pointer_event(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                pointer_id="pointer:reviewed-baseline",
                pointer_family="reviewed_baseline",
                event_kind="promoted",
                to_generation=0,
                artifact_version_id="av-pointer-current",
                basis_digest=BASIS_DIGEST,
                payload_json={"artifact_version_id": "av-pointer-current", "changed": True},
                recorded_at=NOW,
                recorded_by_actor_ref="system:tests",
            )
        assert conflict.value.code == "artifact_pointer_event_conflict"

        with pytest.raises(ArtifactPointerFoundationError) as generation:
            record_artifact_pointer_event(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                pointer_id="pointer:reviewed-baseline",
                pointer_family="reviewed_baseline",
                event_kind="promoted",
                from_generation=2,
                to_generation=1,
                basis_digest=BASIS_DIGEST,
                payload_json={"artifact_version_id": "av-pointer-current"},
                recorded_at=NOW,
                recorded_by_actor_ref="system:tests",
            )
        assert generation.value.code == "artifact_pointer_generation_mismatch"

        with pytest.raises(ArtifactPointerFoundationError) as scope:
            record_artifact_pointer_event(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                pointer_id="pointer:other",
                pointer_family="reviewed_baseline",
                event_kind="promoted",
                to_generation=0,
                artifact_version_id="av-pointer-other",
                basis_digest=BASIS_DIGEST,
                payload_json={"artifact_version_id": "av-pointer-other"},
                recorded_at=NOW,
                recorded_by_actor_ref="system:tests",
            )
        assert scope.value.code == "artifact_pointer_scope_mismatch"

        with pytest.raises(ArtifactPointerFoundationError) as digest:
            record_artifact_pointer_event(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                pointer_id="pointer:digest",
                pointer_family="reviewed_baseline",
                event_kind="promoted",
                to_generation=0,
                basis_digest="bad-digest",
                payload_json={"artifact_version_id": "av-pointer-current"},
                recorded_at=NOW,
                recorded_by_actor_ref="system:tests",
            )
        assert digest.value.code == "artifact_pointer_digest_invalid"

        with pytest.raises(ArtifactPointerFoundationError) as raw:
            record_artifact_pointer_event(
                connection,
                tenant_id=TENANT_ID,
                domain_id=DOMAIN_ID,
                project_id=PROJECT_ID,
                pointer_id="pointer:raw",
                pointer_family="reviewed_baseline",
                event_kind="promoted",
                to_generation=0,
                basis_digest=BASIS_DIGEST,
                payload_json={"raw_text": "do not store me"},
                recorded_at=NOW,
                recorded_by_actor_ref="system:tests",
            )
        assert raw.value.code == "artifact_pointer_raw_material"
    finally:
        connection.close()
