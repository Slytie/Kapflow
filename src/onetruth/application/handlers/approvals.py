from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.artifact_effects import (
    _create_artifact_version_effects,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _assert_actor_type,
    _command_receipt_payload,
    _decision_has_reason,
    _event_idempotency_key,
    _event_envelope,
    _execute_with_command_receipt,
    _forbidden_command_error,
    _prepare_command_receipt,
    _principal_from_payload,
    _receipt_event_idempotency_key,
    _require_fields,
    _validate_task_run_belongs_to_workflow,
    _workflow_scope,
)
from onetruth.application.handlers.pointers import _promote_pointer_effects
from onetruth.application.handlers.logistics_handoff import notify_only_handoff_command
from onetruth.application.services.dispatch_reporting_build import (
    FINAL_PACKET_ARTIFACT_KIND as DISPATCH_FINAL_PACKET_ARTIFACT_KIND,
    FINAL_PACKET_POINTER_KEY as DISPATCH_FINAL_PACKET_POINTER_KEY,
    MANAGER_REVIEW_ARTIFACT_KIND as DISPATCH_MANAGER_REVIEW_ARTIFACT_KIND,
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
from onetruth.application.services.task_requirements import (
    REVIEW_CONFIRMATION_ARTIFACT_KIND,
    build_human_task_requirement_index,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.approvals import (
    create_approval,
    get_approval,
    list_approvals_for_workflow_run,
    respond_approval,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.human_tasks import get_human_task_by_task_run_id
from onetruth.infrastructure.repositories.task_runs import get_task_run
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run

APPROVAL_STATES = {"PENDING", "RESPONDED"}
APPROVAL_RESPONSE_TO_OUTCOME = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "changes_requested",
    "cancel": "canceled",
    "expire": "expired",
}
WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"
WEEKLY_STAGE06_SCOPE_REF = "Stage06"
WEEKLY_PUBLISH_ACTION = "publish_weekly_base_schedule"
WEEKLY_DRAFT_ARTIFACT_KIND = "planning.draft_weekly_schedule.workbook"
WEEKLY_MANAGER_REVIEW_ARTIFACT_KIND = "planning.manager_review.doc"
WEEKLY_PUBLISH_PACKET_ARTIFACT_KIND = "planning.publish_packet.doc"
WEEKLY_PUBLISHED_ARTIFACT_KIND = "planning.published_weekly_schedule.workbook"
WEEKLY_OFFICIAL_POINTER_KEY = "official:planning.published_weekly_schedule.workbook"


def _request_approval_effects(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    approval_id: str,
    task_run_id: str | None,
    requested_by_task_run_id: str | None,
    candidate_roles: list[str],
    allowed_responses: list[str],
    event_idempotency: str | None,
) -> dict[str, Any]:
    workflow_run_id = str(payload["workflow_run_id"])
    workflow_scope = _workflow_scope(connection, workflow_run_id)
    if task_run_id is not None:
        _validate_task_run_belongs_to_workflow(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
        )
    if requested_by_task_run_id is not None:
        _validate_task_run_belongs_to_workflow(
            connection,
            task_run_id=requested_by_task_run_id,
            workflow_run_id=workflow_run_id,
        )

    now = utc_now_iso()
    create_approval(
        connection,
        approval_id=approval_id,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        approval_kind=str(payload["approval_kind"]),
        scope_kind=str(payload["scope_kind"]),
        scope_ref=str(payload["scope_ref"]),
        state="PENDING",
        requested_by_task_run_id=requested_by_task_run_id,
        candidate_roles=[str(role) for role in candidate_roles],
        required_role=(
            str(payload["required_role"])
            if payload.get("required_role") is not None
            else None
        ),
        requested_at=now,
        generation=0,
        created_at=now,
    )
    links = [
        {"rel": "subject", "type": "approval", "id": approval_id},
        {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
    ]
    if task_run_id is not None:
        links.append({"rel": "subject", "type": "task_run", "id": task_run_id})

    append_event(
        connection,
        _event_envelope(
            event_type="approval.requested",
            tenant_id=workflow_scope["tenant_id"],
            domain_id=workflow_scope["domain_id"],
            actor_type=str(payload.get("actor_type", "system")),
            actor_id=str(payload.get("actor_id", "system:runtime")),
            links=links,
            payload={
                "approval_id": approval_id,
                "approval_kind": str(payload["approval_kind"]),
                "action": str(payload.get("action") or f"{payload['scope_kind']}:{payload['scope_ref']}"),
                "allowed_responses": [str(value) for value in allowed_responses],
                "requested_from_role": (
                    str(payload["required_role"])
                    if payload.get("required_role") is not None
                    else str(candidate_roles[0])
                ),
            },
            idempotency_key=event_idempotency,
        ),
    )
    approval = get_approval(connection, approval_id)
    if approval is None:
        raise CommandError(
            code="approval_not_found",
            message="approval was not found after creation",
            details={"approval_id": approval_id},
        )
    return approval


def request_approval_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "approval_kind",
            "scope_kind",
            "scope_ref",
            "candidate_roles",
            "idempotency_key",
        ],
    )
    candidate_roles = payload.get("candidate_roles")
    if not isinstance(candidate_roles, list) or not candidate_roles:
        raise CommandError(
            code="invalid_candidate_roles",
            message="candidate_roles must be a non-empty list",
            details={},
        )
    allowed_responses = payload.get("allowed_responses") or list(APPROVAL_RESPONSE_TO_OUTCOME.keys())
    if not isinstance(allowed_responses, list) or not allowed_responses:
        raise CommandError(
            code="invalid_allowed_responses",
            message="allowed_responses must be a non-empty list",
            details={},
        )
    invalid_responses = [str(value) for value in allowed_responses if str(value) not in APPROVAL_RESPONSE_TO_OUTCOME]
    if invalid_responses:
        raise CommandError(
            code="invalid_allowed_responses",
            message="allowed_responses contains unsupported values",
            details={"invalid_values": invalid_responses},
        )

    requested_approval_id = payload.get("approval_id")
    approval_id = str(requested_approval_id or f"ap-{uuid4()}")
    task_run_id = str(payload["task_run_id"]) if payload.get("task_run_id") is not None else None
    requested_by_task_run_id = (
        str(payload["requested_by_task_run_id"])
        if payload.get("requested_by_task_run_id") is not None
        else task_run_id
    )
    receipt = _prepare_command_receipt(
        command_name="approvals.request",
        payload=payload,
        fingerprint_payload={
            "approval_id": (
                str(requested_approval_id)
                if requested_approval_id is not None
                else None
            ),
            "workflow_run_id": str(payload["workflow_run_id"]),
            "task_run_id": task_run_id,
            "approval_kind": str(payload["approval_kind"]),
            "scope_kind": str(payload["scope_kind"]),
            "scope_ref": str(payload["scope_ref"]),
            "requested_by_task_run_id": requested_by_task_run_id,
            "candidate_roles": [str(role) for role in candidate_roles],
            "required_role": (
                str(payload["required_role"])
                if payload.get("required_role") is not None
                else None
            ),
            "allowed_responses": [str(value) for value in allowed_responses],
            "action": str(payload.get("action") or f"{payload['scope_kind']}:{payload['scope_ref']}"),
            "actor_id": str(payload.get("actor_id", "system:runtime")),
            "actor_type": str(payload.get("actor_type", "system")),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=str(payload["workflow_run_id"]),
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "approvals.request.approval.requested",
    )

    def _operation() -> dict[str, Any]:
        return _request_approval_effects(
            connection,
            payload,
            approval_id=approval_id,
            task_run_id=task_run_id,
            requested_by_task_run_id=requested_by_task_run_id,
            candidate_roles=[str(role) for role in candidate_roles],
            allowed_responses=[str(value) for value in allowed_responses],
            event_idempotency=event_idempotency,
        )

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=_operation,
        )
    except sqlite3.IntegrityError as exc:
        if "approvals.approval_id" in str(exc):
            raise CommandError(
                code="duplicate_approval_id",
                message="approval_id already exists",
                details={"approval_id": approval_id},
            ) from exc
        raise

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def respond_approval_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["approval_id", "actor_id", "actor_type", "response_kind", "idempotency_key"],
    )
    actor_type = str(payload["actor_type"])
    _assert_actor_type(actor_type)
    before = get_approval(connection, str(payload["approval_id"]))
    if before is None:
        raise CommandError(
            code="approval_not_found",
            message="approval not found",
            details={"approval_id": str(payload["approval_id"])},
        )
    principal = _principal_from_payload(payload, require_roles=True)
    from onetruth.application.services.capabilities import respond_decision

    decision = respond_decision(approval=before, principal=principal)
    if _decision_has_reason(decision, "approval_role_mismatch"):
        raise _forbidden_command_error(
            code="approval_respond_forbidden",
            message="actor is not allowed to respond to this approval",
            decision=decision,
            approval_id=str(payload["approval_id"]),
            workflow_run_id=str(before["workflow_run_id"]),
        )
    response_kind = str(payload["response_kind"])
    if response_kind not in APPROVAL_RESPONSE_TO_OUTCOME:
        raise CommandError(
            code="invalid_approval_response",
            message=f"unsupported approval response_kind: {response_kind}",
            details={"allowed_response_kinds": sorted(APPROVAL_RESPONSE_TO_OUTCOME)},
        )
    responded_outcome = APPROVAL_RESPONSE_TO_OUTCOME[response_kind]
    receipt = _prepare_command_receipt(
        command_name="approvals.respond",
        payload=payload,
        fingerprint_payload={
            "approval_id": str(payload["approval_id"]),
            "actor_id": str(payload["actor_id"]),
            "actor_type": actor_type,
            "actor_roles": sorted(set(principal.actor_roles)),
            "response_kind": response_kind,
            "response_reason": (
                str(payload["response_reason"])
                if payload.get("response_reason") is not None
                else None
            ),
        },
        tenant_id=str(before["tenant_id"]) if before.get("tenant_id") is not None else None,
        domain_id=str(before["domain_id"]) if before.get("domain_id") is not None else None,
        workflow_run_id=str(before["workflow_run_id"]),
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "approvals.respond.approval.responded",
    )

    def _operation() -> dict[str, Any]:
        if str(before["state"]) != "PENDING":
            raise CommandError(
                code="approval_not_respondable",
                message="approval has already reached a terminal response state",
                details={
                    "approval_id": str(payload["approval_id"]),
                    "state": str(before["state"]),
                    "response_kind": before.get("response_kind"),
                    "allowed_initial_states": sorted(APPROVAL_STATES),
                },
            )
        now = utc_now_iso()
        responded = respond_approval(
            connection,
            approval_id=str(payload["approval_id"]),
            response_kind=response_kind,
            response_reason=(
                str(payload["response_reason"])
                if payload.get("response_reason") is not None
                else None
            ),
            decided_by_actor_id=str(payload["actor_id"]),
            decided_by_actor_type=actor_type,
            responded_at=now,
            updated_at=now,
        )
        if responded is None:
            raise CommandError(
                code="approval_not_respondable",
                message="approval response raced and could not be applied",
                details={"approval_id": str(payload["approval_id"])},
            )

        workflow_scope = _workflow_scope(connection, str(responded["workflow_run_id"]))
        requested_action = _approval_requested_action(
            connection,
            approval_id=str(responded["approval_id"]),
        ) or f"{responded['scope_kind']}:{responded['scope_ref']}"
        links = [
            {"rel": "subject", "type": "approval", "id": str(responded["approval_id"])},
            {"rel": "subject", "type": "workflow_run", "id": str(responded["workflow_run_id"])},
        ]
        if responded.get("task_run_id") is not None:
            links.append(
                {"rel": "subject", "type": "task_run", "id": str(responded["task_run_id"])},
            )
        append_event(
            connection,
            _event_envelope(
                event_type="approval.responded",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=actor_type,
                actor_id=str(payload["actor_id"]),
                links=links,
                payload={
                    "approval_id": str(responded["approval_id"]),
                    "action": requested_action,
                    "response": response_kind,
                    "outcome": responded_outcome,
                    "rationale": (
                        str(payload["response_reason"])
                        if payload.get("response_reason") is not None
                        else None
                    ),
                },
                idempotency_key=event_idempotency,
            ),
        )
        if response_kind == "approve":
            _maybe_auto_publish_weekly_approval(
                connection,
                approval=responded,
                requested_action=requested_action,
                actor_id=str(payload["actor_id"]),
                actor_type=actor_type,
                event_idempotency_base=receipt.event_idempotency_base if receipt is not None else None,
            )
            _maybe_finalize_dispatch_reporting_approval(
                connection,
                approval=responded,
                requested_action=requested_action,
                actor_id=str(payload["actor_id"]),
                actor_type=actor_type,
                event_idempotency_base=receipt.event_idempotency_base if receipt is not None else None,
            )
        approval = get_approval(connection, str(payload["approval_id"]))
        if approval is None:
            raise CommandError(
                code="approval_not_found",
                message="approval not found after response",
                details={"approval_id": str(payload["approval_id"])},
            )
        return approval

    result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=_operation,
    )
    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def _approval_requested_action(
    connection: sqlite3.Connection,
    *,
    approval_id: str,
) -> str | None:
    rows = connection.execute(
        """
        SELECT payload
        FROM timeline_events
        WHERE event_type = 'approval.requested'
        ORDER BY sequence_no DESC
        """
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(str(row["payload"]))
        except (TypeError, ValueError):
            continue
        if str(payload.get("approval_id") or "") != approval_id:
            continue
        action = str(payload.get("action") or "").strip()
        return action or None
    return None


def _maybe_auto_publish_weekly_approval(
    connection: sqlite3.Connection,
    *,
    approval: dict[str, Any],
    requested_action: str,
    actor_id: str,
    actor_type: str,
    event_idempotency_base: str | None,
) -> None:
    workflow_run_id = str(approval["workflow_run_id"])
    workflow_run = get_workflow_run(connection, workflow_run_id)
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
    if requested_action != WEEKLY_PUBLISH_ACTION:
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
    task_run = get_task_run(connection, task_run_id)
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="review task run not found for weekly publish approval",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
            },
        )
    human_task = get_human_task_by_task_run_id(connection, task_run_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="review human task not found for weekly publish approval",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
            },
        )

    artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
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
        connection,
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

    review_confirmation = _latest_review_confirmation_for_human_task(
        artifacts=artifacts,
        human_task_id=str(human_task["human_task_id"]),
    )
    reviewed_draft_artifact_version_id = _reviewed_artifact_id_from_confirmation(
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

    draft_artifact = get_artifact_version(connection, latest_draft_artifact_version_id)
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
            "id": actor_id,
            "type": actor_type,
        },
        "published_at": utc_now_iso(),
    }
    publish_packet_bytes = _json_bytes(publish_packet_metadata)
    publish_packet = _create_artifact_version_effects(
        connection,
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
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=_event_idempotency_key(
            event_idempotency_base,
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
        connection,
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
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=_event_idempotency_key(
            event_idempotency_base,
            "weekly-publish.published-workbook.artifact.version.created",
        ),
    )
    _promote_pointer_effects(
        connection,
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
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=_event_idempotency_key(
            event_idempotency_base,
            "weekly-publish.artifact.pointer.promoted",
        ),
        drift_idempotency=_event_idempotency_key(
            event_idempotency_base,
            "weekly-publish.artifact.pointer.drift-detected",
        ),
    )


def _maybe_finalize_dispatch_reporting_approval(
    connection: sqlite3.Connection,
    *,
    approval: dict[str, Any],
    requested_action: str,
    actor_id: str,
    actor_type: str,
    event_idempotency_base: str | None,
) -> None:
    workflow_run_id = str(approval["workflow_run_id"])
    workflow_run = get_workflow_run(connection, workflow_run_id)
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
    if requested_action != DISPATCH_REVIEW_APPROVAL_ACTION:
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
    task_run = get_task_run(connection, task_run_id)
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
    human_task = get_human_task_by_task_run_id(connection, task_run_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="review human task not found for dispatch reporting finalize approval",
            details={
                "approval_id": str(approval["approval_id"]),
                "task_run_id": task_run_id,
            },
        )

    artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
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

    requirement_state = build_human_task_requirement_index(
        connection,
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
        artifact_kind=DISPATCH_MANAGER_REVIEW_ARTIFACT_KIND,
    )
    if manager_review_requirement is None or str(manager_review_requirement.get("status") or "") == "missing":
        raise CommandError(
            code="dispatch_reporting_finalize_requirements_not_satisfied",
            message="dispatch reporting finalize requires the manager review attachment",
            details={
                "approval_id": str(approval["approval_id"]),
                "human_task_id": str(human_task["human_task_id"]),
                "artifact_kind": DISPATCH_MANAGER_REVIEW_ARTIFACT_KIND,
            },
        )

    review_confirmation = _latest_review_confirmation_for_human_task(
        artifacts=artifacts,
        human_task_id=str(human_task["human_task_id"]),
    )
    reviewed_draft_artifact_version_id = _reviewed_artifact_id_from_confirmation(
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

    draft_artifact = get_artifact_version(connection, latest_draft_artifact_version_id)
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
        connection,
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
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=_event_idempotency_key(
            event_idempotency_base,
            "dispatch-reporting.final-packet.artifact.version.created",
        ),
    )
    _promote_pointer_effects(
        connection,
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
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=_event_idempotency_key(
            event_idempotency_base,
            "dispatch-reporting.final-packet.artifact.pointer.promoted",
        ),
        drift_idempotency=_event_idempotency_key(
            event_idempotency_base,
            "dispatch-reporting.final-packet.artifact.pointer.drift-detected",
        ),
    )
    notify_only_handoff_command(
        connection,
        {
            "edge_id": DISPATCH_REPORTING_TO_PLANNING_EDGE_ID,
            "source_workflow_run_id": workflow_run_id,
            "source_artifact_version_id": str(finalized_artifact["artifact_version_id"]),
            "idempotency_key": (
                f"{event_idempotency_base}:dispatch-reporting:planning-handoff"
                if event_idempotency_base is not None
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


def _latest_review_confirmation_for_human_task(
    *,
    artifacts: list[dict[str, Any]],
    human_task_id: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in artifacts:
        if str(artifact.get("artifact_kind") or "") != REVIEW_CONFIRMATION_ARTIFACT_KIND:
            continue
        metadata = artifact.get("metadata_json")
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("human_task_id") or "") != human_task_id:
            continue
        latest = artifact
    return latest


def _reviewed_artifact_id_from_confirmation(
    *,
    artifacts: list[dict[str, Any]],
    review_confirmation: dict[str, Any] | None,
    artifact_kind: str,
) -> str | None:
    if review_confirmation is None:
        return None
    metadata = review_confirmation.get("metadata_json")
    if not isinstance(metadata, dict):
        return None
    reviewed_ids = metadata.get("reviewed_artifact_version_ids")
    if not isinstance(reviewed_ids, list):
        return None
    artifacts_by_id = {
        str(artifact.get("artifact_version_id")): artifact for artifact in artifacts
    }
    for raw_reviewed_id in reviewed_ids:
        reviewed_id = str(raw_reviewed_id or "").strip()
        if not reviewed_id:
            continue
        artifact = artifacts_by_id.get(reviewed_id)
        if artifact is None:
            continue
        if str(artifact.get("artifact_kind") or "") == artifact_kind:
            return reviewed_id
    return None


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def show_approval_command(
    connection: sqlite3.Connection,
    approval_id: str,
) -> dict[str, Any]:
    approval = get_approval(connection, approval_id)
    if approval is None:
        raise CommandError(
            code="approval_not_found",
            message="approval not found",
            details={"approval_id": approval_id},
        )
    return approval


def list_approvals_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_approvals_for_workflow_run(connection, workflow_run_id)
