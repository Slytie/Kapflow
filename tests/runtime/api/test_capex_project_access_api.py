from __future__ import annotations

import sqlite3
from pathlib import Path

from onetruth.application.handlers.workflow_task_lifecycle import (
    create_workflow_run_command,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from tests.runtime.helpers.runtime_api import RuntimeApiClient


TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-api-001"


def _init_db(path: Path) -> str:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    try:
        create_sqlite_substrate(connection)
    finally:
        connection.close()
    return f"sqlite:///{path}"


def _client(db_url: str, actor_id: str) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_id=actor_id,
        actor_type="human",
        actor_roles=["capex_user"],
    )


def _create_no_project_run(db_url: str) -> None:
    path = db_url.removeprefix("sqlite:///")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        create_workflow_run_command(
            connection,
            {
                "workflow_run_id": "wr-no-project-api",
                "workflow_id": "capex.reference.v1",
                "workflow_version": "v1",
                "tenant_id": TENANT_ID,
                "domain_id": DOMAIN_ID,
                "partition_key": "NO-PROJECT",
                "logical_date": "2026-06-04",
                "activation_key": "api-no-project",
            },
        )
    finally:
        connection.close()


def test_capex_project_api_enforces_membership_and_project_run_visibility(tmp_path: Path) -> None:
    db_url = _init_db(tmp_path / "capex-project-api.db")
    admin = _client(db_url, "human:admin")
    viewer = _client(db_url, "human:viewer")
    contributor = _client(db_url, "human:contributor")
    outsider = _client(db_url, "human:outsider")

    created = admin.post(
        "/api/v1/capex/projects",
        payload={
            "project_id": PROJECT_ID,
            "project_key": "CAPEX-API-001",
            "name": "API project",
            "metadata_json": {"cost_center": "plant-12"},
            "idempotency_key": "api:capex-project:create",
        },
    )
    assert created.status_code == 200
    assert created.payload["project"]["project_id"] == PROJECT_ID
    assert created.payload["admin_membership"]["role"] == "project_admin"
    assert created.payload["idempotent_replay"] is False

    replay = admin.post(
        "/api/v1/capex/projects",
        payload={
            "project_id": PROJECT_ID,
            "project_key": "CAPEX-API-001",
            "name": "API project",
            "metadata_json": {"cost_center": "plant-12"},
            "idempotency_key": "api:capex-project:create",
        },
    )
    assert replay.status_code == 200
    assert replay.payload["idempotent_replay"] is True

    hidden_project = outsider.get(f"/api/v1/capex/projects/{PROJECT_ID}")
    assert hidden_project.status_code == 404
    assert hidden_project.payload["error"]["code"] == "capex_project_not_found"

    grant_viewer = admin.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/memberships",
        payload={
            "actor_id": "human:viewer",
            "actor_type": "human",
            "role": "project_viewer",
            "idempotency_key": "api:capex-project:grant-viewer",
        },
    )
    assert grant_viewer.status_code == 200
    assert grant_viewer.payload["membership"]["role"] == "project_viewer"

    grant_contributor = admin.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/memberships",
        payload={
            "actor_id": "human:contributor",
            "actor_type": "human",
            "role": "project_contributor",
            "idempotency_key": "api:capex-project:grant-contributor",
        },
    )
    assert grant_contributor.status_code == 200
    assert grant_contributor.payload["membership"]["role"] == "project_contributor"

    viewer_detail = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}")
    assert viewer_detail.status_code == 200
    assert viewer_detail.payload["project"]["project_id"] == PROJECT_ID

    viewer_memberships = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/memberships")
    assert viewer_memberships.status_code == 403
    assert viewer_memberships.payload["error"]["code"] == "capex_project_access_forbidden"

    admin_memberships = admin.get(f"/api/v1/capex/projects/{PROJECT_ID}/memberships")
    assert admin_memberships.status_code == 200
    assert {
        (row["actor_id"], row["role"])
        for row in admin_memberships.payload["memberships"]
    } == {
        ("human:admin", "project_admin"),
        ("human:viewer", "project_viewer"),
        ("human:contributor", "project_contributor"),
    }

    viewer_create_denied = viewer.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/workflow-runs",
        payload={
            "workflow_run_id": "wr-viewer-denied-api",
            "workflow_id": "capex.intake.v1",
            "workflow_version": "v1",
            "partition_key": "CAPEX-API-001",
            "logical_date": "2026-06-04",
            "activation_key": "api-viewer-denied",
        },
    )
    assert viewer_create_denied.status_code == 403
    assert viewer_create_denied.payload["error"]["code"] == "capex_project_access_forbidden"

    project_run = contributor.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/workflow-runs",
        payload={
            "workflow_run_id": "wr-project-api",
            "workflow_id": "capex.intake.v1",
            "workflow_version": "v1",
            "partition_key": "CAPEX-API-001",
            "logical_date": "2026-06-04",
            "activation_key": "api-project-run",
            "idempotency_key": "api:capex-project:create-workflow-run",
        },
    )
    assert project_run.status_code == 200
    assert project_run.payload["workflow_run"]["project_id"] == PROJECT_ID

    _create_no_project_run(db_url)

    outsider_project_run = outsider.get("/api/v1/workflow-runs/wr-project-api")
    assert outsider_project_run.status_code == 404
    assert outsider_project_run.payload["error"]["code"] == "workflow_run_not_found"

    viewer_project_run = viewer.get("/api/v1/workflow-runs/wr-project-api")
    assert viewer_project_run.status_code == 200
    assert viewer_project_run.payload["workflow_run"]["project_id"] == PROJECT_ID

    outsider_runs = outsider.get("/api/v1/workflow-runs")
    assert outsider_runs.status_code == 200
    assert [row["workflow_run_id"] for row in outsider_runs.payload["workflow_runs"]] == [
        "wr-no-project-api"
    ]

    viewer_project_runs = viewer.get(
        "/api/v1/workflow-runs",
        query={"project_id": PROJECT_ID},
    )
    assert viewer_project_runs.status_code == 200
    assert [row["workflow_run_id"] for row in viewer_project_runs.payload["workflow_runs"]] == [
        "wr-project-api"
    ]

    outsider_projects = outsider.get("/api/v1/capex/projects")
    assert outsider_projects.status_code == 200
    assert outsider_projects.payload["projects"] == []

    viewer_projects = viewer.get("/api/v1/capex/projects")
    assert viewer_projects.status_code == 200
    assert [row["project_id"] for row in viewer_projects.payload["projects"]] == [PROJECT_ID]

    outsider_timeline = outsider.get("/api/v1/timeline-events")
    assert outsider_timeline.status_code == 200
    assert [event["payload"]["workflow_id"] for event in outsider_timeline.payload["events"]] == [
        "capex.reference.v1"
    ]

    admin_timeline = admin.get("/api/v1/timeline-events")
    assert admin_timeline.status_code == 200
    event_types = {event["event_type"] for event in admin_timeline.payload["events"]}
    assert {
        "capex.project.created",
        "capex.project_membership.granted",
        "workflow.run.created",
    } <= event_types


def test_capex_project_membership_revoke_api_fails_closed_without_refresh_gap(
    tmp_path: Path,
) -> None:
    db_url = _init_db(tmp_path / "capex-project-revoke-api.db")
    admin = _client(db_url, "human:admin")
    viewer = _client(db_url, "human:viewer")
    outsider = _client(db_url, "human:outsider")

    created = admin.post(
        "/api/v1/capex/projects",
        payload={
            "project_id": PROJECT_ID,
            "project_key": "CAPEX-REVOKE-001",
            "name": "Revoke project",
            "idempotency_key": "api:capex-project-revoke:create",
        },
    )
    assert created.status_code == 200
    admin_membership_id = created.payload["admin_membership"]["project_membership_id"]

    grant_viewer = admin.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/memberships",
        payload={
            "actor_id": "human:viewer",
            "actor_type": "human",
            "role": "project_viewer",
            "idempotency_key": "api:capex-project-revoke:grant-viewer",
        },
    )
    assert grant_viewer.status_code == 200
    viewer_membership_id = grant_viewer.payload["membership"]["project_membership_id"]

    viewer_detail = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}")
    assert viewer_detail.status_code == 200

    viewer_revoke_denied = viewer.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/memberships/{viewer_membership_id}/revoke",
        payload={"idempotency_key": "api:capex-project-revoke:viewer-denied"},
    )
    assert viewer_revoke_denied.status_code == 403
    assert viewer_revoke_denied.payload["error"]["code"] == "capex_project_access_forbidden"

    outsider_revoke_hidden = outsider.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/memberships/{admin_membership_id}/revoke",
        payload={"idempotency_key": "api:capex-project-revoke:outsider-hidden"},
    )
    assert outsider_revoke_hidden.status_code == 404
    assert outsider_revoke_hidden.payload["error"]["code"] == "capex_project_not_found"

    revoked = admin.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/memberships/{viewer_membership_id}/revoke",
        payload={"idempotency_key": "api:capex-project-revoke:revoke-viewer"},
    )
    replay = admin.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/memberships/{viewer_membership_id}/revoke",
        payload={"idempotency_key": "api:capex-project-revoke:revoke-viewer"},
    )
    assert revoked.status_code == 200
    assert replay.status_code == 200
    assert revoked.payload["membership"]["state"] == "revoked"
    assert revoked.payload["idempotent_replay"] is False
    assert replay.payload["idempotent_replay"] is True

    hidden_detail = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}")
    assert hidden_detail.status_code == 404
    assert hidden_detail.payload["error"]["code"] == "capex_project_not_found"

    viewer_projects = viewer.get("/api/v1/capex/projects")
    assert viewer_projects.status_code == 200
    assert viewer_projects.payload["projects"] == []

    project_run = admin.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/workflow-runs",
        payload={
            "workflow_run_id": "wr-revoked-hidden-api",
            "workflow_id": "capex.intake.v1",
            "workflow_version": "v1",
            "partition_key": "CAPEX-REVOKE-001",
            "logical_date": "2026-06-04",
            "activation_key": "api-revoked-hidden",
            "idempotency_key": "api:capex-project-revoke:create-workflow-run",
        },
    )
    assert project_run.status_code == 200

    hidden_run = viewer.get("/api/v1/workflow-runs/wr-revoked-hidden-api")
    assert hidden_run.status_code == 404
    assert hidden_run.payload["error"]["code"] == "workflow_run_not_found"
