from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.artifact_effects import (
    _ingest_artifact_document_effects,
)
from onetruth.application.handlers._shared.command_boundary import (
    CommandError,
    _assert_actor_type,
    _command_receipt_payload,
    _decision_has_reason,
    _event_envelope,
    _event_idempotency_key,
    _execute_with_command_receipt,
    _forbidden_command_error,
    _future_iso,
    _prepare_command_receipt,
    _principal_from_payload,
    _receipt_event_idempotency_key,
    _require_fields,
    _workflow_scope,
)
from onetruth.application.services.schedule_planning_stage06 import (
    Stage06SpawnError,
    resolve_stage06_spawn_plans,
)
from onetruth.application.services.schedule_planning_stage07 import (
    Stage07SpawnError,
    resolve_stage07_spawn_plans,
)
from onetruth.application.services.task_requirements import (
    REVIEW_CONFIRMATION_ARTIFACT_KIND,
    build_human_task_requirement_index,
    task_has_unsatisfied_requirements,
)
from onetruth.infrastructure.artifacts.storage import (
    ArtifactIngressDescriptor,
    encode_base64_content,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.artifact_versions import get_artifact_version
from onetruth.infrastructure.repositories.human_tasks import (
    claim_human_task as claim_human_task_row,
    complete_human_task as complete_human_task_row,
    create_human_task,
    get_human_task,
)
from onetruth.infrastructure.repositories.task_runs import (
    create_task_run,
    get_task_run,
    get_task_run_for_human_task,
    transition_task_run_state,
)


def claim_human_task_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["human_task_id", "actor_id", "actor_type", "lease_seconds", "idempotency_key"],
    )
    actor_type = str(payload["actor_type"])
    _assert_actor_type(actor_type)
    lease_seconds = int(payload["lease_seconds"])
    if lease_seconds <= 0:
        raise CommandError(
            code="invalid_lease_seconds",
            message="lease_seconds must be positive",
            details={},
        )
    existing = get_human_task(connection, str(payload["human_task_id"]))
    if existing is None:
        raise CommandError(
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": str(payload["human_task_id"])},
        )
    principal = _principal_from_payload(payload, require_roles=True)
    from onetruth.application.services.capabilities import claim_decision

    decision = claim_decision(task=existing, principal=principal)
    if _decision_has_reason(decision, "candidate_role_mismatch"):
        raise _forbidden_command_error(
            code="task_claim_forbidden",
            message="actor is not allowed to claim this human task",
            decision=decision,
            human_task_id=str(payload["human_task_id"]),
            workflow_run_id=str(existing["workflow_run_id"]),
        )

    receipt = _prepare_command_receipt(
        command_name="tasks.claim",
        payload=payload,
        fingerprint_payload={
            "human_task_id": str(payload["human_task_id"]),
            "actor_id": str(payload["actor_id"]),
            "actor_type": actor_type,
            "actor_roles": sorted(set(principal.actor_roles)),
            "lease_seconds": lease_seconds,
        },
        tenant_id=str(existing["tenant_id"]) if existing.get("tenant_id") is not None else None,
        domain_id=str(existing["domain_id"]) if existing.get("domain_id") is not None else None,
        workflow_run_id=str(existing["workflow_run_id"]),
        idempotency_required=True,
    )
    claimed_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "tasks.claim.task.claimed",
    )
    state_change_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "tasks.claim.task.run.state_changed",
    )

    def _operation() -> dict[str, Any]:
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
            existing_after_claim = get_human_task(connection, str(payload["human_task_id"]))
            if existing_after_claim is None:
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
                    "state": existing_after_claim["state"],
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
        claimed_now = get_human_task(connection, str(payload["human_task_id"]))
        run_now = get_task_run_for_human_task(connection, str(payload["human_task_id"]))
        return {
            "human_task": claimed_now,
            "task_run": run_now,
        }

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


def complete_human_task_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        ["human_task_id", "actor_id", "actor_type", "outcome", "idempotency_key"],
    )
    actor_type = str(payload["actor_type"])
    _assert_actor_type(actor_type)
    before = get_human_task(connection, str(payload["human_task_id"]))
    if before is None:
        raise CommandError(
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": str(payload["human_task_id"])},
        )
    principal = _principal_from_payload(payload, require_roles=False)
    from onetruth.application.services.capabilities import complete_decision

    decision = complete_decision(task=before, principal=principal)
    if _decision_has_reason(decision, "claimed_by_other_actor") or _decision_has_reason(
        decision,
        "task_not_assigned_to_actor",
    ):
        raise _forbidden_command_error(
            code="task_complete_forbidden",
            message="actor is not allowed to complete this human task",
            decision=decision,
            human_task_id=str(payload["human_task_id"]),
            workflow_run_id=str(before["workflow_run_id"]),
        )

    receipt = _prepare_command_receipt(
        command_name="tasks.complete",
        payload=payload,
        fingerprint_payload={
            "human_task_id": str(payload["human_task_id"]),
            "actor_id": str(payload["actor_id"]),
            "actor_type": actor_type,
            "outcome": str(payload["outcome"]),
            "child_task_run_id": (
                str(payload["child_task_run_id"])
                if payload.get("child_task_run_id") is not None
                else None
            ),
            "child_human_task_id": (
                str(payload["child_human_task_id"])
                if payload.get("child_human_task_id") is not None
                else None
            ),
        },
        tenant_id=str(before["tenant_id"]) if before.get("tenant_id") is not None else None,
        domain_id=str(before["domain_id"]) if before.get("domain_id") is not None else None,
        workflow_run_id=str(before["workflow_run_id"]),
        idempotency_required=True,
    )
    completed_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "tasks.complete.task.completed",
    )
    state_change_event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "tasks.complete.task.run.state_changed",
    )

    def _operation() -> dict[str, Any]:
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

        requirement_state = build_human_task_requirement_index(
            connection,
            workflow_run_id=str(completed["workflow_run_id"]),
            human_tasks=[
                {
                    **before,
                    "stage_id": task_run.get("stage_id"),
                    "task_kind": task_run.get("task_kind"),
                }
            ],
        ).get(str(completed["human_task_id"]), {})
        if task_has_unsatisfied_requirements(requirement_state):
            raise CommandError(
                code="task_requirements_not_satisfied",
                message="task cannot be completed until required uploads/reviews are satisfied",
                details={
                    "human_task_id": str(completed["human_task_id"]),
                    "workflow_run_id": str(completed["workflow_run_id"]),
                    "blocking_reason_codes": list(
                        requirement_state.get("blocking_reason_codes") or []
                    ),
                    "required_uploads": list(
                        requirement_state.get("required_uploads") or []
                    ),
                    "required_reviews": list(
                        requirement_state.get("required_reviews") or []
                    ),
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
            child_generation = (
                int(task_run.get("generation") or 0) + 1
                if spawn_plan.stage_id == "Stage07"
                else 0
            )
            spawned_from_flag_id = (
                str(spawn_plan.spawned_from_flag_id)
                if getattr(spawn_plan, "spawned_from_flag_id", None) is not None
                else None
            )
            child_task_event_idempotency = _event_idempotency_key(
                receipt.event_idempotency_base if receipt is not None else None,
                f"tasks.complete.spawn.{spawn_plan.spawn_rule_id}.{index}.task.run.created",
            )
            child_human_event_idempotency = _event_idempotency_key(
                receipt.event_idempotency_base if receipt is not None else None,
                f"tasks.complete.spawn.{spawn_plan.spawn_rule_id}.{index}.task.created",
            )
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
        completed_now = get_human_task(connection, str(payload["human_task_id"]))
        run_now = get_task_run_for_human_task(connection, str(payload["human_task_id"]))
        return {
            "human_task": completed_now,
            "task_run": run_now,
            "spawned_children": spawned_children,
        }

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


def confirm_human_task_review_command(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    storage_root: Path,
    include_receipt: bool = False,
) -> dict[str, Any]:
    _require_fields(
        payload,
        [
            "human_task_id",
            "actor_id",
            "actor_type",
            "reviewed_artifact_version_ids",
            "idempotency_key",
        ],
    )
    actor_type = str(payload["actor_type"])
    _assert_actor_type(actor_type)

    reviewed_ids_raw = payload.get("reviewed_artifact_version_ids")
    if not isinstance(reviewed_ids_raw, list) or not reviewed_ids_raw:
        raise CommandError(
            code="invalid_payload",
            message="reviewed_artifact_version_ids must be a non-empty list",
            details={},
        )
    reviewed_artifact_version_ids = [
        str(item).strip() for item in reviewed_ids_raw if str(item).strip()
    ]
    if not reviewed_artifact_version_ids:
        raise CommandError(
            code="invalid_payload",
            message="reviewed_artifact_version_ids must contain at least one value",
            details={},
        )
    reviewed_artifact_version_ids = sorted(set(reviewed_artifact_version_ids))

    human_task_id = str(payload["human_task_id"])
    human_task = get_human_task(connection, human_task_id)
    if human_task is None:
        raise CommandError(
            code="human_task_not_found",
            message="human task not found",
            details={"human_task_id": human_task_id},
        )
    if str(human_task.get("state")) != "CLAIMED":
        raise CommandError(
            code="task_not_completable",
            message="review confirmation requires a claimed human task",
            details={"human_task_id": human_task_id, "state": str(human_task.get("state"))},
        )
    workflow_run_id = str(human_task["workflow_run_id"])
    task_run_id = str(human_task["task_run_id"])
    task_run = get_task_run(connection, task_run_id)
    if task_run is None:
        raise CommandError(
            code="task_run_not_found",
            message="task run not found for review confirmation",
            details={"task_run_id": task_run_id},
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
    ).get(human_task_id, {})
    required_review_ids = {
        str(item["reviewed_artifact_version_id"])
        for item in requirement_state.get("required_reviews") or []
        if isinstance(item, dict) and item.get("reviewed_artifact_version_id") is not None
    }
    has_pending_review_confirmation = any(
        isinstance(item, dict) and str(item.get("status") or "") == "pending_confirmation"
        for item in requirement_state.get("required_reviews") or []
    )
    principal = _principal_from_payload(payload, require_roles=False)
    from onetruth.application.services.capabilities import confirm_review_decision

    decision = confirm_review_decision(
        task=human_task,
        principal=principal,
        has_pending_review_confirmation=has_pending_review_confirmation,
    )
    if (
        str(human_task.get("state") or "") == "CLAIMED"
        and (
            _decision_has_reason(decision, "claimed_by_other_actor")
            or _decision_has_reason(decision, "task_not_assigned_to_actor")
        )
    ):
        raise _forbidden_command_error(
            code="task_confirm_review_forbidden",
            message="actor is not allowed to confirm review for this human task",
            decision=decision,
            human_task_id=human_task_id,
            workflow_run_id=workflow_run_id,
        )
    missing_required_reviewed_ids = sorted(
        required_review_ids.difference(set(reviewed_artifact_version_ids))
    )
    if missing_required_reviewed_ids:
        raise CommandError(
            code="missing_required_review_artifacts",
            message="review confirmation must include all required draft artifacts",
            details={
                "human_task_id": human_task_id,
                "missing_reviewed_artifact_version_ids": missing_required_reviewed_ids,
            },
        )

    for artifact_version_id in reviewed_artifact_version_ids:
        artifact = get_artifact_version(connection, artifact_version_id)
        if artifact is None:
            raise CommandError(
                code="artifact_version_not_found",
                message="reviewed artifact version was not found",
                details={"artifact_version_id": artifact_version_id},
            )
        if str(artifact["workflow_run_id"]) != workflow_run_id:
            raise CommandError(
                code="cross_workflow_artifact_reference",
                message="reviewed artifact belongs to a different workflow_run",
                details={
                    "artifact_version_id": artifact_version_id,
                    "artifact_workflow_run_id": str(artifact["workflow_run_id"]),
                    "workflow_run_id": workflow_run_id,
                },
            )

    idempotency_key = str(payload["idempotency_key"])
    artifact_version_id = _stable_review_confirmation_artifact_id(
        workflow_run_id=workflow_run_id,
        human_task_id=human_task_id,
        idempotency_key=idempotency_key,
    )
    confirmed_at = utc_now_iso()
    evidence_payload = {
        "schema_version": "1.0",
        "kind": "human_task_review_confirmation",
        "human_task_id": human_task_id,
        "task_run_id": task_run_id,
        "workflow_run_id": workflow_run_id,
        "reviewed_artifact_version_ids": reviewed_artifact_version_ids,
        "reviewer": {
            "id": str(payload["actor_id"]),
            "type": actor_type,
        },
        "confirmed_at": confirmed_at,
        "confirmation_idempotency_key": idempotency_key,
    }

    ingest_payload = {
        "artifact_version_id": artifact_version_id,
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "artifact_kind": REVIEW_CONFIRMATION_ARTIFACT_KIND,
        "artifact_role": "review_evidence",
        "media_type": "application/json",
        "file_name": f"human-task-review-confirmation-{human_task_id}.json",
        "metadata_json": evidence_payload,
        "links": [
            {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
                "relation_kind": "review_confirmation",
            },
            {
                "subject_kind": "task_run",
                "subject_id": task_run_id,
                "relation_kind": "review_confirmation",
            },
            *[
                {
                    "subject_kind": "artifact_version",
                    "subject_id": reviewed_artifact_version_id,
                    "relation_kind": "reviewed_artifact",
                }
                for reviewed_artifact_version_id in reviewed_artifact_version_ids
            ],
        ],
        "idempotency_key": idempotency_key,
        "actor_id": str(payload["actor_id"]),
        "actor_type": actor_type,
    }
    confirmation_bytes = json.dumps(
        evidence_payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    ingress_descriptor = ArtifactIngressDescriptor.request_bytes(
        content_base64=encode_base64_content(confirmation_bytes)
    )
    receipt = _prepare_command_receipt(
        command_name="tasks.confirm-review",
        payload=payload,
        fingerprint_payload={
            "human_task_id": human_task_id,
            "actor_id": str(payload["actor_id"]),
            "actor_type": actor_type,
            "reviewed_artifact_version_ids": reviewed_artifact_version_ids,
            "artifact_version_id": artifact_version_id,
            "storage_root": str(storage_root),
            "artifact_kind": REVIEW_CONFIRMATION_ARTIFACT_KIND,
            "file_name": f"human-task-review-confirmation-{human_task_id}.json",
            "media_type": "application/json",
        },
        tenant_id=None,
        domain_id=None,
        workflow_run_id=workflow_run_id,
        idempotency_required=True,
    )
    event_idempotency = _receipt_event_idempotency_key(
        receipt,
        "tasks.confirm-review.artifact.version.created",
    )
    result, replay = _execute_with_command_receipt(
        connection,
        receipt=receipt,
        operation=lambda: _ingest_artifact_document_effects(
            connection,
            ingest_payload,
            storage_root=storage_root,
            ingress_descriptor=ingress_descriptor,
            raw_content=confirmation_bytes,
            file_name=str(ingest_payload["file_name"]),
            media_type=str(ingest_payload["media_type"]),
            event_idempotency=event_idempotency,
        ),
    )
    return _command_receipt_payload(
        result,
        receipt=receipt,
        replay=replay,
        include_receipt=include_receipt,
    )


def _stable_review_confirmation_artifact_id(
    *,
    workflow_run_id: str,
    human_task_id: str,
    idempotency_key: str,
) -> str:
    import hashlib

    digest = hashlib.sha256(
        f"{workflow_run_id}|{human_task_id}|{idempotency_key}".encode("utf-8")
    ).hexdigest()[:24]
    return f"av-{digest}"
