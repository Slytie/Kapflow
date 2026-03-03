from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STAGE07_MAX_SPAWN_DEPTH = 5
STAGE07_MAX_CHILDREN_PER_ISSUE = 4


@dataclass(frozen=True)
class Stage07SpawnPlan:
    activation_key: str
    spawn_rule_id: str
    stage_id: str
    task_kind: str
    candidate_roles: list[str]
    owner_role: str | None
    spawned_from_flag_id: str
    spawn_depth: int
    spawn_budget_key: str
    spawn_cause_kind: str
    spawn_cause_event_id: str


class Stage07SpawnError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, Any]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def build_stage07_issue_activation_key(
    *,
    workflow_run_id: str,
    flag_id: str,
    task_kind: str,
    generation: int,
) -> str:
    return f"{workflow_run_id}|{flag_id}|{task_kind}|{generation}"


def resolve_stage07_spawn_plans(
    *,
    parent_task_run: dict[str, Any],
    completion_outcome: str,
    parent_completion_event_id: str,
) -> list[Stage07SpawnPlan]:
    stage_id = str(parent_task_run.get("stage_id") or "")
    if stage_id != "Stage07":
        return []

    parent_task_kind = str(parent_task_run.get("task_kind") or "")
    if parent_task_kind in {"final_review", "information_request"}:
        return []

    spawned_from_flag_id = str(parent_task_run.get("spawned_from_flag_id") or "").strip()
    if not spawned_from_flag_id:
        # Stage07 loop tasks are always issue-scoped.
        return []

    outcome_map: dict[str, dict[str, Any]] = {
        "replan_requires_missing_information": {
            "spawn_rule_id": "stage07_request_issue_information",
            "stage_id": "Stage07",
            "task_kind": "information_request",
            "candidate_roles": ["fleet_coordinator", "schedule_planner"],
            "owner_role": "operations_manager",
        },
        "resolution_creates_child_issue": {
            "spawn_rule_id": "stage07_follow_on_exception_triage",
            "stage_id": "Stage07",
            "task_kind": "exception_triage",
            "candidate_roles": ["operations_manager"],
            "owner_role": "operations_manager",
        },
        "major_replan_is_ready_for_review": {
            "spawn_rule_id": "stage07_final_replan_review",
            "stage_id": "Stage07",
            "task_kind": "final_review",
            "candidate_roles": ["operations_manager"],
            "owner_role": "operations_manager",
        },
    }
    if completion_outcome not in outcome_map:
        return []

    next_depth = int(parent_task_run.get("spawn_depth") or 0) + 1
    if next_depth > STAGE07_MAX_SPAWN_DEPTH:
        raise Stage07SpawnError(
            code="stage07_spawn_depth_exceeded",
            message="stage07 completion spawn depth budget exceeded",
            details={
                "parent_task_run_id": str(parent_task_run.get("task_run_id")),
                "parent_spawn_depth": int(parent_task_run.get("spawn_depth") or 0),
                "next_spawn_depth": next_depth,
                "max_spawn_depth": STAGE07_MAX_SPAWN_DEPTH,
            },
        )

    workflow_run_id = str(parent_task_run.get("workflow_run_id"))
    parent_task_run_id = str(parent_task_run.get("task_run_id"))
    next_generation = int(parent_task_run.get("generation") or 0) + 1
    spawn_budget_key = str(
        parent_task_run.get("spawn_budget_key")
        or f"stage07:{workflow_run_id}:{spawned_from_flag_id}"
    )
    selected = outcome_map[completion_outcome]
    activation_key = build_stage07_issue_activation_key(
        workflow_run_id=workflow_run_id,
        flag_id=spawned_from_flag_id,
        task_kind=str(selected["task_kind"]),
        generation=next_generation,
    )
    plans = [
        Stage07SpawnPlan(
            activation_key=activation_key,
            spawn_rule_id=str(selected["spawn_rule_id"]),
            stage_id=str(selected["stage_id"]),
            task_kind=str(selected["task_kind"]),
            candidate_roles=[str(role) for role in selected["candidate_roles"]],
            owner_role=(
                str(selected["owner_role"])
                if selected.get("owner_role") is not None
                else None
            ),
            spawned_from_flag_id=spawned_from_flag_id,
            spawn_depth=next_depth,
            spawn_budget_key=spawn_budget_key,
            spawn_cause_kind="task_completion",
            spawn_cause_event_id=parent_completion_event_id,
        )
    ]
    if len(plans) > STAGE07_MAX_CHILDREN_PER_ISSUE:
        raise Stage07SpawnError(
            code="stage07_spawn_budget_exceeded",
            message="stage07 completion exceeded per-issue child spawn budget",
            details={
                "parent_task_run_id": parent_task_run_id,
                "max_children": STAGE07_MAX_CHILDREN_PER_ISSUE,
            },
        )
    return plans
