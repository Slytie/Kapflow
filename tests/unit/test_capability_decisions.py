from __future__ import annotations

from onetruth.application.services.capabilities import (
    DecisionReason,
    Principal,
    claim_decision,
    complete_decision,
    confirm_review_decision,
    download_decision,
    execute_stage06_agent_review_decision,
    execute_weekly_stage04_openai_agent_decision,
    legacy_reason_codes,
    respond_decision,
    transition_decision,
    upload_decision,
)
from onetruth.application.services.task_actionability import (
    compute_human_task_actionability,
)


def _principal(*, actor_id: str, actor_roles: tuple[str, ...]) -> Principal:
    return Principal(
        actor_id=actor_id,
        actor_type="human",
        actor_roles=actor_roles,
    )


def _task(**overrides):
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


def _approval(**overrides):
    approval = {
        "state": "PENDING",
        "required_role": None,
        "candidate_roles": ["dispatch_supervisor"],
    }
    approval.update(overrides)
    return approval


def _flag(**overrides):
    flag = {"state": "open"}
    flag.update(overrides)
    return flag


def test_task_claim_decision_denies_candidate_role_mismatch() -> None:
    decision = claim_decision(
        task=_task(),
        principal=_principal(
            actor_id="human:schedule-planner-1",
            actor_roles=("schedule_planner",),
        ),
    )

    assert decision.allowed is False
    assert legacy_reason_codes(decision.reasons) == ["candidate_role_mismatch"]


def test_task_completion_is_assignee_based_not_candidate_role_based() -> None:
    decision = complete_decision(
        task=_task(
            state="CLAIMED",
            assignee_actor_id="human:finance-approver-1",
            assignee_actor_type="human",
        ),
        principal=_principal(
            actor_id="human:finance-approver-1",
            actor_roles=("finance_approver",),
        ),
    )

    assert decision.allowed is True


def test_confirm_review_stays_separate_from_completion_blockers() -> None:
    task = _task(
        state="CLAIMED",
        assignee_actor_id="human:dispatch-supervisor-1",
        assignee_actor_type="human",
    )
    completion = complete_decision(
        task=task,
        principal=_principal(
            actor_id="human:dispatch-supervisor-1",
            actor_roles=("dispatch_supervisor",),
        ),
        requirement_reasons=(
            DecisionReason(
                code="required_review_confirmation_missing",
                details={"artifact_kind": "schedule.stage06.publish_packet"},
            ),
        ),
    )
    confirmation = confirm_review_decision(
        task=task,
        principal=_principal(
            actor_id="human:dispatch-supervisor-1",
            actor_roles=("dispatch_supervisor",),
        ),
        has_pending_review_confirmation=True,
    )

    assert completion.allowed is False
    assert confirmation.allowed is True


def test_stage06_execute_decision_is_policy_gated() -> None:
    allowed = execute_stage06_agent_review_decision(
        task=_task(
            state="CLAIMED",
            stage_id="Stage06",
            task_kind="review_packet",
            assignee_actor_id="human:dispatch-supervisor-1",
            assignee_actor_type="human",
        ),
        principal=_principal(
            actor_id="human:dispatch-supervisor-1",
            actor_roles=("dispatch_supervisor",),
        ),
    )
    denied = execute_stage06_agent_review_decision(
        task=_task(
            state="CLAIMED",
            stage_id="Stage06",
            task_kind="review_packet",
            assignee_actor_id="human:schedule-planner-1",
            assignee_actor_type="human",
        ),
        principal=_principal(
            actor_id="human:schedule-planner-1",
            actor_roles=("schedule_planner",),
        ),
    )

    assert allowed.allowed is True
    assert denied.allowed is False
    assert legacy_reason_codes(denied.reasons) == ["task_policy_denied"]


def test_weekly_stage04_execute_decision_is_policy_gated() -> None:
    allowed = execute_weekly_stage04_openai_agent_decision(
        task=_task(
            state="CLAIMED",
            stage_id="Stage04",
            task_kind="work_item",
            assignee_actor_id="human:schedule-planner-1",
            assignee_actor_type="human",
        ),
        principal=_principal(
            actor_id="human:schedule-planner-1",
            actor_roles=("schedule_planner",),
        ),
    )
    denied = execute_weekly_stage04_openai_agent_decision(
        task=_task(
            state="CLAIMED",
            stage_id="Stage04",
            task_kind="work_item",
            assignee_actor_id="human:finance-approver-1",
            assignee_actor_type="human",
        ),
        principal=_principal(
            actor_id="human:finance-approver-1",
            actor_roles=("finance_approver",),
        ),
    )

    assert allowed.allowed is True
    assert denied.allowed is False
    assert legacy_reason_codes(denied.reasons) == ["task_policy_denied"]


def test_approval_required_role_takes_precedence_over_candidate_roles() -> None:
    denied = respond_decision(
        approval=_approval(
            required_role="dispatch_supervisor",
            candidate_roles=["schedule_planner"],
        ),
        principal=_principal(
            actor_id="human:schedule-planner-1",
            actor_roles=("schedule_planner",),
        ),
    )
    allowed = respond_decision(
        approval=_approval(
            required_role="dispatch_supervisor",
            candidate_roles=["schedule_planner"],
        ),
        principal=_principal(
            actor_id="human:dispatch-supervisor-1",
            actor_roles=("dispatch_supervisor",),
        ),
    )

    assert denied.allowed is False
    assert legacy_reason_codes(denied.reasons) == ["approval_role_mismatch"]
    assert allowed.allowed is True


def test_flag_transition_is_separate_from_upload_and_download() -> None:
    transition = transition_decision(
        flag=_flag(),
        principal=_principal(
            actor_id="human:finance-approver-1",
            actor_roles=("finance_approver",),
        ),
    )
    upload = upload_decision()
    download = download_decision(linked_artifact_count=0)

    assert transition.allowed is False
    assert upload.allowed is True
    assert download.allowed is False


def test_structured_reasons_project_back_to_legacy_reason_codes() -> None:
    result = compute_human_task_actionability(
        task=_task(
            state="CLAIMED",
            assignee_actor_id="human:schedule-planner-1",
            assignee_actor_type="human",
            candidate_roles=["schedule_planner"],
        ),
        actor_id="human:schedule-planner-1",
        actor_type="human",
        actor_roles=("schedule_planner",),
        linked_artifact_count=0,
        requirement_state={
            "required_uploads": [],
            "required_reviews": [],
            "blocking_reasons": [
                {
                    "code": "required_upload_missing",
                    "details": {"dataset_key": "schedule.supervisor_review.doc"},
                }
            ],
            "blocking_reason_codes": [],
            "missing_required_inputs": ["schedule.supervisor_review.doc"],
        },
    )

    assert result["can_complete"] is False
    assert result["blocking_reason_codes"] == [
        "required_upload_missing:schedule.supervisor_review.doc"
    ]
