from __future__ import annotations

import sqlite3
from typing import Any

from onetruth.application.handlers.workflow_task_lifecycle import CommandError
from onetruth.application.services.stage06_openai_sandbox import (
    evaluate_stage06_policy_for_actor,
)

ACTIVE_FLAG_STATES = {"open", "triage", "blocked"}
FLAG_TRANSITION_ROLES = {
    "dispatch_supervisor",
    "operations_manager",
    "fleet_coordinator",
    "schedule_planner",
}


def build_artifact_link_count_index(
    connection: sqlite3.Connection,
    *,
    workflow_run_id: str,
) -> dict[tuple[str, str], int]:
    rows = connection.execute(
        """
        SELECT
            subject_kind,
            subject_id,
            COUNT(*) AS linked_artifact_count
        FROM artifact_links
        WHERE workflow_run_id = ?
        GROUP BY subject_kind, subject_id
        """,
        (workflow_run_id,),
    ).fetchall()
    index: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row["subject_kind"]), str(row["subject_id"]))
        index[key] = int(row["linked_artifact_count"])
    return index


def compute_human_task_actionability(
    *,
    task: dict[str, Any],
    actor_id: str,
    actor_type: str,
    actor_roles: tuple[str, ...],
    linked_artifact_count: int,
) -> dict[str, Any]:
    state = str(task.get("state") or "")
    candidate_roles = tuple(str(role) for role in task.get("candidate_roles") or [])
    role_match = _roles_intersect(candidate_roles, actor_roles) if candidate_roles else True
    assignee_actor_id = str(task.get("assignee_actor_id") or "")
    assignee_actor_type = str(task.get("assignee_actor_type") or "")
    is_assignee = state == "CLAIMED" and assignee_actor_id == actor_id and assignee_actor_type == actor_type

    blocking_requirements: list[dict[str, Any]] = []
    missing_required_inputs: list[str] = []

    if str(task.get("task_kind")) == "information_request":
        requirement = {
            "requirement": "linked_artifact_minimum",
            "minimum_count": 1,
            "current_count": linked_artifact_count,
            "status": "satisfied" if linked_artifact_count >= 1 else "missing",
        }
        blocking_requirements.append(requirement)
        if linked_artifact_count < 1:
            missing_required_inputs.append("linked_artifact")

    if state == "CLAIMED" and not is_assignee:
        blocking_requirements.append(
            {
                "requirement": "claimed_by_other_actor",
                "assignee_actor_id": assignee_actor_id or None,
                "assignee_actor_type": assignee_actor_type or None,
                "status": "missing",
            }
        )

    can_claim = state == "OPEN" and not assignee_actor_id and role_match
    can_complete = is_assignee and not missing_required_inputs
    can_upload_attachment = True
    can_run_stage06_agent_review = _can_run_stage06_agent_review(
        stage_id=str(task.get("stage_id") or ""),
        task_kind=str(task.get("task_kind") or ""),
        is_assignee=is_assignee,
        actor_type=actor_type,
        actor_roles=actor_roles,
    )

    if state == "OPEN" and not role_match:
        blocking_requirements.append(
            {
                "requirement": "candidate_role_match",
                "candidate_roles": list(candidate_roles),
                "actor_roles": list(actor_roles),
                "status": "missing",
            }
        )

    available_actions: list[str] = []
    if can_claim:
        available_actions.append("claim")
    if can_complete:
        available_actions.append("complete")
    if can_run_stage06_agent_review:
        available_actions.append("run_stage06_agent_review")
    if can_upload_attachment:
        available_actions.append("upload_attachment")
    if linked_artifact_count > 0:
        available_actions.append("download_attachments")

    return {
        "available_actions": available_actions,
        "blocking_requirements": blocking_requirements,
        "linked_artifact_count": linked_artifact_count,
        "missing_required_inputs": missing_required_inputs,
        "can_complete": can_complete,
        "can_upload_attachment": can_upload_attachment,
        "can_run_stage06_agent_review": can_run_stage06_agent_review,
    }


def compute_approval_actionability(
    *,
    approval: dict[str, Any],
    actor_roles: tuple[str, ...],
    linked_artifact_count: int,
) -> dict[str, Any]:
    state = str(approval.get("state") or "")
    required_role = str(approval.get("required_role") or "")
    candidate_roles = tuple(str(role) for role in approval.get("candidate_roles") or [])
    role_match = (
        required_role in actor_roles
        if required_role
        else (_roles_intersect(candidate_roles, actor_roles) if candidate_roles else False)
    )
    can_respond = state == "PENDING" and role_match
    can_upload_attachment = True

    blocking_requirements: list[dict[str, Any]] = []
    if state == "PENDING" and not role_match:
        blocking_requirements.append(
            {
                "requirement": "approval_role_match",
                "required_role": required_role or None,
                "candidate_roles": list(candidate_roles),
                "actor_roles": list(actor_roles),
                "status": "missing",
            }
        )

    available_actions: list[str] = []
    if can_respond:
        available_actions.append("respond")
    if can_upload_attachment:
        available_actions.append("upload_attachment")
    if linked_artifact_count > 0:
        available_actions.append("download_attachments")

    return {
        "available_actions": available_actions,
        "blocking_requirements": blocking_requirements,
        "linked_artifact_count": linked_artifact_count,
        "missing_required_inputs": [],
        "can_complete": False,
        "can_upload_attachment": can_upload_attachment,
        "can_run_stage06_agent_review": False,
    }


def compute_flag_actionability(
    *,
    flag: dict[str, Any],
    actor_roles: tuple[str, ...],
    linked_artifact_count: int,
) -> dict[str, Any]:
    state = str(flag.get("state") or "")
    can_transition = state in ACTIVE_FLAG_STATES and _roles_intersect(
        tuple(FLAG_TRANSITION_ROLES),
        actor_roles,
    )
    can_upload_attachment = True

    available_actions: list[str] = []
    if can_transition:
        available_actions.append("transition")
    if can_upload_attachment:
        available_actions.append("upload_attachment")
    if linked_artifact_count > 0:
        available_actions.append("download_attachments")

    return {
        "available_actions": available_actions,
        "blocking_requirements": [],
        "linked_artifact_count": linked_artifact_count,
        "missing_required_inputs": [],
        "can_complete": False,
        "can_upload_attachment": can_upload_attachment,
        "can_run_stage06_agent_review": False,
    }


def _roles_intersect(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return bool(set(left).intersection(right))


def _can_run_stage06_agent_review(
    *,
    stage_id: str,
    task_kind: str,
    is_assignee: bool,
    actor_type: str,
    actor_roles: tuple[str, ...],
) -> bool:
    if not is_assignee:
        return False
    if stage_id != "Stage06" or task_kind != "review_packet":
        return False
    try:
        decision, _, _ = evaluate_stage06_policy_for_actor(
            actor_type=actor_type,
            actor_roles=actor_roles,
        )
    except CommandError:
        # Misconfigured policy override should fail closed in read projections.
        return False
    return decision == "allow"

