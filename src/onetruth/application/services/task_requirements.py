from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.services.template_registry import list_templates
from onetruth.infrastructure.repositories.artifact_versions import (
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run

REVIEW_CONFIRMATION_ARTIFACT_KIND = "human_task.review_confirmation.json"

_REQUIRED_UPLOAD_SPECS: dict[tuple[str, str, str], tuple[dict[str, Any], ...]] = {
    (
        "schedule_planning.v1",
        "Stage05",
        "information_request",
    ): (
        {
            "dataset_key": "schedule.draft_schedule.workbook",
            "artifact_kind": "schedule.draft_schedule.workbook",
            "allowed_relation_kinds": ("attachment",),
            "template_workflow_id": "schedule_planning.v1",
            "template_variant": "empty",
        },
    ),
    (
        "schedule_planning.v1",
        "Stage06",
        "information_request",
    ): (
        {
            "dataset_key": "schedule.supervisor_review.doc",
            "artifact_kind": "schedule.supervisor_review.doc",
            "allowed_relation_kinds": ("attachment",),
        },
    ),
    (
        "schedule_planning.v1",
        "Stage07",
        "exception_triage",
    ): (
        {
            "dataset_key": "schedule.exception_board.doc",
            "artifact_kind": "schedule.exception_board.doc",
            "allowed_relation_kinds": ("attachment",),
        },
    ),
    (
        "schedule_planning.v1",
        "Stage07",
        "information_request",
    ): (
        {
            "dataset_key": "schedule.exception_board.doc",
            "artifact_kind": "schedule.exception_board.doc",
            "allowed_relation_kinds": ("attachment",),
        },
    ),
    (
        "weekly_schedule_planning.v1",
        "Stage05",
        "information_request",
    ): (
        {
            "dataset_key": "planning.draft_weekly_schedule.workbook",
            "artifact_kind": "planning.draft_weekly_schedule.workbook",
            "allowed_relation_kinds": ("response",),
        },
    ),
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
    workflow_run = get_workflow_run(connection, workflow_run_id)
    workflow_id = str(workflow_run.get("workflow_id") or "") if workflow_run is not None else ""
    subject_kind_counts: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    link_rows = connection.execute(
        """
        SELECT
            al.subject_kind,
            al.subject_id,
            al.artifact_version_id,
            al.relation_kind,
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
        relation_kind = str(row["relation_kind"] or "attachment")
        bucket = subject_kind_counts.setdefault(subject_key, {})
        artifact_bucket = bucket.setdefault(
            artifact_kind,
            {"linked_count": 0, "by_relation_kind": {}},
        )
        artifact_bucket["linked_count"] = int(artifact_bucket["linked_count"]) + 1
        by_relation_kind = artifact_bucket.setdefault("by_relation_kind", {})
        by_relation_kind[relation_kind] = int(by_relation_kind.get(relation_kind, 0)) + 1

    templates_by_scope = _load_template_indexes_by_scope()
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

        for spec in _REQUIRED_UPLOAD_SPECS.get((workflow_id, stage_id, task_kind), ()):
            dataset_key = str(spec["dataset_key"])
            artifact_kind = str(spec.get("artifact_kind") or dataset_key)
            template = _resolve_template_record(
                templates_by_scope,
                template_workflow_id=spec.get("template_workflow_id"),
                template_variant=spec.get("template_variant"),
                dataset_key=dataset_key,
            )
            artifact_link_counts = subject_kind_counts.get(("human_task", human_task_id), {}).get(
                artifact_kind,
                {},
            )
            linked_count = int(artifact_link_counts.get("linked_count", 0))
            current_count = _allowed_relation_kind_count(
                artifact_link_counts,
                allowed_relation_kinds=tuple(spec.get("allowed_relation_kinds") or ()),
            )
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


def _load_template_indexes_by_scope() -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    indexes: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for requirements in _REQUIRED_UPLOAD_SPECS.values():
        for spec in requirements:
            workflow_id = str(spec.get("template_workflow_id") or "").strip()
            variant = str(spec.get("template_variant") or "").strip()
            if not workflow_id or not variant:
                continue
            scope_key = (workflow_id, variant)
            if scope_key in indexes:
                continue
            indexes[scope_key] = {
                str(item["dataset_key"]): item
                for item in list_templates(
                    workflow_id=workflow_id,
                    variant=variant,
                )
            }
    return indexes


def _resolve_template_record(
    templates_by_scope: dict[tuple[str, str], dict[str, dict[str, Any]]],
    *,
    template_workflow_id: Any,
    template_variant: Any,
    dataset_key: str,
) -> dict[str, Any] | None:
    workflow_id = str(template_workflow_id or "").strip()
    variant = str(template_variant or "").strip()
    if not workflow_id or not variant:
        return None
    return templates_by_scope.get((workflow_id, variant), {}).get(dataset_key)


def _allowed_relation_kind_count(
    artifact_link_counts: dict[str, Any],
    *,
    allowed_relation_kinds: tuple[str, ...],
) -> int:
    if not allowed_relation_kinds:
        return int(artifact_link_counts.get("linked_count", 0))
    by_relation_kind = artifact_link_counts.get("by_relation_kind")
    if not isinstance(by_relation_kind, dict):
        return 0
    return sum(int(by_relation_kind.get(relation_kind, 0)) for relation_kind in allowed_relation_kinds)
