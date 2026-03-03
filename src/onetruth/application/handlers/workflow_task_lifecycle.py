from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.infrastructure.events.event_store import (
    DuplicateIdempotencyKeyError,
    append_event,
    event_id_for_type,
    get_event_by_idempotency_key,
    utc_now_iso,
)
from onetruth.application.services.schedule_planning_stage06 import (
    Stage06SpawnError,
    resolve_stage06_spawn_plans,
)
from onetruth.application.services.schedule_planning_stage07 import (
    Stage07SpawnError,
    build_stage07_issue_activation_key,
    resolve_stage07_spawn_plans,
)
from onetruth.infrastructure.repositories.flags import (
    create_flag,
    get_flag,
    list_flags_for_workflow_run,
    list_open_flags_for_workflow_run,
    transition_flag_state,
)
from onetruth.infrastructure.repositories.human_tasks import (
    claim_human_task as claim_human_task_row,
    complete_human_task as complete_human_task_row,
    create_human_task,
    get_human_task,
    get_human_task_by_task_run_id,
    list_human_tasks_for_workflow_run,
    list_expired_claimed_human_tasks,
    reopen_human_task_after_lease_expiry,
)
from onetruth.infrastructure.repositories.approvals import (
    create_approval,
    get_approval,
    list_approvals_for_workflow_run,
    respond_approval,
)
from onetruth.infrastructure.repositories.artifact_pointers import (
    PointerConflictError,
    PointerDefinitionMismatchError,
    PointerGenerationMismatchError,
    get_pointer,
    list_pointers_for_workflow_run,
    promote_pointer,
)
from onetruth.infrastructure.repositories.artifact_versions import (
    create_artifact_version,
    get_artifact_version,
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.task_runs import (
    create_task_run,
    get_task_run,
    get_task_run_by_activation_key,
    get_task_run_for_human_task,
    transition_task_run_state,
)
from onetruth.infrastructure.repositories.workflow_runs import (
    create_workflow_run,
    get_workflow_run,
    list_workflow_runs,
)

WORKFLOW_RUN_STATES = {"OPEN", "COMPLETED"}
TASK_RUN_STATES = {"READY", "IN_PROGRESS", "COMPLETED"}
HUMAN_TASK_STATES = {"OPEN", "CLAIMED", "COMPLETED"}
APPROVAL_STATES = {"PENDING", "RESPONDED"}
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
APPROVAL_RESPONSE_TO_OUTCOME = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "changes_requested",
    "cancel": "canceled",
    "expire": "expired",
}
VALID_ACTOR_TYPES = {"human", "agent", "service", "system"}


@dataclass
class CommandError(Exception):
    code: str
    message: str
    details: dict[str, Any]


def create_workflow_run_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    required = [
        "workflow_id",
        "workflow_version",
        "tenant_id",
        "domain_id",
        "partition_key",
        "activation_key",
    ]
    _require_fields(payload, required)
    workflow_run_id = str(payload.get("workflow_run_id") or f"wr-{uuid4()}")
    state = str(payload.get("state", "OPEN"))
    if state not in WORKFLOW_RUN_STATES:
        raise CommandError(
            code="invalid_workflow_state",
            message=f"unsupported workflow run state: {state}",
            details={"allowed_states": sorted(WORKFLOW_RUN_STATES)},
        )
    event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "runs.create.workflow.run.created",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, event_idempotency)
        now = utc_now_iso()
        create_workflow_run(
            connection,
            workflow_run_id=workflow_run_id,
            workflow_id=str(payload["workflow_id"]),
            workflow_version=str(payload["workflow_version"]),
            tenant_id=str(payload["tenant_id"]),
            domain_id=str(payload["domain_id"]),
            partition_key=str(payload["partition_key"]),
            logical_date=(
                str(payload["logical_date"])
                if payload.get("logical_date") is not None
                else None
            ),
            activation_key=str(payload["activation_key"]),
            state=state,
            created_at=now,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="workflow.run.created",
                tenant_id=str(payload["tenant_id"]),
                domain_id=str(payload["domain_id"]),
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {
                        "rel": "uses_definition",
                        "type": "workflow_contract_version",
                        "id": f"{payload['workflow_id']}@{payload['workflow_version']}",
                    },
                    {
                        "rel": "uses_decisions",
                        "type": "decision_catalog_version",
                        "id": f"{payload['workflow_id']}@{payload['workflow_version']}",
                    },
                    {
                        "rel": "uses_profile",
                        "type": "execution_profile_version",
                        "id": f"{payload['workflow_id']}@{payload['workflow_version']}",
                    },
                ],
                payload={
                    "workflow_id": str(payload["workflow_id"]),
                    "partition_key": str(payload["partition_key"]),
                    "activation_key": str(payload["activation_key"]),
                    "logical_date": (
                        str(payload["logical_date"])
                        if payload.get("logical_date") is not None
                        else None
                    ),
                },
                idempotency_key=event_idempotency,
            ),
        )
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        message = str(exc)
        if "workflow_runs.workflow_run_id" in message:
            raise CommandError(
                code="duplicate_workflow_run_id",
                message="workflow_run_id already exists",
                details={"workflow_run_id": workflow_run_id},
            ) from exc
        raise CommandError(
            code="duplicate_workflow_activation",
            message="workflow activation key already exists in scope",
            details={
                "tenant_id": str(payload["tenant_id"]),
                "domain_id": str(payload["domain_id"]),
                "workflow_id": str(payload["workflow_id"]),
                "partition_key": str(payload["partition_key"]),
                "activation_key": str(payload["activation_key"]),
            },
        ) from exc
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run was not found after creation",
            details={"workflow_run_id": workflow_run_id},
        )
    return workflow_run


def create_task_run_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["workflow_run_id", "stage_id", "task_kind", "activation_key"],
    )
    workflow_run_id = str(payload["workflow_run_id"])
    task_run_id = str(payload.get("task_run_id") or f"tr-{uuid4()}")
    create_human = bool(payload.get("create_human_task", False))
    task_state = str(payload.get("state", "READY"))
    if task_state not in TASK_RUN_STATES:
        raise CommandError(
            code="invalid_task_run_state",
            message=f"unsupported task run state: {task_state}",
            details={"allowed_states": sorted(TASK_RUN_STATES)},
        )
    candidate_roles = payload.get("candidate_roles", [])
    if create_human and not isinstance(candidate_roles, list):
        raise CommandError(
            code="invalid_candidate_roles",
            message="candidate_roles must be a list when create_human_task=true",
            details={},
        )
    human_task_state = str(payload.get("human_task_state", "OPEN"))
    if create_human and human_task_state not in HUMAN_TASK_STATES:
        raise CommandError(
            code="invalid_human_task_state",
            message=f"unsupported human task state: {human_task_state}",
            details={"allowed_states": sorted(HUMAN_TASK_STATES)},
        )

    task_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "tasks.create.task.run.created",
    )
    human_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "tasks.create.task.created",
    )
    human_task_id = str(payload.get("human_task_id") or f"ht-{uuid4()}")

    _begin_transaction(connection)
    try:
        workflow_run = get_workflow_run(connection, workflow_run_id)
        if workflow_run is None:
            raise CommandError(
                code="workflow_run_not_found",
                message="workflow run not found for task creation",
                details={"workflow_run_id": workflow_run_id},
            )
        _assert_idempotency_available(connection, task_event_idempotency)
        if create_human:
            _assert_idempotency_available(connection, human_event_idempotency)

        spawned_from_flag_id = (
            str(payload["spawned_from_flag_id"])
            if payload.get("spawned_from_flag_id") is not None
            else None
        )
        if spawned_from_flag_id is not None:
            flag = get_flag(connection, spawned_from_flag_id)
            if flag is None:
                raise CommandError(
                    code="flag_not_found",
                    message="spawned_from_flag_id was not found",
                    details={"flag_id": spawned_from_flag_id},
                )
            if str(flag["workflow_run_id"]) != workflow_run_id:
                raise CommandError(
                    code="cross_workflow_flag_reference",
                    message="spawned_from_flag_id belongs to a different workflow_run",
                    details={
                        "flag_id": spawned_from_flag_id,
                        "flag_workflow_run_id": str(flag["workflow_run_id"]),
                        "workflow_run_id": workflow_run_id,
                    },
                )

        now = utc_now_iso()
        create_task_run(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            stage_id=str(payload["stage_id"]),
            task_kind=str(payload["task_kind"]),
            state=task_state,
            generation=int(payload.get("generation", 0)),
            activation_key=str(payload["activation_key"]),
            blocked_on_kind=(
                str(payload["blocked_on_kind"])
                if payload.get("blocked_on_kind") is not None
                else None
            ),
            blocked_on_ref=(
                str(payload["blocked_on_ref"])
                if payload.get("blocked_on_ref") is not None
                else None
            ),
            spawned_from_flag_id=spawned_from_flag_id,
            spawned_from_task_run_id=(
                str(payload["spawned_from_task_run_id"])
                if payload.get("spawned_from_task_run_id") is not None
                else None
            ),
            spawn_rule_id=(
                str(payload["spawn_rule_id"])
                if payload.get("spawn_rule_id") is not None
                else None
            ),
            spawn_cause_kind=(
                str(payload["spawn_cause_kind"])
                if payload.get("spawn_cause_kind") is not None
                else None
            ),
            spawn_cause_event_id=(
                str(payload["spawn_cause_event_id"])
                if payload.get("spawn_cause_event_id") is not None
                else None
            ),
            spawn_depth=int(payload.get("spawn_depth", 0)),
            spawn_budget_key=(
                str(payload["spawn_budget_key"])
                if payload.get("spawn_budget_key") is not None
                else None
            ),
            created_at=now,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.created",
                tenant_id=str(workflow_run["tenant_id"]),
                domain_id=str(workflow_run["domain_id"]),
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                ],
                payload={
                    "task_run_id": task_run_id,
                    "stage_id": str(payload["stage_id"]),
                    "task_kind": str(payload["task_kind"]),
                    "activation_key": str(payload["activation_key"]),
                    "generation": int(payload.get("generation", 0)),
                    "spawned_from_flag_id": spawned_from_flag_id,
                    "spawned_from_task_run_id": (
                        str(payload["spawned_from_task_run_id"])
                        if payload.get("spawned_from_task_run_id") is not None
                        else None
                    ),
                    "spawn_rule_id": (
                        str(payload["spawn_rule_id"])
                        if payload.get("spawn_rule_id") is not None
                        else None
                    ),
                    "spawn_cause_kind": (
                        str(payload["spawn_cause_kind"])
                        if payload.get("spawn_cause_kind") is not None
                        else "none"
                    ),
                    "spawn_cause_event_id": (
                        str(payload["spawn_cause_event_id"])
                        if payload.get("spawn_cause_event_id") is not None
                        else None
                    ),
                    "spawn_budget_key": (
                        str(payload["spawn_budget_key"])
                        if payload.get("spawn_budget_key") is not None
                        else None
                    ),
                    "spawn_depth": int(payload.get("spawn_depth", 0)),
                },
                idempotency_key=task_event_idempotency,
            ),
        )

        if create_human:
            create_human_task(
                connection,
                human_task_id=human_task_id,
                workflow_run_id=workflow_run_id,
                task_run_id=task_run_id,
                task_kind=str(payload["task_kind"]),
                state=human_task_state,
                candidate_roles=[str(role) for role in candidate_roles],
                owner_role=(
                    str(payload["owner_role"])
                    if payload.get("owner_role") is not None
                    else None
                ),
                due_at=(
                    str(payload["due_at"]) if payload.get("due_at") is not None else None
                ),
                escalation_at=(
                    str(payload["escalation_at"])
                    if payload.get("escalation_at") is not None
                    else None
                ),
                generation=int(payload.get("generation", 0)),
                created_at=now,
            )
            append_event(
                connection,
                _event_envelope(
                    event_type="task.created",
                    tenant_id=str(workflow_run["tenant_id"]),
                    domain_id=str(workflow_run["domain_id"]),
                    actor_type=str(payload.get("actor_type", "system")),
                    actor_id=str(payload.get("actor_id", "system:runtime")),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                        {"rel": "subject", "type": "task_run", "id": task_run_id},
                        {"rel": "subject", "type": "human_task", "id": human_task_id},
                    ],
                    payload={
                        "human_task_id": human_task_id,
                        "task_kind": str(payload["task_kind"]),
                        "state": human_task_state,
                        "candidate_roles": [str(role) for role in candidate_roles],
                    },
                    idempotency_key=human_event_idempotency,
                ),
            )
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "task_runs.workflow_run_id, task_runs.activation_key" in str(exc):
            raise CommandError(
                code="duplicate_task_activation",
                message="task activation key already exists in workflow run scope",
                details={
                    "workflow_run_id": workflow_run_id,
                    "activation_key": str(payload["activation_key"]),
                },
            ) from exc
        if "human_tasks.task_run_id" in str(exc):
            raise CommandError(
                code="duplicate_human_task",
                message="human task already exists for task run",
                details={"task_run_id": task_run_id},
            ) from exc
        raise
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    task_run = get_task_run(connection, task_run_id)
    human_task = get_human_task(connection, human_task_id) if create_human else None
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="task run was not found after creation",
            details={"task_run_id": task_run_id},
        )
    result: dict[str, Any] = {"task_run": task_run}
    if human_task is not None:
        result["human_task"] = human_task
    return result


def claim_human_task_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["human_task_id", "actor_id", "actor_type", "lease_seconds", "idempotency_key"],
    )
    actor_type = str(payload["actor_type"])
    if actor_type not in VALID_ACTOR_TYPES:
        raise CommandError(
            code="invalid_actor_type",
            message=f"unsupported actor_type: {actor_type}",
            details={"allowed_actor_types": sorted(VALID_ACTOR_TYPES)},
        )
    lease_seconds = int(payload["lease_seconds"])
    if lease_seconds <= 0:
        raise CommandError(
            code="invalid_lease_seconds",
            message="lease_seconds must be positive",
            details={},
        )

    claimed_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "tasks.claim.task.claimed",
    )
    state_change_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "tasks.claim.task.run.state_changed",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, claimed_event_idempotency)
        now = utc_now_iso()
        claimed_until = _future_iso(lease_seconds)
        claimed = claim_human_task_row(
            connection,
            human_task_id=str(payload["human_task_id"]),
            actor_id=str(payload["actor_id"]),
            actor_type=actor_type,
            claimed_at=now,
            claimed_until=claimed_until,
            updated_at=now,
        )
        if claimed is None:
            existing = get_human_task(connection, str(payload["human_task_id"]))
            if existing is None:
                raise CommandError(
                    code="human_task_not_found",
                    message="human task not found",
                    details={"human_task_id": str(payload["human_task_id"])},
                )
            raise CommandError(
                code="task_not_claimable",
                message="human task is not claimable in current state",
                details={
                    "human_task_id": str(payload["human_task_id"]),
                    "state": existing["state"],
                },
            )

        task_run = get_task_run(connection, str(claimed["task_run_id"]))
        if task_run is None:
            raise CommandError(
                code="task_run_not_found",
                message="task run not found for human task claim",
                details={"task_run_id": str(claimed["task_run_id"])},
            )
        if str(task_run["state"]) == "COMPLETED":
            raise CommandError(
                code="task_run_not_claimable",
                message="task run is already completed",
                details={"task_run_id": str(task_run["task_run_id"])},
            )

        task_run_state_changed = False
        task_run_from_state = str(task_run["state"])
        if task_run_from_state == "READY":
            transition_task_run_state(
                connection,
                task_run_id=str(task_run["task_run_id"]),
                expected_from_state="READY",
                to_state="IN_PROGRESS",
                updated_at=now,
            )
            task_run_state_changed = True

        scope = _workflow_scope(connection, str(claimed["workflow_run_id"]))
        append_event(
            connection,
            _event_envelope(
                event_type="task.claimed",
                tenant_id=scope["tenant_id"],
                domain_id=scope["domain_id"],
                actor_type=actor_type,
                actor_id=str(payload["actor_id"]),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": str(claimed["workflow_run_id"])},
                    {"rel": "subject", "type": "task_run", "id": str(claimed["task_run_id"])},
                    {"rel": "subject", "type": "human_task", "id": str(claimed["human_task_id"])},
                ],
                payload={
                    "human_task_id": str(claimed["human_task_id"]),
                    "lease_version": int(claimed["lease_version"]),
                    "claimed_until": str(claimed["claimed_until"]),
                },
                idempotency_key=claimed_event_idempotency,
            ),
        )

        if task_run_state_changed:
            _assert_idempotency_available(connection, state_change_event_idempotency)
            append_event(
                connection,
                _event_envelope(
                    event_type="task.run.state_changed",
                    tenant_id=scope["tenant_id"],
                    domain_id=scope["domain_id"],
                    actor_type=actor_type,
                    actor_id=str(payload["actor_id"]),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(claimed["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": str(claimed["task_run_id"])},
                    ],
                    payload={
                        "task_run_id": str(claimed["task_run_id"]),
                        "from_state": task_run_from_state,
                        "to_state": "IN_PROGRESS",
                        "reason": "human_task_claimed",
                    },
                    idempotency_key=state_change_event_idempotency,
                ),
            )
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    claimed_now = get_human_task(connection, str(payload["human_task_id"]))
    run_now = get_task_run_for_human_task(connection, str(payload["human_task_id"]))
    return {
        "human_task": claimed_now,
        "task_run": run_now,
    }


def complete_human_task_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["human_task_id", "actor_id", "actor_type", "outcome", "idempotency_key"],
    )
    actor_type = str(payload["actor_type"])
    if actor_type not in VALID_ACTOR_TYPES:
        raise CommandError(
            code="invalid_actor_type",
            message=f"unsupported actor_type: {actor_type}",
            details={"allowed_actor_types": sorted(VALID_ACTOR_TYPES)},
        )

    completed_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "tasks.complete.task.completed",
    )
    state_change_event_idempotency = _event_idempotency_key(
        payload.get("idempotency_key"),
        "tasks.complete.task.run.state_changed",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, completed_event_idempotency)
        before = get_human_task(connection, str(payload["human_task_id"]))
        if before is None:
            raise CommandError(
                code="human_task_not_found",
                message="human task not found",
                details={"human_task_id": str(payload["human_task_id"])},
            )
        now = utc_now_iso()
        completed = complete_human_task_row(
            connection,
            human_task_id=str(payload["human_task_id"]),
            actor_id=str(payload["actor_id"]),
            actor_type=actor_type,
            updated_at=now,
        )
        if completed is None:
            raise CommandError(
                code="task_not_completable",
                message="human task must be claimed by actor before completion",
                details={
                    "human_task_id": str(payload["human_task_id"]),
                    "state": before["state"],
                    "assignee_actor_id": before["assignee_actor_id"],
                    "assignee_actor_type": before["assignee_actor_type"],
                },
            )

        task_run = get_task_run(connection, str(completed["task_run_id"]))
        if task_run is None:
            raise CommandError(
                code="task_run_not_found",
                message="task run not found for human task completion",
                details={"task_run_id": str(completed["task_run_id"])},
            )

        from_state = str(task_run["state"])
        if from_state not in {"IN_PROGRESS", "READY"}:
            raise CommandError(
                code="task_run_not_completable",
                message="task run cannot transition to completed from current state",
                details={
                    "task_run_id": str(task_run["task_run_id"]),
                    "state": from_state,
                },
            )

        transition_task_run_state(
            connection,
            task_run_id=str(task_run["task_run_id"]),
            expected_from_state=from_state,
            to_state="COMPLETED",
            updated_at=now,
        )

        scope = _workflow_scope(connection, str(completed["workflow_run_id"]))
        completed_event = _event_envelope(
            event_type="task.completed",
            tenant_id=scope["tenant_id"],
            domain_id=scope["domain_id"],
            actor_type=actor_type,
            actor_id=str(payload["actor_id"]),
            links=[
                {"rel": "subject", "type": "workflow_run", "id": str(completed["workflow_run_id"])},
                {"rel": "subject", "type": "task_run", "id": str(completed["task_run_id"])},
                {"rel": "subject", "type": "human_task", "id": str(completed["human_task_id"])},
            ],
            payload={
                "human_task_id": str(completed["human_task_id"]),
                "completion_code": str(payload["outcome"]),
            },
            idempotency_key=completed_event_idempotency,
        )
        append_event(connection, completed_event)
        parent_completion_event_id = str(completed_event["event_id"])

        _assert_idempotency_available(connection, state_change_event_idempotency)
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.state_changed",
                tenant_id=scope["tenant_id"],
                domain_id=scope["domain_id"],
                actor_type=actor_type,
                actor_id=str(payload["actor_id"]),
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": str(completed["workflow_run_id"])},
                    {"rel": "subject", "type": "task_run", "id": str(completed["task_run_id"])},
                ],
                payload={
                    "task_run_id": str(completed["task_run_id"]),
                    "from_state": from_state,
                    "to_state": "COMPLETED",
                    "reason": "human_task_completed",
                },
                idempotency_key=state_change_event_idempotency,
            ),
        )

        spawn_plans: list[Any] = []
        try:
            spawn_plans.extend(
                resolve_stage06_spawn_plans(
                    parent_task_run=task_run,
                    completion_outcome=str(payload["outcome"]),
                    parent_completion_event_id=parent_completion_event_id,
                )
            )
        except Stage06SpawnError as exc:
            raise CommandError(
                code=exc.code,
                message=str(exc),
                details=exc.details,
            ) from exc
        try:
            spawn_plans.extend(
                resolve_stage07_spawn_plans(
                    parent_task_run=task_run,
                    completion_outcome=str(payload["outcome"]),
                    parent_completion_event_id=parent_completion_event_id,
                )
            )
        except Stage07SpawnError as exc:
            raise CommandError(
                code=exc.code,
                message=str(exc),
                details=exc.details,
            ) from exc

        spawned_children: list[dict[str, Any]] = []
        for index, spawn_plan in enumerate(spawn_plans):
            child_task_run_id = str(payload.get("child_task_run_id") or f"tr-{uuid4()}")
            child_human_task_id = str(payload.get("child_human_task_id") or f"ht-{uuid4()}")
            child_generation = int(task_run.get("generation") or 0) + 1 if spawn_plan.stage_id == "Stage07" else 0
            spawned_from_flag_id = (
                str(spawn_plan.spawned_from_flag_id)
                if getattr(spawn_plan, "spawned_from_flag_id", None) is not None
                else None
            )
            child_task_event_idempotency = _event_idempotency_key(
                payload.get("idempotency_key"),
                f"tasks.complete.spawn.{spawn_plan.spawn_rule_id}.{index}.task.run.created",
            )
            child_human_event_idempotency = _event_idempotency_key(
                payload.get("idempotency_key"),
                f"tasks.complete.spawn.{spawn_plan.spawn_rule_id}.{index}.task.created",
            )
            _assert_idempotency_available(connection, child_task_event_idempotency)
            _assert_idempotency_available(connection, child_human_event_idempotency)
            try:
                create_task_run(
                    connection,
                    task_run_id=child_task_run_id,
                    workflow_run_id=str(completed["workflow_run_id"]),
                    stage_id=spawn_plan.stage_id,
                    task_kind=spawn_plan.task_kind,
                    state="READY",
                    generation=child_generation,
                    activation_key=spawn_plan.activation_key,
                    blocked_on_kind=None,
                    blocked_on_ref=None,
                    spawned_from_flag_id=spawned_from_flag_id,
                    spawned_from_task_run_id=str(completed["task_run_id"]),
                    spawn_rule_id=spawn_plan.spawn_rule_id,
                    spawn_cause_kind=spawn_plan.spawn_cause_kind,
                    spawn_cause_event_id=spawn_plan.spawn_cause_event_id,
                    spawn_depth=spawn_plan.spawn_depth,
                    spawn_budget_key=spawn_plan.spawn_budget_key,
                    created_at=now,
                )
                create_human_task(
                    connection,
                    human_task_id=child_human_task_id,
                    workflow_run_id=str(completed["workflow_run_id"]),
                    task_run_id=child_task_run_id,
                    task_kind=spawn_plan.task_kind,
                    state="OPEN",
                    candidate_roles=spawn_plan.candidate_roles,
                    owner_role=spawn_plan.owner_role,
                    due_at=None,
                    escalation_at=None,
                    generation=child_generation,
                    created_at=now,
                )
            except sqlite3.IntegrityError as exc:
                if "task_runs.workflow_run_id, task_runs.activation_key" in str(exc):
                    raise CommandError(
                        code="duplicate_spawned_task_activation",
                        message="spawned child activation key already exists in workflow run scope",
                        details={
                            "workflow_run_id": str(completed["workflow_run_id"]),
                            "activation_key": spawn_plan.activation_key,
                            "spawn_rule_id": spawn_plan.spawn_rule_id,
                        },
                    ) from exc
                raise

            append_event(
                connection,
                _event_envelope(
                    event_type="task.run.created",
                    tenant_id=scope["tenant_id"],
                    domain_id=scope["domain_id"],
                    actor_type=actor_type,
                    actor_id=str(payload["actor_id"]),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(completed["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": child_task_run_id},
                    ],
                    payload={
                        "task_run_id": child_task_run_id,
                        "stage_id": spawn_plan.stage_id,
                        "task_kind": spawn_plan.task_kind,
                        "activation_key": spawn_plan.activation_key,
                        "generation": child_generation,
                        "spawned_from_flag_id": spawned_from_flag_id,
                        "spawned_from_task_run_id": str(completed["task_run_id"]),
                        "spawn_rule_id": spawn_plan.spawn_rule_id,
                        "spawn_cause_kind": spawn_plan.spawn_cause_kind,
                        "spawn_cause_event_id": spawn_plan.spawn_cause_event_id,
                        "spawn_budget_key": spawn_plan.spawn_budget_key,
                        "spawn_depth": spawn_plan.spawn_depth,
                    },
                    idempotency_key=child_task_event_idempotency,
                ),
            )
            append_event(
                connection,
                _event_envelope(
                    event_type="task.created",
                    tenant_id=scope["tenant_id"],
                    domain_id=scope["domain_id"],
                    actor_type=actor_type,
                    actor_id=str(payload["actor_id"]),
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(completed["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": child_task_run_id},
                        {"rel": "subject", "type": "human_task", "id": child_human_task_id},
                    ],
                    payload={
                        "human_task_id": child_human_task_id,
                        "task_kind": spawn_plan.task_kind,
                        "state": "OPEN",
                        "candidate_roles": spawn_plan.candidate_roles,
                    },
                    idempotency_key=child_human_event_idempotency,
                ),
            )
            spawned_children.append(
                {
                    "task_run_id": child_task_run_id,
                    "human_task_id": child_human_task_id,
                    "stage_id": spawn_plan.stage_id,
                    "task_kind": spawn_plan.task_kind,
                    "spawn_rule_id": spawn_plan.spawn_rule_id,
                    "activation_key": spawn_plan.activation_key,
                    "generation": child_generation,
                    "spawned_from_flag_id": spawned_from_flag_id,
                }
            )
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    completed_now = get_human_task(connection, str(payload["human_task_id"]))
    run_now = get_task_run_for_human_task(connection, str(payload["human_task_id"]))
    return {
        "human_task": completed_now,
        "task_run": run_now,
        "spawned_children": spawned_children,
    }


def show_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> dict[str, Any]:
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    return workflow_run


def list_workflow_runs_command(
    connection: sqlite3.Connection,
    *,
    workflow_id: str | None = None,
    tenant_id: str | None = None,
    domain_id: str | None = None,
    state: str | None = None,
) -> list[dict[str, Any]]:
    if state is not None and state not in WORKFLOW_RUN_STATES:
        raise CommandError(
            code="invalid_workflow_state",
            message=f"unsupported workflow run state: {state}",
            details={"allowed_states": sorted(WORKFLOW_RUN_STATES)},
        )
    return list_workflow_runs(
        connection,
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        domain_id=domain_id,
        state=state,
    )


def show_human_task_command(
    connection: sqlite3.Connection,
    human_task_id: str,
) -> dict[str, Any]:
    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": human_task_id},
        )
    task_run = get_task_run(connection, str(human_task["task_run_id"]))
    if task_run is not None:
        human_task["task_run_state"] = task_run["state"]
        human_task["stage_id"] = task_run["stage_id"]
        human_task["blocked_on_kind"] = task_run["blocked_on_kind"]
        human_task["blocked_on_ref"] = task_run["blocked_on_ref"]
        human_task["spawned_from_flag_id"] = task_run["spawned_from_flag_id"]
    return human_task


def list_tasks_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    if get_workflow_run(connection, workflow_run_id) is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    tasks = list_human_tasks_for_workflow_run(connection, workflow_run_id)
    results: list[dict[str, Any]] = []
    for task in tasks:
        task_run = get_task_run(connection, str(task["task_run_id"]))
        item = dict(task)
        if task_run is not None:
            item["task_run_state"] = task_run["state"]
            item["stage_id"] = task_run["stage_id"]
            item["blocked_on_kind"] = task_run["blocked_on_kind"]
            item["blocked_on_ref"] = task_run["blocked_on_ref"]
            item["spawned_from_flag_id"] = task_run["spawned_from_flag_id"]
        results.append(item)
    return results


def create_flag_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
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
    flag_id = str(payload.get("flag_id") or f"fl-{uuid4()}")
    event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "flags.create.flag.created",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, event_idempotency)
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
                    {"rel": "subject", "type": "workflow_run", "id": str(payload["workflow_run_id"])},
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
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        message = str(exc)
        if "flags.flag_id" in message:
            raise CommandError(
                code="duplicate_flag_id",
                message="flag_id already exists",
                details={"flag_id": flag_id},
            ) from exc
        if "uq_flags_workflow_dedupe_key" in message or "flags.workflow_run_id, flags.dedupe_key" in message:
            raise CommandError(
                code="duplicate_flag_dedupe",
                message="duplicate dedupe key for workflow run",
                details={
                    "workflow_run_id": str(payload["workflow_run_id"]),
                    "dedupe_key": str(payload.get("dedupe_key") or payload["idempotency_key"]),
                },
            ) from exc
        raise
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    created = get_flag(connection, flag_id)
    if created is None:
        raise CommandError(
            code="flag_not_found",
            message="flag was not found after creation",
            details={"flag_id": flag_id},
        )
    return created


def transition_flag_state_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
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
    event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "flags.transition.flag.state_changed",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, event_idempotency)
        current = get_flag(connection, str(payload["flag_id"]))
        if current is None:
            raise CommandError(
                code="flag_not_found",
                message="flag not found",
                details={"flag_id": str(payload["flag_id"])},
            )
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
                    {"rel": "subject", "type": "workflow_run", "id": str(updated["workflow_run_id"])},
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
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    transitioned = get_flag(connection, str(payload["flag_id"]))
    if transitioned is None:
        raise CommandError(
            code="flag_not_found",
            message="flag not found after transition",
            details={"flag_id": str(payload["flag_id"])},
        )
    return transitioned


def show_flag_command(
    connection: sqlite3.Connection,
    flag_id: str,
) -> dict[str, Any]:
    flag = get_flag(connection, flag_id)
    if flag is None:
        raise CommandError(
            code="flag_not_found",
            message="flag not found",
            details={"flag_id": flag_id},
        )
    return flag


def list_flags_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_flags_for_workflow_run(connection, workflow_run_id)


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
            "human_task": get_human_task_by_task_run_id(connection, str(existing["task_run_id"])),
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
        "human_task": get_human_task_by_task_run_id(connection, str(created_task_run["task_run_id"])),
        "deduped": False,
    }


def sweep_leases_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    now = str(payload.get("now") or utc_now_iso())
    workflow_run_id = (
        str(payload["workflow_run_id"])
        if payload.get("workflow_run_id") is not None
        else None
    )

    _begin_transaction(connection)
    try:
        expired = list_expired_claimed_human_tasks(
            connection,
            now_iso=now,
            workflow_run_id=workflow_run_id,
        )
        reopened_task_ids: list[str] = []
        processed: list[dict[str, Any]] = []
        for task in expired:
            reopened = reopen_human_task_after_lease_expiry(
                connection,
                human_task_id=str(task["human_task_id"]),
                expected_lease_version=int(task["lease_version"]),
                updated_at=now,
            )
            if reopened is None:
                continue
            task_run = get_task_run(connection, str(task["task_run_id"]))
            if task_run is None:
                continue
            scope = _workflow_scope(connection, str(task["workflow_run_id"]))
            append_event(
                connection,
                _event_envelope(
                    event_type="task.lease_expired",
                    tenant_id=scope["tenant_id"],
                    domain_id=scope["domain_id"],
                    actor_type="system",
                    actor_id="system:lease-sweeper",
                    links=[
                        {"rel": "subject", "type": "workflow_run", "id": str(task["workflow_run_id"])},
                        {"rel": "subject", "type": "task_run", "id": str(task["task_run_id"])},
                        {"rel": "subject", "type": "human_task", "id": str(task["human_task_id"])},
                    ],
                    payload={
                        "human_task_id": str(task["human_task_id"]),
                        "lease_version": int(task["lease_version"]),
                        "expiry_kind": "claim_timeout",
                        "reopened": True,
                        "escalated": False,
                    },
                    idempotency_key=None,
                ),
            )
            if str(task_run["state"]) == "IN_PROGRESS":
                transition_task_run_state(
                    connection,
                    task_run_id=str(task_run["task_run_id"]),
                    expected_from_state="IN_PROGRESS",
                    to_state="READY",
                    updated_at=now,
                )
                append_event(
                    connection,
                    _event_envelope(
                        event_type="task.run.state_changed",
                        tenant_id=scope["tenant_id"],
                        domain_id=scope["domain_id"],
                        actor_type="system",
                        actor_id="system:lease-sweeper",
                        links=[
                            {"rel": "subject", "type": "workflow_run", "id": str(task["workflow_run_id"])},
                            {"rel": "subject", "type": "task_run", "id": str(task["task_run_id"])},
                        ],
                        payload={
                            "task_run_id": str(task["task_run_id"]),
                            "from_state": "IN_PROGRESS",
                            "to_state": "READY",
                            "reason": "human_task_lease_expired",
                        },
                        idempotency_key=None,
                    ),
                )
            reopened_task_ids.append(str(task["human_task_id"]))
            processed.append(
                {
                    "human_task_id": str(task["human_task_id"]),
                    "task_run_id": str(task["task_run_id"]),
                    "workflow_run_id": str(task["workflow_run_id"]),
                    "lease_version": int(task["lease_version"]),
                }
            )
    except Exception:
        connection.rollback()
        raise
    connection.commit()
    return {
        "now": now,
        "processed_count": len(processed),
        "reopened_human_task_ids": reopened_task_ids,
        "processed": processed,
    }


def reconcile_stage07_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(payload, ["workflow_run_id"])
    workflow_run_id = str(payload["workflow_run_id"])
    _workflow_scope(connection, workflow_run_id)
    target_flag_id = str(payload["flag_id"]) if payload.get("flag_id") is not None else None
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


def request_approval_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
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

    approval_id = str(payload.get("approval_id") or f"ap-{uuid4()}")
    task_run_id = str(payload["task_run_id"]) if payload.get("task_run_id") is not None else None
    requested_by_task_run_id = (
        str(payload["requested_by_task_run_id"])
        if payload.get("requested_by_task_run_id") is not None
        else task_run_id
    )
    event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "approvals.request.approval.requested",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, event_idempotency)
        workflow_scope = _workflow_scope(connection, str(payload["workflow_run_id"]))
        if task_run_id is not None:
            _validate_task_run_belongs_to_workflow(
                connection,
                task_run_id=task_run_id,
                workflow_run_id=str(payload["workflow_run_id"]),
            )
        if requested_by_task_run_id is not None:
            _validate_task_run_belongs_to_workflow(
                connection,
                task_run_id=requested_by_task_run_id,
                workflow_run_id=str(payload["workflow_run_id"]),
            )

        now = utc_now_iso()
        create_approval(
            connection,
            approval_id=approval_id,
            workflow_run_id=str(payload["workflow_run_id"]),
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
            {"rel": "subject", "type": "workflow_run", "id": str(payload["workflow_run_id"])},
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
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "approvals.approval_id" in str(exc):
            raise CommandError(
                code="duplicate_approval_id",
                message="approval_id already exists",
                details={"approval_id": approval_id},
            ) from exc
        raise
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    approval = get_approval(connection, approval_id)
    if approval is None:
        raise CommandError(
            code="approval_not_found",
            message="approval was not found after creation",
            details={"approval_id": approval_id},
        )
    return approval


def respond_approval_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["approval_id", "actor_id", "actor_type", "response_kind", "idempotency_key"],
    )
    actor_type = str(payload["actor_type"])
    _assert_actor_type(actor_type)
    response_kind = str(payload["response_kind"])
    if response_kind not in APPROVAL_RESPONSE_TO_OUTCOME:
        raise CommandError(
            code="invalid_approval_response",
            message=f"unsupported approval response_kind: {response_kind}",
            details={"allowed_response_kinds": sorted(APPROVAL_RESPONSE_TO_OUTCOME)},
        )
    responded_outcome = APPROVAL_RESPONSE_TO_OUTCOME[response_kind]
    event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "approvals.respond.approval.responded",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, event_idempotency)
        before = get_approval(connection, str(payload["approval_id"]))
        if before is None:
            raise CommandError(
                code="approval_not_found",
                message="approval not found",
                details={"approval_id": str(payload["approval_id"])},
            )
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
                    "action": f"{responded['scope_kind']}:{responded['scope_ref']}",
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
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    approval = get_approval(connection, str(payload["approval_id"]))
    if approval is None:
        raise CommandError(
            code="approval_not_found",
            message="approval not found after response",
            details={"approval_id": str(payload["approval_id"])},
        )
    return approval


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


def create_artifact_version_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "artifact_kind",
            "media_type",
            "storage_uri",
            "content_digest",
            "metadata_json",
            "idempotency_key",
        ],
    )
    metadata_json = payload.get("metadata_json")
    if not isinstance(metadata_json, dict):
        raise CommandError(
            code="invalid_metadata_json",
            message="metadata_json must be a JSON object",
            details={},
        )
    artifact_version_id = str(payload.get("artifact_version_id") or f"av-{uuid4()}")
    task_run_id = str(payload["task_run_id"]) if payload.get("task_run_id") is not None else None
    event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "artifacts.create-version.artifact.version.created",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, event_idempotency)
        workflow_scope = _workflow_scope(connection, str(payload["workflow_run_id"]))
        if task_run_id is not None:
            _validate_task_run_belongs_to_workflow(
                connection,
                task_run_id=task_run_id,
                workflow_run_id=str(payload["workflow_run_id"]),
            )
        now = utc_now_iso()
        create_artifact_version(
            connection,
            artifact_version_id=artifact_version_id,
            workflow_run_id=str(payload["workflow_run_id"]),
            task_run_id=task_run_id,
            artifact_kind=str(payload["artifact_kind"]),
            artifact_role=(
                str(payload["artifact_role"])
                if payload.get("artifact_role") is not None
                else None
            ),
            media_type=str(payload["media_type"]),
            storage_uri=str(payload["storage_uri"]),
            content_digest=str(payload["content_digest"]),
            byte_size=(
                int(payload["byte_size"])
                if payload.get("byte_size") is not None
                else None
            ),
            metadata_json=metadata_json,
            parent_artifact_version_id=(
                str(payload["parent_artifact_version_id"])
                if payload.get("parent_artifact_version_id") is not None
                else None
            ),
            supersedes_artifact_version_id=(
                str(payload["supersedes_artifact_version_id"])
                if payload.get("supersedes_artifact_version_id") is not None
                else None
            ),
            lineage_note=(
                str(payload["lineage_note"])
                if payload.get("lineage_note") is not None
                else None
            ),
            created_at=now,
        )
        links = [
            {"rel": "subject", "type": "artifact_version", "id": artifact_version_id},
            {"rel": "subject", "type": "workflow_run", "id": str(payload["workflow_run_id"])},
        ]
        if task_run_id is not None:
            links.append({"rel": "subject", "type": "task_run", "id": task_run_id})

        append_event(
            connection,
            _event_envelope(
                event_type="artifact.version.created",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=links,
                payload={
                    "artifact_version_id": artifact_version_id,
                    "dataset_key": str(payload["artifact_kind"]),
                    "supersedes_artifact_version_id": (
                        str(payload["supersedes_artifact_version_id"])
                        if payload.get("supersedes_artifact_version_id") is not None
                        else None
                    ),
                },
                idempotency_key=event_idempotency,
            ),
        )
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        if "artifact_versions.artifact_version_id" in str(exc):
            raise CommandError(
                code="duplicate_artifact_version_id",
                message="artifact_version_id already exists",
                details={"artifact_version_id": artifact_version_id},
            ) from exc
        raise
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    artifact_version = get_artifact_version(connection, artifact_version_id)
    if artifact_version is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version was not found after creation",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact_version


def show_artifact_version_command(
    connection: sqlite3.Connection,
    artifact_version_id: str,
) -> dict[str, Any]:
    artifact_version = get_artifact_version(connection, artifact_version_id)
    if artifact_version is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact version not found",
            details={"artifact_version_id": artifact_version_id},
        )
    return artifact_version


def list_artifacts_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_artifact_versions_for_workflow_run(connection, workflow_run_id)


def promote_pointer_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "workflow_run_id",
            "scope_kind",
            "scope_ref",
            "pointer_key",
            "artifact_kind",
            "artifact_version_id",
            "idempotency_key",
        ],
    )
    event_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "pointers.promote.artifact.pointer.promoted",
    )
    drift_idempotency = _required_event_idempotency_key(
        payload.get("idempotency_key"),
        "pointers.promote.artifact.pointer.drift_detected",
    )

    _begin_transaction(connection)
    try:
        _assert_idempotency_available(connection, event_idempotency)
        workflow_scope = _workflow_scope(connection, str(payload["workflow_run_id"]))
        artifact_version = get_artifact_version(connection, str(payload["artifact_version_id"]))
        if artifact_version is None:
            raise CommandError(
                code="artifact_version_not_found",
                message="artifact version not found for pointer promotion",
                details={"artifact_version_id": str(payload["artifact_version_id"])},
            )
        if str(artifact_version["workflow_run_id"]) != str(payload["workflow_run_id"]):
            raise CommandError(
                code="cross_workflow_artifact_reference",
                message="artifact version belongs to a different workflow_run",
                details={
                    "artifact_version_id": str(payload["artifact_version_id"]),
                    "artifact_workflow_run_id": str(artifact_version["workflow_run_id"]),
                    "workflow_run_id": str(payload["workflow_run_id"]),
                },
            )

        promotion_reason = (
            str(payload["promotion_reason"])
            if payload.get("promotion_reason") is not None
            else None
        )
        approved_by_approval_id = (
            str(payload["approved_by_approval_id"])
            if payload.get("approved_by_approval_id") is not None
            else None
        )
        if promotion_reason in {"official_publish", "official_major_replan"} and approved_by_approval_id is None:
            raise CommandError(
                code="approval_required_for_promotion",
                message=f"{promotion_reason} promotions require approved_by_approval_id",
                details={"promotion_reason": promotion_reason},
            )
        if approved_by_approval_id is not None:
            approval = get_approval(connection, approved_by_approval_id)
            if approval is None:
                raise CommandError(
                    code="approval_not_found",
                    message="approved_by_approval_id was not found",
                    details={"approved_by_approval_id": approved_by_approval_id},
                )
            if str(approval["workflow_run_id"]) != str(payload["workflow_run_id"]):
                raise CommandError(
                    code="cross_workflow_approval_reference",
                    message="approval belongs to a different workflow_run",
                    details={
                        "approved_by_approval_id": approved_by_approval_id,
                        "approval_workflow_run_id": str(approval["workflow_run_id"]),
                        "workflow_run_id": str(payload["workflow_run_id"]),
                    },
                )
            if str(approval["state"]) != "RESPONDED" or str(approval.get("response_kind")) != "approve":
                raise CommandError(
                    code="approval_not_approved",
                    message="pointer promotion requires an approved approval response",
                    details={
                        "approved_by_approval_id": approved_by_approval_id,
                        "state": str(approval["state"]),
                        "response_kind": approval.get("response_kind"),
                    },
                )
            if (
                promotion_reason == "official_major_replan"
                and str(approval.get("scope_ref")) != "Stage07"
            ):
                raise CommandError(
                    code="major_replan_approval_required",
                    message="official_major_replan requires a Stage07 approval response",
                    details={
                        "approved_by_approval_id": approved_by_approval_id,
                        "scope_ref": str(approval.get("scope_ref")),
                    },
                )

        promoted_by_task_run_id = (
            str(payload["promoted_by_task_run_id"])
            if payload.get("promoted_by_task_run_id") is not None
            else None
        )
        if promoted_by_task_run_id is not None:
            _validate_task_run_belongs_to_workflow(
                connection,
                task_run_id=promoted_by_task_run_id,
                workflow_run_id=str(payload["workflow_run_id"]),
            )

        now = utc_now_iso()
        pointer, changed = promote_pointer(
            connection,
            workflow_run_id=str(payload["workflow_run_id"]),
            pointer_key=str(payload["pointer_key"]),
            scope_kind=str(payload["scope_kind"]),
            scope_ref=str(payload["scope_ref"]),
            artifact_kind=str(payload["artifact_kind"]),
            artifact_version_id=str(payload["artifact_version_id"]),
            promotion_reason=promotion_reason,
            promoted_by_task_run_id=promoted_by_task_run_id,
            approved_by_approval_id=approved_by_approval_id,
            updated_at=now,
            expected_generation=(
                int(payload["expected_generation"])
                if payload.get("expected_generation") is not None
                else None
            ),
        )
        if not changed:
            raise CommandError(
                code="pointer_already_current",
                message="pointer already targets requested artifact_version_id",
                details={
                    "workflow_run_id": str(payload["workflow_run_id"]),
                    "pointer_key": str(payload["pointer_key"]),
                    "artifact_version_id": str(payload["artifact_version_id"]),
                },
            )

        links = [
            {"rel": "subject", "type": "pointer", "id": str(payload["pointer_key"])},
            {"rel": "subject", "type": "workflow_run", "id": str(payload["workflow_run_id"])},
            {"rel": "subject", "type": "artifact_version", "id": str(payload["artifact_version_id"])},
        ]
        reviewed_artifact_version_id = (
            str(payload["reviewed_artifact_version_id"])
            if payload.get("reviewed_artifact_version_id") is not None
            else (
                str(payload["reviewed_base_artifact_version_id"])
                if payload.get("reviewed_base_artifact_version_id") is not None
                else None
            )
        )
        append_event(
            connection,
            _event_envelope(
                event_type="artifact.pointer.promoted",
                tenant_id=workflow_scope["tenant_id"],
                domain_id=workflow_scope["domain_id"],
                actor_type=str(payload.get("actor_type", "system")),
                actor_id=str(payload.get("actor_id", "system:runtime")),
                links=links,
                payload={
                    "pointer_id": str(payload["pointer_key"]),
                    "dataset_key": str(payload["artifact_kind"]),
                    "promoted_artifact_version_id": str(payload["artifact_version_id"]),
                    "reviewed_artifact_version_id": reviewed_artifact_version_id,
                },
                idempotency_key=event_idempotency,
            ),
        )

        drift_detected = False
        drift_reason = (
            str(payload["drift_reason"])
            if payload.get("drift_reason") is not None
            else None
        )
        reviewed_base_artifact_version_id = (
            str(payload["reviewed_base_artifact_version_id"])
            if payload.get("reviewed_base_artifact_version_id") is not None
            else None
        )
        if reviewed_base_artifact_version_id is not None:
            base_pointer_key = str(
                payload.get("base_pointer_key") or "official:schedule.published_schedule.workbook"
            )
            base_pointer = get_pointer(
                connection,
                workflow_run_id=str(payload["workflow_run_id"]),
                pointer_key=base_pointer_key,
            )
            if base_pointer is None:
                raise CommandError(
                    code="base_pointer_not_found",
                    message="base pointer was not found for drift check",
                    details={
                        "workflow_run_id": str(payload["workflow_run_id"]),
                        "base_pointer_key": base_pointer_key,
                    },
                )
            current_base_artifact_version_id = str(base_pointer["artifact_version_id"])
            if reviewed_base_artifact_version_id != current_base_artifact_version_id:
                drift_detected = True
                if drift_reason is None:
                    drift_reason = "reviewed_base_version_stale_at_promotion"
        elif (
            reviewed_artifact_version_id is not None
            and reviewed_artifact_version_id != str(payload["artifact_version_id"])
        ):
            drift_detected = True
            if drift_reason is None:
                drift_reason = "reviewed_version_differs_from_promoted_version"

        if drift_detected:
            _assert_idempotency_available(connection, drift_idempotency)
            append_event(
                connection,
                _event_envelope(
                    event_type="artifact.pointer.drift_detected",
                    tenant_id=workflow_scope["tenant_id"],
                    domain_id=workflow_scope["domain_id"],
                    actor_type=str(payload.get("actor_type", "system")),
                    actor_id=str(payload.get("actor_id", "system:runtime")),
                    links=links,
                    payload={
                        "pointer_id": str(payload["pointer_key"]),
                        "dataset_key": str(payload["artifact_kind"]),
                        "reviewed_artifact_version_id": str(
                            reviewed_artifact_version_id or reviewed_base_artifact_version_id
                        ),
                        "promoted_artifact_version_id": str(payload["artifact_version_id"]),
                        "drift_reason": drift_reason,
                    },
                    idempotency_key=drift_idempotency,
                ),
            )
    except (PointerConflictError, PointerGenerationMismatchError, PointerDefinitionMismatchError) as exc:
        connection.rollback()
        if isinstance(exc, PointerConflictError):
            raise CommandError(
                code="pointer_conflict",
                message=str(exc),
                details={
                    "pointer_key": exc.pointer_key,
                    "current_artifact_version_id": exc.current_artifact_version_id,
                    "current_generation": exc.generation,
                },
            ) from exc
        if isinstance(exc, PointerGenerationMismatchError):
            raise CommandError(
                code="pointer_generation_mismatch",
                message=str(exc),
                details={
                    "pointer_key": exc.pointer_key,
                    "expected_generation": exc.expected_generation,
                    "actual_generation": exc.actual_generation,
                },
            ) from exc
        raise CommandError(
            code="pointer_definition_mismatch",
            message=str(exc),
            details={"pointer_key": exc.pointer_key},
        ) from exc
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise CommandError(
            code="pointer_conflict",
            message="pointer promotion violated uniqueness constraints",
            details={
                "workflow_run_id": str(payload["workflow_run_id"]),
                "pointer_key": str(payload["pointer_key"]),
            },
        ) from exc
    except Exception:
        connection.rollback()
        raise
    connection.commit()

    promoted_pointer = get_pointer(
        connection,
        workflow_run_id=str(payload["workflow_run_id"]),
        pointer_key=str(payload["pointer_key"]),
    )
    if promoted_pointer is None:
        raise CommandError(
            code="pointer_not_found",
            message="pointer not found after promotion",
            details={
                "workflow_run_id": str(payload["workflow_run_id"]),
                "pointer_key": str(payload["pointer_key"]),
            },
        )
    return promoted_pointer


def show_pointer_command(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    pointer_key: str,
) -> dict[str, Any]:
    pointer = get_pointer(
        connection,
        workflow_run_id=workflow_run_id,
        pointer_key=pointer_key,
    )
    if pointer is None:
        raise CommandError(
            code="pointer_not_found",
            message="pointer not found",
            details={"workflow_run_id": workflow_run_id, "pointer_key": pointer_key},
        )
    return pointer


def list_pointers_for_workflow_run_command(
    connection: sqlite3.Connection,
    workflow_run_id: str,
) -> list[dict[str, Any]]:
    _workflow_scope(connection, workflow_run_id)
    return list_pointers_for_workflow_run(connection, workflow_run_id)


def _begin_transaction(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")


def _event_idempotency_key(idempotency_key: Any, suffix: str) -> str | None:
    if idempotency_key is None:
        return None
    key = str(idempotency_key).strip()
    if not key:
        return None
    return f"{key}:{suffix}"


def _required_event_idempotency_key(idempotency_key: Any, suffix: str) -> str:
    key = _event_idempotency_key(idempotency_key, suffix)
    if key is None:
        raise CommandError(
            code="invalid_idempotency_key",
            message="idempotency_key must be a non-empty string",
            details={},
        )
    return key


def _assert_idempotency_available(
    connection: sqlite3.Connection,
    event_idempotency_key: str | None,
) -> None:
    if event_idempotency_key is None:
        return
    existing = get_event_by_idempotency_key(connection, event_idempotency_key)
    if existing is None:
        return
    raise DuplicateIdempotencyKeyError(
        event_idempotency_key,
        str(existing["event_id"]),
    )


def _event_envelope(
    *,
    event_type: str,
    tenant_id: str,
    domain_id: str,
    actor_type: str,
    actor_id: str,
    links: list[dict[str, str]],
    payload: dict[str, Any],
    idempotency_key: str | None,
) -> dict[str, Any]:
    _assert_actor_type(actor_type)
    occurred_at = utc_now_iso()
    clean_payload = {k: v for k, v in payload.items() if v is not None}
    return {
        "event_id": event_id_for_type(event_type),
        "event_type": event_type,
        "schema_version": "1.0",
        "occurred_at": occurred_at,
        "recorded_at": occurred_at,
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "actor": {"type": actor_type, "id": actor_id},
        "links": links,
        "payload": clean_payload,
        "idempotency_key": idempotency_key,
    }


def _require_fields(payload: dict[str, Any], fields: list[str]) -> None:
    missing = [field for field in fields if field not in payload or payload[field] is None]
    if missing:
        raise CommandError(
            code="invalid_payload",
            message=f"missing required fields: {', '.join(missing)}",
            details={"missing_fields": missing},
        )


def _assert_actor_type(actor_type: str) -> None:
    if actor_type not in VALID_ACTOR_TYPES:
        raise CommandError(
            code="invalid_actor_type",
            message=f"unsupported actor_type: {actor_type}",
            details={"allowed_actor_types": sorted(VALID_ACTOR_TYPES)},
        )


def _future_iso(lease_seconds: int) -> str:
    now = utc_now_iso()
    from datetime import datetime, timezone

    parsed = datetime.fromisoformat(now.replace("Z", "+00:00"))
    return (parsed + timedelta(seconds=lease_seconds)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_task_run_belongs_to_workflow(
    connection: sqlite3.Connection,
    *,
    task_run_id: str,
    workflow_run_id: str,
) -> dict[str, Any]:
    task_run = get_task_run(connection, task_run_id)
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="task run not found",
            details={"task_run_id": task_run_id},
        )
    if str(task_run["workflow_run_id"]) != workflow_run_id:
        raise CommandError(
            code="cross_workflow_task_reference",
            message="task_run belongs to a different workflow_run",
            details={
                "task_run_id": task_run_id,
                "task_workflow_run_id": str(task_run["workflow_run_id"]),
                "workflow_run_id": workflow_run_id,
            },
        )
    return task_run


def _workflow_scope(connection: sqlite3.Connection, workflow_run_id: str) -> dict[str, str]:
    workflow_run = get_workflow_run(connection, workflow_run_id)
    if workflow_run is None:
        raise CommandError(
            code="workflow_run_not_found",
            message="workflow run not found",
            details={"workflow_run_id": workflow_run_id},
        )
    return {
        "tenant_id": str(workflow_run["tenant_id"]),
        "domain_id": str(workflow_run["domain_id"]),
    }
