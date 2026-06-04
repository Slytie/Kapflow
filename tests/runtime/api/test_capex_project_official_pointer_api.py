from __future__ import annotations

import base64
from pathlib import Path
import sqlite3

from onetruth.application.handlers.artifacts import ingest_artifact_document_command
from onetruth.application.handlers.capex_projects import (
    create_capex_project_command,
    grant_project_membership_command,
)
from onetruth.application.handlers.workflow_task_lifecycle import create_workflow_run_command
from onetruth.infrastructure.artifacts.storage import default_storage_root_for_db_url
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from tests.runtime.helpers.runtime_api import RuntimeApiClient

TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-official-pointer-001"
OTHER_PROJECT_ID = "cp-official-pointer-002"
WORKFLOW_RUN_ID = "wr-official-pointer-001"
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


def _client(db_url: str, actor_id: str) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_type="human",
        actor_id=actor_id,
        actor_roles=["capex_user"],
    )


def _seed(db_url: str) -> tuple[str, str]:
    connection = _open(db_url)
    try:
        for project_id, project_key in [
            (PROJECT_ID, "CAPEX-OFFICIAL-001"),
            (OTHER_PROJECT_ID, "CAPEX-OFFICIAL-002"),
        ]:
            create_capex_project_command(
                connection,
                {
                    "project_id": project_id,
                    "tenant_id": TENANT_ID,
                    "domain_id": DOMAIN_ID,
                    "project_key": project_key,
                    "name": f"{project_key} project",
                    "actor_id": "human:admin",
                    "actor_type": "human",
                    "idempotency_key": f"api:official-pointer:{project_id}:create",
                },
            )
            grant_project_membership_command(
                connection,
                {
                    "project_id": project_id,
                    "tenant_id": TENANT_ID,
                    "domain_id": DOMAIN_ID,
                    "actor_id": "human:admin",
                    "actor_type": "human",
                    "target_actor_id": "human:viewer",
                    "target_actor_type": "human",
                    "role": "project_viewer",
                    "idempotency_key": f"api:official-pointer:{project_id}:viewer",
                },
            )
            grant_project_membership_command(
                connection,
                {
                    "project_id": project_id,
                    "tenant_id": TENANT_ID,
                    "domain_id": DOMAIN_ID,
                    "actor_id": "human:admin",
                    "actor_type": "human",
                    "target_actor_id": "human:contributor",
                    "target_actor_type": "human",
                    "role": "project_contributor",
                    "idempotency_key": f"api:official-pointer:{project_id}:contributor",
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
                "activation_key": "official-pointer-run",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
        )
        first = _artifact(connection, db_url=db_url, artifact_version_id="av-official-pointer-001")
        second = _artifact(connection, db_url=db_url, artifact_version_id="av-official-pointer-002")
        connection.commit()
    finally:
        connection.close()
    return str(first["artifact_version_id"]), str(second["artifact_version_id"])


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
            "idempotency_key": f"api:official-pointer:{artifact_version_id}",
            "actor_id": "human:admin",
            "actor_type": "human",
        },
        storage_root=default_storage_root_for_db_url(db_url),
        include_receipt=True,
    )["result"]["artifact_version"]


def _promote_payload(artifact_version_id: str, key: str) -> dict[str, object]:
    return {
        "workflow_run_id": WORKFLOW_RUN_ID,
        "artifact_version_id": artifact_version_id,
        "artifact_kind": ARTIFACT_KIND,
        "idempotency_key": key,
    }


def test_capex_project_official_pointer_routes_promote_and_scope_snapshots(tmp_path: Path) -> None:
    db_url = _init_db(tmp_path / "capex-official-pointer-api.db")
    first_artifact_id, second_artifact_id = _seed(db_url)
    contributor = _client(db_url, "human:contributor")
    viewer = _client(db_url, "human:viewer")
    outsider = _client(db_url, "human:outsider")

    empty = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers")
    assert empty.status_code == 200
    assert empty.payload["official_pointers"] == []

    viewer_denied = viewer.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers/current-schedule/promote",
        payload=_promote_payload(first_artifact_id, "api:official-pointer:viewer-denied"),
    )
    assert viewer_denied.status_code == 403
    assert viewer_denied.payload["error"]["code"] == "capex_project_access_forbidden"

    promoted = contributor.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers/current-schedule/promote",
        payload=_promote_payload(first_artifact_id, "api:official-pointer:promote-first"),
    )
    assert promoted.status_code == 200
    assert promoted.payload["command"] == "api.capex.projects.official_pointers.promote"
    assert promoted.payload["pointer_family"] == "current-schedule"
    assert promoted.payload["pointer"]["project_id"] == PROJECT_ID
    assert promoted.payload["pointer"]["pointer_key"] == "official:current-schedule"
    assert promoted.payload["snapshot"]["generation"] == 0

    listed = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers")
    assert listed.status_code == 200
    assert [row["pointer_family"] for row in listed.payload["official_pointers"]] == [
        "current-schedule"
    ]
    assert listed.payload["snapshots"][0]["artifact_version_id"] == first_artifact_id

    detail = viewer.get(
        f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers/current-schedule"
    )
    assert detail.status_code == 200
    assert detail.payload["snapshot"]["pointer_family"] == "current-schedule"

    conflict = contributor.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers/current-schedule/promote",
        payload=_promote_payload(second_artifact_id, "api:official-pointer:promote-conflict"),
    )
    assert conflict.status_code == 409
    assert conflict.payload["error"]["code"] == "pointer_conflict"

    repoint_payload = _promote_payload(second_artifact_id, "api:official-pointer:promote-second")
    repoint_payload["expected_generation"] = 0
    repointed = contributor.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers/current-schedule/promote",
        payload=repoint_payload,
    )
    assert repointed.status_code == 200
    assert repointed.payload["snapshot"]["artifact_version_id"] == second_artifact_id
    assert repointed.payload["snapshot"]["generation"] == 1

    mismatched_project = contributor.post(
        f"/api/v1/capex/projects/{OTHER_PROJECT_ID}/official-pointers/current-schedule/promote",
        payload=_promote_payload(second_artifact_id, "api:official-pointer:mismatch"),
    )
    assert mismatched_project.status_code == 404
    assert mismatched_project.payload["error"]["code"] == "workflow_run_not_found"

    hidden = outsider.get(f"/api/v1/capex/projects/{PROJECT_ID}/official-pointers")
    assert hidden.status_code == 404
    assert hidden.payload["error"]["code"] == "capex_project_not_found"
