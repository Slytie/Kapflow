from __future__ import annotations

import json
import sqlite3
from typing import Any

from onetruth.application.services.template_registry import list_templates
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)

REVIEW_CONFIRMATION_ARTIFACT_KIND = "human_task.review_confirmation.json"

_REQUIRED_UPLOAD_DATASET_KEYS: dict[tuple[str, str], tuple[str, ...]] = {
    ("Stage05", "information_request"): ("schedule.draft_schedule.workbook",),
    ("Stage06", "information_request"): ("schedule.supervisor_review.doc",),
    ("Stage07", "exception_triage"): ("schedule.exception_board.doc",),
    ("Stage07", "information_request"): ("schedule.exception_board.doc",),
}

_REQUIRED_REVIEW_ARTIFACT_KINDS: dict[tuple[str, str], tuple[str, ...]] = {
    (
        "Stage06",
        "final_review",
    ): (
        "schedule.stage06.publish_packet",
        "schedule.published_schedule.workbook",
    ),
    (
        "Stage07",
        "final_review",
    ): (
        "schedule.stage07.replan_packet",
        "schedule.replan_delta.workbook",
    ),
}


def build_human_task_requirement_index(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    human_tasks: list[dict[str, Any]],
    artifact_versions: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    tasks_by_id = {
        str(task["human_task_id"]): task
        for task in human_tasks
        if task.get("human_task_id") is not None
    }
    if not tasks_by_id:
        return {}

    artifacts = (
        artifact_versions
        if artifact_versions is not None
        else list_artifact_versions_for_workflow_run(connection, workflow_run_id)
    )
    subject_kind_counts: dict[tuple[str, str], dict[str, int]] = {}
    link_rows = connection.execute(
        """
        SELECT
            al.subject_kind,
            al.subject_id,
            al.artifact_version_id,
            av.artifact_kind
        FROM artifact_links al
        JOIN artifact_versions av
            ON av.artifact_version_id = al.artifact_version_id
        WHERE al.workflow_run_id = ?
        """,
        (workflow_run_id,),
    ).fetchall()
    for row in link_rows:
        subject_key = (str(row["subject_kind"]), str(row["subject_id"]))
        artifact_kind = str(row["artifact_kind"])
        bucket = subject_kind_counts.setdefault(subject_key, {})
        bucket[artifact_kind] = bucket.get(artifact_kind, 0) + 1

    templates_by_dataset = {
        str(item["dataset_key"]): item
        for item in list_templates(
            workflow_id="schedule_planning.v1",
            variant="empty",
        )
    }
    latest_draft_by_kind = _latest_draft_artifacts_by_kind(artifacts)
    confirmed_reviews = _confirmed_reviews_by_human_task(artifacts)

    requirements: dict[str, dict[str, Any]] = {}
    for human_task_id, task in tasks_by_id.items():
        stage_id = str(task.get("stage_id") or "")
        task_kind = str(task.get("task_kind") or "")
        required_uploads: list[dict[str, Any]] = []
        required_reviews: list[dict[str, Any]] = []
        blocking_reasons: list[dict[str, Any]] = []
        blocking_reason_codes: list[str] = []
        missing_required_inputs: list[str] = []

        for dataset_key in _REQUIRED_UPLOAD_DATASET_KEYS.get((stage_id, task_kind), ()):
            template = templates_by_dataset.get(dataset_key)
            artifact_kind = (
                str(template["artifact_kind"]) if template is not None else dataset_key
            )
            linked_count = int(
                subject_kind_counts.get(("human_task", human_task_id), {}).get(
                    artifact_kind,
                    0,
                )
            )
            current_count = linked_count
            status = "satisfied" if current_count >= 1 else "missing"
            if status == "missing":
                blocking_reasons.append(
                    {
                        "code": "required_upload_missing",
                        "details": {"dataset_key": dataset_key},
                    }
                )
                blocking_reason_codes.append(f"required_upload_missing:{dataset_key}")
                missing_required_inputs.append(dataset_key)
            required_uploads.append(
                {
                    "dataset_key": dataset_key,
                    "template_id": (
                        str(template["template_id"]) if template is not None else None
                    ),
                    "artifact_kind": artifact_kind,
                    "required_count": 1,
                    "current_count": current_count,
                    "linked_count": linked_count,
                    "status": status,
                }
            )

        task_confirmed_reviews = confirmed_reviews.get(human_task_id, {})
        for artifact_kind in _REQUIRED_REVIEW_ARTIFACT_KINDS.get((stage_id, task_kind), ()):
            draft_artifact = latest_draft_by_kind.get(artifact_kind)
            if draft_artifact is None:
                # Review confirmation is required only for draft artifacts that
                # actually exist for this workflow run.
                continue
            reviewed_artifact_version_id = str(draft_artifact["artifact_version_id"])
            review_confirmation_artifact_version_id = task_confirmed_reviews.get(
                reviewed_artifact_version_id
            )
            if review_confirmation_artifact_version_id is not None:
                status = "confirmed"
            else:
                status = "pending_confirmation"
                blocking_reasons.append(
                    {
                        "code": "required_review_confirmation_missing",
                        "details": {"artifact_kind": artifact_kind},
                    }
                )
                blocking_reason_codes.append(
                    f"required_review_confirmation_missing:{artifact_kind}"
                )
                missing_required_inputs.append(artifact_kind)
            required_reviews.append(
                {
                    "dataset_key": artifact_kind,
                    "artifact_kind": artifact_kind,
                    "required_count": 1,
                    "reviewed_artifact_version_id": reviewed_artifact_version_id,
                    "review_confirmation_artifact_version_id": review_confirmation_artifact_version_id,
                    "status": status,
                }
            )

        requirements[human_task_id] = {
            "required_uploads": required_uploads,
            "required_reviews": required_reviews,
            "blocking_reasons": blocking_reasons,
            "blocking_reason_codes": blocking_reason_codes,
            "missing_required_inputs": missing_required_inputs,
        }
    return requirements


def task_has_unsatisfied_requirements(requirement_state: dict[str, Any]) -> bool:
    return bool(requirement_state.get("blocking_reason_codes"))


def _latest_draft_artifacts_by_kind(
    artifacts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_kind: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        artifact_kind = str(artifact.get("artifact_kind") or "")
        if not artifact_kind:
            continue
        if artifact_kind == REVIEW_CONFIRMATION_ARTIFACT_KIND:
            continue
        by_kind[artifact_kind] = artifact
    return by_kind


def _confirmed_reviews_by_human_task(
    artifacts: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    confirmed: dict[str, dict[str, str]] = {}
    for artifact in artifacts:
        if str(artifact.get("artifact_kind")) != REVIEW_CONFIRMATION_ARTIFACT_KIND:
            continue
        metadata = artifact.get("metadata_json")
        if not isinstance(metadata, dict):
            continue
        human_task_id = str(metadata.get("human_task_id") or "").strip()
        if not human_task_id:
            continue
        reviewed_ids = metadata.get("reviewed_artifact_version_ids")
        if not isinstance(reviewed_ids, list):
            continue
        bucket = confirmed.setdefault(human_task_id, {})
        for reviewed_id in reviewed_ids:
            raw = str(reviewed_id).strip()
            if not raw:
                continue
            bucket[raw] = str(artifact.get("artifact_version_id"))
    return confirmed
