import type {
  ApprovalRow,
  FlagRow,
  HumanTaskRow,
  WorkflowRunDetailContract,
  WorkflowWorkspaceApprovalWorkItem,
  WorkflowWorkspaceFlagWorkItem,
  WorkflowWorkspaceTaskWorkItem,
  WorkflowWorkspaceWorkItem,
  WorkflowWorkspaceWorkpageAction
} from "@/lib/types/contracts";
import type { DrawerPayload } from "@/lib/types/ui";
import { buildTaskDetailPayload } from "@/lib/workspace/taskDetailPayload";
import { taskDisplayLabel } from "@/lib/workspace/taskLabels";

export type WorkspaceLaneId = "todo" | "in_progress" | "review" | "done";

export interface WorkspaceTaskCard {
  cardId: string;
  lane: WorkspaceLaneId;
  kind: "task";
  title: string;
  tag: "Design" | "Backend" | "Frontend";
  avatars: string[];
  primaryCount: number;
  secondaryCount: number;
  task: HumanTaskRow;
  item: WorkflowWorkspaceTaskWorkItem | null;
}

export interface WorkspaceApprovalCard {
  cardId: string;
  lane: WorkspaceLaneId;
  kind: "approval";
  title: string;
  tag: "Backend";
  avatars: string[];
  primaryCount: number;
  secondaryCount: number;
  approval: ApprovalRow;
  item: WorkflowWorkspaceApprovalWorkItem | null;
}

export interface WorkspaceFlagCard {
  cardId: string;
  lane: WorkspaceLaneId;
  kind: "flag";
  title: string;
  tag: "Backend";
  avatars: string[];
  primaryCount: number;
  secondaryCount: number;
  flag: FlagRow;
  item: WorkflowWorkspaceFlagWorkItem | null;
}

export type WorkspaceBoardCard = WorkspaceTaskCard | WorkspaceApprovalCard | WorkspaceFlagCard;

export const LANE_CONFIG: Array<{ id: WorkspaceLaneId; label: string }> = [
  { id: "todo", label: "To Do" },
  { id: "in_progress", label: "In Progress" },
  { id: "review", label: "Review" },
  { id: "done", label: "Done" }
];

export function hasAction(item: WorkflowWorkspaceWorkItem | null, candidates: string[]): boolean {
  if (!item) {
    return false;
  }
  const actions = new Set(item.available_actions.map((action) => action.toLowerCase()));
  return candidates.some((candidate) => actions.has(candidate.toLowerCase()));
}

export function workpageActionStateLabel(action: WorkflowWorkspaceWorkpageAction): string {
  if (action.disabled_reason === "schedule_draft_unavailable") {
    return "Schedule draft unavailable for this run yet";
  }
  return action.disabled_reason ?? action.label;
}

export function actionRefTargetsSubject(
  action: WorkflowWorkspaceWorkpageAction | undefined,
  subjectKind: "human_task" | "approval",
  subjectId: string
): boolean {
  const subject = action?.action_ref?.subject;
  return subject?.subject_kind === subjectKind && subject.subject_id === subjectId;
}

export function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function humanizeBlockingReason(code: string): string {
  if (code === "claimed_by_other_actor") {
    return "Claimed by another actor";
  }
  if (code === "candidate_role_mismatch") {
    return "Your current actor role cannot claim this task";
  }
  if (code === "required_artifact_missing") {
    return "A current draft weekly schedule is still required";
  }
  return humanize(code.split(":")[0] ?? code);
}

export function initials(input: string): string {
  const normalized = input
    .replace(/^(human:|agent:|service:|system:)/, "")
    .replace(/[-_]+/g, " ");
  const parts = normalized.split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "CO";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

export function taskTag(task: HumanTaskRow): "Design" | "Backend" | "Frontend" {
  const key = `${task.stage_id} ${task.task_kind}`.toLowerCase();
  if (key.includes("review")) {
    return "Design";
  }
  if (key.includes("exception") || key.includes("stage07") || key.includes("approval")) {
    return "Backend";
  }
  return "Frontend";
}

export function laneForTask(task: HumanTaskRow): WorkspaceLaneId {
  if (task.state === "COMPLETED") {
    return "done";
  }
  if (task.state === "CLAIMED") {
    return "in_progress";
  }
  if (task.task_kind.toLowerCase().includes("review")) {
    return "review";
  }
  return "todo";
}

export function laneForApproval(approval: ApprovalRow): WorkspaceLaneId {
  return approval.state === "PENDING" ? "review" : "done";
}

export function laneForFlag(flag: FlagRow): WorkspaceLaneId {
  return flag.state.toLowerCase() === "closed" ? "done" : "review";
}

export function isInteractiveTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    Boolean(
      target.closest(
        "button, a, input, select, textarea, summary, details, label, [role='button']"
      )
    )
  );
}

export function taskDetailPayload(
  item: WorkflowWorkspaceTaskWorkItem | null,
  task: HumanTaskRow,
  artifactVersions: WorkflowRunDetailContract["artifact_versions"]
): DrawerPayload {
  return buildTaskDetailPayload({ task, item, artifactVersions });
}

export function approvalDetailPayload(
  item: WorkflowWorkspaceApprovalWorkItem | null,
  approval: ApprovalRow
): DrawerPayload {
  return {
    title: `${approval.approval_kind} ${approval.scope_ref}`,
    subtitle: approval.approval_id,
    description: "Approval evidence and response context are shown in drawer.",
    fields: [
      { label: "State", value: approval.state },
      { label: "Required role", value: approval.required_role },
      { label: "Response", value: approval.response_kind ?? "pending" },
      { label: "Available actions", value: item?.available_actions.join(", ") || "none" },
      { label: "Blocking reason", value: item?.blocking_reason ?? "none" }
    ]
  };
}

export function flagDetailPayload(
  item: WorkflowWorkspaceFlagWorkItem | null,
  flag: FlagRow
): DrawerPayload {
  return {
    title: flag.summary,
    subtitle: flag.flag_id,
    description: "Flag detail and attachment context are shown in drawer.",
    fields: [
      { label: "State", value: flag.state },
      { label: "Severity", value: flag.severity },
      { label: "Assigned group", value: flag.assigned_group ?? "unassigned" },
      { label: "Available actions", value: item?.available_actions.join(", ") || "none" }
    ]
  };
}

export function buildWorkspaceBoardCards(input: {
  detail: WorkflowRunDetailContract;
  taskItemById: Map<string, WorkflowWorkspaceTaskWorkItem>;
  approvalItemById: Map<string, WorkflowWorkspaceApprovalWorkItem>;
  flagItemById: Map<string, WorkflowWorkspaceFlagWorkItem>;
}): WorkspaceBoardCard[] {
  const { detail, taskItemById, approvalItemById, flagItemById } = input;
  const taskCards: WorkspaceTaskCard[] = detail.human_tasks.map((task) => {
    const item = taskItemById.get(task.human_task_id) ?? null;
    const avatarSources = [task.assignee_actor_id, task.owner_role, ...task.candidate_roles].filter(
      (value): value is string => Boolean(value)
    );
    return {
      cardId: `task:${task.human_task_id}`,
      kind: "task",
      lane: laneForTask(task),
      title: taskDisplayLabel(task),
      tag: taskTag(task),
      avatars: avatarSources.slice(0, 2),
      primaryCount: Math.max(1, avatarSources.length),
      secondaryCount: Math.max(0, item?.available_actions.length ?? 0),
      task,
      item
    };
  });

  const approvalCards: WorkspaceApprovalCard[] = detail.approvals.map((approval) => {
    const item = approvalItemById.get(approval.approval_id) ?? null;
    const avatarSources = [approval.required_role, ...approval.candidate_roles].filter(Boolean);
    return {
      cardId: `approval:${approval.approval_id}`,
      kind: "approval",
      lane: laneForApproval(approval),
      title: `${humanize(approval.scope_ref)} Approval`,
      tag: "Backend",
      avatars: avatarSources.slice(0, 2),
      primaryCount: Math.max(1, avatarSources.length),
      secondaryCount: approval.state === "PENDING" ? 1 : 0,
      approval,
      item
    };
  });

  const flagCards: WorkspaceFlagCard[] = detail.flags.map((flag) => {
    const item = flagItemById.get(flag.flag_id) ?? null;
    const avatarSources = [flag.created_by_actor_id, flag.assigned_group].filter(
      (value): value is string => Boolean(value)
    );
    return {
      cardId: `flag:${flag.flag_id}`,
      kind: "flag",
      lane: laneForFlag(flag),
      title: flag.summary,
      tag: "Backend",
      avatars: avatarSources.slice(0, 2),
      primaryCount: Math.max(1, avatarSources.length),
      secondaryCount: flag.severity === "high" ? 3 : flag.severity === "medium" ? 2 : 1,
      flag,
      item
    };
  });

  return [...taskCards, ...approvalCards, ...flagCards];
}

export function buildWorkspaceLaneCards(
  cards: WorkspaceBoardCard[]
): Record<WorkspaceLaneId, WorkspaceBoardCard[]> {
  return LANE_CONFIG.reduce<Record<WorkspaceLaneId, WorkspaceBoardCard[]>>(
    (accumulator, lane) => {
      accumulator[lane.id] = cards.filter((card) => card.lane === lane.id);
      return accumulator;
    },
    {
      todo: [],
      in_progress: [],
      review: [],
      done: []
    }
  );
}
