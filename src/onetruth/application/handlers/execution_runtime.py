from __future__ import annotations

from datetime import timedelta
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _assert_actor_type,
    _assert_idempotency_available,
    _begin_transaction,
    _command_receipt_payload,
    _event_envelope,
    _execute_with_command_receipt,
    _parse_iso_datetime,
    _prepare_command_receipt,
    _receipt_event_idempotency_key,
    _required_event_idempotency_key,
    _require_fields,
    _validate_task_run_belongs_to_workflow,
    _workflow_scope,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version
from onetruth.infrastructure.repositories.execution_sessions import (
    create_execution_session,
    get_execution_session,
    increment_tool_call_count,
    list_reconcilable_execution_sessions,
    transition_execution_session_state,
)
from onetruth.infrastructure.repositories.policy_decisions import (
    create_policy_decision,
    get_policy_decision,
    get_policy_decision_for_tool_execution,
)
from onetruth.infrastructure.repositories.tool_executions import (
    create_tool_execution,
    get_tool_execution,
    get_tool_execution_by_session_idempotency,
    list_tool_executions_for_session,
    transition_tool_execution_state,
)
from onetruth.infrastructure.repositories.tool_execution_attempts import (
    ToolExecutionAttemptError,
    complete_tool_execution_attempt,
    create_tool_execution_attempt,
    get_active_tool_execution_attempt,
)

EXECUTION_SESSION_STATES = {
    "CREATED",
    "RUNNING",
    "WAITING_POLICY",
    "WAITING_APPROVAL",
    "PAUSED",
    "SUCCEEDED",
    "FAILED",
    "CANCELED",
}
TOOL_EXECUTION_STATES = {
    "REQUESTED",
    "APPROVED",
    "DENIED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELED",
}
POLICY_DECISIONS = {"allow", "deny", "require_approval"}


def _attempt_error_to_command_error(error: ToolExecutionAttemptError) -> CommandError:
    return CommandError(code=error.code, message=error.code, details=error.details)


def create_execution_session_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "task_run_id",
            "execution_spec_id",
            "owner_mode",
            "idempotency_key",
        ],
    )
    owner_mode = str(payload["owner_mode"])
    if owner_mode not in {"human", "agent", "service", "mixed"}:
        raise CommandError(
            code="invalid_owner_mode",
            message=f"unsupported owner_mode: {owner_mode}",
            details={"allowed_owner_modes": ["human", "agent", "service", "mixed"]},
        )
    initial_state = str(payload.get("state", "RUNNING"))
    if initial_state not in EXECUTION_SESSION_STATES:
        raise CommandError(
            code="invalid_execution_session_state",
            message=f"unsupported execution session state: {initial_state}",
            details={"allowed_states": sorted(EXECUTION_SESSION_STATES)},
        )
    requested_execution_session_id = payload.get("execution_session_id")
    execution_session_id = str(requested_execution_session_id or f"xs-{uuid4()}")
    receipt = _prepare_command_receipt(
        command_name="execution-sessions.create",
        payload=payload,
        fingerprint_payload={
            "execution_session_id": (
                str(requested_execution_session_id)
                if requested_execution_session_id is not None
                else None
            ),
            "workflow_run_id": str(payload["workflow_run_id"]),
            "task_run_id": str(payload["task_run_id"]),
            "execution_spec_id": str(payload["execution_spec_id"]),
            "owner_mode": owner_mode,
            "state": initial_state,
            "principal_actor": payload.get("principal_actor"),
            "budget": payload.get("budget"),
            "tool_call_count": int(payload.get("tool_call_count", 0)),
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
        "execution-sessions.create.execution.session.created",
    )
    state_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "execution-sessions.create.execution.session.state_changed",
    )

    def _operation() -> dict[str, Any]:
        workflow_scope = _workflow_scope(connection, str(payload["workflow_run_id"]))
        _validate_task_run_belongs_to_workflow(
            connection,
            task_run_id=str(payload["task_run_id"]),
            workflow_run_id=str(payload["workflow_run_id"]),
        )
        principal_actor = payload.get("principal_actor")
        if principal_actor is not None:
            if not isinstance(principal_actor, dict):
                raise CommandError(
                    code="invalid_principal_actor",
                    message="principal_actor must be an object",
                    details={},
                )
            actor_type = principal_actor.get("type")
            actor_id = principal_actor.get("id")
            if actor_type is None or actor_id is None:
                raise CommandError(
                    code="invalid_principal_actor",
                    message="principal_actor requires type and id",
                    details={},
                )
            _assert_actor_type(str(actor_type))
        budget = payload.get("budget")
        if budget is not None and not isinstance(budget, dict):
            raise CommandError(
                code="invalid_execution_budget",
                message="budget must be a JSON object",
                details={},
            )
        now = utc_now_iso()
        create_execution_session(
            connection,
            execution_session_id=execution_session_id,
            workflow_run_id=str(payload["workflow_run_id"]),
            task_run_id=str(payload["task_run_id"]),
            execution_spec_id=str(payload["execution_spec_id"]),
            state="CREATED",
            owner_mode=owner_mode,
            principal_actor=principal_actor if isinstance(principal_actor, dict) else None,
            budget=budget if isinstance(budget, dict) else None,
            tool_call_count=int(payload.get("tool_call_count", 0)),
            created_at=now,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="execution.session.created",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": str(payload["workflow_run_id"])},
                    {"rel": "subject", "type": "task_run", "id": str(payload["task_run_id"])},
                    {"rel": "subject", "type": "execution_session", "id": execution_session_id},
                    {
                        "rel": "uses_execution_spec",
                        "type": "execution_spec",
                        "id": str(payload["execution_spec_id"]),
                    },
                ],
                payload={
                    "execution_session_id": execution_session_id,
                    "execution_spec_id": str(payload["execution_spec_id"]),
                    "owner_mode": owner_mode,
                    "principal_actor_type": (
                        str(principal_actor["type"])
                        if isinstance(principal_actor, dict)
                        and principal_actor.get("type") is not None
                        else None
                    ),
                },
                idempotency_key=event_idempotency,
            ),
        )

        if initial_state != "CREATED":
            transitioned = transition_execution_session_state(
                connection,
                execution_session_id=execution_session_id,
                from_states=["CREATED"],
                to_state=initial_state,
                updated_at=now,
                closed_at=(now if initial_state in {"SUCCEEDED", "FAILED", "CANCELED"} else None),
            )
            if transitioned is None:
                raise CommandError(
                    code="execution_session_transition_conflict",
                    message="execution session transition failed during creation",
                    details={"execution_session_id": execution_session_id},
                )
            append_event(
                connection,
                _event_envelope(
                    event_type="execution.session.state_changed",
                    tenant_id=workflow_scope["tenant_id"],
                    domain_id=workflow_scope["domain_id"],
                    actor_type=str(payload.get("actor_type", "system")),
                    actor_id=str(payload.get("actor_id", "system:runtime")),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(payload["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": str(payload["task_run_id"])},
                        {"rel": "subject", "type": "execution_session", "id": execution_session_id},
                    ],
                    payload={
                        "execution_session_id": execution_session_id,
                        "from_state": "CREATED",
                        "to_state": initial_state,
                        "reason": "initial_state",
                    },
                    idempotency_key=state_event_idempotency,
                ),
            )
        session = get_execution_session(connection, execution_session_id)
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found after creation",
                details={"execution_session_id": execution_session_id},
            )
        return session

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=_operation,
        )
    except sqlite3.IntegrityError as exc:
        if "execution_sessions.execution_session_id" in str(exc):
            raise CommandError(
                code="duplicate_execution_session_id",
                message="execution_session_id already exists",
                details={"execution_session_id": execution_session_id},
            ) from exc
        raise

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def request_tool_execution_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "execution_session_id",
            "tool_class",
            "idempotency_key",
        ],
    )
    receipt = _prepare_command_receipt(
        command_name="tool-executions.request",
        payload=payload,
        fingerprint_payload={
            "tool_execution_id": payload.get("tool_execution_id"),
            "execution_session_id": str(payload["execution_session_id"]),
            "tool_class": str(payload["tool_class"]),
            "tool_name": (
                str(payload["tool_name"])
                if payload.get("tool_name") is not None
                else None
            ),
            "attempt_no": int(payload.get("attempt_no", 0)),
            "actor_id": str(payload.get("actor_id", "system:runtime")),
            "actor_type": str(payload.get("actor_type", "system")),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=None,
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "tool-executions.request.tool.execution.requested",
    )
    tool_execution_id = str(payload.get("tool_execution_id") or f"tx-{uuid4()}")

    def _operation() -> dict[str, Any]:
        session = get_execution_session(connection, str(payload["execution_session_id"]))
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found for tool execution request",
                details={"execution_session_id": str(payload["execution_session_id"])},
            )
        if str(session["state"]) in {"SUCCEEDED", "FAILED", "CANCELED"}:
            raise CommandError(
                code="execution_session_closed",
                message="tool execution cannot be requested on a closed session",
                details={
                    "execution_session_id": str(payload["execution_session_id"]),
                    "state": str(session["state"]),
                },
            )
        workflow_scope = _workflow_scope(connection, str(session["workflow_run_id"]))
        now = utc_now_iso()
        create_tool_execution(
            connection,
            tool_execution_id=tool_execution_id,
            execution_session_id=str(payload["execution_session_id"]),
            tool_class=str(payload["tool_class"]),
            tool_name=(
                str(payload["tool_name"])
                if payload.get("tool_name") is not None
                else None
            ),
            state="REQUESTED",
            idempotency_key=str(payload["idempotency_key"]),
            attempt_no=int(payload.get("attempt_no", 0)),
            policy_decision_id=None,
            output_artifact_version_ids=None,
            requested_at=now,
            completed_at=None,
            error_code=None,
        )
        incremented = increment_tool_call_count(
            connection,
            execution_session_id=str(payload["execution_session_id"]),
            updated_at=now,
        )
        if incremented is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found while incrementing tool call count",
                details={"execution_session_id": str(payload["execution_session_id"])},
            )
        append_event(
            connection,
            _event_envelope(
                event_type="tool.execution.requested",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                    {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                    {
                        "rel": "subject",
                        "type": "execution_session",
                        "id": str(session["execution_session_id"]),
                    },
                    {"rel": "subject", "type": "tool_execution", "id": tool_execution_id},
                ],
                payload={
                    "tool_execution_id": tool_execution_id,
                    "tool_class": str(payload["tool_class"]),
                    "idempotency_key": str(payload["idempotency_key"]),
                    "tool_name": (
                        str(payload["tool_name"])
                        if payload.get("tool_name") is not None
                        else None
                    ),
                },
                idempotency_key=event_idempotency,
            ),
        )
        tool_execution = get_tool_execution(connection, tool_execution_id)
        if tool_execution is None:
            raise CommandError(
                code="tool_execution_not_found",
                message="tool execution not found after request",
                details={"tool_execution_id": tool_execution_id},
            )
        return tool_execution

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=_operation,
        )
    except sqlite3.IntegrityError as exc:
        if "tool_executions.tool_execution_id" in str(exc):
            raise CommandError(
                code="duplicate_tool_execution_id",
                message="tool_execution_id already exists",
                details={"tool_execution_id": tool_execution_id},
            ) from exc
        if "uq_tool_executions_session_idempotency" in str(exc):
            existing = get_tool_execution_by_session_idempotency(
                connection,
                execution_session_id=str(payload["execution_session_id"]),
                idempotency_key=str(payload["idempotency_key"]),
            )
            if existing is not None:
                result = existing
                replay = True
            else:
                raise CommandError(
                    code="duplicate_tool_execution_idempotency",
                    message="tool execution idempotency key already exists in session",
                    details={
                        "execution_session_id": str(payload["execution_session_id"]),
                        "idempotency_key": str(payload["idempotency_key"]),
                    },
                ) from exc
        else:
            raise

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def evaluate_policy_decision_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "tool_execution_id",
            "decision",
            "principal_actor",
            "idempotency_key",
        ],
    )
    decision = str(payload["decision"])
    if decision not in POLICY_DECISIONS:
        raise CommandError(
            code="invalid_policy_decision",
            message=f"unsupported policy decision: {decision}",
            details={"allowed_decisions": sorted(POLICY_DECISIONS)},
        )
    principal_actor = payload.get("principal_actor")
    if not isinstance(principal_actor, dict):
        raise CommandError(
            code="invalid_principal_actor",
            message="principal_actor must be a JSON object",
            details={},
        )
    if principal_actor.get("id") is None or principal_actor.get("type") is None:
        raise CommandError(
            code="invalid_principal_actor",
            message="principal_actor requires id and type",
            details={},
        )
    _assert_actor_type(str(principal_actor["type"]))
    policy_event_suffix = (
        "tool-executions.evaluate.tool.execution.approved"
        if decision == "allow"
        else "tool-executions.evaluate.tool.execution.denied"
    )
    tool_event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        policy_event_suffix,
    )
    session_event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "tool-executions.evaluate.execution.session.state_changed",
    )
    policy_decision_id = str(payload.get("policy_decision_id") or f"pd-{uuid4()}")

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, tool_event_idempotency)
        tool_execution = get_tool_execution(connection, str(payload["tool_execution_id"]))
        if tool_execution is None:
            raise CommandError(
                code="tool_execution_not_found",
                message="tool execution not found",
                details={"tool_execution_id": str(payload["tool_execution_id"])},
            )
        if str(tool_execution["state"]) != "REQUESTED":
            raise CommandError(
                code="tool_execution_not_requestable",
                message="policy decision can only be evaluated from REQUESTED state",
                details={
                    "tool_execution_id": str(payload["tool_execution_id"]),
                    "state": str(tool_execution["state"]),
                },
            )
        session = get_execution_session(connection, str(tool_execution["execution_session_id"]))
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found for tool execution",
                details={"execution_session_id": str(tool_execution["execution_session_id"])},
            )
        session_state = str(session["state"])
        if session_state in {"SUCCEEDED", "FAILED", "CANCELED"}:
            raise CommandError(
                code="execution_session_closed",
                message="policy decision cannot be evaluated for a closed execution session",
                details={
                    "execution_session_id": str(session["execution_session_id"]),
                    "state": session_state,
                },
            )
        needs_session_transition_event = decision != "allow" or session_state != "RUNNING"
        if needs_session_transition_event:
            _assert_idempotency_available(connection, session_event_idempotency)
        workflow_scope = _workflow_scope(connection, str(session["workflow_run_id"]))
        now = utc_now_iso()
        create_policy_decision(
            connection,
            policy_decision_id=policy_decision_id,
            principal_actor={
                "type": str(principal_actor["type"]),
                "id": str(principal_actor["id"]),
                "display": (
                    str(principal_actor["display"])
                    if principal_actor.get("display") is not None
                    else None
                ),
            },
            decision=decision,
            reason_code=(
                str(payload["reason_code"])
                if payload.get("reason_code") is not None
                else None
            ),
            required_approval_action=(
                str(payload["required_approval_action"])
                if payload.get("required_approval_action") is not None
                else None
            ),
            tool_execution_id=str(payload["tool_execution_id"]),
            decided_at=now,
        )
        if decision == "allow":
            transitioned_tool = transition_tool_execution_state(
                connection,
                tool_execution_id=str(payload["tool_execution_id"]),
                from_states=["REQUESTED"],
                to_state="APPROVED",
                policy_decision_id=policy_decision_id,
                output_artifact_version_ids=None,
                completed_at=None,
                error_code=None,
            )
            if transitioned_tool is None:
                raise CommandError(
                    code="tool_execution_transition_conflict",
                    message="tool execution transition raced during policy allow",
                    details={"tool_execution_id": str(payload["tool_execution_id"])},
                )
            append_event(
                connection,
                _event_envelope(
                    event_type="tool.execution.approved",
                    tenant_id=workflow_scope["tenant_id"],
                    domain_id=workflow_scope["domain_id"],
                    actor_type=str(principal_actor["type"]),
                    actor_id=str(principal_actor["id"]),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                        {
                            "rel": "subject",
                            "type": "execution_session",
                            "id": str(session["execution_session_id"]),
                        },
                        {"rel": "subject", "type": "tool_execution", "id": str(payload["tool_execution_id"])},
                        {"rel": "subject", "type": "policy_decision", "id": policy_decision_id},
                    ],
                    payload={
                        "tool_execution_id": str(payload["tool_execution_id"]),
                        "tool_class": str(tool_execution["tool_class"]),
                        "policy_decision_id": policy_decision_id,
                    },
                    idempotency_key=tool_event_idempotency,
                ),
            )
            transitioned_session = session
            if session_state != "RUNNING":
                transitioned_session = transition_execution_session_state(
                    connection,
                    execution_session_id=str(session["execution_session_id"]),
                    from_states=["CREATED", "WAITING_POLICY", "PAUSED"],
                    to_state="RUNNING",
                    updated_at=now,
                    closed_at=None,
                )
                if transitioned_session is None:
                    raise CommandError(
                        code="execution_session_transition_conflict",
                        message="execution session transition raced during policy allow",
                        details={"execution_session_id": str(session["execution_session_id"])},
                    )
                append_event(
                    connection,
                    _event_envelope(
                        event_type="execution.session.state_changed",
                        tenant_id=workflow_scope["tenant_id"],
                        domain_id=workflow_scope["domain_id"],
                        actor_type=str(principal_actor["type"]),
                        actor_id=str(principal_actor["id"]),
                        links=[
                            {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                            {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                            {
                                "rel": "subject",
                                "type": "execution_session",
                                "id": str(session["execution_session_id"]),
                            },
                        ],
                        payload={
                            "execution_session_id": str(session["execution_session_id"]),
                            "from_state": session_state,
                            "to_state": "RUNNING",
                            "reason": "policy_allow",
                        },
                        idempotency_key=session_event_idempotency,
                    ),
                )
            return_payload = {
                "tool_execution": transitioned_tool,
                "policy_decision": get_policy_decision(connection, policy_decision_id),
                "execution_session": transitioned_session,
            }
        else:
            denial_reason = (
                str(payload["reason_code"])
                if payload.get("reason_code") is not None
                else decision
            )
            transitioned_tool = transition_tool_execution_state(
                connection,
                tool_execution_id=str(payload["tool_execution_id"]),
                from_states=["REQUESTED"],
                to_state="DENIED",
                policy_decision_id=policy_decision_id,
                output_artifact_version_ids=None,
                completed_at=now,
                error_code=denial_reason,
            )
            if transitioned_tool is None:
                raise CommandError(
                    code="tool_execution_transition_conflict",
                    message="tool execution transition raced during policy denial",
                    details={"tool_execution_id": str(payload["tool_execution_id"])},
                )
            append_event(
                connection,
                _event_envelope(
                    event_type="tool.execution.denied",
                    tenant_id=workflow_scope["tenant_id"],
                    domain_id=workflow_scope["domain_id"],
                    actor_type=str(principal_actor["type"]),
                    actor_id=str(principal_actor["id"]),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                        {
                            "rel": "subject",
                            "type": "execution_session",
                            "id": str(session["execution_session_id"]),
                        },
                        {"rel": "subject", "type": "tool_execution", "id": str(payload["tool_execution_id"])},
                        {"rel": "subject", "type": "policy_decision", "id": policy_decision_id},
                    ],
                    payload={
                        "tool_execution_id": str(payload["tool_execution_id"]),
                        "tool_class": str(tool_execution["tool_class"]),
                        "policy_decision_id": policy_decision_id,
                        "denial_reason": denial_reason,
                    },
                    idempotency_key=tool_event_idempotency,
                ),
            )
            target_session_state = "WAITING_APPROVAL" if decision == "require_approval" else "FAILED"
            transitioned_session = transition_execution_session_state(
                connection,
                execution_session_id=str(session["execution_session_id"]),
                from_states=["CREATED", "RUNNING", "WAITING_POLICY", "PAUSED"],
                to_state=target_session_state,
                updated_at=now,
                closed_at=(now if target_session_state == "FAILED" else None),
            )
            if transitioned_session is None:
                raise CommandError(
                    code="execution_session_transition_conflict",
                    message="execution session transition raced during policy denial",
                    details={"execution_session_id": str(session["execution_session_id"])},
                )
            append_event(
                connection,
                _event_envelope(
                    event_type="execution.session.state_changed",
                    tenant_id=workflow_scope["tenant_id"],
                    domain_id=workflow_scope["domain_id"],
                    actor_type=str(principal_actor["type"]),
                    actor_id=str(principal_actor["id"]),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                        {
                            "rel": "subject",
                            "type": "execution_session",
                            "id": str(session["execution_session_id"]),
                        },
                    ],
                    payload={
                        "execution_session_id": str(session["execution_session_id"]),
                        "from_state": session_state,
                        "to_state": target_session_state,
                        "reason": f"policy_{decision}",
                    },
                    idempotency_key=session_event_idempotency,
                ),
            )
            return_payload = {
                "tool_execution": transitioned_tool,
                "policy_decision": get_policy_decision(connection, policy_decision_id),
                "execution_session": transitioned_session,
            }
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "policy_decisions.policy_decision_id" in str(exc):
            raise CommandError(
                code="duplicate_policy_decision_id",
                message="policy_decision_id already exists",
                details={"policy_decision_id": policy_decision_id},
            ) from exc
        if "uq_policy_decisions_tool_execution_id" in str(exc):
            existing = get_policy_decision_for_tool_execution(
                connection,
                tool_execution_id=str(payload["tool_execution_id"]),
            )
            if existing is not None:
                existing_tool = get_tool_execution(connection, str(payload["tool_execution_id"]))
                if existing_tool is None:
                    raise CommandError(
                        code="tool_execution_not_found",
                        message="tool execution not found while resolving duplicate policy decision",
                        details={"tool_execution_id": str(payload["tool_execution_id"])},
                    ) from exc
                return {
                    "tool_execution": existing_tool,
                    "policy_decision": existing,
                    "execution_session": get_execution_session(
                        connection,
                        str(existing_tool["execution_session_id"]),
                    ),
                }
            raise CommandError(
                code="duplicate_policy_decision",
                message="policy decision already exists for this tool execution",
                details={"tool_execution_id": str(payload["tool_execution_id"])},
            ) from exc
        raise
    except Exception:
        connection.rollback()
        raise
    connection.commit()
    return return_payload


def start_tool_execution_attempt_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["tool_execution_id", "lease_token"],
    )
    requested_tool_execution_attempt_id = payload.get("tool_execution_attempt_id")
    tool_execution_attempt_id = str(requested_tool_execution_attempt_id or f"txa-{uuid4()}")
    lease_token = str(payload["lease_token"])
    _begin_transaction(connection)
    try:
        tool_execution = get_tool_execution(connection, str(payload["tool_execution_id"]))
        if tool_execution is None:
            raise CommandError(
                code="tool_execution_not_found",
                message="tool execution not found",
                details={"tool_execution_id": str(payload["tool_execution_id"])},
            )
        if str(tool_execution["state"]) not in {"APPROVED", "RUNNING"}:
            raise CommandError(
                code="tool_execution_not_attemptable",
                message="tool execution attempts can only start from APPROVED or RUNNING",
                details={
                    "tool_execution_id": str(payload["tool_execution_id"]),
                    "state": str(tool_execution["state"]),
                },
            )
        session = get_execution_session(connection, str(tool_execution["execution_session_id"]))
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found for tool execution",
                details={"execution_session_id": str(tool_execution["execution_session_id"])},
            )
        active = get_active_tool_execution_attempt(
            connection,
            tool_execution_id=str(payload["tool_execution_id"]),
        )
        if active is not None:
            if (
                active["lease_token"] == lease_token
                and (
                    requested_tool_execution_attempt_id is None
                    or active["tool_execution_attempt_id"] == tool_execution_attempt_id
                )
            ):
                connection.rollback()
                return active
            raise CommandError(
                code="tool_execution_attempt_active_conflict",
                message="tool execution already has an active attempt",
                details={
                    "tool_execution_id": str(payload["tool_execution_id"]),
                    "active_tool_execution_attempt_id": active["tool_execution_attempt_id"],
                },
            )
        now = utc_now_iso()
        attempt = create_tool_execution_attempt(
            connection,
            tool_execution_attempt_id=tool_execution_attempt_id,
            tool_execution_id=str(payload["tool_execution_id"]),
            execution_session_id=str(tool_execution["execution_session_id"]),
            lease_token=lease_token,
            started_at=now,
        )
        if str(tool_execution["state"]) == "APPROVED":
            transitioned = transition_tool_execution_state(
                connection,
                tool_execution_id=str(payload["tool_execution_id"]),
                from_states=["APPROVED"],
                to_state="RUNNING",
                policy_decision_id=tool_execution.get("policy_decision_id"),
                output_artifact_version_ids=None,
                completed_at=None,
                error_code=None,
            )
            if transitioned is None:
                raise CommandError(
                    code="tool_execution_transition_conflict",
                    message="tool execution transition failed while starting attempt",
                    details={"tool_execution_id": str(payload["tool_execution_id"])},
                )
        connection.commit()
        return attempt
    except ToolExecutionAttemptError as exc:
        connection.rollback()
        raise _attempt_error_to_command_error(exc) from exc
    except Exception:
        connection.rollback()
        raise


def complete_tool_execution_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["tool_execution_id", "result", "idempotency_key"],
    )
    result = str(payload["result"])
    if result not in {"succeeded", "failed", "canceled"}:
        raise CommandError(
            code="invalid_tool_execution_result",
            message=f"unsupported tool execution result: {result}",
            details={"allowed_results": ["succeeded", "failed", "canceled"]},
        )
    receipt = _prepare_command_receipt(
        command_name="tool-executions.complete",
        payload=payload,
        fingerprint_payload={
            "tool_execution_id": str(payload["tool_execution_id"]),
            "tool_execution_attempt_id": (
                str(payload["tool_execution_attempt_id"])
                if payload.get("tool_execution_attempt_id") is not None
                else None
            ),
            "lease_token": (
                str(payload["lease_token"])
                if payload.get("lease_token") is not None
                else None
            ),
            "result": result,
            "output_artifact_version_ids": payload.get("output_artifact_version_ids"),
            "error_code": payload.get("error_code"),
            "actor_id": payload.get("actor_id", "system:runtime"),
            "actor_type": payload.get("actor_type", "system"),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=None,
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "tool-executions.complete.tool.execution.completed",
    )
    to_state = (
        "COMPLETED"
        if result == "succeeded"
        else ("CANCELED" if result == "canceled" else "FAILED")
    )

    def _operation() -> dict[str, Any]:
        tool_execution = get_tool_execution(connection, str(payload["tool_execution_id"]))
        if tool_execution is None:
            raise CommandError(
                code="tool_execution_not_found",
                message="tool execution not found",
                details={"tool_execution_id": str(payload["tool_execution_id"])},
            )
        active_attempt = get_active_tool_execution_attempt(
            connection,
            tool_execution_id=str(payload["tool_execution_id"]),
        )
        has_attempt_completion_fields = (
            payload.get("tool_execution_attempt_id") is not None
            or payload.get("lease_token") is not None
        )
        if active_attempt is None and has_attempt_completion_fields:
            raise CommandError(
                code="tool_execution_attempt_stale_completion",
                message="tool execution attempt is no longer active",
                details={"tool_execution_id": str(payload["tool_execution_id"])},
            )
        if str(tool_execution["state"]) not in {"APPROVED", "RUNNING"}:
            raise CommandError(
                code="tool_execution_not_completable",
                message="tool execution can only complete from APPROVED or RUNNING",
                details={
                    "tool_execution_id": str(payload["tool_execution_id"]),
                    "state": str(tool_execution["state"]),
                },
            )
        session = get_execution_session(connection, str(tool_execution["execution_session_id"]))
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found for tool execution",
                details={"execution_session_id": str(tool_execution["execution_session_id"])},
            )
        workflow_scope = _workflow_scope(connection, str(session["workflow_run_id"]))
        if active_attempt is not None:
            if (
                payload.get("tool_execution_attempt_id") is None
                or payload.get("lease_token") is None
            ):
                raise CommandError(
                    code="tool_execution_attempt_lease_required",
                    message="active tool execution attempt requires attempt id and lease token",
                    details={"tool_execution_id": str(payload["tool_execution_id"])},
                )
        output_artifact_version_ids = payload.get("output_artifact_version_ids")
        if output_artifact_version_ids is not None:
            if not isinstance(output_artifact_version_ids, list):
                raise CommandError(
                    code="invalid_output_artifact_version_ids",
                    message="output_artifact_version_ids must be a list when provided",
                    details={},
                )
            for artifact_version_id in output_artifact_version_ids:
                artifact = get_artifact_version(connection, str(artifact_version_id))
                if artifact is None:
                    raise CommandError(
                        code="artifact_version_not_found",
                        message="output artifact version id was not found",
                        details={"artifact_version_id": str(artifact_version_id)},
                    )
                if str(artifact["workflow_run_id"]) != str(session["workflow_run_id"]):
                    raise CommandError(
                        code="cross_workflow_artifact_reference",
                        message="output artifact version belongs to a different workflow_run",
                        details={
                            "artifact_version_id": str(artifact_version_id),
                            "artifact_workflow_run_id": str(artifact["workflow_run_id"]),
                            "workflow_run_id": str(session["workflow_run_id"]),
                        },
                    )
        now = utc_now_iso()
        if active_attempt is not None:
            try:
                complete_tool_execution_attempt(
                    connection,
                    tool_execution_attempt_id=str(payload["tool_execution_attempt_id"]),
                    tool_execution_id=str(payload["tool_execution_id"]),
                    lease_token=str(payload["lease_token"]),
                    state=to_state,
                    output_artifact_version_ids=(
                        [str(item) for item in output_artifact_version_ids]
                        if isinstance(output_artifact_version_ids, list)
                        else None
                    ),
                    completed_at=now,
                    error_code=(
                        str(payload["error_code"])
                        if payload.get("error_code") is not None
                        else None
                    ),
                )
            except ToolExecutionAttemptError as exc:
                raise _attempt_error_to_command_error(exc) from exc
        transitioned = transition_tool_execution_state(
            connection,
            tool_execution_id=str(payload["tool_execution_id"]),
            from_states=["APPROVED", "RUNNING"],
            to_state=to_state,
            policy_decision_id=tool_execution.get("policy_decision_id"),
            output_artifact_version_ids=(
                [str(item) for item in output_artifact_version_ids]
                if isinstance(output_artifact_version_ids, list)
                else None
            ),
            completed_at=now,
            error_code=(
                str(payload["error_code"])
                if payload.get("error_code") is not None
                else None
            ),
        )
        if transitioned is None:
            raise CommandError(
                code="tool_execution_transition_conflict",
                message="tool execution transition failed",
                details={"tool_execution_id": str(payload["tool_execution_id"])},
            )
        append_event(
            connection,
            _event_envelope(
                event_type="tool.execution.completed",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                    {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                    {
                        "rel": "subject",
                        "type": "execution_session",
                        "id": str(session["execution_session_id"]),
                    },
                    {"rel": "subject", "type": "tool_execution", "id": str(payload["tool_execution_id"])},
                ],
                payload={
                    "tool_execution_id": str(payload["tool_execution_id"]),
                    "tool_class": str(tool_execution["tool_class"]),
                    "result": result,
                    "output_artifact_version_ids": (
                        [str(item) for item in output_artifact_version_ids]
                        if isinstance(output_artifact_version_ids, list)
                        and output_artifact_version_ids
                        else None
                    ),
                },
                idempotency_key=event_idempotency,
            ),
        )
        completed = get_tool_execution(connection, str(payload["tool_execution_id"]))
        if completed is None:
            raise CommandError(
                code="tool_execution_not_found",
                message="tool execution not found after completion",
                details={"tool_execution_id": str(payload["tool_execution_id"])},
            )
        return completed

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


def transition_execution_session_state_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["execution_session_id", "to_state", "idempotency_key"],
    )
    to_state = str(payload["to_state"])
    if to_state not in EXECUTION_SESSION_STATES:
        raise CommandError(
            code="invalid_execution_session_state",
            message=f"unsupported execution session state: {to_state}",
            details={"allowed_states": sorted(EXECUTION_SESSION_STATES)},
        )
    receipt = _prepare_command_receipt(
        command_name="execution-sessions.transition",
        payload=payload,
        fingerprint_payload={
            "execution_session_id": str(payload["execution_session_id"]),
            "to_state": to_state,
            "reason": (
                str(payload["reason"])
                if payload.get("reason") is not None
                else None
            ),
            "actor_id": payload.get("actor_id", "system:runtime"),
            "actor_type": payload.get("actor_type", "system"),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=None,
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "execution-sessions.transition.execution.session.state_changed",
    )

    def _operation() -> dict[str, Any]:
        session = get_execution_session(connection, str(payload["execution_session_id"]))
        if session is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found",
                details={"execution_session_id": str(payload["execution_session_id"])},
            )
        from_state = str(session["state"])
        if from_state == to_state:
            raise CommandError(
                code="execution_session_already_in_state",
                message="execution session already in requested state",
                details={
                    "execution_session_id": str(payload["execution_session_id"]),
                    "state": from_state,
                },
            )
        workflow_scope = _workflow_scope(connection, str(session["workflow_run_id"]))
        now = utc_now_iso()
        transitioned = transition_execution_session_state(
            connection,
            execution_session_id=str(payload["execution_session_id"]),
            from_states=[from_state],
            to_state=to_state,
            updated_at=now,
            closed_at=(now if to_state in {"SUCCEEDED", "FAILED", "CANCELED"} else None),
        )
        if transitioned is None:
            raise CommandError(
                code="execution_session_transition_conflict",
                message="execution session transition raced",
                details={"execution_session_id": str(payload["execution_session_id"])},
            )
        append_event(
            connection,
            _event_envelope(
                event_type="execution.session.state_changed",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                    {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                    {"rel": "subject", "type": "execution_session", "id": str(payload["execution_session_id"])},
                ],
                payload={
                    "execution_session_id": str(payload["execution_session_id"]),
                    "from_state": from_state,
                    "to_state": to_state,
                    "reason": (
                        str(payload["reason"])
                        if payload.get("reason") is not None
                        else None
                    ),
                },
                idempotency_key=event_idempotency,
            ),
        )
        transitioned = get_execution_session(connection, str(payload["execution_session_id"]))
        if transitioned is None:
            raise CommandError(
                code="execution_session_not_found",
                message="execution session not found after transition",
                details={"execution_session_id": str(payload["execution_session_id"])},
            )
        return transitioned

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


def reconcile_executions_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    now_iso = str(payload.get("now") or utc_now_iso())
    stale_seconds = int(payload.get("stale_seconds", 300))
    if stale_seconds < 0:
        raise CommandError(
            code="invalid_stale_seconds",
            message="stale_seconds must be >= 0",
            details={"stale_seconds": stale_seconds},
        )
    now_dt = _parse_iso_datetime(now_iso)
    stale_before = (now_dt - timedelta(seconds=stale_seconds)).isoformat().replace("+00:00", "Z")

    _begin_transaction(connection)
    processed: list[dict[str, Any]] = []
    try:
        sessions = list_reconcilable_execution_sessions(
            connection,
            stale_before_iso=stale_before,
        )
        for session in sessions:
            workflow_scope = _workflow_scope(connection, str(session["workflow_run_id"]))
            open_tools = [
                row
                for row in list_tool_executions_for_session(
                    connection,
                    str(session["execution_session_id"]),
                )
                if str(row["state"]) in {"REQUESTED", "APPROVED", "RUNNING"}
            ]
            failed_tool_ids: list[str] = []
            for tool in open_tools:
                transitioned_tool = transition_tool_execution_state(
                    connection,
                    tool_execution_id=str(tool["tool_execution_id"]),
                    from_states=["REQUESTED", "APPROVED", "RUNNING"],
                    to_state="FAILED",
                    policy_decision_id=tool.get("policy_decision_id"),
                    output_artifact_version_ids=tool.get("output_artifact_version_ids"),
                    completed_at=now_iso,
                    error_code="execution_reconcile_timeout",
                )
                if transitioned_tool is None:
                    continue
                failed_tool_ids.append(str(tool["tool_execution_id"]))
                append_event(
                    connection,
                    _event_envelope(
                        event_type="tool.execution.completed",
                        tenant_id=workflow_scope["tenant_id"],
                        domain_id=workflow_scope["domain_id"],
                        actor_type="system",
                        actor_id="system:execution-reconcile",
                        links=[
                            {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                            {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                            {
                                "rel": "subject",
                                "type": "execution_session",
                                "id": str(session["execution_session_id"]),
                            },
                            {"rel": "subject", "type": "tool_execution", "id": str(tool["tool_execution_id"])},
                        ],
                        payload={
                            "tool_execution_id": str(tool["tool_execution_id"]),
                            "tool_class": str(tool["tool_class"]),
                            "result": "failed",
                            "output_artifact_version_ids": None,
                        },
                        idempotency_key=None,
                    ),
                )
            transitioned_session = transition_execution_session_state(
                connection,
                execution_session_id=str(session["execution_session_id"]),
                from_states=["CREATED", "RUNNING", "WAITING_POLICY", "WAITING_APPROVAL"],
                to_state="FAILED",
                updated_at=now_iso,
                closed_at=now_iso,
            )
            if transitioned_session is None:
                continue
            append_event(
                connection,
                _event_envelope(
                    event_type="execution.session.state_changed",
                    tenant_id=workflow_scope["tenant_id"],
                    domain_id=workflow_scope["domain_id"],
                    actor_type="system",
                    actor_id="system:execution-reconcile",
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(session["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": str(session["task_run_id"])},
                        {
                            "rel": "subject",
                            "type": "execution_session",
                            "id": str(session["execution_session_id"]),
                        },
                    ],
                    payload={
                        "execution_session_id": str(session["execution_session_id"]),
                        "from_state": str(session["state"]),
                        "to_state": "FAILED",
                        "reason": "reconcile_timeout",
                    },
                    idempotency_key=None,
                ),
            )
            processed.append(
                {
                    "execution_session_id": str(session["execution_session_id"]),
                    "workflow_run_id": str(session["workflow_run_id"]),
                    "task_run_id": str(session["task_run_id"]),
                    "failed_tool_execution_ids": failed_tool_ids,
                }
            )
    except Exception:
        connection.rollback()
        raise
    connection.commit()
    return {
        "now": now_iso,
        "stale_before": stale_before,
        "processed_count": len(processed),
        "processed": processed,
    }
