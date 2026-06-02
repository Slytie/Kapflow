from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _assert_actor_type,
    _command_receipt_payload,
    _decision_has_reason,
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
from onetruth.application.services.approval_response_hooks import (
    ApprovalResponseHookContext,
    run_registered_approval_response_hooks,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.approvals import (
    create_approval,
    get_approval,
    list_approvals_for_workflow_run,
    respond_approval,
)

APPROVAL_STATES = {"PENDING", "RESPONDED"}
APPROVAL_RESPONSE_TO_OUTCOME = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "changes_requested",
    "cancel": "canceled",
    "expire": "expired",
}


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
        run_registered_approval_response_hooks(
            ApprovalResponseHookContext(
                connection=connection,
                approval=responded,
                requested_action=requested_action,
                response_kind=response_kind,
                actor_id=str(payload["actor_id"]),
                actor_type=actor_type,
                event_idempotency_base=(
                    receipt.event_idempotency_base if receipt is not None else None
                ),
            ),
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
