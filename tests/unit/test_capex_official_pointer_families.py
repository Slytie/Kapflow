from __future__ import annotations

import base64
from pathlib import Path
import sqlite3

import pytest

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.handlers.approvals import request_approval_command, respond_approval_command
from onetruth.application.handlers.artifacts import ingest_artifact_document_command
from onetruth.application.handlers.capex_projects import (
    create_capex_project_command,
    grant_project_membership_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.application.services.capex_official_pointers import (
    get_project_official_pointer,
    list_project_official_pointers,
    promote_project_official_pointer_command,
    stream_key_for_project_family,
)
from onetruth.infrastructure.artifacts.storage import default_storage_root_for_db_url
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from onetruth.infrastructure.repositories.capex_projects import get_capex_project

TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-pointer-001"
WORKFLOW_RUN_ID = "wr-pointer-001"
ARTIFACT_KIND = "schedule.published_schedule.workbook"


def _init_db(path: Path) -> str:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    connection.close()
    return f"sqlite:///{path}"


def _open(db_url: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_url.removeprefix("sqlite:///"))
    connection.row_factory = sqlite3.Row
    return connection


def _seed(connection: sqlite3.Connection, db_url: str) -> tuple[dict[str, object], dict[str, object]]:
    create_capex_project_command(
        connection,
        {
            "project_id": PROJECT_ID,
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "project_key": "CAPEX-POINTER-001",
            "name": "Pointer project",
            "actor_id": "human:admin",
            "actor_type": "human",
            "idempotency_key": "unit:capex-pointer:create",
        },
    )
    for actor_id, role in [
        ("human:contributor", "project_contributor"),
        ("human:viewer", "project_viewer"),
    ]:
        grant_project_membership_command(
            connection,
            {
                "project_id": PROJECT_ID,
                "tenant_id": TENANT_ID,
                "domain_id": DOMAIN_ID,
                "actor_id": "human:admin",
                "actor_type": "human",
                "target_actor_id": actor_id,
                "target_actor_type": "human",
                "role": role,
                "idempotency_key": f"unit:capex-pointer:{actor_id}",
            },
        )
    create_workflow_run_command(
        connection,
        {
            "workflow_run_id": WORKFLOW_RUN_ID,
            "project_id": PROJECT_ID,
            "workflow_id": "capex.intake.v1",
            "workflow_version": "v1",
            "tenant_id": TENANT_ID,
            "domain_id": DOMAIN_ID,
            "partition_key": "SD-2026-06-04",
            "logical_date": "2026-06-04",
            "activation_key": "capex-pointer-run",
            "actor_id": "human:admin",
            "actor_type": "human",
        },
    )
    first = _artifact(connection, db_url=db_url, artifact_version_id="av-pointer-001")
    second = _artifact(connection, db_url=db_url, artifact_version_id="av-pointer-002")
    return first, second


def _artifact(
    connection: sqlite3.Connection,
    *,
    db_url: str,
    artifact_version_id: str,
) -> dict[str, object]:
    return ingest_artifact_document_command(
        connection,
        {
            "artifact_version_id": artifact_version_id,
            "workflow_run_id": WORKFLOW_RUN_ID,
            "artifact_kind": ARTIFACT_KIND,
            "artifact_role": "official_output",
            "content_base64": base64.b64encode(artifact_version_id.encode("ascii")).decode("ascii"),
            "file_name": f"{artifact_version_id}.json",
            "media_type": "application/json",
            "canonical_partition_kind": "ScheduleDateID",
            "canonical_partition_key": "SD-2026-06-04",
            "idempotency_key": f"unit:capex-pointer:{artifact_version_id}",
            "actor_id": "human:admin",
            "actor_type": "human",
        },
        storage_root=default_storage_root_for_db_url(db_url),
        include_receipt=True,
    )["result"]["artifact_version"]


def _promote_payload(*, artifact_version_id: str, actor_id: str, key: str) -> dict[str, object]:
    return {
        "project_id": PROJECT_ID,
        "tenant_id": TENANT_ID,
        "domain_id": DOMAIN_ID,
        "pointer_family": "current-schedule",
        "workflow_run_id": WORKFLOW_RUN_ID,
        "artifact_kind": ARTIFACT_KIND,
        "artifact_version_id": artifact_version_id,
        "actor_id": actor_id,
        "actor_type": "human",
        "idempotency_key": key,
    }


def test_project_official_pointer_requires_explicit_promotion_and_tracks_generation(tmp_path: Path) -> None:
    db_url = _init_db(tmp_path / "capex-pointer-unit.db")
    connection = _open(db_url)
    try:
        first, second = _seed(connection, db_url)
        project = get_capex_project(connection, PROJECT_ID)
        assert project is not None

        approval = request_approval_command(
            connection,
            {
                "approval_id": "ap-pointer-001",
                "workflow_run_id": WORKFLOW_RUN_ID,
                "approval_kind": "project_official_pointer",
                "scope_kind": "workflow_run",
                "scope_ref": WORKFLOW_RUN_ID,
                "candidate_roles": ["capex_user"],
                "required_role": "capex_user",
                "allowed_responses": ["approve", "reject"],
                "idempotency_key": "unit:capex-pointer:approval",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
        )
        respond_approval_command(
            connection,
            {
                "approval_id": approval["approval_id"],
                "actor_id": "human:contributor",
                "actor_type": "human",
                "actor_roles": ["capex_user"],
                "response_kind": "approve",
                "response_reason": "ready",
                "idempotency_key": "unit:capex-pointer:approval-response",
            },
        )
        assert list_project_official_pointers(connection, project=project) == []

        promoted = promote_project_official_pointer_command(
            connection,
            _promote_payload(
                artifact_version_id=str(first["artifact_version_id"]),
                actor_id="human:contributor",
                key="unit:capex-pointer:promote-first",
            ),
            include_receipt=True,
        )
        pointer = promoted["pointer"]
        assert pointer["project_id"] == PROJECT_ID
        assert pointer["pointer_family"] == "current-schedule"
        assert pointer["pointer_key"] == "official:current-schedule"
        assert pointer["scope_kind"] == "capex_project"
        assert pointer["scope_ref"] == PROJECT_ID
        assert pointer["stream_key"] == stream_key_for_project_family(
            project_id=PROJECT_ID,
            pointer_family="current-schedule",
        )
        assert int(pointer["generation"]) == 0

        with pytest.raises(CommandError) as missing_generation:
            promote_project_official_pointer_command(
                connection,
                _promote_payload(
                    artifact_version_id=str(second["artifact_version_id"]),
                    actor_id="human:contributor",
                    key="unit:capex-pointer:promote-conflict",
                ),
            )
        assert missing_generation.value.code == "pointer_conflict"

        repointed_payload = _promote_payload(
            artifact_version_id=str(second["artifact_version_id"]),
            actor_id="human:contributor",
            key="unit:capex-pointer:promote-second",
        )
        repointed_payload["expected_generation"] = 0
        repointed = promote_project_official_pointer_command(connection, repointed_payload)
        assert int(repointed["pointer"]["generation"]) == 1
        assert repointed["snapshot"]["artifact_version_id"] == second["artifact_version_id"]

        fetched = get_project_official_pointer(
            connection,
            project=project,
            pointer_family="current-schedule",
        )
        assert fetched is not None
        assert fetched["artifact_version_id"] == second["artifact_version_id"]
    finally:
        connection.close()


def test_project_official_pointer_promotion_requires_project_write_role(tmp_path: Path) -> None:
    db_url = _init_db(tmp_path / "capex-pointer-unit-denial.db")
    connection = _open(db_url)
    try:
        first, _second = _seed(connection, db_url)

        with pytest.raises(CommandError) as denied:
            promote_project_official_pointer_command(
                connection,
                _promote_payload(
                    artifact_version_id=str(first["artifact_version_id"]),
                    actor_id="human:viewer",
                    key="unit:capex-pointer:viewer-denied",
                ),
            )
        assert denied.value.code == "capex_project_access_forbidden"
    finally:
        connection.close()
