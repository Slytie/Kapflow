from __future__ import annotations

import sqlite3

from onetruth.application.handlers.artifacts import create_artifact_version_command
from onetruth.application.handlers.workflow_task_lifecycle import (
    create_task_run_command,
    create_workflow_run_command,
)
from onetruth.application.services.task_requirements import (
    build_human_task_requirement_index,
)
from onetruth.infrastructure.events.event_store import create_sqlite_substrate


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    create_sqlite_substrate(connection)
    return connection


def _workflow_payload(workflow_run_id: str) -> dict[str, str]:
    return {
        "workflow_run_id": workflow_run_id,
        "workflow_id": "weekly_schedule_planning.v1",
        "workflow_version": "v1",
        "tenant_id": "tenant-a",
        "domain_id": "domain-x",
        "partition_key": "PW-2026-W13",
        "logical_date": "2026-03-22",
        "activation_key": "weekly-stage05-info",
        "idempotency_key": f"idem:runs.create:{workflow_run_id}",
    }


def _task_payload(workflow_run_id: str) -> dict[str, object]:
    return {
        "workflow_run_id": workflow_run_id,
        "task_run_id": "tr-weekly-stage05-info",
        "human_task_id": "ht-weekly-stage05-info",
        "stage_id": "Stage05",
        "task_kind": "information_request",
        "activation_key": "weekly-stage05-information-request",
        "create_human_task": True,
        "candidate_roles": ["schedule_planner"],
        "owner_role": "schedule_planner",
        "idempotency_key": "idem:tasks.create:ht-weekly-stage05-info",
    }


def _artifact_payload(
    workflow_run_id: str,
    *,
    artifact_version_id: str,
    relation_kind: str,
) -> dict[str, object]:
    return {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "artifact_kind": "planning.draft_weekly_schedule.workbook",
        "artifact_role": "official_input",
        "media_type": "application/json",
        "storage_uri": f"file:///tmp/{artifact_version_id}.json",
        "content_digest": f"sha256:{artifact_version_id}",
        "byte_size": 128,
        "metadata_json": {"fixture": artifact_version_id},
        "links": [
            {
                "subject_kind": "human_task",
                "subject_id": "ht-weekly-stage05-info",
                "relation_kind": relation_kind,
            }
        ],
        "idempotency_key": f"idem:artifacts.create:{artifact_version_id}",
        "actor_id": "system:runtime",
        "actor_type": "system",
    }


def _requirement_state(connection: sqlite3.Connection, workflow_run_id: str) -> dict[str, object]:
    index = build_human_task_requirement_index(
        connection,
        workflow_run_id=workflow_run_id,
        human_tasks=[
            {
                "human_task_id": "ht-weekly-stage05-info",
                "stage_id": "Stage05",
                "task_kind": "information_request",
            }
        ],
    )
    return index["ht-weekly-stage05-info"]


def test_weekly_stage05_information_request_counts_only_response_links() -> None:
    connection = _connection()
    workflow_run_id = "wr-weekly-stage05-info"
    create_workflow_run_command(connection, _workflow_payload(workflow_run_id))
    create_task_run_command(connection, _task_payload(workflow_run_id))

    initial_state = _requirement_state(connection, workflow_run_id)
    initial_upload = initial_state["required_uploads"][0]
    assert initial_upload["dataset_key"] == "planning.draft_weekly_schedule.workbook"
    assert initial_upload["linked_count"] == 0
    assert initial_upload["current_count"] == 0
    assert initial_upload["status"] == "missing"
    assert initial_state["missing_required_inputs"] == ["planning.draft_weekly_schedule.workbook"]

    create_artifact_version_command(
        connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-weekly-stage05-draft",
            relation_kind="draft",
        ),
    )
    draft_state = _requirement_state(connection, workflow_run_id)
    draft_upload = draft_state["required_uploads"][0]
    assert draft_upload["linked_count"] == 1
    assert draft_upload["current_count"] == 0
    assert draft_upload["status"] == "missing"
    assert draft_state["missing_required_inputs"] == ["planning.draft_weekly_schedule.workbook"]

    create_artifact_version_command(
        connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-weekly-stage05-attachment",
            relation_kind="attachment",
        ),
    )
    attachment_state = _requirement_state(connection, workflow_run_id)
    attachment_upload = attachment_state["required_uploads"][0]
    assert attachment_upload["linked_count"] == 2
    assert attachment_upload["current_count"] == 0
    assert attachment_upload["status"] == "missing"
    assert attachment_state["missing_required_inputs"] == ["planning.draft_weekly_schedule.workbook"]

    create_artifact_version_command(
        connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-weekly-stage05-response",
            relation_kind="response",
        ),
    )
    response_state = _requirement_state(connection, workflow_run_id)
    response_upload = response_state["required_uploads"][0]
    assert response_upload["linked_count"] == 3
    assert response_upload["current_count"] == 1
    assert response_upload["status"] == "satisfied"
    assert response_state["missing_required_inputs"] == []
    assert response_state["blocking_reason_codes"] == []
