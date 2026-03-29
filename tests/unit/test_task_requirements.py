from __future__ import annotations

import sqlite3

from onetruth.application.handlers.artifacts import create_artifact_version_command
from onetruth.application.handlers.human_tasks import REVIEW_CONFIRMATION_ARTIFACT_KIND
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


def _task_payload(
    workflow_run_id: str,
    *,
    task_run_id: str = "tr-weekly-stage05-info",
    human_task_id: str = "ht-weekly-stage05-info",
    stage_id: str = "Stage05",
    task_kind: str = "information_request",
    activation_key: str = "weekly-stage05-information-request",
) -> dict[str, object]:
    return {
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "stage_id": stage_id,
        "task_kind": task_kind,
        "activation_key": activation_key,
        "create_human_task": True,
        "candidate_roles": ["schedule_planner"],
        "owner_role": "schedule_planner",
        "idempotency_key": f"idem:tasks.create:{human_task_id}",
    }


def _artifact_payload(
    workflow_run_id: str,
    *,
    artifact_version_id: str,
    artifact_kind: str = "planning.draft_weekly_schedule.workbook",
    artifact_role: str = "official_input",
    metadata_json: dict[str, object] | None = None,
    links: list[dict[str, str]] | None = None,
    relation_kind: str,
    subject_id: str = "ht-weekly-stage05-info",
) -> dict[str, object]:
    return {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "artifact_kind": artifact_kind,
        "artifact_role": artifact_role,
        "media_type": "application/json",
        "storage_uri": f"file:///tmp/{artifact_version_id}.json",
        "content_digest": f"sha256:{artifact_version_id}",
        "byte_size": 128,
        "metadata_json": metadata_json or {"fixture": artifact_version_id},
        "links": (
            links
            if links is not None
            else [
                {
                    "subject_kind": "human_task",
                    "subject_id": subject_id,
                    "relation_kind": relation_kind,
                }
            ]
        ),
        "idempotency_key": f"idem:artifacts.create:{artifact_version_id}",
        "actor_id": "system:runtime",
        "actor_type": "system",
    }


def _requirement_state(
    connection: sqlite3.Connection,
    workflow_run_id: str,
    *,
    human_task_id: str = "ht-weekly-stage05-info",
    stage_id: str = "Stage05",
    task_kind: str = "information_request",
) -> dict[str, object]:
    index = build_human_task_requirement_index(
        connection,
        workflow_run_id=workflow_run_id,
        human_tasks=[
            {
                "human_task_id": human_task_id,
                "stage_id": stage_id,
                "task_kind": task_kind,
            }
        ],
    )
    return index[human_task_id]


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


def test_weekly_stage04_input_intake_requirements_expose_artifact_roles() -> None:
    connection = _connection()
    workflow_run_id = "wr-weekly-stage04-intake"
    human_task_id = "ht-weekly-stage04-intake"
    create_workflow_run_command(connection, _workflow_payload(workflow_run_id))
    create_task_run_command(
        connection,
        _task_payload(
            workflow_run_id,
            task_run_id="tr-weekly-stage04-intake",
            human_task_id=human_task_id,
            stage_id="Stage04",
            task_kind="weekly_input_intake",
            activation_key="weekly-stage04-input-intake",
        ),
    )

    state = _requirement_state(
        connection,
        workflow_run_id,
        human_task_id=human_task_id,
        stage_id="Stage04",
        task_kind="weekly_input_intake",
    )

    assert state["missing_required_inputs"] == [
        "planning.route_slot_requirements.workbook",
        "planning.approved_availability.workbook",
        "planning.driver_capabilities.workbook",
    ]
    assert state["blocking_reason_codes"] == [
        "required_upload_missing:planning.route_slot_requirements.workbook",
        "required_upload_missing:planning.approved_availability.workbook",
        "required_upload_missing:planning.driver_capabilities.workbook",
    ]
    assert state["required_reviews"] == []
    assert state["required_uploads"] == [
        {
            "dataset_key": "planning.route_slot_requirements.workbook",
            "template_id": None,
            "artifact_kind": "planning.route_slot_requirements.workbook",
            "artifact_role": "official_input",
            "required": True,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "missing",
        },
        {
            "dataset_key": "planning.approved_availability.workbook",
            "template_id": None,
            "artifact_kind": "planning.approved_availability.workbook",
            "artifact_role": "official_input",
            "required": True,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "missing",
        },
        {
            "dataset_key": "planning.driver_capabilities.workbook",
            "template_id": None,
            "artifact_kind": "planning.driver_capabilities.workbook",
            "artifact_role": "official_input",
            "required": True,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "missing",
        },
        {
            "dataset_key": "planning.actual_hours_snapshot.workbook",
            "template_id": None,
            "artifact_kind": "planning.actual_hours_snapshot.workbook",
            "artifact_role": "official_input",
            "required": False,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "optional",
        },
        {
            "dataset_key": "planning.route_horizon.doc",
            "template_id": None,
            "artifact_kind": "planning.route_horizon.doc",
            "artifact_role": "evidence",
            "required": False,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "optional",
        },
        {
            "dataset_key": "planning.route_horizon.workbook",
            "template_id": None,
            "artifact_kind": "planning.route_horizon.workbook",
            "artifact_role": "evidence",
            "required": False,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "optional",
        },
    ]


def test_weekly_stage04_work_item_requires_latest_draft_artifact() -> None:
    connection = _connection()
    workflow_run_id = "wr-weekly-stage04-build"
    human_task_id = "ht-weekly-stage04-build"
    create_workflow_run_command(connection, _workflow_payload(workflow_run_id))
    create_task_run_command(
        connection,
        _task_payload(
            workflow_run_id,
            task_run_id="tr-weekly-stage04-build",
            human_task_id=human_task_id,
            stage_id="Stage04",
            task_kind="work_item",
            activation_key="weekly-stage04-build",
        ),
    )

    initial_state = _requirement_state(
        connection,
        workflow_run_id,
        human_task_id=human_task_id,
        stage_id="Stage04",
        task_kind="work_item",
    )
    assert initial_state["required_uploads"] == []
    assert initial_state["required_reviews"] == []
    assert initial_state["missing_required_inputs"] == ["planning.draft_weekly_schedule.workbook"]
    assert initial_state["blocking_reason_codes"] == [
        "required_artifact_missing:planning.draft_weekly_schedule.workbook"
    ]

    create_artifact_version_command(
        connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-weekly-stage04-draft",
            relation_kind="draft",
            links=[],
        ),
    )
    ready_state = _requirement_state(
        connection,
        workflow_run_id,
        human_task_id=human_task_id,
        stage_id="Stage04",
        task_kind="work_item",
    )
    assert ready_state["required_uploads"] == []
    assert ready_state["required_reviews"] == []
    assert ready_state["missing_required_inputs"] == []
    assert ready_state["blocking_reason_codes"] == []


def test_weekly_stage05_final_review_requires_manager_review_and_latest_review_confirmation() -> None:
    connection = _connection()
    workflow_run_id = "wr-weekly-stage05-final-review"
    human_task_id = "ht-weekly-stage05-final-review"
    task_run_id = "tr-weekly-stage05-final-review"
    create_workflow_run_command(connection, _workflow_payload(workflow_run_id))
    create_task_run_command(
        connection,
        _task_payload(
            workflow_run_id,
            task_run_id=task_run_id,
            human_task_id=human_task_id,
            stage_id="Stage05",
            task_kind="final_review",
            activation_key="weekly-stage05-final-review",
        ),
    )

    initial_state = _requirement_state(
        connection,
        workflow_run_id,
        human_task_id=human_task_id,
        stage_id="Stage05",
        task_kind="final_review",
    )
    assert initial_state["required_reviews"] == []
    assert initial_state["missing_required_inputs"] == [
        "planning.manager_review.doc",
        "planning.draft_weekly_schedule.workbook",
    ]
    assert initial_state["blocking_reason_codes"] == [
        "required_upload_missing:planning.manager_review.doc",
        "required_artifact_missing:planning.draft_weekly_schedule.workbook",
    ]

    create_artifact_version_command(
        connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-weekly-stage05-draft",
            relation_kind="draft",
            links=[],
        ),
    )
    draft_state = _requirement_state(
        connection,
        workflow_run_id,
        human_task_id=human_task_id,
        stage_id="Stage05",
        task_kind="final_review",
    )
    assert draft_state["required_uploads"] == [
        {
            "dataset_key": "planning.manager_review.doc",
            "template_id": None,
            "artifact_kind": "planning.manager_review.doc",
            "artifact_role": "evidence",
            "required": True,
            "required_count": 1,
            "current_count": 0,
            "linked_count": 0,
            "status": "missing",
        }
    ]
    assert draft_state["required_reviews"] == [
        {
            "dataset_key": "planning.draft_weekly_schedule.workbook",
            "artifact_kind": "planning.draft_weekly_schedule.workbook",
            "required_count": 1,
            "reviewed_artifact_version_id": "av-weekly-stage05-draft",
            "review_confirmation_artifact_version_id": None,
            "status": "pending_confirmation",
        }
    ]
    assert draft_state["missing_required_inputs"] == [
        "planning.manager_review.doc",
        "planning.draft_weekly_schedule.workbook",
    ]
    assert draft_state["blocking_reason_codes"] == [
        "required_upload_missing:planning.manager_review.doc",
        "required_review_confirmation_missing:planning.draft_weekly_schedule.workbook",
    ]

    create_artifact_version_command(
        connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-weekly-stage05-manager-review",
            artifact_kind="planning.manager_review.doc",
            artifact_role="evidence",
            relation_kind="attachment",
            links=[
                {
                    "subject_kind": "human_task",
                    "subject_id": human_task_id,
                    "relation_kind": "attachment",
                }
            ],
        ),
    )
    uploaded_state = _requirement_state(
        connection,
        workflow_run_id,
        human_task_id=human_task_id,
        stage_id="Stage05",
        task_kind="final_review",
    )
    assert uploaded_state["missing_required_inputs"] == ["planning.draft_weekly_schedule.workbook"]
    assert uploaded_state["blocking_reason_codes"] == [
        "required_review_confirmation_missing:planning.draft_weekly_schedule.workbook"
    ]

    create_artifact_version_command(
        connection,
        _artifact_payload(
            workflow_run_id,
            artifact_version_id="av-weekly-stage05-review-confirmed",
            artifact_kind=REVIEW_CONFIRMATION_ARTIFACT_KIND,
            artifact_role="review_evidence",
            metadata_json={
                "human_task_id": human_task_id,
                "task_run_id": task_run_id,
                "workflow_run_id": workflow_run_id,
                "reviewed_artifact_version_ids": ["av-weekly-stage05-draft"],
            },
            relation_kind="review_confirmation",
            links=[
                {
                    "subject_kind": "human_task",
                    "subject_id": human_task_id,
                    "relation_kind": "review_confirmation",
                }
            ],
        ),
    )
    confirmed_state = _requirement_state(
        connection,
        workflow_run_id,
        human_task_id=human_task_id,
        stage_id="Stage05",
        task_kind="final_review",
    )
    assert confirmed_state["required_reviews"] == [
        {
            "dataset_key": "planning.draft_weekly_schedule.workbook",
            "artifact_kind": "planning.draft_weekly_schedule.workbook",
            "required_count": 1,
            "reviewed_artifact_version_id": "av-weekly-stage05-draft",
            "review_confirmation_artifact_version_id": "av-weekly-stage05-review-confirmed",
            "status": "confirmed",
        }
    ]
    assert confirmed_state["missing_required_inputs"] == []
    assert confirmed_state["blocking_reason_codes"] == []
