from __future__ import annotations

from typing import Any, Iterable

from onetruth.application.handlers._shared.command_boundary import CommandError
from onetruth.application.services.stage06_openai_sandbox import (
    evaluate_stage06_policy_for_actor,
)
from onetruth.application.services.weekly_stage04_openai_agent import (
    evaluate_weekly_stage04_policy_for_actor,
)

from .shared import CapabilityDecision, DecisionReason, Principal, allow, deny, reason


def claim_decision(
    *,
    task: dict[str, Any],
    principal: Principal,
) -> CapabilityDecision:
    state = str(task.get("state") or "")
    candidate_roles = tuple(str(role) for role in task.get("candidate_roles") or [])
    assignee_actor_id = str(task.get("assignee_actor_id") or "")
    assignee_actor_type = str(task.get("assignee_actor_type") or "")
    role_match = _roles_intersect(candidate_roles, principal.actor_roles) if candidate_roles else True

    reasons: list[DecisionReason] = []
    if state != "OPEN":
        reasons.append(reason("task_not_open", state=state))
    if assignee_actor_id:
        reasons.append(
            reason(
                "task_already_assigned",
                assignee_actor_id=assignee_actor_id or None,
                assignee_actor_type=assignee_actor_type or None,
            )
        )
    if state == "OPEN" and not role_match:
        reasons.append(
            reason(
                "candidate_role_mismatch",
                candidate_roles=list(candidate_roles),
                actor_roles=list(principal.actor_roles),
            )
        )

    if state == "OPEN" and not assignee_actor_id and role_match:
        return allow("task.claim")
    return deny("task.claim", reasons=reasons)


def complete_decision(
    *,
    task: dict[str, Any],
    principal: Principal,
    requirement_reasons: Iterable[DecisionReason] = (),
) -> CapabilityDecision:
    state = str(task.get("state") or "")
    reasons: list[DecisionReason] = []
    if state != "CLAIMED":
        reasons.append(reason("task_not_claimed", state=state))
    elif not _is_assignee(task, principal):
        reasons.append(_task_assignee_reason(task=task, principal=principal))

    requirement_reason_list = tuple(requirement_reasons)
    if not reasons and requirement_reason_list:
        reasons.extend(requirement_reason_list)

    if state == "CLAIMED" and _is_assignee(task, principal) and not requirement_reason_list:
        return allow("task.complete")
    return deny("task.complete", reasons=reasons)


def confirm_review_decision(
    *,
    task: dict[str, Any],
    principal: Principal,
    has_pending_review_confirmation: bool,
) -> CapabilityDecision:
    reasons: list[DecisionReason] = []
    if not _is_assignee(task, principal):
        reasons.append(_task_assignee_reason(task=task, principal=principal))
    if not has_pending_review_confirmation:
        reasons.append(reason("review_confirmation_not_pending"))
    if _is_assignee(task, principal) and has_pending_review_confirmation:
        return allow("task.confirm_review")
    return deny("task.confirm_review", reasons=reasons)


def execute_stage06_agent_review_decision(
    *,
    task: dict[str, Any],
    principal: Principal,
) -> CapabilityDecision:
    return _execute_decision(
        capability_id="task.execute.stage06_agent_review",
        task=task,
        principal=principal,
        expected_stage_id="Stage06",
        expected_task_kind="review_packet",
        evaluator=evaluate_stage06_policy_for_actor,
    )


def execute_weekly_stage04_openai_agent_decision(
    *,
    task: dict[str, Any],
    principal: Principal,
) -> CapabilityDecision:
    return _execute_decision(
        capability_id="task.execute.weekly_stage04_openai_agent",
        task=task,
        principal=principal,
        expected_stage_id="Stage04",
        expected_task_kind="work_item",
        evaluator=evaluate_weekly_stage04_policy_for_actor,
    )


def _execute_decision(
    *,
    capability_id: str,
    task: dict[str, Any],
    principal: Principal,
    expected_stage_id: str,
    expected_task_kind: str,
    evaluator,
) -> CapabilityDecision:
    reasons: list[DecisionReason] = []
    if not _is_assignee(task, principal):
        reasons.append(_task_assignee_reason(task=task, principal=principal))

    stage_id = str(task.get("stage_id") or "")
    task_kind = str(task.get("task_kind") or "")
    if stage_id != expected_stage_id or task_kind != expected_task_kind:
        reasons.append(
            reason(
                "task_execute_target_mismatch",
                stage_id=stage_id,
                task_kind=task_kind,
                expected_stage_id=expected_stage_id,
                expected_task_kind=expected_task_kind,
            )
        )

    if reasons:
        return deny(capability_id, reasons=reasons)

    try:
        decision, _, _ = evaluator(
            actor_type=principal.actor_type,
            actor_roles=principal.actor_roles,
        )
    except CommandError:
        return deny(
            capability_id,
            reasons=[reason("task_policy_check_failed")],
        )
    if decision != "allow":
        return deny(
            capability_id,
            reasons=[reason("task_policy_denied", policy_decision=decision)],
        )
    return allow(capability_id)


def _is_assignee(task: dict[str, Any], principal: Principal) -> bool:
    state = str(task.get("state") or "")
    assignee_actor_id = str(task.get("assignee_actor_id") or "")
    assignee_actor_type = str(task.get("assignee_actor_type") or "")
    return (
        state == "CLAIMED"
        and assignee_actor_id == principal.actor_id
        and assignee_actor_type == principal.actor_type
    )


def _task_assignee_reason(
    *,
    task: dict[str, Any],
    principal: Principal,
) -> DecisionReason:
    assignee_actor_id = str(task.get("assignee_actor_id") or "")
    assignee_actor_type = str(task.get("assignee_actor_type") or "")
    if assignee_actor_id:
        return reason(
            "claimed_by_other_actor",
            assignee_actor_id=assignee_actor_id or None,
            assignee_actor_type=assignee_actor_type or None,
            actor_id=principal.actor_id,
            actor_type=principal.actor_type,
        )
    return reason(
        "task_not_assigned_to_actor",
        actor_id=principal.actor_id,
        actor_type=principal.actor_type,
    )


def _roles_intersect(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return bool(set(left).intersection(right))
