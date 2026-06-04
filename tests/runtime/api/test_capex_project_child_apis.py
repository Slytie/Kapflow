from __future__ import annotations

import base64
from pathlib import Path
import sqlite3
from urllib.parse import quote

from onetruth.application.handlers.approvals import request_approval_command
from onetruth.application.handlers.artifacts import ingest_artifact_document_command
from onetruth.application.handlers.capex_projects import (
    create_capex_project_command,
    grant_project_membership_command,
)
from onetruth.application.handlers.flags import create_flag_command
from onetruth.application.handlers.pointers import promote_pointer_command
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_task_run_command,
    create_workflow_run_command,
)
from onetruth.infrastructure.artifacts.storage import default_storage_root_for_db_url
from onetruth.infrastructure.events.event_store import create_sqlite_substrate
from tests.runtime.helpers.runtime_api import RuntimeApiClient

TENANT_ID = "tenant-a"
DOMAIN_ID = "domain-x"
PROJECT_ID = "cp-child-001"
OTHER_PROJECT_ID = "cp-child-002"
WORKFLOW_RUN_ID = "wr-project-child-001"
TASK_RUN_ID = "tr-project-child-001"
HUMAN_TASK_ID = "ht-project-child-001"
APPROVAL_ID = "ap-project-child-001"
FLAG_ID = "fl-project-child-001"
ARTIFACT_VERSION_ID = "av-project-child-001"
ARTIFACT_KIND = "schedule.published_schedule.workbook"
ARTIFACT_CONTENT = b'{"project_child":true}'


def _init_db(path: Path) -> str:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    try:
        create_sqlite_substrate(connection)
    finally:
        connection.close()
    return f"sqlite:///{path}"


def _open(db_url: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_url.removeprefix("sqlite:///"))
    connection.row_factory = sqlite3.Row
    return connection


def _client(
    db_url: str,
    actor_id: str,
    *,
    roles: list[str] | None = None,
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id=TENANT_ID,
        domain_id=DOMAIN_ID,
        actor_id=actor_id,
        actor_type="human",
        actor_roles=roles or ["reviewer", "approver", "operations_manager", "capex_user"],
    )


def _seed_project_child_state(db_url: str) -> str:
    connection = _open(db_url)
    try:
        for project_id, project_key in [
            (PROJECT_ID, "CAPEX-CHILD-001"),
            (OTHER_PROJECT_ID, "CAPEX-CHILD-002"),
        ]:
            create_capex_project_command(
                connection,
                {
                    "project_id": project_id,
                    "tenant_id": TENANT_ID,
                    "domain_id": DOMAIN_ID,
                    "project_key": project_key,
                    "name": f"{project_key} test project",
                    "actor_id": "human:admin",
                    "actor_type": "human",
                    "idempotency_key": f"tests:capex-child:{project_id}:create",
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
                    "idempotency_key": f"tests:capex-child:{project_id}:viewer",
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
                "activation_key": "project-child-run",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
        )
        create_task_run_command(
            connection,
            {
                "workflow_run_id": WORKFLOW_RUN_ID,
                "task_run_id": TASK_RUN_ID,
                "stage_id": "Stage01",
                "task_kind": "planning_feedback_review",
                "activation_key": "project-child-task",
                "create_human_task": True,
                "human_task_id": HUMAN_TASK_ID,
                "candidate_roles": ["reviewer"],
                "owner_role": "reviewer",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
        )
        request_approval_command(
            connection,
            {
                "approval_id": APPROVAL_ID,
                "workflow_run_id": WORKFLOW_RUN_ID,
                "task_run_id": TASK_RUN_ID,
                "approval_kind": "project_review",
                "scope_kind": "task_run",
                "scope_ref": TASK_RUN_ID,
                "candidate_roles": ["approver"],
                "required_role": "approver",
                "allowed_responses": ["approve", "reject"],
                "idempotency_key": "tests:capex-child:approval",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
        )
        create_flag_command(
            connection,
            {
                "flag_id": FLAG_ID,
                "workflow_run_id": WORKFLOW_RUN_ID,
                "kind": "project_gap",
                "severity": "high",
                "summary": "Project gap",
                "details_json": {"fixture": True},
                "assigned_group": "flag_resolver",
                "created_by": {"id": "human:admin", "type": "human"},
                "idempotency_key": "tests:capex-child:flag",
            },
        )
        artifact = ingest_artifact_document_command(
            connection,
            {
                "artifact_version_id": ARTIFACT_VERSION_ID,
                "workflow_run_id": WORKFLOW_RUN_ID,
                "task_run_id": TASK_RUN_ID,
                "artifact_kind": ARTIFACT_KIND,
                "artifact_role": "official_output",
                "content_base64": base64.b64encode(ARTIFACT_CONTENT).decode("ascii"),
                "file_name": "published.json",
                "media_type": "application/json",
                "canonical_partition_kind": "ScheduleDateID",
                "canonical_partition_key": "SD-2026-06-04",
                "links": [
                    {
                        "subject_kind": "workflow_run",
                        "subject_id": WORKFLOW_RUN_ID,
                        "relation_kind": "output",
                    }
                ],
                "idempotency_key": "tests:capex-child:artifact",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
            storage_root=default_storage_root_for_db_url(db_url),
            include_receipt=True,
        )["result"]["artifact_version"]
        promoted = promote_pointer_command(
            connection,
            {
                "workflow_run_id": WORKFLOW_RUN_ID,
                "scope_kind": "workflow_run",
                "scope_ref": WORKFLOW_RUN_ID,
                "pointer_key": f"official:{ARTIFACT_KIND}",
                "artifact_kind": ARTIFACT_KIND,
                "artifact_version_id": str(artifact["artifact_version_id"]),
                "promotion_reason": "project_child_test",
                "promoted_by_task_run_id": TASK_RUN_ID,
                "idempotency_key": "tests:capex-child:pointer",
                "actor_id": "human:admin",
                "actor_type": "human",
            },
            include_receipt=True,
        )["result"]
        connection.commit()
    finally:
        connection.close()
    return str(promoted["pointer_id"])


def test_capex_project_child_routes_scope_reads_and_delegate_mutations(tmp_path: Path) -> None:
    db_url = _init_db(tmp_path / "capex-project-child.db")
    pointer_id = _seed_project_child_state(db_url)
    viewer = _client(db_url, "human:viewer")
    outsider = _client(db_url, "human:outsider")

    dashboard = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.payload["dashboard"]
    assert body["project"]["project_id"] == PROJECT_ID
    assert body["caller_role"] == "project_viewer"
    assert body["counts"]["workflow_run_count"] == 1
    assert body["counts"]["open_human_task_count"] == 1
    assert body["counts"]["pending_approval_count"] == 1
    assert body["counts"]["active_flag_count"] == 1
    assert body["counts"]["artifact_version_count"] == 1
    assert body["counts"]["pointer_count"] == 1
    assert body["human_tasks"][0]["project_id"] == PROJECT_ID
    assert body["approvals"][0]["project_id"] == PROJECT_ID
    assert body["flags"][0]["project_id"] == PROJECT_ID
    assert body["artifact_versions"][0]["project_id"] == PROJECT_ID
    assert body["pointers"][0]["project_id"] == PROJECT_ID

    runs = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/workflow-runs")
    assert runs.status_code == 200
    assert runs.payload["command"] == "api.capex.projects.workflow_runs.list"
    assert [row["workflow_run_id"] for row in runs.payload["workflow_runs"]] == [
        WORKFLOW_RUN_ID
    ]
    assert runs.payload["workflow_runs"][0]["project_id"] == PROJECT_ID

    empty_other_project = viewer.get(f"/api/v1/capex/projects/{OTHER_PROJECT_ID}/workflow-runs")
    assert empty_other_project.status_code == 200
    assert empty_other_project.payload["workflow_runs"] == []

    mismatched_run = viewer.get(
        f"/api/v1/capex/projects/{OTHER_PROJECT_ID}/workflow-runs/{WORKFLOW_RUN_ID}"
    )
    assert mismatched_run.status_code == 404
    assert mismatched_run.payload["error"]["code"] == "workflow_run_not_found"

    workspace = viewer.get(
        f"/api/v1/capex/projects/{PROJECT_ID}/workflow-runs/{WORKFLOW_RUN_ID}/workspace"
    )
    assert workspace.status_code == 200
    assert workspace.payload["command"] == "api.capex.projects.workflow_runs.workspace"
    assert workspace.payload["workflow_run"]["project_id"] == PROJECT_ID

    timeline = viewer.get(
        f"/api/v1/capex/projects/{PROJECT_ID}/workflow-runs/{WORKFLOW_RUN_ID}/timeline"
    )
    assert timeline.status_code == 200
    assert timeline.payload["command"] == "api.capex.projects.workflow_runs.timeline"
    assert timeline.payload["events"]

    tasks = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/human-tasks")
    approvals = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/approvals")
    flags = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/flags")
    artifacts = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/artifacts")
    pointers = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/pointers")
    project_events = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/timeline-events")
    assert [row["human_task_id"] for row in tasks.payload["human_tasks"]] == [
        HUMAN_TASK_ID
    ]
    assert tasks.payload["human_tasks"][0]["project_id"] == PROJECT_ID
    assert [row["approval_id"] for row in approvals.payload["approvals"]] == [
        APPROVAL_ID
    ]
    assert approvals.payload["approvals"][0]["project_id"] == PROJECT_ID
    assert [row["flag_id"] for row in flags.payload["flags"]] == [FLAG_ID]
    assert flags.payload["flags"][0]["project_id"] == PROJECT_ID
    assert [row["artifact_version_id"] for row in artifacts.payload["artifact_versions"]] == [
        ARTIFACT_VERSION_ID
    ]
    assert artifacts.payload["artifact_versions"][0]["project_id"] == PROJECT_ID
    assert [row["pointer_id"] for row in pointers.payload["pointers"]] == [pointer_id]
    assert pointers.payload["pointers"][0]["project_id"] == PROJECT_ID
    assert {event["event_type"] for event in project_events.payload["events"]} >= {
        "workflow.run.created",
        "task.created",
    }

    pointer_detail = viewer.get(
        f"/api/v1/capex/projects/{PROJECT_ID}/pointers/{quote(pointer_id, safe='')}"
    )
    assert pointer_detail.status_code == 200
    assert pointer_detail.payload["pointer"]["pointer_id"] == pointer_id

    claimed = viewer.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/human-tasks/{HUMAN_TASK_ID}/claim",
        payload={
            "lease_seconds": 300,
            "idempotency_key": "api:capex-child:claim",
        },
    )
    assert claimed.status_code == 200
    assert claimed.payload["command"] == "api.capex.projects.human_tasks.claim"

    responded = viewer.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/approvals/{APPROVAL_ID}/respond",
        payload={
            "response_kind": "approve",
            "response_reason": "ready",
            "idempotency_key": "api:capex-child:approval-respond",
        },
    )
    assert responded.status_code == 200
    assert responded.payload["command"] == "api.capex.projects.approvals.respond"
    assert responded.payload["approval"]["response_kind"] == "approve"

    transitioned = viewer.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/flags/{FLAG_ID}/transition",
        payload={
            "to_state": "triage",
            "reason": "accepted",
            "idempotency_key": "api:capex-child:flag-transition",
        },
    )
    assert transitioned.status_code == 200
    assert transitioned.payload["command"] == "api.capex.projects.flags.transition"
    assert transitioned.payload["flag"]["state"] == "triage"

    uploaded = viewer.post(
        f"/api/v1/capex/projects/{PROJECT_ID}/workflow-runs/{WORKFLOW_RUN_ID}/artifacts/upload",
        payload={
            "artifact_kind": "schedule.supervisor_review.doc",
            "artifact_role": "evidence",
            "content_base64": base64.b64encode(b"review note").decode("ascii"),
            "file_name": "review.txt",
            "media_type": "text/plain",
            "idempotency_key": "api:capex-child:artifact-upload",
        },
    )
    assert uploaded.status_code == 200
    assert uploaded.payload["command"] == "api.capex.projects.workflow_runs.artifacts.upload"
    assert uploaded.payload["artifact_version"]["workflow_run_id"] == WORKFLOW_RUN_ID

    downloaded = viewer.get(f"/api/v1/capex/projects/{PROJECT_ID}/artifacts/{ARTIFACT_VERSION_ID}/download")
    assert downloaded.status_code == 200
    assert base64.b64decode(downloaded.payload["content_base64"]) == ARTIFACT_CONTENT

    binary = viewer.get_raw(
        f"/api/v1/capex/projects/{PROJECT_ID}/artifacts/{ARTIFACT_VERSION_ID}/download.bin"
    )
    assert binary.status_code == 200
    assert binary.body == ARTIFACT_CONTENT

    outsider_hidden = outsider.get(f"/api/v1/capex/projects/{PROJECT_ID}/human-tasks")
    assert outsider_hidden.status_code == 404
    assert outsider_hidden.payload["error"]["code"] == "capex_project_not_found"
