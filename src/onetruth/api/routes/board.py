from __future__ import annotations

from typing import Any

from onetruth.api.dependencies import Page, RequestContext
from onetruth.api.routes.approvals import query_approvals
from onetruth.api.routes.human_tasks import query_human_tasks
from onetruth.api.routes.pointers import query_pointers
from onetruth.api.routes.workflow_runs import query_workflow_runs

LANE_ORDER = {
    "human_tasks.open": 10,
    "human_tasks.claimed": 20,
    "approvals.pending": 30,
    "approvals.responded": 40,
    "human_tasks.completed": 50,
}

LANE_LABELS = {
    "human_tasks.open": "Open Tasks",
    "human_tasks.claimed": "Claimed Tasks",
    "approvals.pending": "Pending Approvals",
    "approvals.responded": "Responded Approvals",
    "human_tasks.completed": "Completed Tasks",
}


def schedule_planning_board_endpoint(
    connection,
    *,
    context: RequestContext,
    query: dict[str, str],
    page: Page,
) -> dict[str, Any]:
    workflow_run_id = query.get("workflow_run_id")
    workflow_id = query.get("workflow_id", "schedule_planning.v1")

    source_page = Page(limit=500, offset=0)
    workflow_runs = query_workflow_runs(
        connection,
        context=context,
        workflow_id=workflow_id,
        state=query.get("workflow_state"),
        page=source_page,
    )
    workflow_lookup = {str(run["workflow_run_id"]): run for run in workflow_runs}

    human_tasks = query_human_tasks(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        state=query.get("task_state"),
        stage_id=query.get("stage_id"),
        task_kind=query.get("task_kind"),
        assignee_actor_id=query.get("assignee_actor_id"),
        owner_role=query.get("owner_role"),
        page=source_page,
    )
    approvals = query_approvals(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        state=query.get("approval_state"),
        approval_kind=query.get("approval_kind"),
        required_role=query.get("required_role"),
        page=source_page,
    )
    pointers = query_pointers(
        connection,
        context=context,
        workflow_run_id=workflow_run_id,
        scope_kind=query.get("scope_kind"),
        scope_ref=query.get("scope_ref"),
        artifact_kind=query.get("artifact_kind"),
        page=source_page,
    )

    approvals_by_task_run_id: dict[str, list[dict[str, Any]]] = {}
    for approval in approvals:
        task_run_id = approval.get("task_run_id")
        if task_run_id is None:
            continue
        approvals_by_task_run_id.setdefault(str(task_run_id), []).append(approval)

    cards: list[dict[str, Any]] = []
    for task in human_tasks:
        lane = _human_task_lane(str(task["state"]))
        related_approvals = approvals_by_task_run_id.get(str(task["task_run_id"]), [])
        workflow_run = workflow_lookup.get(str(task["workflow_run_id"]), {})
        cards.append(
            {
                "card_id": f"human_task:{task['human_task_id']}",
                "card_type": "human_task",
                "lane": lane,
                "title": f"{task['stage_id']} {task['task_kind']}",
                "workflow_run_id": task["workflow_run_id"],
                "workflow_id": workflow_run.get("workflow_id"),
                "task_run_id": task["task_run_id"],
                "human_task_id": task["human_task_id"],
                "stage_id": task["stage_id"],
                "task_kind": task["task_kind"],
                "state": task["state"],
                "owner_role": task["owner_role"],
                "assignee_actor_id": task["assignee_actor_id"],
                "assignee_actor_type": task["assignee_actor_type"],
                "due_at": task["due_at"],
                "claimed_at": task["claimed_at"],
                "claimed_until": task["claimed_until"],
                "blocked_on_kind": task.get("blocked_on_kind"),
                "blocked_on_ref": task.get("blocked_on_ref"),
                "spawned_from_flag_id": task.get("spawned_from_flag_id"),
                "linked_approval_count": len(related_approvals),
                "linked_approval_states": sorted(
                    {str(approval["state"]) for approval in related_approvals}
                ),
            }
        )

    for approval in approvals:
        lane = _approval_lane(str(approval["state"]))
        workflow_run = workflow_lookup.get(str(approval["workflow_run_id"]), {})
        cards.append(
            {
                "card_id": f"approval:{approval['approval_id']}",
                "card_type": "approval",
                "lane": lane,
                "title": f"{approval['approval_kind']} {approval['scope_ref']}",
                "workflow_run_id": approval["workflow_run_id"],
                "workflow_id": workflow_run.get("workflow_id"),
                "approval_id": approval["approval_id"],
                "task_run_id": approval["task_run_id"],
                "approval_kind": approval["approval_kind"],
                "scope_kind": approval["scope_kind"],
                "scope_ref": approval["scope_ref"],
                "state": approval["state"],
                "required_role": approval["required_role"],
                "candidate_roles": approval["candidate_roles"],
                "requested_at": approval["requested_at"],
                "responded_at": approval["responded_at"],
                "response_kind": approval["response_kind"],
            }
        )

    cards.sort(key=_card_sort_key)

    lane_counts = {lane: 0 for lane in LANE_ORDER}
    for card in cards:
        lane_counts[str(card["lane"])] += 1

    paged_cards = cards[page.offset : page.offset + page.limit]
    lanes = [
        {
            "lane": lane,
            "label": LANE_LABELS[lane],
            "position": LANE_ORDER[lane],
            "card_count": lane_counts[lane],
        }
        for lane in sorted(LANE_ORDER, key=LANE_ORDER.get)
    ]

    return {
        "command": "api.board.schedule_planning",
        "board": {
            "board_id": "schedule-planning",
            "filters": {
                "workflow_id": workflow_id,
                "workflow_run_id": workflow_run_id,
                "stage_id": query.get("stage_id"),
                "task_kind": query.get("task_kind"),
                "task_state": query.get("task_state"),
                "approval_state": query.get("approval_state"),
            },
            "lanes": lanes,
            "cards": paged_cards,
            "page": {"limit": page.limit, "offset": page.offset},
            "workflow_runs": workflow_runs,
            "pointers": pointers,
            "summary": {
                "workflow_run_count": len(workflow_runs),
                "human_task_count": len(human_tasks),
                "approval_count": len(approvals),
                "pointer_count": len(pointers),
                "card_count": len(cards),
            },
        },
    }


def _human_task_lane(state: str) -> str:
    if state == "OPEN":
        return "human_tasks.open"
    if state == "CLAIMED":
        return "human_tasks.claimed"
    return "human_tasks.completed"


def _approval_lane(state: str) -> str:
    if state == "PENDING":
        return "approvals.pending"
    return "approvals.responded"


def _card_sort_key(card: dict[str, Any]) -> tuple[Any, ...]:
    lane = str(card["lane"])
    lane_position = LANE_ORDER.get(lane, 999)

    if card["card_type"] == "human_task":
        due_at = card.get("due_at") or "9999-12-31T23:59:59Z"
        claimed_at = card.get("claimed_at") or "9999-12-31T23:59:59Z"
        return (
            lane_position,
            due_at,
            claimed_at,
            str(card.get("title") or ""),
            str(card["card_id"]),
        )

    requested_at = card.get("requested_at") or "9999-12-31T23:59:59Z"
    responded_at = card.get("responded_at") or "9999-12-31T23:59:59Z"
    return (
        lane_position,
        requested_at,
        responded_at,
        str(card.get("title") or ""),
        str(card["card_id"]),
    )
