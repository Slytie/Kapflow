from __future__ import annotations

import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _assert_actor_type,
    _assert_idempotency_available,
    _begin_transaction,
    _command_receipt_payload,
    _decision_has_reason,
    _event_envelope,
    _event_idempotency_key,
    _execute_with_command_receipt,
    _forbidden_command_error,
    _prepare_command_receipt,
    _principal_from_payload,
    _receipt_event_idempotency_key,
    _require_fields,
    _workflow_scope,
)
from onetruth.application.services.schedule_planning_stage07 import (
    build_stage07_issue_activation_key,
)
from onetruth.infrastructure.events.event_store import (
    append_event,
    utc_now_iso,
)
from onetruth.infrastructure.repositories.flags import (
    create_flag,
    get_flag,
    list_open_flags_for_workflow_run,
    transition_flag_state,
)
from onetruth.infrastructure.repositories.human_tasks import (
    create_human_task,
    get_human_task_by_task_run_id,
)
from onetruth.infrastructure.repositories.task_runs import (
    create_task_run,
    get_task_run_by_activation_key,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run

FLAG_STATES = {"open", "triage", "blocked", "resolved", "closed", "waived"}
FLAG_ACTIVE_STATES = {"open", "triage", "blocked"}
FLAG_SEVERITIES = {"info", "low", "medium", "high", "critical"}
FLAG_ALLOWED_TRANSITIONS = {
    "open": {"triage", "blocked", "resolved", "closed", "waived"},
    "triage": {"blocked", "resolved", "closed", "waived"},
    "blocked": {"triage", "resolved", "closed", "waived"},
    "resolved": {"closed"},
    "closed": set(),
    "waived": set(),
}


def create_flag_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["workflow_run_id", "kind", "severity", "summary", "idempotency_key"],
    )
    severity = str(payload["severity"])
    if severity not in FLAG_SEVERITIES:
        raise CommandError(
            code="invalid_flag_severity",
            message=f"unsupported flag severity: {severity}",
            details={"allowed_severities": sorted(FLAG_SEVERITIES)},
        )
    state = str(payload.get("state", "open"))
    if state not in FLAG_STATES:
        raise CommandError(
            code="invalid_flag_state",
            message=f"unsupported flag state: {state}",
            details={"allowed_states": sorted(FLAG_STATES)},
        )

    details_json = payload.get("details_json") or {}
    if not isinstance(details_json, dict):
        raise CommandError(
            code="invalid_flag_details",
            message="details_json must be a JSON object",
            details={},
        )
    requested_flag_id = payload.get("flag_id")
    flag_id = str(requested_flag_id or f"fl-{uuid4()}")
    receipt = _prepare_command_receipt(
        command_name="flags.create",
        payload=payload,
        fingerprint_payload={
            "flag_id": str(requested_flag_id) if requested_flag_id is not None else None,
            "workflow_run_id": str(payload["workflow_run_id"]),
            "kind": str(payload["kind"]),
            "severity": severity,
            "state": state,
            "summary": str(payload["summary"]),
            "details_json": details_json,
            "assigned_group": (
                str(payload["assigned_group"])
                if payload.get("assigned_group") is not None
                else None
            ),
            "source_event_id": (
                str(payload["source_event_id"])
                if payload.get("source_event_id") is not None
                else None
            ),
            "dedupe_key": (
                str(payload["dedupe_key"])
                if payload.get("dedupe_key") is not None
                else str(payload["idempotency_key"])
            ),
            "created_by": payload.get("created_by"),
            "actor_id": payload.get("actor_id", "system:runtime"),
            "actor_type": payload.get("actor_type", "system"),
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=str(payload["workflow_run_id"]),
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "flags.create.flag.created",
    )

    def _operation() -> dict[str, Any]:
        workflow_run = get_workflow_run(connection, str(payload["workflow_run_id"]))
        if workflow_run is None:
            raise CommandError(
                code="workflow_run_not_found",
                message="workflow run not found for flag creation",
                details={"workflow_run_id": str(payload["workflow_run_id"])},
            )

        created_by = payload.get("created_by") or {}
        created_by_actor_id = str(
            created_by.get("id")
            or payload.get("actor_id")
            or payload.get("created_by_actor_id")
            or "system:runtime"
        )
        created_by_actor_type = str(
            created_by.get("type")
            or payload.get("actor_type")
            or payload.get("created_by_actor_type")
            or "system"
        )
        _assert_actor_type(created_by_actor_type)
        now = utc_now_iso()
        create_flag(
            connection,
            flag_id=flag_id,
            workflow_run_id=str(payload["workflow_run_id"]),
            tenant_id=str(workflow_run["tenant_id"]),
            domain_id=str(workflow_run["domain_id"]),
            workflow_id=str(workflow_run["workflow_id"]),
            partition_key=str(workflow_run["partition_key"]),
            kind=str(payload["kind"]),
            severity=severity,
            state=state,
            summary=str(payload["summary"]),
            details_json=details_json,
            assigned_group=(
                str(payload["assigned_group"])
                if payload.get("assigned_group") is not None
                else None
            ),
            created_at=now,
            closed_at=(now if state in {"closed", "waived"} else None),
            created_by_actor_id=created_by_actor_id,
            created_by_actor_type=created_by_actor_type,
            source_event_id=(
                str(payload["source_event_id"])
                if payload.get("source_event_id") is not None
                else None
            ),
            dedupe_key=(
                str(payload["dedupe_key"])
                if payload.get("dedupe_key") is not None
                else str(payload["idempotency_key"])
            ),
        )
        append_event(
            connection,
            _event_envelope(
                event_type="flag.created",
                tenant_id=str(workflow_run["tenant_id"]),
                domain_id=str(workflow_run["domain_id"]),
                actor_type=created_by_actor_type,
                actor_id=created_by_actor_id,
                links=[
                    {"rel": "subject", "type": "flag", "id": flag_id},
                    {
                        "rel": "subject",
                        "type": "workflow_run",
                        "id": str(payload["workflow_run_id"]),
                    },
                ],
                payload={
                    "flag_id": flag_id,
                    "flag_type": str(payload["kind"]),
                    "state": state,
                    "summary": str(payload["summary"]),
                },
                idempotency_key=event_idempotency,
            ),
        )
        created = get_flag(connection, flag_id)
        if created is None:
            raise CommandError(
                code="flag_not_found",
                message="flag was not found after creation",
                details={"flag_id": flag_id},
            )
        return created

    try:
        result, replay = _execute_with_command_receipt(
            connection,
            receipt=receipt,
            operation=_operation,
        )
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if "flags.flag_id" in message:
            raise CommandError(
                code="duplicate_flag_id",
                message="flag_id already exists",
                details={"flag_id": flag_id},
            ) from exc
        if (
            "uq_flags_workflow_dedupe_key" in message
            or "flags.workflow_run_id, flags.dedupe_key" in message
        ):
            raise CommandError(
                code="duplicate_flag_dedupe",
                message="duplicate dedupe key for workflow run",
                details={
                    "workflow_run_id": str(payload["workflow_run_id"]),
                    "dedupe_key": str(
                        payload.get("dedupe_key") or payload["idempotency_key"]
                    ),
                },
            ) from exc
        raise

    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def transition_flag_state_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["flag_id", "to_state", "actor_id", "actor_type", "idempotency_key"],
    )
    to_state = str(payload["to_state"])
    if to_state not in FLAG_STATES:
        raise CommandError(
            code="invalid_flag_state",
            message=f"unsupported flag state: {to_state}",
            details={"allowed_states": sorted(FLAG_STATES)},
        )
    actor_type = str(payload["actor_type"])
    _assert_actor_type(actor_type)
    current = get_flag(connection, str(payload["flag_id"]))
    if current is None:
        raise CommandError(
            code="flag_not_found",
            message="flag not found",
            details={"flag_id": str(payload["flag_id"])},
        )
    principal = _principal_from_payload(payload, require_roles=True)
    from onetruth.application.services.capabilities import transition_decision

    decision = transition_decision(flag=current, principal=principal)
    if _decision_has_reason(decision, "flag_transition_role_mismatch"):
        raise _forbidden_command_error(
            code="flag_transition_forbidden",
            message="actor is not allowed to transition this flag",
            decision=decision,
            flag_id=str(payload["flag_id"]),
            workflow_run_id=str(current["workflow_run_id"]),
        )
    receipt = _prepare_command_receipt(
        command_name="flags.transition",
        payload=payload,
        fingerprint_payload={
            "flag_id": str(payload["flag_id"]),
            "to_state": to_state,
            "reason": (
                str(payload["reason"])
                if payload.get("reason") is not None
                else None
            ),
            "actor_id": str(payload["actor_id"]),
            "actor_type": actor_type,
            "actor_roles": sorted(set(principal.actor_roles)),
        },
        tenant_id=str(current["tenant_id"])
        if current.get("tenant_id") is not None
        else None,
        domain_id=str(current["domain_id"])
        if current.get("domain_id") is not None
        else None,
        workflow_run_id=str(current["workflow_run_id"]),
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "flags.transition.flag.state_changed",
    )

    def _operation() -> dict[str, Any]:
        from_state = str(current["state"])
        if from_state == to_state:
            raise CommandError(
                code="illegal_flag_transition",
                message="flag already in requested state",
                details={"flag_id": str(payload["flag_id"]), "state": from_state},
            )
        allowed_to_states = FLAG_ALLOWED_TRANSITIONS.get(from_state, set())
        if to_state not in allowed_to_states:
            raise CommandError(
                code="illegal_flag_transition",
                message="flag transition is not allowed",
                details={
                    "flag_id": str(payload["flag_id"]),
                    "from_state": from_state,
                    "to_state": to_state,
                    "allowed_to_states": sorted(allowed_to_states),
                },
            )
        now = utc_now_iso()
        updated = transition_flag_state(
            connection,
            flag_id=str(payload["flag_id"]),
            expected_from_state=from_state,
            to_state=to_state,
            updated_at=now,
        )
        if updated is None:
            raise CommandError(
                code="flag_transition_conflict",
                message="flag transition raced and could not be applied",
                details={"flag_id": str(payload["flag_id"])},
            )

        scope = _workflow_scope(connection, str(updated["workflow_run_id"]))
        append_event(
            connection,
            _event_envelope(
                event_type="flag.state_changed",
                tenant_id=scope["tenant_id"],
                domain_id=scope["domain_id"],
                actor_type=actor_type,
                actor_id=str(payload["actor_id"]),
                links=[
                    {"rel": "subject", "type": "flag", "id": str(payload["flag_id"])},
                    {
                        "rel": "subject",
                        "type": "workflow_run",
                        "id": str(updated["workflow_run_id"]),
                    },
                ],
                payload={
                    "flag_id": str(payload["flag_id"]),
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
        transitioned = get_flag(connection, str(payload["flag_id"]))
        if transitioned is None:
            raise CommandError(
                code="flag_not_found",
                message="flag not found after transition",
                details={"flag_id": str(payload["flag_id"])},
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


def activate_stage07_issue_from_flag_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(payload, ["workflow_run_id", "flag_id"])
    task_kind = str(payload.get("task_kind", "exception_triage"))
    if task_kind != "exception_triage":
        raise CommandError(
            code="invalid_stage07_task_kind",
            message="stage07 root issue activation only supports exception_triage",
            details={"task_kind": task_kind},
        )
    generation = int(payload.get("generation", 0))
    if generation < 0:
        raise CommandError(
            code="invalid_generation",
            message="generation must be >= 0",
            details={"generation": generation},
        )
    workflow_run_id = str(payload["workflow_run_id"])
    flag_id = str(payload["flag_id"])
    activation_key = build_stage07_issue_activation_key(
        workflow_run_id=workflow_run_id,
        flag_id=flag_id,
        task_kind=task_kind,
        generation=generation,
    )
    existing = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing is not None:
        return {
            "task_run": existing,
            "human_task": get_human_task_by_task_run_id(
                connection,
                str(existing["task_run_id"]),
            ),
            "deduped": True,
        }

    task_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "stage07.activate-issue.task.run.created",
    )
    human_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "stage07.activate-issue.task.created",
    )

    _begin_transaction(connection)
    try:
        workflow_scope = _workflow_scope(connection, workflow_run_id)
        flag = get_flag(connection, flag_id)
        if flag is None:
            raise CommandError(
                code="flag_not_found",
                message="flag not found for stage07 activation",
                details={"flag_id": flag_id},
            )
        if str(flag["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_flag_reference",
                message="flag belongs to a different workflow_run",
                details={
                    "flag_id": flag_id,
                    "flag_workflow_run_id": str(flag["workflow_run_id"]),
                    "workflow_run_id": workflow_run_id,
                },
            )
        if str(flag["state"]) not in FLAG_ACTIVE_STATES:
            raise CommandError(
                code="flag_not_active",
                message="only active flags can activate Stage07 issue tasks",
                details={"flag_id": flag_id, "state": str(flag["state"])},
            )
        _assert_idempotency_available(connection, task_event_idempotency)
        _assert_idempotency_available(connection, human_event_idempotency)

        now = utc_now_iso()
        task_run_id = str(payload.get("task_run_id") or f"tr-{uuid4()}")
        human_task_id = str(payload.get("human_task_id") or f"ht-{uuid4()}")
        create_task_run(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            stage_id="Stage07",
            task_kind=task_kind,
            state="READY",
            generation=generation,
            activation_key=activation_key,
            blocked_on_kind=None,
            blocked_on_ref=None,
            spawned_from_flag_id=flag_id,
            spawned_from_task_run_id=None,
            spawn_rule_id="stage07_issue_activation",
            spawn_cause_kind="flag_trigger",
            spawn_cause_event_id=(
                str(flag["source_event_id"])
                if flag.get("source_event_id") is not None
                else None
            ),
            spawn_depth=0,
            spawn_budget_key=f"stage07:{workflow_run_id}:{flag_id}",
            created_at=now,
        )
        create_human_task(
            connection,
            human_task_id=human_task_id,
            workflow_run_id=workflow_run_id,
            task_run_id=task_run_id,
            task_kind=task_kind,
            state="OPEN",
            candidate_roles=["operations_manager"],
            owner_role="operations_manager",
            due_at=None,
            escalation_at=None,
            generation=generation,
            created_at=now,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.created",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                ],
                payload={
                    "task_run_id": task_run_id,
                    "stage_id": "Stage07",
                    "task_kind": task_kind,
                    "activation_key": activation_key,
                    "generation": generation,
                    "spawned_from_flag_id": flag_id,
                    "spawn_rule_id": "stage07_issue_activation",
                    "spawn_cause_kind": "flag_trigger",
                    "spawn_cause_event_id": (
                        str(flag["source_event_id"])
                        if flag.get("source_event_id") is not None
                        else None
                    ),
                    "spawn_budget_key": f"stage07:{workflow_run_id}:{flag_id}",
                    "spawn_depth": 0,
                },
                idempotency_key=task_event_idempotency,
            ),
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.created",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                    {"rel": "subject", "type": "human_task", "id": human_task_id},
                ],
                payload={
                    "human_task_id": human_task_id,
                    "task_kind": task_kind,
                    "state": "OPEN",
                    "candidate_roles": ["operations_manager"],
                },
                idempotency_key=human_event_idempotency,
            ),
        )
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "task_runs.workflow_run_id, task_runs.activation_key" in str(exc):
            existing_after_race = get_task_run_by_activation_key(
                connection,
                workflow_run_id=workflow_run_id,
                activation_key=activation_key,
            )
            if existing_after_race is not None:
                return {
                    "task_run": existing_after_race,
                    "human_task": get_human_task_by_task_run_id(
                        connection,
                        str(existing_after_race["task_run_id"]),
                    ),
                    "deduped": True,
                }
            raise CommandError(
                code="duplicate_stage07_issue_activation",
                message="stage07 issue activation key already exists",
                details={
                    "workflow_run_id": workflow_run_id,
                    "flag_id": flag_id,
                    "activation_key": activation_key,
                },
            ) from exc
        raise
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    created_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if created_task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="stage07 activation task run not found after creation",
            details={"activation_key": activation_key},
        )
    return {
        "task_run": created_task_run,
        "human_task": get_human_task_by_task_run_id(
            connection,
            str(created_task_run["task_run_id"]),
        ),
        "deduped": False,
    }


def reconcile_stage07_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(payload, ["workflow_run_id"])
    workflow_run_id = str(payload["workflow_run_id"])
    _workflow_scope(connection, workflow_run_id)
    target_flag_id = (
        str(payload["flag_id"]) if payload.get("flag_id") is not None else None
    )
    generation = int(payload.get("generation", 0))
    idempotency_base = (
        str(payload["idempotency_key"])
        if payload.get("idempotency_key") is not None
        else None
    )

    flags = list_open_flags_for_workflow_run(connection, workflow_run_id)
    if target_flag_id is not None:
        flags = [flag for flag in flags if str(flag["flag_id"]) == target_flag_id]
    results: list[dict[str, Any]] = []
    for index, flag in enumerate(flags):
        activation_payload: dict[str, Any] = {
            "workflow_run_id": workflow_run_id,
            "flag_id": str(flag["flag_id"]),
            "generation": generation,
            "actor_type": "system",
            "actor_id": "system:stage07-reconcile",
        }
        if idempotency_base is not None:
            activation_payload["idempotency_key"] = (
                f"{idempotency_base}:flag:{flag['flag_id']}:{index}"
            )
        activation = activate_stage07_issue_from_flag_command(
            connection,
            activation_payload,
        )
        results.append(
            {
                "flag_id": str(flag["flag_id"]),
                "task_run_id": str(activation["task_run"]["task_run_id"]),
                "human_task_id": (
                    str(activation["human_task"]["human_task_id"])
                    if activation.get("human_task") is not None
                    else None
                ),
                "deduped": bool(activation.get("deduped", False)),
            }
        )
    return {
        "workflow_run_id": workflow_run_id,
        "open_flag_count": len(flags),
        "activations": results,
    }
