from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest
from jsonschema import Draft202012Validator

from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.capex_platform.generated_artifact_submission import (
    CapexGeneratedArtifactSubmissionError,
    build_runtime_generated_artifact_view,
    build_submitted_generated_artifact_envelope,
    validate_submitted_generated_artifact,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.artifact_versions import (
    ARTIFACT_VERSION_IDENTITY_PROFILE,
    create_artifact_version,
    get_artifact_version,
)
from onetruth.infrastructure.repositories.capex_projects import (
    create_capex_project,
    create_project_membership,
)


ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-06-23T00:00:00Z"
TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-generated"
SOURCE_REF = "source_occurrence:so-generated"
INPUT_DIGEST = "sha256:" + ("1" * 64)


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    create_sqlite_substrate(connection)
    return connection


def _submission() -> dict[str, object]:
    return {
        "schema_version": "capex.submitted_generated_artifact.v1",
        "artifact_kind": "capex.project_intake.profile",
        "artifact_role": "evidence",
        "source_refs": [SOURCE_REF],
        "input_digests": [INPUT_DIGEST],
        "validation_summary": {"result": "planning_only"},
        "payload": {"project_key": "CP-GENERATED", "observation_count": 2},
    }


def _create_project_and_run(connection: sqlite3.Connection) -> None:
    create_capex_project(
        connection,
        project_id=PROJECT_ID,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_key=PROJECT_ID.upper(),
        name=PROJECT_ID,
        state="active",
        metadata_json={},
        created_by_actor_id="human:admin",
        created_by_actor_type="human",
        created_at=NOW,
    )
    create_project_membership(
        connection,
        project_membership_id="pm-generated-system-tests",
        project_id=PROJECT_ID,
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
            "cpa-generated-system-tests",
            PROJECT_ID,
            TENANT_ID,
            DOMAIN_ID,
            "system",
            "system:tests",
            "project_admin",
            "project_admin",
            "pm-generated-system-tests",
            "active",
            NOW,
            NOW,
        ),
    )
    create_workflow_run_command(
        connection,
        {
            "workflow_run_id": "wr-generated-view",
            "workflow_id": "weekly_schedule_planning.v1",
            "workflow_version": "v1",
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "partition_key": "PW-2026-W26",
            "logical_date": "2026-06-23",
            "activation_key": "generated-view:wr-generated-view",
            "project_id": PROJECT_ID,
            "actor_id": "system:tests",
            "actor_type": "system",
        },
    )


def _create_artifact(connection: sqlite3.Connection) -> dict[str, object]:
    create_artifact_version(
        connection,
        artifact_version_id="av-generated-view",
        workflow_run_id="wr-generated-view",
        task_run_id=None,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        project_id=PROJECT_ID,
        dataset_key="capex.project_intake.profile",
        partition_kind="capex_project",
        partition_key=PROJECT_ID,
        artifact_kind="capex.project_intake.profile",
        artifact_role="evidence",
        media_type="application/json",
        storage_uri="s3://artifact-store/capex.project_intake.profile.v1.json",
        content_digest="sha256:" + ("2" * 64),
        byte_size=256,
        metadata_json={"capex_generated_artifact_file_name": "capex.project_intake.profile.v1.json"},
        parent_artifact_version_id=None,
        supersedes_artifact_version_id=None,
        lineage_note=None,
        created_at=NOW,
    )
    artifact = get_artifact_version(connection, "av-generated-view")
    assert artifact is not None
    return artifact


def test_submitted_generated_artifact_validates_schema_and_builds_existing_envelope() -> None:
    submission = _submission()
    schema = json.loads(
        (ROOT / "schemas/runtime/capex_submitted_generated_artifact.schema.json").read_text(
            encoding="utf-8",
        ),
    )
    Draft202012Validator(schema).validate(submission)

    normalized = validate_submitted_generated_artifact(submission)
    envelope = build_submitted_generated_artifact_envelope(submission)

    assert normalized == submission
    assert envelope["schema_version"] == "capex.generated_artifact_envelope.v1"
    assert envelope["artifact_kind"] == submission["artifact_kind"]
    assert envelope["payload"] == submission["payload"]


def test_submitted_generated_artifact_rejects_runtime_owned_fields_and_raw_material() -> None:
    for field in (
        "artifact_version_id",
        "storage_uri",
        "content_digest",
        "byte_size",
        "artifact_identity_digest",
        "pointer_id",
        "official_status",
        "event_id",
        "created_at",
    ):
        with pytest.raises(CapexGeneratedArtifactSubmissionError) as exc_info:
            validate_submitted_generated_artifact({**_submission(), field: "runtime-owned"})
        assert exc_info.value.code == "submitted_generated_artifact_runtime_field"

    with pytest.raises(CapexGeneratedArtifactSubmissionError) as nested:
        validate_submitted_generated_artifact(
            {
                **_submission(),
                "payload": {"nested": {"storage_uri": "s3://should-not-submit"}},
            },
        )
    assert nested.value.code == "submitted_generated_artifact_runtime_field"

    with pytest.raises(CapexGeneratedArtifactSubmissionError) as raw:
        validate_submitted_generated_artifact(
            {**_submission(), "payload": {"raw_text": "do not store me"}},
        )
    assert raw.value.code == "submitted_generated_artifact_raw_material"


def test_runtime_generated_artifact_view_exposes_runtime_metadata_without_pointer_authority() -> None:
    connection = _connection()
    try:
        _create_project_and_run(connection)
        artifact = _create_artifact(connection)
        view = build_runtime_generated_artifact_view(artifact)
        schema = json.loads(
            (
                ROOT / "schemas/runtime/capex_runtime_generated_artifact_view.schema.json"
            ).read_text(encoding="utf-8"),
        )

        Draft202012Validator(schema).validate(view)

        assert view["schema_version"] == "capex.runtime_generated_artifact_view.v1"
        assert view["artifact_version_id"] == "av-generated-view"
        assert view["artifact_identity_profile"] == ARTIFACT_VERSION_IDENTITY_PROFILE
        assert view["runtime_state"] == {
            "promotable": False,
            "evidence_sufficient": False,
            "reviewed_baseline": False,
            "pointer_bound": False,
        }
        assert "pointer_id" not in view
        assert "pointer_key" not in view
        assert "officialness" not in view
        assert "official_status" not in view
        assert "is_official" not in view
    finally:
        connection.close()
