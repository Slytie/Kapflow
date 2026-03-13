from __future__ import annotations

from typing import Any

import yaml

from onetruth.application.services.task_actionability import (
    compute_approval_actionability,
    compute_flag_actionability,
    compute_human_task_actionability,
)
from tests.helpers.repo_paths import REPO_ROOT


CAPABILITY_MATRIX: dict[str, dict[str, Any]] = {
    "routing": {"permission_action": None},
    "claim": {"permission_action": "task.claim"},
    "complete": {"permission_action": "task.complete"},
    "execute": {"permission_action": None},
    "collaborate_upload": {"permission_action": "artifact.upload"},
    "approval_respond": {"permission_action": "approval.respond"},
    "flag_transition": {"permission_action": "flag.resolve"},
    "override": {"permission_action": None},
}


def _permission_action_ids() -> set[str]:
    loaded = yaml.safe_load(
        (REPO_ROOT / "schemas" / "policy" / "permissions.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    actions = loaded.get("actions")
    assert isinstance(actions, list)
    return {
        str(item["id"])
        for item in actions
        if isinstance(item, dict) and item.get("id") is not None
    }


def _human_task(**overrides: Any) -> dict[str, Any]:
    task = {
        "state": "OPEN",
        "candidate_roles": ["dispatch_supervisor"],
        "assignee_actor_id": None,
        "assignee_actor_type": None,
        "stage_id": "Stage05",
        "task_kind": "information_request",
    }
    task.update(overrides)
    return task


def _approval(**overrides: Any) -> dict[str, Any]:
    approval = {
        "state": "PENDING",
        "required_role": None,
        "candidate_roles": ["dispatch_supervisor"],
    }
    approval.update(overrides)
    return approval


def _flag(**overrides: Any) -> dict[str, Any]:
    flag = {"state": "open"}
    flag.update(overrides)
    return flag


def test_capability_matrix_uses_existing_permission_vocabulary() -> None:
    action_ids = _permission_action_ids()
    referenced_actions = {
        entry["permission_action"]
        for entry in CAPABILITY_MATRIX.values()
        if entry["permission_action"] is not None
    }

    assert referenced_actions <= action_ids
    assert CAPABILITY_MATRIX["routing"]["permission_action"] is None
    assert CAPABILITY_MATRIX["execute"]["permission_action"] is None
    assert CAPABILITY_MATRIX["override"]["permission_action"] is None


def test_candidate_roles_gate_claim_but_not_upload() -> None:
    allowed = compute_human_task_actionability(
        task=_human_task(),
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=("dispatch_supervisor",),
        linked_artifact_count=0,
    )
    denied = compute_human_task_actionability(
        task=_human_task(),
        actor_id="human:schedule-planner-1",
        actor_type="human",
        actor_roles=("schedule_planner",),
        linked_artifact_count=0,
    )

    assert "claim" in allowed["available_actions"]
    assert "claim" not in denied["available_actions"]
    assert "candidate_role_mismatch" in denied["blocking_reason_codes"]
    assert denied["can_upload_attachment"] is True
    assert "upload_attachment" in denied["available_actions"]


def test_completion_is_assignee_based_after_claim() -> None:
    result = compute_human_task_actionability(
        task=_human_task(
            state="CLAIMED",
            assignee_actor_id="human:schedule-planner-1",
            assignee_actor_type="human",
        ),
        actor_id="human:schedule-planner-1",
        actor_type="human",
        actor_roles=("finance_approver",),
        linked_artifact_count=0,
    )

    assert result["can_complete"] is True
    assert "complete" in result["available_actions"]


def test_stage06_execute_is_separate_from_completion() -> None:
    allowed = compute_human_task_actionability(
        task=_human_task(
            state="CLAIMED",
            stage_id="Stage06",
            task_kind="review_packet",
            assignee_actor_id="human:dispatch-supervisor-1",
            assignee_actor_type="human",
        ),
        actor_id="human:dispatch-supervisor-1",
        actor_type="human",
        actor_roles=("dispatch_supervisor",),
        linked_artifact_count=0,
    )
    denied = compute_human_task_actionability(
        task=_human_task(
            state="CLAIMED",
            stage_id="Stage06",
            task_kind="review_packet",
            assignee_actor_id="human:schedule-planner-1",
            assignee_actor_type="human",
        ),
        actor_id="human:schedule-planner-1",
        actor_type="human",
        actor_roles=("schedule_planner",),
        linked_artifact_count=0,
    )

    assert allowed["can_complete"] is True
    assert allowed["can_run_stage06_agent_review"] is True
    assert "run_stage06_agent_review" in allowed["available_actions"]

    assert denied["can_complete"] is True
    assert denied["can_run_stage06_agent_review"] is False
    assert "run_stage06_agent_review" not in denied["available_actions"]


def test_weekly_stage04_execute_is_policy_gated_separately() -> None:
    allowed = compute_human_task_actionability(
        task=_human_task(
            state="CLAIMED",
            stage_id="Stage04",
            task_kind="work_item",
            assignee_actor_id="human:schedule-planner-1",
            assignee_actor_type="human",
        ),
        actor_id="human:schedule-planner-1",
        actor_type="human",
        actor_roles=("schedule_planner",),
        linked_artifact_count=0,
    )
    denied = compute_human_task_actionability(
        task=_human_task(
            state="CLAIMED",
            stage_id="Stage04",
            task_kind="work_item",
            assignee_actor_id="human:finance-approver-1",
            assignee_actor_type="human",
        ),
        actor_id="human:finance-approver-1",
        actor_type="human",
        actor_roles=("finance_approver",),
        linked_artifact_count=0,
    )

    assert allowed["can_complete"] is True
    assert allowed["can_run_weekly_stage04_openai_agent"] is True
    assert "run_weekly_stage04_openai_agent" in allowed["available_actions"]

    assert denied["can_complete"] is True
    assert denied["can_run_weekly_stage04_openai_agent"] is False
    assert "run_weekly_stage04_openai_agent" not in denied["available_actions"]


def test_required_role_takes_precedence_for_approval_response() -> None:
    denied = compute_approval_actionability(
        approval=_approval(
            required_role="dispatch_supervisor",
            candidate_roles=["schedule_planner"],
        ),
        actor_roles=("schedule_planner",),
        linked_artifact_count=0,
    )
    allowed = compute_approval_actionability(
        approval=_approval(
            required_role="dispatch_supervisor",
            candidate_roles=["schedule_planner"],
        ),
        actor_roles=("dispatch_supervisor",),
        linked_artifact_count=0,
    )

    assert "respond" not in denied["available_actions"]
    assert "upload_attachment" in denied["available_actions"]
    assert denied["blocking_requirements"][0]["required_role"] == "dispatch_supervisor"
    assert "respond" in allowed["available_actions"]


def test_candidate_roles_are_approval_fallback_when_required_role_is_absent() -> None:
    result = compute_approval_actionability(
        approval=_approval(required_role=None, candidate_roles=["operations_manager"]),
        actor_roles=("operations_manager",),
        linked_artifact_count=0,
    )

    assert "respond" in result["available_actions"]


def test_flag_transition_is_separate_from_upload() -> None:
    allowed = compute_flag_actionability(
        flag=_flag(),
        actor_roles=("operations_manager",),
        linked_artifact_count=0,
    )
    denied = compute_flag_actionability(
        flag=_flag(),
        actor_roles=("finance_approver",),
        linked_artifact_count=0,
    )

    assert "transition" in allowed["available_actions"]
    assert "transition" not in denied["available_actions"]
    assert "upload_attachment" in denied["available_actions"]
