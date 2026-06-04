from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.artifact_effects import (
    _create_artifact_version_effects,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _event_idempotency_key,
)
from onetruth.application.handlers.logistics_handoff import notify_only_handoff_command
from onetruth.application.handlers.pointers import _promote_pointer_effects
from onetruth.application.services.approval_response_hooks import (
    ApprovalResponseHook,
    ApprovalResponseHookContext,
)
from onetruth.application.services.dispatch_reporting_build import (
    FINAL_PACKET_ARTIFACT_KIND as DISPATCH_FINAL_PACKET_ARTIFACT_KIND,
    FINAL_PACKET_POINTER_KEY as DISPATCH_FINAL_PACKET_POINTER_KEY,
    REPORTING_TO_PLANNING_EDGE_ID as DISPATCH_REPORTING_TO_PLANNING_EDGE_ID,
    REVIEW_APPROVAL_ACTION as DISPATCH_REVIEW_APPROVAL_ACTION,
    REVIEW_APPROVAL_SCOPE_REF as DISPATCH_REVIEW_APPROVAL_SCOPE_REF,
    REVIEW_TASK_KIND as DISPATCH_REVIEW_TASK_KIND,
    UPD_DRAFT_ARTIFACT_KIND as DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
    WORKFLOW_ID as DISPATCH_REPORTING_WORKFLOW_ID,
)
from onetruth.application.services.schedule_control.workpage_calculations import (
    project_schedule_dependency_state,
    schedule_save_disabled_reason,
)
from onetruth.application.services.review_confirmation import (
    latest_review_confirmation_for_human_task,
    reviewed_artifact_id_from_confirmation,
)
from onetruth.application.services.task_requirements import (
    build_human_task_requirement_index,
)
from onetruth.infrastructure.events.event_store import utc_now_iso
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.human_tasks import get_human_task_by_task_run_id
from onetruth.infrastructure.repositories.task_runs import get_task_run
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run


WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"
WEEKLY_STAGE06_SCOPE_REF = "Stage06"
WEEKLY_PUBLISH_ACTION = "publish_weekly_base_schedule"
WEEKLY_DRAFT_ARTIFACT_KIND = "planning.draft_weekly_schedule.workbook"
WEEKLY_MANAGER_REVIEW_ARTIFACT_KIND = "planning.manager_review.doc"
WEEKLY_PUBLISH_PACKET_ARTIFACT_KIND = "planning.publish_packet.doc"
WEEKLY_PUBLISHED_ARTIFACT_KIND = "planning.published_weekly_schedule.workbook"
WEEKLY_OFFICIAL_POINTER_KEY = "official:planning.published_weekly_schedule.workbook"


def weekly_publish_approval_hook(context: ApprovalResponseHookContext) -> None:
    if context.response_kind != "approve":
        return
    approval = context.approval
    workflow_run_id = str(approval["workflow_run_id"])
    workflow_run = get_workflow_run(context.connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found for approval publish side effect",
            details={"workflow_run_id": workflow_run_id},
        )
    if str(workflow_run.get("workflow_id") or "") != WEEKLY_WORKFLOW_ID:
        return
    if str(approval.get("scope_ref") or "") != WEEKLY_STAGE06_SCOPE_REF:
        return
    if context.requested_action != WEEKLY_PUBLISH_ACTION:
        return

    task_run_id = str(
        approval.get("task_run_id")
        or approval.get("requested_by_task_run_id")
        or ""
    ).strip()
    if not task_run_id:
        raise CommandError(
            code="weekly_publish_context_missing",
            message="weekly publish approval must reference the reviewed final-review task",
            details={"approval_id": str(approval["approval_id"])},
        )
    task_run = get_task_run(context.connection, task_run_id)
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="review task run not found for weekly publish approval",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
            },
        )
    human_task = get_human_task_by_task_run_id(context.connection, task_run_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="review human task not found for weekly publish approval",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
            },
        )

    artifacts = list_artifact_versions_for_workflow_run(context.connection, workflow_run_id)
    latest_draft = _latest_artifact_of_kind(artifacts, WEEKLY_DRAFT_ARTIFACT_KIND)
    if latest_draft is None:
        raise CommandError(
            code="stable_base_schedule_required",
            message="weekly publish requires a current draft weekly schedule artifact",
            details={
                "approval_id": str(approval["approval_id"]),
                "workflow_run_id": workflow_run_id,
                "artifact_kind": WEEKLY_DRAFT_ARTIFACT_KIND,
            },
        )

    requirement_state = build_human_task_requirement_index(
        context.connection,
        workflow_run_id=workflow_run_id,
        human_tasks=[
            {
                **human_task,
                "stage_id": task_run.get("stage_id"),
                "task_kind": task_run.get("task_kind"),
            }
        ],
        artifact_versions=artifacts,
    ).get(str(human_task["human_task_id"]), {})
    manager_review_requirement = _required_upload_for_kind(
        requirement_state=requirement_state,
        artifact_kind=WEEKLY_MANAGER_REVIEW_ARTIFACT_KIND,
    )
    if manager_review_requirement is None or str(manager_review_requirement.get("status") or "") == "missing":
        raise CommandError(
            code="weekly_publish_requirements_not_satisfied",
            message="weekly publish requires the manager review attachment",
            details={
                "approval_id": str(approval["approval_id"]),
                "human_task_id": str(human_task["human_task_id"]),
                "artifact_kind": WEEKLY_MANAGER_REVIEW_ARTIFACT_KIND,
            },
        )

    review_confirmation = latest_review_confirmation_for_human_task(
        artifacts=artifacts,
        human_task_id=str(human_task["human_task_id"]),
    )
    reviewed_draft_artifact_version_id = reviewed_artifact_id_from_confirmation(
        artifacts=artifacts,
        review_confirmation=review_confirmation,
        artifact_kind=WEEKLY_DRAFT_ARTIFACT_KIND,
    )
    if reviewed_draft_artifact_version_id is None:
        raise CommandError(
            code="weekly_publish_requirements_not_satisfied",
            message="weekly publish requires a review confirmation for the reviewed draft",
            details={
                "approval_id": str(approval["approval_id"]),
                "human_task_id": str(human_task["human_task_id"]),
                "artifact_kind": WEEKLY_DRAFT_ARTIFACT_KIND,
            },
        )

    latest_draft_artifact_version_id = str(latest_draft["artifact_version_id"])
    if reviewed_draft_artifact_version_id != latest_draft_artifact_version_id:
        raise CommandError(
            code="stable_base_schedule_required",
            message="weekly publish requires the reviewed draft to remain the latest draft",
            details={
                "approval_id": str(approval["approval_id"]),
                "workflow_run_id": workflow_run_id,
                "reviewed_draft_artifact_version_id": reviewed_draft_artifact_version_id,
                "latest_draft_artifact_version_id": latest_draft_artifact_version_id,
            },
        )

    draft_artifact = get_artifact_version(context.connection, latest_draft_artifact_version_id)
    if draft_artifact is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="reviewed draft artifact was not found for weekly publish",
            details={"artifact_version_id": latest_draft_artifact_version_id},
        )
    dependency_projection = project_schedule_dependency_state(
        dependency_manifest=(
            draft_artifact.get("metadata_json", {}).get("dependency_manifest")
            if isinstance(draft_artifact.get("metadata_json"), dict)
            else None
        ),
        artifacts=artifacts,
    )
    dependency_block_reason = schedule_save_disabled_reason(
        dependency_projection.dependencies
    )
    if dependency_block_reason is not None:
        raise CommandError(
            code=dependency_block_reason,
            message=(
                "weekly publish requires aligned pinned schedule dependencies"
                if dependency_block_reason == "dependency_drift_detected"
                else "weekly publish requires a pinned schedule dependency baseline"
            ),
            details={
                "approval_id": str(approval["approval_id"]),
                "workflow_run_id": workflow_run_id,
                "artifact_version_id": latest_draft_artifact_version_id,
                "dependency_state": dependency_projection.dependency_state,
                "dependencies": dependency_projection.dependencies,
            },
        )
    publish_packet_metadata = {
        "schema_version": "1.0",
        "kind": "weekly_publish_packet",
        "workflow_run_id": workflow_run_id,
        "approval_id": str(approval["approval_id"]),
        "task_run_id": task_run_id,
        "human_task_id": str(human_task["human_task_id"]),
        "review_confirmation_artifact_version_id": (
            str(review_confirmation["artifact_version_id"])
            if review_confirmation is not None
            else None
        ),
        "reviewed_draft_artifact_version_id": reviewed_draft_artifact_version_id,
        "published_artifact_kind": WEEKLY_PUBLISHED_ARTIFACT_KIND,
        "published_by": {
            "id": context.actor_id,
            "type": context.actor_type,
        },
        "published_at": utc_now_iso(),
    }
    publish_packet_bytes = _json_bytes(publish_packet_metadata)
    publish_packet = _create_artifact_version_effects(
        context.connection,
        {
            "artifact_version_id": f"av-{uuid4()}",
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": WEEKLY_PUBLISH_PACKET_ARTIFACT_KIND,
            "artifact_role": "evidence",
            "media_type": "application/json",
            "storage_uri": (
                f"inmem://weekly-publish/{workflow_run_id}/{approval['approval_id']}/publish-packet.json"
            ),
            "content_digest": _sha256_bytes(publish_packet_bytes),
            "byte_size": len(publish_packet_bytes),
            "metadata_json": publish_packet_metadata,
            "parent_artifact_version_id": reviewed_draft_artifact_version_id,
            "lineage_note": "weekly_publish_packet",
            "links": [
                {
                    "subject_kind": "approval",
                    "subject_id": str(approval["approval_id"]),
                    "relation_kind": "attachment",
                },
                {
                    "subject_kind": "task_run",
                    "subject_id": task_run_id,
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "human_task",
                    "subject_id": str(human_task["human_task_id"]),
                    "relation_kind": "output",
                },
            ],
            "actor_id": context.actor_id,
            "actor_type": context.actor_type,
        },
        event_idempotency=_event_idempotency_key(
            context.event_idempotency_base,
            "weekly-publish.publish-packet.artifact.version.created",
        ),
    )
    draft_metadata = draft_artifact.get("metadata_json")
    published_metadata = dict(draft_metadata) if isinstance(draft_metadata, dict) else {}
    published_metadata.update(
        {
            "published_from_artifact_version_id": reviewed_draft_artifact_version_id,
            "publish_packet_artifact_version_id": str(publish_packet["artifact_version_id"]),
            "approval_id": str(approval["approval_id"]),
            "published_at": publish_packet_metadata["published_at"],
        }
    )
    published_artifact = _create_artifact_version_effects(
        context.connection,
        {
            "artifact_version_id": f"av-{uuid4()}",
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": WEEKLY_PUBLISHED_ARTIFACT_KIND,
            "artifact_role": "official_output",
            "media_type": str(draft_artifact["media_type"]),
            "storage_uri": str(draft_artifact["storage_uri"]),
            "content_digest": str(draft_artifact["content_digest"]),
            "byte_size": draft_artifact.get("byte_size"),
            "metadata_json": published_metadata,
            "parent_artifact_version_id": reviewed_draft_artifact_version_id,
            "lineage_note": "official_weekly_publish",
            "links": [
                {
                    "subject_kind": "approval",
                    "subject_id": str(approval["approval_id"]),
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "task_run",
                    "subject_id": task_run_id,
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "human_task",
                    "subject_id": str(human_task["human_task_id"]),
                    "relation_kind": "output",
                },
            ],
            "actor_id": context.actor_id,
            "actor_type": context.actor_type,
        },
        event_idempotency=_event_idempotency_key(
            context.event_idempotency_base,
            "weekly-publish.published-workbook.artifact.version.created",
        ),
    )
    _promote_pointer_effects(
        context.connection,
        {
            "workflow_run_id": workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": WEEKLY_STAGE06_SCOPE_REF,
            "pointer_key": WEEKLY_OFFICIAL_POINTER_KEY,
            "artifact_kind": WEEKLY_PUBLISHED_ARTIFACT_KIND,
            "artifact_version_id": str(published_artifact["artifact_version_id"]),
            "promotion_reason": "official_publish",
            "approved_by_approval_id": str(approval["approval_id"]),
            "promoted_by_task_run_id": task_run_id,
            "reviewed_artifact_version_id": reviewed_draft_artifact_version_id,
            "actor_id": context.actor_id,
            "actor_type": context.actor_type,
        },
        event_idempotency=_event_idempotency_key(
            context.event_idempotency_base,
            "weekly-publish.artifact.pointer.promoted",
        ),
        drift_idempotency=_event_idempotency_key(
            context.event_idempotency_base,
            "weekly-publish.artifact.pointer.drift-detected",
        ),
    )


def dispatch_reporting_finalize_approval_hook(context: ApprovalResponseHookContext) -> None:
    if context.response_kind != "approve":
        return
    approval = context.approval
    workflow_run_id = str(approval["workflow_run_id"])
    workflow_run = get_workflow_run(context.connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found for dispatch reporting finalize side effect",
            details={"workflow_run_id": workflow_run_id},
        )
    if str(workflow_run.get("workflow_id") or "") != DISPATCH_REPORTING_WORKFLOW_ID:
        return
    if str(approval.get("scope_ref") or "") != DISPATCH_REVIEW_APPROVAL_SCOPE_REF:
        return
    if context.requested_action != DISPATCH_REVIEW_APPROVAL_ACTION:
        return

    task_run_id = str(
        approval.get("task_run_id")
        or approval.get("requested_by_task_run_id")
        or ""
    ).strip()
    if not task_run_id:
        raise CommandError(
            code="dispatch_reporting_finalize_context_missing",
            message="dispatch reporting finalize approval must reference the reviewed Stage04 task",
            details={"approval_id": str(approval["approval_id"])},
        )
    task_run = get_task_run(context.connection, task_run_id)
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="review task run not found for dispatch reporting finalize approval",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
            },
        )
    if str(task_run.get("task_kind") or "") != DISPATCH_REVIEW_TASK_KIND:
        raise CommandError(
            code="dispatch_reporting_finalize_context_missing",
            message="dispatch reporting finalize approval must reference the Stage04 review task",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
                "task_kind": str(task_run.get("task_kind") or ""),
            },
        )
    human_task = get_human_task_by_task_run_id(context.connection, task_run_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="review human task not found for dispatch reporting finalize approval",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
            },
        )

    artifacts = list_artifact_versions_for_workflow_run(context.connection, workflow_run_id)
    latest_draft = _latest_artifact_of_kind(artifacts, DISPATCH_UPD_DRAFT_ARTIFACT_KIND)
    if latest_draft is None:
        raise CommandError(
            code="stable_base_schedule_required",
            message="dispatch reporting finalize requires a current EOD draft artifact",
            details={
                "approval_id": str(approval["approval_id"]),
                "workflow_run_id": workflow_run_id,
                "artifact_kind": DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
            },
        )

    review_confirmation = latest_review_confirmation_for_human_task(
        artifacts=artifacts,
        human_task_id=str(human_task["human_task_id"]),
    )
    reviewed_draft_artifact_version_id = reviewed_artifact_id_from_confirmation(
        artifacts=artifacts,
        review_confirmation=review_confirmation,
        artifact_kind=DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
    )
    if reviewed_draft_artifact_version_id is None:
        raise CommandError(
            code="dispatch_reporting_finalize_requirements_not_satisfied",
            message="dispatch reporting finalize requires a review confirmation for the reviewed draft",
            details={
                "approval_id": str(approval["approval_id"]),
                "human_task_id": str(human_task["human_task_id"]),
                "artifact_kind": DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
            },
        )

    latest_draft_artifact_version_id = str(latest_draft["artifact_version_id"])
    if reviewed_draft_artifact_version_id != latest_draft_artifact_version_id:
        raise CommandError(
            code="stable_base_schedule_required",
            message="dispatch reporting finalize requires the reviewed draft to remain the latest draft",
            details={
                "approval_id": str(approval["approval_id"]),
                "workflow_run_id": workflow_run_id,
                "reviewed_draft_artifact_version_id": reviewed_draft_artifact_version_id,
                "latest_draft_artifact_version_id": latest_draft_artifact_version_id,
            },
        )

    draft_artifact = get_artifact_version(context.connection, latest_draft_artifact_version_id)
    if draft_artifact is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="reviewed draft artifact was not found for dispatch reporting finalize",
            details={"artifact_version_id": latest_draft_artifact_version_id},
        )

    draft_metadata = draft_artifact.get("metadata_json")
    finalized_metadata = dict(draft_metadata) if isinstance(draft_metadata, dict) else {}
    finalized_metadata.update(
        {
            "finalized_from_artifact_version_id": reviewed_draft_artifact_version_id,
            "approval_id": str(approval["approval_id"]),
            "finalized_at": utc_now_iso(),
        }
    )
    finalized_artifact = _create_artifact_version_effects(
        context.connection,
        {
            "artifact_version_id": f"av-{uuid4()}",
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": DISPATCH_FINAL_PACKET_ARTIFACT_KIND,
            "artifact_role": "official_output",
            "media_type": str(draft_artifact["media_type"]),
            "storage_uri": str(draft_artifact["storage_uri"]),
            "content_digest": str(draft_artifact["content_digest"]),
            "byte_size": draft_artifact.get("byte_size"),
            "metadata_json": finalized_metadata,
            "parent_artifact_version_id": reviewed_draft_artifact_version_id,
            "lineage_note": "dispatch_reporting_finalized_packet",
            "links": [
                {
                    "subject_kind": "approval",
                    "subject_id": str(approval["approval_id"]),
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "task_run",
                    "subject_id": task_run_id,
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "human_task",
                    "subject_id": str(human_task["human_task_id"]),
                    "relation_kind": "output",
                },
            ],
            "actor_id": context.actor_id,
            "actor_type": context.actor_type,
        },
        event_idempotency=_event_idempotency_key(
            context.event_idempotency_base,
            "dispatch-reporting.final-packet.artifact.version.created",
        ),
    )
    _promote_pointer_effects(
        context.connection,
        {
            "workflow_run_id": workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": DISPATCH_REVIEW_APPROVAL_SCOPE_REF,
            "pointer_key": DISPATCH_FINAL_PACKET_POINTER_KEY,
            "artifact_kind": DISPATCH_FINAL_PACKET_ARTIFACT_KIND,
            "artifact_version_id": str(finalized_artifact["artifact_version_id"]),
            "promotion_reason": "official_finalize",
            "approved_by_approval_id": str(approval["approval_id"]),
            "promoted_by_task_run_id": task_run_id,
            "reviewed_artifact_version_id": reviewed_draft_artifact_version_id,
            "actor_id": context.actor_id,
            "actor_type": context.actor_type,
        },
        event_idempotency=_event_idempotency_key(
            context.event_idempotency_base,
            "dispatch-reporting.final-packet.artifact.pointer.promoted",
        ),
        drift_idempotency=_event_idempotency_key(
            context.event_idempotency_base,
            "dispatch-reporting.final-packet.artifact.pointer.drift-detected",
        ),
    )
    notify_only_handoff_command(
        context.connection,
        {
            "edge_id": DISPATCH_REPORTING_TO_PLANNING_EDGE_ID,
            "source_workflow_run_id": workflow_run_id,
            "source_artifact_version_id": str(finalized_artifact["artifact_version_id"]),
            "idempotency_key": (
                f"{context.event_idempotency_base}:dispatch-reporting:planning-handoff"
                if context.event_idempotency_base is not None
                else f"dispatch-reporting:planning-handoff:{approval['approval_id']}"
            ),
        },
    )


def _required_upload_for_kind(
    *,
    requirement_state: dict[str, Any],
    artifact_kind: str,
) -> dict[str, Any] | None:
    for item in requirement_state.get("required_uploads") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("artifact_kind") or "") == artifact_kind:
            return item
    return None


def _latest_artifact_of_kind(
    artifacts: list[dict[str, Any]],
    artifact_kind: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in artifacts:
        if str(artifact.get("artifact_kind") or "") != artifact_kind:
            continue
        latest = artifact
    return latest


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


LOGISTICS_APPROVAL_RESPONSE_HOOKS: tuple[ApprovalResponseHook, ...] = (
    ApprovalResponseHook(
        hook_id="logistics.weekly_publish_approval",
        handler=weekly_publish_approval_hook,
    ),
    ApprovalResponseHook(
        hook_id="logistics.dispatch_reporting_finalize_approval",
        handler=dispatch_reporting_finalize_approval_hook,
    ),
)

LOGISTICS_APPROVAL_RESPONSE_WORKFLOW_IDS = frozenset(
    {
        WEEKLY_WORKFLOW_ID,
        DISPATCH_REPORTING_WORKFLOW_ID,
    }
)


def logistics_approval_response_hooks_for_workflow(
    workflow_id: str,
) -> tuple[ApprovalResponseHook, ...]:
    if workflow_id in LOGISTICS_APPROVAL_RESPONSE_WORKFLOW_IDS:
        return LOGISTICS_APPROVAL_RESPONSE_HOOKS
    return ()


__all__ = [
    "LOGISTICS_APPROVAL_RESPONSE_HOOKS",
    "LOGISTICS_APPROVAL_RESPONSE_WORKFLOW_IDS",
    "dispatch_reporting_finalize_approval_hook",
    "logistics_approval_response_hooks_for_workflow",
    "weekly_publish_approval_hook",
]
