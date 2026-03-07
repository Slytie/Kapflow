from __future__ import annotations

from dataclasses import dataclass
from typing import Any


STAGE06_MAX_SPAWN_DEPTH = 3


@dataclass(frozen=True)
class Stage06SpawnPlan:
    activation_key: str
    spawn_rule_id: str
    stage_id: str
    task_kind: str
    candidate_roles: list[str]
    owner_role: str | None
    spawn_depth: int
    spawn_budget_key: str
    spawn_cause_kind: str
    spawn_cause_event_id: str


class Stage06SpawnError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, Any]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def resolve_stage06_spawn_plans(
    *,
    parent_task_run: dict[str, Any],
    completion_outcome: str,
    parent_completion_event_id: str,
) -> list[Stage06SpawnPlan]:
    stage_id = str(parent_task_run.get("stage_id") or "")
    if stage_id != "Stage06":
        return []

    parent_task_kind = str(parent_task_run.get("task_kind") or "")
    if parent_task_kind == "information_request":
        return []

    outcome_map: dict[str, dict[str, Any]] = {
        "review_requires_more_information": {
            "spawn_rule_id": "stage06_request_missing_information",
            "stage_id": "Stage06",
            "task_kind": "information_request",
            "candidate_roles": ["fleet_coordinator", "schedule_planner"],
            "owner_role": "dispatch_supervisor",
        },
        "review_requests_changes": {
            "spawn_rule_id": "stage06_request_changes_to_draft",
            "stage_id": "Stage05",
            "task_kind": "work_item",
            "candidate_roles": ["schedule_planner"],
            "owner_role": "dispatch_supervisor",
        },
    }
    if parent_task_kind == "review_packet":
        outcome_map["draft_is_publish_ready"] = {
            "spawn_rule_id": "stage06_final_publish_review",
            "stage_id": "Stage06",
            "task_kind": "final_review",
            "candidate_roles": ["dispatch_supervisor"],
            "owner_role": "dispatch_supervisor",
        }

    if parent_task_kind == "final_review" and completion_outcome == "draft_is_publish_ready":
        # final_review is already the canonical Stage06 review task kind.
        return []

    if completion_outcome not in outcome_map:
        return []

    next_depth = int(parent_task_run.get("spawn_depth") or 0) + 1
    if next_depth > STAGE06_MAX_SPAWN_DEPTH:
        raise Stage06SpawnError(
            code="stage06_spawn_depth_exceeded",
            message="stage06 completion spawn depth budget exceeded",
            details={
                "parent_task_run_id": str(parent_task_run.get("task_run_id")),
                "parent_spawn_depth": int(parent_task_run.get("spawn_depth") or 0),
                "next_spawn_depth": next_depth,
                "max_spawn_depth": STAGE06_MAX_SPAWN_DEPTH,
            },
        )

    workflow_run_id = str(parent_task_run.get("workflow_run_id"))
    parent_task_run_id = str(parent_task_run.get("task_run_id"))
    spawn_budget_key = str(
        parent_task_run.get("spawn_budget_key")
        or f"stage06:{workflow_run_id}:{parent_task_run_id}"
    )

    selected = outcome_map[completion_outcome]
    return [
        Stage06SpawnPlan(
            activation_key=(
                f"spawn:{parent_task_run_id}:{selected['spawn_rule_id']}:{completion_outcome}"
            ),
            spawn_rule_id=str(selected["spawn_rule_id"]),
            stage_id=str(selected["stage_id"]),
            task_kind=str(selected["task_kind"]),
            candidate_roles=[str(role) for role in selected["candidate_roles"]],
            owner_role=(
                str(selected["owner_role"])
                if selected.get("owner_role") is not None
                else None
            ),
            spawn_depth=next_depth,
            spawn_budget_key=spawn_budget_key,
            spawn_cause_kind="task_completion",
            spawn_cause_event_id=parent_completion_event_id,
        )
    ]
