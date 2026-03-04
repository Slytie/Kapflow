import type { ApprovalRow, BoardCard, FlagRow, HumanTaskRow } from "@/lib/types/contracts";
import type { BoardItem, BoardLaneId, BoardLaneView } from "@/lib/types/ui";

const BOARD_LANE_ORDER: BoardLaneId[] = [
  "unclaimed",
  "claimed",
  "awaiting_approval",
  "needs_information",
  "exception_work"
];

const LANE_TITLES: Record<BoardLaneId, string> = {
  unclaimed: "Unclaimed",
  claimed: "Claimed / In Progress",
  awaiting_approval: "Awaiting Approval",
  needs_information: "Needs Information",
  exception_work: "Exception Work"
};

function taskLane(task: Pick<HumanTaskRow, "state" | "task_kind" | "spawned_from_flag_id">): BoardLaneId {
  if (task.spawned_from_flag_id) {
    return "exception_work";
  }
  if (task.task_kind === "information_request") {
    return "needs_information";
  }
  if (task.state === "OPEN") {
    return "unclaimed";
  }
  return "claimed";
}

function toHumanTask(card: BoardCard): HumanTaskRow | null {
  if (card.card_type !== "human_task") {
    return null;
  }

  return {
    human_task_id: card.human_task_id ?? card.card_id,
    workflow_run_id: card.workflow_run_id,
    task_run_id: card.task_run_id ?? card.card_id,
    task_kind: card.task_kind ?? "unknown",
    state: (card.state as HumanTaskRow["state"] | undefined) ?? "OPEN",
    candidate_roles: card.owner_role ? [card.owner_role] : [],
    owner_role: card.owner_role ?? null,
    assignee_actor_id: card.assignee_actor_id ?? null,
    assignee_actor_type: card.assignee_actor_type ?? null,
    due_at: card.due_at ?? null,
    escalation_at: null,
    lease_version: 0,
    claimed_at: card.claimed_at ?? null,
    claimed_until: card.claimed_until ?? null,
    linked_approval_id: null,
    reopen_count: 0,
    generation: 0,
    created_at: card.claimed_at ?? "",
    updated_at: card.claimed_at ?? "",
    task_run_state: card.state === "COMPLETED" ? "COMPLETED" : "READY",
    stage_id: card.stage_id ?? "Unknown",
    blocked_on_kind: card.blocked_on_kind ?? null,
    blocked_on_ref: card.blocked_on_ref ?? null,
    spawned_from_flag_id: card.spawned_from_flag_id ?? null
  };
}

function toApproval(card: BoardCard): ApprovalRow | null {
  if (card.card_type !== "approval") {
    return null;
  }

  return {
    approval_id: card.approval_id ?? card.card_id,
    workflow_run_id: card.workflow_run_id,
    task_run_id: card.task_run_id ?? card.card_id,
    approval_kind: card.approval_kind ?? "business_decision",
    scope_kind: card.scope_kind ?? "stage",
    scope_ref: card.scope_ref ?? "unknown",
    state: (card.state as ApprovalRow["state"] | undefined) ?? "PENDING",
    requested_by_task_run_id: card.task_run_id ?? null,
    candidate_roles: card.candidate_roles ?? [],
    required_role: card.required_role ?? "unknown",
    requested_at: card.requested_at ?? "",
    responded_at: card.responded_at ?? null,
    response_kind: card.response_kind ?? null,
    response_reason: null,
    decided_by_actor_id: null,
    decided_by_actor_type: null,
    generation: 0,
    created_at: card.requested_at ?? "",
    updated_at: card.responded_at ?? card.requested_at ?? ""
  };
}

export function deriveBoardLanes(input: {
  cards: BoardCard[];
  flags: FlagRow[];
}): BoardLaneView[] {
  const buckets: Record<BoardLaneId, BoardItem[]> = {
    unclaimed: [],
    claimed: [],
    awaiting_approval: [],
    needs_information: [],
    exception_work: []
  };

  input.cards.forEach((card) => {
    const task = toHumanTask(card);
    if (task) {
      buckets[taskLane(task)].push({ kind: "task", task });
      return;
    }

    const approval = toApproval(card);
    if (approval) {
      buckets.awaiting_approval.push({ kind: "approval", approval });
    }
  });

  input.flags.forEach((flag) => {
    buckets.exception_work.push({ kind: "flag", flag });
  });

  return BOARD_LANE_ORDER.map((laneId) => ({
    id: laneId,
    title: LANE_TITLES[laneId],
    items: buckets[laneId]
  }));
}
