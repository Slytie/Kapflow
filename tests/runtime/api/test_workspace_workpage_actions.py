from __future__ import annotations

from pathlib import Path

from tests.runtime.helpers.runtime_api import RuntimeApiClient
from tests.runtime.helpers.workpage_runs import (
    seed_dispatch_workspace_stage04_approval_with_draft,
    seed_dispatch_workspace_stage04_approval_without_draft,
    seed_dispatch_workspace_stage04_review_task_with_draft,
    seed_weekly_workspace_stage04_task_surface_without_draft,
    seed_weekly_workspace_supported_task_surface_with_draft,
)


def _client(
    *,
    db_url: str,
    actor_id: str,
    actor_roles: list[str],
) -> RuntimeApiClient:
    return RuntimeApiClient(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def _workspace_item(payload: dict[str, object], *, subject_kind: str, subject_id: str) -> dict[str, object]:
    for key in ("user_work", "blocking_work"):
        items = payload.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("subject_kind") == subject_kind and item.get("subject_id") == subject_id:
                return item
    raise AssertionError(f"workspace item not found: {subject_kind}:{subject_id}")


def test_weekly_workspace_supported_surface_projects_available_schedule_action(
    tmp_path: Path,
) -> None:
    db_url = f"sqlite:///{tmp_path / 'workspace_schedule_action_available.db'}"
    seeded = seed_weekly_workspace_supported_task_surface_with_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="test:workspace-schedule-action-available",
    )
    human_task_id = str(seeded["workspace_surface"]["human_task"]["human_task_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])

    response = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-1",
        actor_roles=["schedule_planner"],
    ).get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace")
    assert response.status_code == 200

    item = _workspace_item(
        response.payload,
        subject_kind="human_task",
        subject_id=human_task_id,
    )
    assert item["workpage_actions"] == [
        {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "label": "Open schedule draft",
            "presentation": "open_route",
            "state": "available",
            "route": (
                f"/runs/{seeded['workflow_run_id']}/workpages/schedule-v0/artifacts/"
                f"{artifact_version_id}"
            ),
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "link_policy": {
                "create_relation_kind": None,
                "submit_relation_kind": "response",
            },
            "disabled_reason": None,
        }
    ]


def test_human_task_detail_projects_available_schedule_action(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'task_detail_schedule_action_available.db'}"
    seeded = seed_weekly_workspace_supported_task_surface_with_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="test:task-detail-schedule-action-available",
    )
    human_task_id = str(seeded["workspace_surface"]["human_task"]["human_task_id"])
    artifact_version_id = str(seeded["stage04_outputs"]["draft_workbook"]["artifact_version_id"])

    response = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-1",
        actor_roles=["schedule_planner"],
    ).get(f"/api/v1/human-tasks/{human_task_id}")
    assert response.status_code == 200

    assert response.payload["human_task"]["workpage_actions"] == [
        {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "label": "Open schedule draft",
            "presentation": "open_route",
            "state": "available",
            "route": (
                f"/runs/{seeded['workflow_run_id']}/workpages/schedule-v0/artifacts/"
                f"{artifact_version_id}"
            ),
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "link_policy": {
                "create_relation_kind": None,
                "submit_relation_kind": "response",
            },
            "disabled_reason": None,
        }
    ]


def test_weekly_stage04_surface_projects_unavailable_schedule_action(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'workspace_schedule_action_unavailable.db'}"
    seeded = seed_weekly_workspace_stage04_task_surface_without_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="test:workspace-schedule-action-unavailable",
    )
    human_task_id = str(seeded["workspace_surface"]["human_task"]["human_task_id"])

    response = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-2",
        actor_roles=["schedule_planner"],
    ).get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace")
    assert response.status_code == 200

    item = _workspace_item(
        response.payload,
        subject_kind="human_task",
        subject_id=human_task_id,
    )
    assert item["workpage_actions"] == [
        {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "label": "Open schedule draft",
            "presentation": "open_route",
            "state": "unavailable",
            "route": None,
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "link_policy": {
                "create_relation_kind": None,
                "submit_relation_kind": "response",
            },
            "disabled_reason": "schedule_draft_unavailable",
        }
    ]


def test_human_task_detail_projects_unavailable_schedule_action(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'task_detail_schedule_action_unavailable.db'}"
    seeded = seed_weekly_workspace_stage04_task_surface_without_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="test:task-detail-schedule-action-unavailable",
    )
    human_task_id = str(seeded["workspace_surface"]["human_task"]["human_task_id"])

    response = _client(
        db_url=db_url,
        actor_id="human:schedule-planner-2",
        actor_roles=["schedule_planner"],
    ).get(f"/api/v1/human-tasks/{human_task_id}")
    assert response.status_code == 200

    assert response.payload["human_task"]["workpage_actions"] == [
        {
            "action_id": "workpage.schedule-v0.open_latest_draft",
            "workpage_kind": "schedule-v0",
            "label": "Open schedule draft",
            "presentation": "open_route",
            "state": "unavailable",
            "route": None,
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "link_policy": {
                "create_relation_kind": None,
                "submit_relation_kind": "response",
            },
            "disabled_reason": "schedule_draft_unavailable",
        }
    ]


def test_dispatch_stage04_approval_projects_create_draft_action(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'workspace_eod_action_create.db'}"
    seeded = seed_dispatch_workspace_stage04_approval_without_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="test:workspace-eod-action-create",
    )
    approval_id = str(seeded["workspace_surface"]["approval"]["approval_id"])

    response = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-1",
        actor_roles=["dispatch_supervisor"],
    ).get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace")
    assert response.status_code == 200

    item = _workspace_item(
        response.payload,
        subject_kind="approval",
        subject_id=approval_id,
    )
    assert item["workpage_actions"] == [
        {
            "action_id": "workpage.eod-v0.create_draft",
            "workpage_kind": "eod-v0",
            "label": "Create EOD draft",
            "presentation": "create_draft_then_open",
            "state": "available",
            "route": None,
            "create_path": (
                f"/api/v1/workpages/workflow-runs/{seeded['workflow_run_id']}/eod-v0/drafts"
            ),
            "subject_context": {
                "subject_kind": "approval",
                "subject_id": approval_id,
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "link_policy": {
                "create_relation_kind": "draft",
                "submit_relation_kind": "response",
            },
            "disabled_reason": None,
        }
    ]


def test_dispatch_stage04_approval_projects_open_latest_draft_action(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'workspace_eod_action_open.db'}"
    seeded = seed_dispatch_workspace_stage04_approval_with_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="test:workspace-eod-action-open",
    )
    approval_id = str(seeded["workspace_surface"]["approval"]["approval_id"])
    artifact_version_id = str(seeded["draft"]["draft"]["artifact_version_id"])

    response = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-2",
        actor_roles=["dispatch_supervisor"],
    ).get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace")
    assert response.status_code == 200

    item = _workspace_item(
        response.payload,
        subject_kind="approval",
        subject_id=approval_id,
    )
    assert item["workpage_actions"] == [
        {
            "action_id": "workpage.eod-v0.open_latest_draft",
            "workpage_kind": "eod-v0",
            "label": "Open EOD draft",
            "presentation": "open_route",
            "state": "available",
            "route": (
                f"/runs/{seeded['workflow_run_id']}/workpages/eod-v0/artifacts/{artifact_version_id}"
            ),
            "create_path": None,
            "subject_context": {
                "subject_kind": "approval",
                "subject_id": approval_id,
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "link_policy": {
                "create_relation_kind": "draft",
                "submit_relation_kind": "response",
            },
            "disabled_reason": None,
        }
    ]


def test_dispatch_stage04_review_task_projects_open_latest_draft_action(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'workspace_eod_review_task_open.db'}"
    seeded = seed_dispatch_workspace_stage04_review_task_with_draft(
        db_url=db_url,
        tenant_id="tenant-a",
        domain_id="domain-x",
        run_tag="test:workspace-eod-review-task-open",
    )
    human_task_id = str(seeded["workspace_surface"]["human_task"]["human_task_id"])
    artifact_version_id = str(seeded["draft"]["draft"]["artifact_version_id"])

    response = _client(
        db_url=db_url,
        actor_id="human:dispatch-supervisor-3",
        actor_roles=["dispatch_supervisor"],
    ).get(f"/api/v1/workflow-runs/{seeded['workflow_run_id']}/workspace")
    assert response.status_code == 200

    item = _workspace_item(
        response.payload,
        subject_kind="human_task",
        subject_id=human_task_id,
    )
    assert item["workpage_actions"] == [
        {
            "action_id": "workpage.eod-v0.open_latest_draft",
            "workpage_kind": "eod-v0",
            "label": "Open EOD draft",
            "presentation": "open_route",
            "state": "available",
            "route": (
                f"/runs/{seeded['workflow_run_id']}/workpages/eod-v0/artifacts/{artifact_version_id}"
            ),
            "create_path": None,
            "subject_context": {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
                "workflow_run_id": seeded["workflow_run_id"],
            },
            "link_policy": {
                "create_relation_kind": "draft",
                "submit_relation_kind": "response",
            },
            "disabled_reason": None,
        }
    ]
