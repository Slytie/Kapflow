from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from onetruth.application.handlers._shared.artifact_effects import (
    _create_artifact_version_effects,
    _ingest_artifact_document_effects,
)
from onetruth.application.handlers.approvals import (
    _latest_review_confirmation_for_human_task,
    _request_approval_effects,
    _reviewed_artifact_id_from_confirmation,
)
from onetruth.application.handlers.availability_exceptions import (
    materialize_weekly_approved_availability_exceptions,
)
from onetruth.application.handlers.pointers import _promote_pointer_effects
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
from onetruth.application.services.dispatch_reporting_build import (
    DispatchReportingBuildError,
    EOS_RAW_ARTIFACT_KIND,
    NORMALIZED_ACTUALS_ARTIFACT_KIND,
    REVIEW_APPROVAL_ACTION as DISPATCH_REVIEW_APPROVAL_ACTION,
    REVIEW_APPROVAL_SCOPE_REF as DISPATCH_REVIEW_APPROVAL_SCOPE_REF,
    REVIEW_TASK_KIND as DISPATCH_REVIEW_TASK_KIND,
    UPD_DRAFT_ARTIFACT_KIND as DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
    WORKFLOW_ID as DISPATCH_REPORTING_WORKFLOW_ID,
    build_dispatch_reporting_artifacts,
)
from onetruth.application.services.dispatch_reporting_workbook import (
    WorkbookRuntimeDependencyError,
)
from onetruth.application.services.task_requirements import (
    REVIEW_CONFIRMATION_ARTIFACT_KIND,
    build_human_task_requirement_index,
    task_has_unsatisfied_requirements,
)
from onetruth.application.services.template_registry import load_template_registry_catalog
from onetruth.infrastructure.artifacts.storage import (
    ArtifactIngressDescriptor,
    ArtifactStorageError,
    encode_base64_content,
    read_blob,
    write_blob,
)
from onetruth.infrastructure.events.event_store import append_event, utc_now_iso
from onetruth.infrastructure.repositories.artifact_versions import (
    get_artifact_version,
    list_artifact_versions_for_workflow_run,
)
from onetruth.infrastructure.repositories.approvals import list_approvals_for_workflow_run
from onetruth.infrastructure.repositories.human_tasks import (
    claim_human_task as claim_human_task_row,
    complete_human_task as complete_human_task_row,
    create_human_task,
    get_human_task,
    get_human_task_by_task_run_id,
)
from onetruth.infrastructure.repositories.task_runs import (
    create_task_run,
    get_task_run,
    get_task_run_by_activation_key,
    get_task_run_for_human_task,
    transition_task_run_state,
)
from onetruth.infrastructure.repositories.workflow_runs import get_workflow_run

WEEKLY_WORKFLOW_ID = "weekly_schedule_planning.v1"
WEEKLY_DRAFT_ARTIFACT_KIND = "planning.draft_weekly_schedule.workbook"
WEEKLY_PUBLISH_ACTION = "publish_weekly_base_schedule"
LIVE_DISPATCH_WORKFLOW_ID = "live_dispatch.v1"
LIVE_ROUTE_DELTA_ARTIFACT_KIND = "dispatch.route_delta_intake.workbook"
LIVE_ACTUAL_HOURS_ARTIFACT_KIND = "dispatch.actual_hours_snapshot.workbook"
LIVE_REVIEW_TASK_KIND = "dispatcher_review"
LIVE_OFFICIAL_DELTA_ARTIFACT_KIND = "dispatch.official_replan_delta.workbook"
LIVE_CHANGE_NOTICE_ARTIFACT_KIND = "dispatch.change_notice.doc"
LIVE_OFFICIAL_POINTER_KEY = "official:dispatch.official_replan_delta.workbook"
DISPATCH_REPORTING_DRAFT_TEMPLATE_ID = "dispatch_reporting.stage03.upd_draft.workbook.empty.v1"


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
    storage_root: Path | None = None,
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
        workflow_run = get_workflow_run(connection, str(completed["workflow_run_id"]))
        if workflow_run is None:
            raise CommandError(
                code="workflow_run_not_found",
                message="workflow run not found for human task completion",
                details={"workflow_run_id": str(completed["workflow_run_id"])},
            )
        completion_outcome = _effective_completion_outcome(
            workflow_run=workflow_run,
            task_run=task_run,
            requested_outcome=str(payload["outcome"]),
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
                "completion_code": completion_outcome,
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
                    completion_outcome=completion_outcome,
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
                    completion_outcome=completion_outcome,
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
        weekly_effects = _apply_weekly_completion_effects(
            connection,
            workflow_run=workflow_run,
            task_run=task_run,
            human_task=completed,
            completion_outcome=completion_outcome,
            actor_id=str(payload["actor_id"]),
            actor_type=actor_type,
            scope=scope,
            receipt_event_idempotency_base=(
                receipt.event_idempotency_base if receipt is not None else None
            ),
            parent_completion_event_id=parent_completion_event_id,
            created_at=now,
            storage_root=storage_root,
        )
        dispatch_effects = _apply_dispatch_reporting_completion_effects(
            connection,
            workflow_run=workflow_run,
            task_run=task_run,
            human_task=completed,
            completion_outcome=completion_outcome,
            actor_id=str(payload["actor_id"]),
            actor_type=actor_type,
            scope=scope,
            receipt_event_idempotency_base=(
                receipt.event_idempotency_base if receipt is not None else None
            ),
            parent_completion_event_id=parent_completion_event_id,
            created_at=now,
            storage_root=storage_root,
        )
        live_effects = _apply_live_dispatch_completion_effects(
            connection,
            workflow_run=workflow_run,
            task_run=task_run,
            human_task=completed,
            completion_outcome=completion_outcome,
            actor_id=str(payload["actor_id"]),
            actor_type=actor_type,
            scope=scope,
            receipt_event_idempotency_base=(
                receipt.event_idempotency_base if receipt is not None else None
            ),
            parent_completion_event_id=parent_completion_event_id,
            created_at=now,
            storage_root=storage_root,
        )
        spawned_children.extend(weekly_effects["spawned_children"])
        spawned_children.extend(dispatch_effects["spawned_children"])
        spawned_children.extend(live_effects["spawned_children"])
        completed_now = get_human_task(connection, str(payload["human_task_id"]))
        run_now = get_task_run_for_human_task(connection, str(payload["human_task_id"]))
        return {
            "human_task": completed_now,
            "task_run": run_now,
            "spawned_children": spawned_children,
            "requested_approvals": [
                *weekly_effects["requested_approvals"],
                *dispatch_effects["requested_approvals"],
                *live_effects["requested_approvals"],
            ],
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


def _effective_completion_outcome(
    *,
    workflow_run: dict[str, Any],
    task_run: dict[str, Any],
    requested_outcome: str,
) -> str:
    if requested_outcome != "complete":
        return requested_outcome
    workflow_id = str(workflow_run.get("workflow_id") or "")
    surface = (str(task_run.get("stage_id") or ""), str(task_run.get("task_kind") or ""))
    if workflow_id == WEEKLY_WORKFLOW_ID:
        return {
            ("Stage04", "weekly_input_intake"): "inputs_ready",
            ("Stage04", "work_item"): "draft_ready_for_review",
            ("Stage05", "final_review"): "draft_is_publish_ready",
        }.get(surface, requested_outcome)
    if workflow_id == DISPATCH_REPORTING_WORKFLOW_ID:
        return {
            ("Stage01", "eos_input_intake"): "eos_inputs_ready",
            ("Stage04", DISPATCH_REVIEW_TASK_KIND): "draft_ready_for_manager_confirmation",
        }.get(surface, requested_outcome)
    if workflow_id == LIVE_DISPATCH_WORKFLOW_ID:
        return {
            ("Stage01", "dispatch_seed_intake"): "intake_ready_for_review",
            ("Stage03", LIVE_REVIEW_TASK_KIND): "reviewed_replan_ready",
        }.get(surface, requested_outcome)
    return requested_outcome


def _apply_weekly_completion_effects(
    connection: sqlite3.Connection,
    *,
    workflow_run: dict[str, Any],
    task_run: dict[str, Any],
    human_task: dict[str, Any],
    completion_outcome: str,
    actor_id: str,
    actor_type: str,
    scope: dict[str, Any],
    receipt_event_idempotency_base: str | None,
    parent_completion_event_id: str,
    created_at: str,
    storage_root: Path | None,
) -> dict[str, list[dict[str, Any]]]:
    if str(workflow_run.get("workflow_id") or "") != WEEKLY_WORKFLOW_ID:
        return {"spawned_children": [], "requested_approvals": []}

    workflow_run_id = str(task_run["workflow_run_id"])
    parent_task_run_id = str(task_run["task_run_id"])
    surface = (
        str(task_run.get("stage_id") or ""),
        str(task_run.get("task_kind") or ""),
        completion_outcome,
    )
    if surface == ("Stage04", "weekly_input_intake", "inputs_ready"):
        if storage_root is not None:
            materialize_weekly_approved_availability_exceptions(
                connection,
                workflow_run=workflow_run,
                storage_root=storage_root,
                actor_id=actor_id,
                actor_type=actor_type,
                receipt_event_idempotency_base=receipt_event_idempotency_base,
            )
        build_task = _ensure_weekly_child_human_task(
            connection,
            workflow_run_id=workflow_run_id,
            activation_key=f"weekly:{workflow_run_id}:stage04:build",
            stage_id="Stage04",
            task_kind="work_item",
            candidate_roles=["schedule_planner"],
            owner_role="schedule_planner",
            actor_id=actor_id,
            actor_type=actor_type,
            scope=scope,
            parent_task_run_id=parent_task_run_id,
            spawn_rule_id="weekly_stage04_build_after_intake",
            parent_completion_event_id=parent_completion_event_id,
            receipt_event_idempotency_base=receipt_event_idempotency_base,
            created_at=created_at,
        )
        return {"spawned_children": [build_task], "requested_approvals": []}
    if surface == ("Stage04", "work_item", "draft_ready_for_review"):
        latest_draft = _latest_artifact_for_kind(
            connection,
            workflow_run_id=workflow_run_id,
            artifact_kind=WEEKLY_DRAFT_ARTIFACT_KIND,
        )
        if latest_draft is None:
            raise CommandError(
                code="required_artifact_missing",
                message="weekly Stage04 completion requires a current draft weekly schedule artifact",
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_kind": WEEKLY_DRAFT_ARTIFACT_KIND,
                },
            )
        final_review_task = _ensure_weekly_child_human_task(
            connection,
            workflow_run_id=workflow_run_id,
            activation_key=(
                f"weekly:{workflow_run_id}:stage05:final-review:"
                f"{latest_draft['artifact_version_id']}"
            ),
            stage_id="Stage05",
            task_kind="final_review",
            candidate_roles=["operations_manager"],
            owner_role="operations_manager",
            actor_id=actor_id,
            actor_type=actor_type,
            scope=scope,
            parent_task_run_id=parent_task_run_id,
            spawn_rule_id="weekly_stage05_review_after_stage04_build",
            parent_completion_event_id=parent_completion_event_id,
            receipt_event_idempotency_base=receipt_event_idempotency_base,
            created_at=created_at,
        )
        return {"spawned_children": [final_review_task], "requested_approvals": []}
    if surface == ("Stage05", "final_review", "draft_is_publish_ready"):
        approval = _ensure_weekly_publish_approval(
            connection,
            workflow_run_id=workflow_run_id,
            task_run_id=parent_task_run_id,
            actor_id=actor_id,
            actor_type=actor_type,
            receipt_event_idempotency_base=receipt_event_idempotency_base,
        )
        return {"spawned_children": [], "requested_approvals": [approval]}
    return {"spawned_children": [], "requested_approvals": []}


def _ensure_weekly_child_human_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    activation_key: str,
    stage_id: str,
    task_kind: str,
    candidate_roles: list[str],
    owner_role: str | None,
    actor_id: str,
    actor_type: str,
    scope: dict[str, Any],
    parent_task_run_id: str,
    spawn_rule_id: str,
    parent_completion_event_id: str,
    receipt_event_idempotency_base: str | None,
    created_at: str,
) -> dict[str, Any]:
    existing_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing_task_run is not None:
        if (
            str(existing_task_run.get("stage_id") or "") != stage_id
            or str(existing_task_run.get("task_kind") or "") != task_kind
        ):
            raise CommandError(
                code="duplicate_spawned_task_activation",
                message="weekly follow-on activation key is already in use by a different task",
                details={
                    "workflow_run_id": workflow_run_id,
                    "activation_key": activation_key,
                    "expected_stage_id": stage_id,
                    "expected_task_kind": task_kind,
                    "actual_task_run_id": str(existing_task_run["task_run_id"]),
                },
            )
        existing_human_task = get_human_task_by_task_run_id(
            connection,
            str(existing_task_run["task_run_id"]),
        )
        if existing_human_task is not None:
            return {
                "task_run_id": str(existing_task_run["task_run_id"]),
                "human_task_id": str(existing_human_task["human_task_id"]),
                "stage_id": stage_id,
                "task_kind": task_kind,
                "spawn_rule_id": spawn_rule_id,
                "activation_key": activation_key,
                "generation": int(existing_task_run.get("generation") or 0),
                "spawned_from_flag_id": existing_task_run.get("spawned_from_flag_id"),
            }

    task_run_id = (
        str(existing_task_run["task_run_id"])
        if existing_task_run is not None
        else f"tr-{uuid4()}"
    )
    human_task_id = f"ht-{uuid4()}"

    if existing_task_run is None:
        create_task_run(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            stage_id=stage_id,
            task_kind=task_kind,
            state="READY",
            generation=0,
            activation_key=activation_key,
            blocked_on_kind=None,
            blocked_on_ref=None,
            spawned_from_flag_id=None,
            spawned_from_task_run_id=parent_task_run_id,
            spawn_rule_id=spawn_rule_id,
            spawn_cause_kind="task_completion",
            spawn_cause_event_id=parent_completion_event_id,
            spawn_depth=0,
            spawn_budget_key=None,
            created_at=created_at,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.created",
                tenant_id=scope["tenant_id"],
                domain_id=scope["domain_id"],
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                ],
                payload={
                    "task_run_id": task_run_id,
                    "stage_id": stage_id,
                    "task_kind": task_kind,
                    "activation_key": activation_key,
                    "generation": 0,
                    "spawned_from_flag_id": None,
                    "spawned_from_task_run_id": parent_task_run_id,
                    "spawn_rule_id": spawn_rule_id,
                    "spawn_cause_kind": "task_completion",
                    "spawn_cause_event_id": parent_completion_event_id,
                    "spawn_budget_key": None,
                    "spawn_depth": 0,
                },
                idempotency_key=_event_idempotency_key(
                    receipt_event_idempotency_base,
                    f"weekly.{spawn_rule_id}.task.run.created",
                ),
            ),
        )

    create_human_task(
        connection,
        human_task_id=human_task_id,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        task_kind=task_kind,
        state="OPEN",
        candidate_roles=candidate_roles,
        owner_role=owner_role,
        due_at=None,
        escalation_at=None,
        generation=0,
        created_at=created_at,
    )
    append_event(
        connection,
        _event_envelope(
            event_type="task.created",
            tenant_id=scope["tenant_id"],
            domain_id=scope["domain_id"],
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {"rel": "subject", "type": "task_run", "id": task_run_id},
                {"rel": "subject", "type": "human_task", "id": human_task_id},
            ],
            payload={
                "human_task_id": human_task_id,
                "task_kind": task_kind,
                "state": "OPEN",
                "candidate_roles": candidate_roles,
            },
            idempotency_key=_event_idempotency_key(
                receipt_event_idempotency_base,
                f"weekly.{spawn_rule_id}.task.created",
            ),
        ),
    )
    return {
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "stage_id": stage_id,
        "task_kind": task_kind,
        "spawn_rule_id": spawn_rule_id,
        "activation_key": activation_key,
        "generation": 0,
        "spawned_from_flag_id": None,
    }


def _ensure_weekly_publish_approval(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str,
    actor_id: str,
    actor_type: str,
    receipt_event_idempotency_base: str | None,
) -> dict[str, Any]:
    for approval in list_approvals_for_workflow_run(connection, workflow_run_id):
        if str(approval.get("scope_kind") or "") != "stage":
            continue
        if str(approval.get("scope_ref") or "") != "Stage06":
            continue
        if str(approval.get("task_run_id") or "") != task_run_id:
            continue
        return approval

    return _request_approval_effects(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "requested_by_task_run_id": task_run_id,
            "approval_kind": "business_decision",
            "scope_kind": "stage",
            "scope_ref": "Stage06",
            "candidate_roles": ["operations_manager"],
            "required_role": "operations_manager",
            "action": WEEKLY_PUBLISH_ACTION,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        approval_id=f"ap-{uuid4()}",
        task_run_id=task_run_id,
        requested_by_task_run_id=task_run_id,
        candidate_roles=["operations_manager"],
        allowed_responses=["approve", "reject", "request_changes", "cancel", "expire"],
        event_idempotency=_event_idempotency_key(
            receipt_event_idempotency_base,
            "weekly.stage06.publish.approval.requested",
        ),
    )


def _apply_dispatch_reporting_completion_effects(
    connection: sqlite3.Connection,
    *,
    workflow_run: dict[str, Any],
    task_run: dict[str, Any],
    human_task: dict[str, Any],
    completion_outcome: str,
    actor_id: str,
    actor_type: str,
    scope: dict[str, Any],
    receipt_event_idempotency_base: str | None,
    parent_completion_event_id: str,
    created_at: str,
    storage_root: Path | None,
) -> dict[str, list[dict[str, Any]]]:
    if str(workflow_run.get("workflow_id") or "") != DISPATCH_REPORTING_WORKFLOW_ID:
        return {"spawned_children": [], "requested_approvals": []}

    workflow_run_id = str(task_run["workflow_run_id"])
    parent_task_run_id = str(task_run["task_run_id"])
    surface = (
        str(task_run.get("stage_id") or ""),
        str(task_run.get("task_kind") or ""),
        completion_outcome,
    )
    if surface == ("Stage01", "eos_input_intake", "eos_inputs_ready"):
        if storage_root is None:
            raise CommandError(
                code="storage_root_required",
                message="dispatch reporting intake completion requires artifact storage access",
                details={"workflow_run_id": workflow_run_id},
            )
        eos_artifact = _latest_artifact_for_kind(
            connection,
            workflow_run_id=workflow_run_id,
            artifact_kind=EOS_RAW_ARTIFACT_KIND,
        )
        if eos_artifact is None:
            raise CommandError(
                code="required_artifact_missing",
                message="dispatch reporting intake completion requires an EOS workbook upload",
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_kind": EOS_RAW_ARTIFACT_KIND,
                },
            )
        template = _load_dispatch_reporting_draft_template_record()
        try:
            build_output = build_dispatch_reporting_artifacts(
                eos_workbook_bytes=_read_artifact_blob_or_raise(eos_artifact),
                draft_template_bytes=template.source_path.read_bytes(),
                source_metadata_json=(
                    eos_artifact["metadata_json"]
                    if isinstance(eos_artifact.get("metadata_json"), dict)
                    else None
                ),
                built_at=created_at,
                actor_id=actor_id,
            )
        except WorkbookRuntimeDependencyError as exc:
            raise CommandError(
                code="runtime_dependency_missing",
                message=(
                    "dispatch reporting intake cannot parse the uploaded workbook "
                    "because a required runtime dependency is unavailable"
                ),
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_version_id": str(eos_artifact["artifact_version_id"]),
                    "artifact_kind": EOS_RAW_ARTIFACT_KIND,
                    "dependency": exc.dependency,
                },
            ) from exc
        except DispatchReportingBuildError as exc:
            raise CommandError(
                code="unsupported_eos_workbook_shape",
                message=str(exc),
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_version_id": str(eos_artifact["artifact_version_id"]),
                    "artifact_kind": EOS_RAW_ARTIFACT_KIND,
                },
            ) from exc

        normalized_artifact = _create_blob_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            task_run_id=parent_task_run_id,
            artifact_kind=NORMALIZED_ACTUALS_ARTIFACT_KIND,
            artifact_role="official_input",
            artifact_bytes=_json_bytes(build_output.normalized_payload),
            file_name=f"{workflow_run_id}-actuals-normalized.json",
            media_type="application/json",
            metadata_json={
                "schema_version": "1.0",
                "service_date": build_output.service_date,
                "station_code": build_output.station_code,
                "dsp_name": build_output.dsp_name,
                "source_eos_artifact_version_id": str(eos_artifact["artifact_version_id"]),
                "formula_integrity_warning": build_output.formula_integrity_warning,
                "route_count": len(build_output.normalized_rows),
            },
            parent_artifact_version_id=str(eos_artifact["artifact_version_id"]),
            supersedes_artifact_version_id=None,
            lineage_note="dispatch_reporting_stage02_actuals_normalized",
            actor_id=actor_id,
            actor_type=actor_type,
            links=[
                {
                    "subject_kind": "task_run",
                    "subject_id": parent_task_run_id,
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "human_task",
                    "subject_id": str(human_task["human_task_id"]),
                    "relation_kind": "output",
                },
            ],
            event_idempotency=_event_idempotency_key(
                receipt_event_idempotency_base,
                "dispatch-reporting.stage02.actuals-normalized.artifact.version.created",
            ),
        )
        template_path = template.as_public_dict()["file_path"]
        draft_artifact = _create_blob_artifact_version(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            task_run_id=parent_task_run_id,
            artifact_kind=DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
            artifact_role="official_input",
            artifact_bytes=build_output.draft_workbook_bytes,
            file_name=f"{workflow_run_id}-upd-draft.xlsx",
            media_type=template.media_type,
            metadata_json={
                "template_id": template.template_id,
                "template_source_path": template_path,
                "seed_source_path": template_path,
                "ingress_source_path": template_path,
                "ingress_kind": "workflow_task_completion",
                "service_date": build_output.service_date,
                "station_code": build_output.station_code,
                "dsp_name": build_output.dsp_name,
                "source_eos_artifact_version_id": str(eos_artifact["artifact_version_id"]),
                "normalized_artifact_version_id": str(
                    normalized_artifact["artifact_version_id"]
                ),
                "formula_integrity_warning": build_output.formula_integrity_warning,
            },
            parent_artifact_version_id=str(normalized_artifact["artifact_version_id"]),
            supersedes_artifact_version_id=None,
            lineage_note="dispatch_reporting_stage03_upd_draft_generated",
            actor_id=actor_id,
            actor_type=actor_type,
            links=[
                {
                    "subject_kind": "task_run",
                    "subject_id": parent_task_run_id,
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "human_task",
                    "subject_id": str(human_task["human_task_id"]),
                    "relation_kind": "output",
                },
            ],
            event_idempotency=_event_idempotency_key(
                receipt_event_idempotency_base,
                "dispatch-reporting.stage03.upd-draft.artifact.version.created",
            ),
        )
        review_task = _ensure_dispatch_reporting_child_human_task(
            connection,
            workflow_run_id=workflow_run_id,
            activation_key=(
                f"dispatch:{workflow_run_id}:stage04:final-packet-review:"
                f"{draft_artifact['artifact_version_id']}"
            ),
            stage_id="Stage04",
            task_kind=DISPATCH_REVIEW_TASK_KIND,
            candidate_roles=["dispatch_supervisor"],
            owner_role="dispatch_supervisor",
            actor_id=actor_id,
            actor_type=actor_type,
            scope=scope,
            parent_task_run_id=parent_task_run_id,
            spawn_rule_id="dispatch_stage04_review_after_eos_intake",
            parent_completion_event_id=parent_completion_event_id,
            receipt_event_idempotency_base=receipt_event_idempotency_base,
            created_at=created_at,
        )
        return {"spawned_children": [review_task], "requested_approvals": []}
    if surface == ("Stage04", DISPATCH_REVIEW_TASK_KIND, "draft_ready_for_manager_confirmation"):
        latest_draft = _latest_artifact_for_kind(
            connection,
            workflow_run_id=workflow_run_id,
            artifact_kind=DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
        )
        if latest_draft is None:
            raise CommandError(
                code="required_artifact_missing",
                message="dispatch reporting review completion requires a current EOD draft artifact",
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_kind": DISPATCH_UPD_DRAFT_ARTIFACT_KIND,
                },
            )
        approval = _ensure_dispatch_reporting_review_approval(
            connection,
            workflow_run_id=workflow_run_id,
            task_run_id=parent_task_run_id,
            actor_id=actor_id,
            actor_type=actor_type,
            receipt_event_idempotency_base=receipt_event_idempotency_base,
        )
        return {"spawned_children": [], "requested_approvals": [approval]}
    return {"spawned_children": [], "requested_approvals": []}


def _ensure_dispatch_reporting_child_human_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    activation_key: str,
    stage_id: str,
    task_kind: str,
    candidate_roles: list[str],
    owner_role: str | None,
    actor_id: str,
    actor_type: str,
    scope: dict[str, Any],
    parent_task_run_id: str,
    spawn_rule_id: str,
    parent_completion_event_id: str,
    receipt_event_idempotency_base: str | None,
    created_at: str,
) -> dict[str, Any]:
    existing_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing_task_run is not None:
        if (
            str(existing_task_run.get("stage_id") or "") != stage_id
            or str(existing_task_run.get("task_kind") or "") != task_kind
        ):
            raise CommandError(
                code="duplicate_spawned_task_activation",
                message="dispatch reporting follow-on activation key is already in use by a different task",
                details={
                    "workflow_run_id": workflow_run_id,
                    "activation_key": activation_key,
                    "expected_stage_id": stage_id,
                    "expected_task_kind": task_kind,
                    "actual_task_run_id": str(existing_task_run["task_run_id"]),
                },
            )
        existing_human_task = get_human_task_by_task_run_id(
            connection,
            str(existing_task_run["task_run_id"]),
        )
        if existing_human_task is not None:
            return {
                "task_run_id": str(existing_task_run["task_run_id"]),
                "human_task_id": str(existing_human_task["human_task_id"]),
                "stage_id": stage_id,
                "task_kind": task_kind,
                "spawn_rule_id": spawn_rule_id,
                "activation_key": activation_key,
                "generation": int(existing_task_run.get("generation") or 0),
                "spawned_from_flag_id": existing_task_run.get("spawned_from_flag_id"),
            }

    task_run_id = (
        str(existing_task_run["task_run_id"])
        if existing_task_run is not None
        else f"tr-{uuid4()}"
    )
    human_task_id = f"ht-{uuid4()}"

    if existing_task_run is None:
        create_task_run(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            stage_id=stage_id,
            task_kind=task_kind,
            state="READY",
            generation=0,
            activation_key=activation_key,
            blocked_on_kind=None,
            blocked_on_ref=None,
            spawned_from_flag_id=None,
            spawned_from_task_run_id=parent_task_run_id,
            spawn_rule_id=spawn_rule_id,
            spawn_cause_kind="task_completion",
            spawn_cause_event_id=parent_completion_event_id,
            spawn_depth=0,
            spawn_budget_key=None,
            created_at=created_at,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.created",
                tenant_id=scope["tenant_id"],
                domain_id=scope["domain_id"],
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                ],
                payload={
                    "task_run_id": task_run_id,
                    "stage_id": stage_id,
                    "task_kind": task_kind,
                    "activation_key": activation_key,
                    "generation": 0,
                    "spawned_from_flag_id": None,
                    "spawned_from_task_run_id": parent_task_run_id,
                    "spawn_rule_id": spawn_rule_id,
                    "spawn_cause_kind": "task_completion",
                    "spawn_cause_event_id": parent_completion_event_id,
                    "spawn_budget_key": None,
                    "spawn_depth": 0,
                },
                idempotency_key=_event_idempotency_key(
                    receipt_event_idempotency_base,
                    f"dispatch-reporting.{spawn_rule_id}.task.run.created",
                ),
            ),
        )

    create_human_task(
        connection,
        human_task_id=human_task_id,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        task_kind=task_kind,
        state="OPEN",
        candidate_roles=candidate_roles,
        owner_role=owner_role,
        due_at=None,
        escalation_at=None,
        generation=0,
        created_at=created_at,
    )
    append_event(
        connection,
        _event_envelope(
            event_type="task.created",
            tenant_id=scope["tenant_id"],
            domain_id=scope["domain_id"],
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {"rel": "subject", "type": "task_run", "id": task_run_id},
                {"rel": "subject", "type": "human_task", "id": human_task_id},
            ],
            payload={
                "human_task_id": human_task_id,
                "task_kind": task_kind,
                "state": "OPEN",
                "candidate_roles": candidate_roles,
            },
            idempotency_key=_event_idempotency_key(
                receipt_event_idempotency_base,
                f"dispatch-reporting.{spawn_rule_id}.task.created",
            ),
        ),
    )
    return {
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "stage_id": stage_id,
        "task_kind": task_kind,
        "spawn_rule_id": spawn_rule_id,
        "activation_key": activation_key,
        "generation": 0,
        "spawned_from_flag_id": None,
    }


def _ensure_dispatch_reporting_review_approval(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    task_run_id: str,
    actor_id: str,
    actor_type: str,
    receipt_event_idempotency_base: str | None,
) -> dict[str, Any]:
    for approval in list_approvals_for_workflow_run(connection, workflow_run_id):
        if str(approval.get("scope_kind") or "") != "stage":
            continue
        if str(approval.get("scope_ref") or "") != DISPATCH_REVIEW_APPROVAL_SCOPE_REF:
            continue
        if str(approval.get("task_run_id") or "") != task_run_id:
            continue
        return approval

    return _request_approval_effects(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "requested_by_task_run_id": task_run_id,
            "approval_kind": "business_decision",
            "scope_kind": "stage",
            "scope_ref": DISPATCH_REVIEW_APPROVAL_SCOPE_REF,
            "candidate_roles": ["operations_manager"],
            "required_role": "operations_manager",
            "action": DISPATCH_REVIEW_APPROVAL_ACTION,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        approval_id=f"ap-{uuid4()}",
        task_run_id=task_run_id,
        requested_by_task_run_id=task_run_id,
        candidate_roles=["operations_manager"],
        allowed_responses=["approve", "reject", "request_changes", "cancel", "expire"],
        event_idempotency=_event_idempotency_key(
            receipt_event_idempotency_base,
            "dispatch-reporting.stage04.final-packet.approval.requested",
        ),
    )


def _apply_live_dispatch_completion_effects(
    connection: sqlite3.Connection,
    *,
    workflow_run: dict[str, Any],
    task_run: dict[str, Any],
    human_task: dict[str, Any],
    completion_outcome: str,
    actor_id: str,
    actor_type: str,
    scope: dict[str, Any],
    receipt_event_idempotency_base: str | None,
    parent_completion_event_id: str,
    created_at: str,
    storage_root: Path | None,
) -> dict[str, list[dict[str, Any]]]:
    if str(workflow_run.get("workflow_id") or "") != LIVE_DISPATCH_WORKFLOW_ID:
        return {"spawned_children": [], "requested_approvals": []}

    workflow_run_id = str(task_run["workflow_run_id"])
    parent_task_run_id = str(task_run["task_run_id"])
    human_task_id = str(human_task["human_task_id"])
    surface = (
        str(task_run.get("stage_id") or ""),
        str(task_run.get("task_kind") or ""),
        completion_outcome,
    )
    if surface == ("Stage01", "dispatch_seed_intake", "intake_ready_for_review"):
        latest_route_delta = _latest_artifact_for_kind(
            connection,
            workflow_run_id=workflow_run_id,
            artifact_kind=LIVE_ROUTE_DELTA_ARTIFACT_KIND,
        )
        if latest_route_delta is None:
            raise CommandError(
                code="required_artifact_missing",
                message="live dispatch intake completion requires a route-delta workbook upload",
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_kind": LIVE_ROUTE_DELTA_ARTIFACT_KIND,
                },
            )
        review_task = _ensure_live_dispatch_child_human_task(
            connection,
            workflow_run_id=workflow_run_id,
            activation_key=(
                f"live:{workflow_run_id}:stage03:dispatcher-review:"
                f"{latest_route_delta['artifact_version_id']}"
            ),
            stage_id="Stage03",
            task_kind=LIVE_REVIEW_TASK_KIND,
            candidate_roles=["dispatch_supervisor"],
            owner_role="dispatch_supervisor",
            actor_id=actor_id,
            actor_type=actor_type,
            scope=scope,
            parent_task_run_id=parent_task_run_id,
            spawn_rule_id="live_stage03_review_after_seed_intake",
            parent_completion_event_id=parent_completion_event_id,
            receipt_event_idempotency_base=receipt_event_idempotency_base,
            created_at=created_at,
        )
        return {"spawned_children": [review_task], "requested_approvals": []}

    if surface == ("Stage03", LIVE_REVIEW_TASK_KIND, "reviewed_replan_ready"):
        if storage_root is None:
            raise CommandError(
                code="storage_root_required",
                message="live dispatch finalize requires artifact storage access",
                details={"workflow_run_id": workflow_run_id},
            )
        artifacts = list_artifact_versions_for_workflow_run(connection, workflow_run_id)
        latest_route_delta = _latest_artifact_for_kind(
            connection,
            workflow_run_id=workflow_run_id,
            artifact_kind=LIVE_ROUTE_DELTA_ARTIFACT_KIND,
        )
        if latest_route_delta is None:
            raise CommandError(
                code="required_artifact_missing",
                message="live dispatch review completion requires a current route-delta workbook",
                details={
                    "workflow_run_id": workflow_run_id,
                    "artifact_kind": LIVE_ROUTE_DELTA_ARTIFACT_KIND,
                },
            )
        review_confirmation = _latest_review_confirmation_for_human_task(
            artifacts=artifacts,
            human_task_id=human_task_id,
        )
        reviewed_route_delta_artifact_version_id = _reviewed_artifact_id_from_confirmation(
            artifacts=artifacts,
            review_confirmation=review_confirmation,
            artifact_kind=LIVE_ROUTE_DELTA_ARTIFACT_KIND,
        )
        if reviewed_route_delta_artifact_version_id is None:
            raise CommandError(
                code="live_dispatch_review_requirements_not_satisfied",
                message="live dispatch finalize requires review confirmation on the latest route-delta workbook",
                details={
                    "workflow_run_id": workflow_run_id,
                    "human_task_id": human_task_id,
                    "artifact_kind": LIVE_ROUTE_DELTA_ARTIFACT_KIND,
                },
            )
        latest_route_delta_artifact_version_id = str(latest_route_delta["artifact_version_id"])
        if reviewed_route_delta_artifact_version_id != latest_route_delta_artifact_version_id:
            raise CommandError(
                code="stable_dispatch_delta_required",
                message="live dispatch finalize requires the reviewed route-delta workbook to remain the latest version",
                details={
                    "workflow_run_id": workflow_run_id,
                    "human_task_id": human_task_id,
                    "reviewed_route_delta_artifact_version_id": reviewed_route_delta_artifact_version_id,
                    "latest_route_delta_artifact_version_id": latest_route_delta_artifact_version_id,
                },
            )
        _finalize_live_dispatch_replan(
            connection,
            storage_root=storage_root,
            workflow_run_id=workflow_run_id,
            task_run_id=parent_task_run_id,
            human_task_id=human_task_id,
            reviewed_route_delta_artifact_version_id=reviewed_route_delta_artifact_version_id,
            actor_id=actor_id,
            actor_type=actor_type,
            receipt_event_idempotency_base=receipt_event_idempotency_base,
        )
        return {"spawned_children": [], "requested_approvals": []}

    return {"spawned_children": [], "requested_approvals": []}


def _ensure_live_dispatch_child_human_task(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    activation_key: str,
    stage_id: str,
    task_kind: str,
    candidate_roles: list[str],
    owner_role: str | None,
    actor_id: str,
    actor_type: str,
    scope: dict[str, Any],
    parent_task_run_id: str,
    spawn_rule_id: str,
    parent_completion_event_id: str,
    receipt_event_idempotency_base: str | None,
    created_at: str,
) -> dict[str, Any]:
    existing_task_run = get_task_run_by_activation_key(
        connection,
        workflow_run_id=workflow_run_id,
        activation_key=activation_key,
    )
    if existing_task_run is not None:
        if (
            str(existing_task_run.get("stage_id") or "") != stage_id
            or str(existing_task_run.get("task_kind") or "") != task_kind
        ):
            raise CommandError(
                code="duplicate_spawned_task_activation",
                message="live dispatch follow-on activation key is already in use by a different task",
                details={
                    "workflow_run_id": workflow_run_id,
                    "activation_key": activation_key,
                    "expected_stage_id": stage_id,
                    "expected_task_kind": task_kind,
                    "actual_task_run_id": str(existing_task_run["task_run_id"]),
                },
            )
        existing_human_task = get_human_task_by_task_run_id(
            connection,
            str(existing_task_run["task_run_id"]),
        )
        if existing_human_task is not None:
            return {
                "task_run_id": str(existing_task_run["task_run_id"]),
                "human_task_id": str(existing_human_task["human_task_id"]),
                "stage_id": stage_id,
                "task_kind": task_kind,
                "spawn_rule_id": spawn_rule_id,
                "activation_key": activation_key,
                "generation": int(existing_task_run.get("generation") or 0),
                "spawned_from_flag_id": existing_task_run.get("spawned_from_flag_id"),
            }

    task_run_id = (
        str(existing_task_run["task_run_id"])
        if existing_task_run is not None
        else f"tr-{uuid4()}"
    )
    human_task_id = f"ht-{uuid4()}"

    if existing_task_run is None:
        create_task_run(
            connection,
            task_run_id=task_run_id,
            workflow_run_id=workflow_run_id,
            stage_id=stage_id,
            task_kind=task_kind,
            state="READY",
            generation=0,
            activation_key=activation_key,
            blocked_on_kind=None,
            blocked_on_ref=None,
            spawned_from_flag_id=None,
            spawned_from_task_run_id=parent_task_run_id,
            spawn_rule_id=spawn_rule_id,
            spawn_cause_kind="task_completion",
            spawn_cause_event_id=parent_completion_event_id,
            spawn_depth=0,
            spawn_budget_key=None,
            created_at=created_at,
        )
        append_event(
            connection,
            _event_envelope(
                event_type="task.run.created",
                tenant_id=scope["tenant_id"],
                domain_id=scope["domain_id"],
                actor_type=actor_type,
                actor_id=actor_id,
                links=[
                    {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                    {"rel": "subject", "type": "task_run", "id": task_run_id},
                ],
                payload={
                    "task_run_id": task_run_id,
                    "stage_id": stage_id,
                    "task_kind": task_kind,
                    "activation_key": activation_key,
                    "generation": 0,
                    "spawned_from_flag_id": None,
                    "spawned_from_task_run_id": parent_task_run_id,
                    "spawn_rule_id": spawn_rule_id,
                    "spawn_cause_kind": "task_completion",
                    "spawn_cause_event_id": parent_completion_event_id,
                    "spawn_budget_key": None,
                    "spawn_depth": 0,
                },
                idempotency_key=_event_idempotency_key(
                    receipt_event_idempotency_base,
                    f"live-dispatch.{spawn_rule_id}.task.run.created",
                ),
            ),
        )

    create_human_task(
        connection,
        human_task_id=human_task_id,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        task_kind=task_kind,
        state="OPEN",
        candidate_roles=candidate_roles,
        owner_role=owner_role,
        due_at=None,
        escalation_at=None,
        generation=0,
        created_at=created_at,
    )
    append_event(
        connection,
        _event_envelope(
            event_type="task.created",
            tenant_id=scope["tenant_id"],
            domain_id=scope["domain_id"],
            actor_type=actor_type,
            actor_id=actor_id,
            links=[
                {"rel": "subject", "type": "workflow_run", "id": workflow_run_id},
                {"rel": "subject", "type": "task_run", "id": task_run_id},
                {"rel": "subject", "type": "human_task", "id": human_task_id},
            ],
            payload={
                "human_task_id": human_task_id,
                "task_kind": task_kind,
                "state": "OPEN",
                "candidate_roles": candidate_roles,
            },
            idempotency_key=_event_idempotency_key(
                receipt_event_idempotency_base,
                f"live-dispatch.{spawn_rule_id}.task.created",
            ),
        ),
    )
    return {
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "stage_id": stage_id,
        "task_kind": task_kind,
        "spawn_rule_id": spawn_rule_id,
        "activation_key": activation_key,
        "generation": 0,
        "spawned_from_flag_id": None,
    }


def _finalize_live_dispatch_replan(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    task_run_id: str,
    human_task_id: str,
    reviewed_route_delta_artifact_version_id: str,
    actor_id: str,
    actor_type: str,
    receipt_event_idempotency_base: str | None,
) -> None:
    reviewed_route_delta = get_artifact_version(
        connection,
        reviewed_route_delta_artifact_version_id,
    )
    if reviewed_route_delta is None:
        raise CommandError(
            code="artifact_version_not_found",
            message="reviewed route-delta artifact was not found for live dispatch finalize",
            details={"artifact_version_id": reviewed_route_delta_artifact_version_id},
        )
    actual_hours_artifact = _latest_artifact_for_kind(
        connection,
        workflow_run_id=workflow_run_id,
        artifact_kind=LIVE_ACTUAL_HOURS_ARTIFACT_KIND,
    )
    finalized_at = utc_now_iso()
    change_notice_metadata = {
        "schema_version": "1.0",
        "kind": "live_dispatch_change_notice",
        "workflow_run_id": workflow_run_id,
        "task_run_id": task_run_id,
        "human_task_id": human_task_id,
        "reviewed_route_delta_artifact_version_id": reviewed_route_delta_artifact_version_id,
        "actual_hours_artifact_version_id": (
            str(actual_hours_artifact["artifact_version_id"])
            if actual_hours_artifact is not None
            else None
        ),
        "published_at": finalized_at,
        "published_by": {"id": actor_id, "type": actor_type},
    }
    change_notice = _create_blob_artifact_version(
        connection,
        storage_root=storage_root,
        workflow_run_id=workflow_run_id,
        task_run_id=task_run_id,
        artifact_kind=LIVE_CHANGE_NOTICE_ARTIFACT_KIND,
        artifact_role="evidence",
        artifact_bytes=_json_bytes(change_notice_metadata),
        file_name=f"{workflow_run_id}-change-notice.json",
        media_type="application/json",
        metadata_json=change_notice_metadata,
        parent_artifact_version_id=reviewed_route_delta_artifact_version_id,
        supersedes_artifact_version_id=None,
        lineage_note="live_dispatch_change_notice",
        actor_id=actor_id,
        actor_type=actor_type,
        links=[
            {
                "subject_kind": "task_run",
                "subject_id": task_run_id,
                "relation_kind": "output",
            },
            {
                "subject_kind": "human_task",
                "subject_id": human_task_id,
                "relation_kind": "output",
            },
        ],
        event_idempotency=_event_idempotency_key(
            receipt_event_idempotency_base,
            "live-dispatch.change-notice.artifact.version.created",
        ),
    )

    reviewed_metadata = reviewed_route_delta.get("metadata_json")
    official_delta_metadata = dict(reviewed_metadata) if isinstance(reviewed_metadata, dict) else {}
    official_delta_metadata.update(
        {
            "officialized_from_artifact_version_id": reviewed_route_delta_artifact_version_id,
            "change_notice_artifact_version_id": str(change_notice["artifact_version_id"]),
            "finalized_at": finalized_at,
        }
    )
    official_delta = _create_artifact_version_effects(
        connection,
        {
            "artifact_version_id": f"av-{uuid4()}",
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": LIVE_OFFICIAL_DELTA_ARTIFACT_KIND,
            "artifact_role": "official_output",
            "media_type": str(reviewed_route_delta["media_type"]),
            "storage_uri": str(reviewed_route_delta["storage_uri"]),
            "content_digest": str(reviewed_route_delta["content_digest"]),
            "byte_size": reviewed_route_delta.get("byte_size"),
            "metadata_json": official_delta_metadata,
            "parent_artifact_version_id": reviewed_route_delta_artifact_version_id,
            "lineage_note": "live_dispatch_official_replan_delta",
            "links": [
                {
                    "subject_kind": "task_run",
                    "subject_id": task_run_id,
                    "relation_kind": "output",
                },
                {
                    "subject_kind": "human_task",
                    "subject_id": human_task_id,
                    "relation_kind": "output",
                },
            ],
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=_event_idempotency_key(
            receipt_event_idempotency_base,
            "live-dispatch.official-replan-delta.artifact.version.created",
        ),
    )
    _promote_pointer_effects(
        connection,
        {
            "workflow_run_id": workflow_run_id,
            "scope_kind": "stage",
            "scope_ref": "Stage05",
            "pointer_key": LIVE_OFFICIAL_POINTER_KEY,
            "artifact_kind": LIVE_OFFICIAL_DELTA_ARTIFACT_KIND,
            "artifact_version_id": str(official_delta["artifact_version_id"]),
            "promotion_reason": "official_dispatch_replan",
            "promoted_by_task_run_id": task_run_id,
            "reviewed_artifact_version_id": reviewed_route_delta_artifact_version_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=_event_idempotency_key(
            receipt_event_idempotency_base,
            "live-dispatch.official-replan-delta.artifact.pointer.promoted",
        ),
        drift_idempotency=_event_idempotency_key(
            receipt_event_idempotency_base,
            "live-dispatch.official-replan-delta.artifact.pointer.drift-detected",
        ),
    )


def _latest_artifact_for_kind(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
    artifact_kind: str,
) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for artifact in list_artifact_versions_for_workflow_run(connection, workflow_run_id):
        if str(artifact.get("artifact_kind") or "") != artifact_kind:
            continue
        latest = artifact
    return latest


def _load_dispatch_reporting_draft_template_record():
    try:
        return load_template_registry_catalog().template_by_id(
            DISPATCH_REPORTING_DRAFT_TEMPLATE_ID
        )
    except ValueError as exc:
        raise CommandError(
            code="template_not_found",
            message="required dispatch reporting draft template is unavailable",
            details={"template_id": DISPATCH_REPORTING_DRAFT_TEMPLATE_ID},
        ) from exc


def _read_artifact_blob_or_raise(artifact: dict[str, Any]) -> bytes:
    storage_uri = str(artifact.get("storage_uri") or "").strip()
    if not storage_uri:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact blob not found",
            details={"artifact_version_id": str(artifact.get("artifact_version_id") or "")},
        )
    try:
        return read_blob(storage_uri)
    except ArtifactStorageError as exc:
        raise CommandError(
            code="artifact_version_not_found",
            message="artifact blob not found",
            details={"artifact_version_id": str(artifact.get("artifact_version_id") or "")},
        ) from exc


def _create_blob_artifact_version(
    connection: sqlite3.Connection,
    *,
    storage_root: Path,
    workflow_run_id: str,
    task_run_id: str | None,
    artifact_kind: str,
    artifact_role: str | None,
    artifact_bytes: bytes,
    file_name: str,
    media_type: str,
    metadata_json: dict[str, Any],
    parent_artifact_version_id: str | None,
    supersedes_artifact_version_id: str | None,
    lineage_note: str,
    actor_id: str,
    actor_type: str,
    links: list[dict[str, str]] | None,
    event_idempotency: str | None,
) -> dict[str, Any]:
    storage_uri, content_digest, byte_size = write_blob(
        storage_root=storage_root,
        workflow_run_id=workflow_run_id,
        file_name=file_name,
        content=artifact_bytes,
    )
    return _create_artifact_version_effects(
        connection,
        {
            "artifact_version_id": f"av-{uuid4()}",
            "workflow_run_id": workflow_run_id,
            "task_run_id": task_run_id,
            "artifact_kind": artifact_kind,
            "artifact_role": artifact_role,
            "media_type": media_type,
            "storage_uri": storage_uri,
            "content_digest": content_digest,
            "byte_size": byte_size,
            "metadata_json": {
                **metadata_json,
                "file_name": file_name,
                "ingress_file_name": file_name,
                "ingress_media_type": media_type,
            },
            "parent_artifact_version_id": parent_artifact_version_id,
            "supersedes_artifact_version_id": supersedes_artifact_version_id,
            "lineage_note": lineage_note,
            "links": links,
            "actor_id": actor_id,
            "actor_type": actor_type,
        },
        event_idempotency=event_idempotency,
    )


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


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
