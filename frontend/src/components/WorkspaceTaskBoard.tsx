import { useMemo } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { AttachmentActions } from "@/components/AttachmentActions";
import { StatePanel } from "@/components/StatePanel";
import { TaskDocumentCues } from "@/components/TaskDocumentCues";
import { errorText } from "@/lib/api/errorText";
import {
  approvalsRepository,
  flagsRepository,
  humanTasksRepository,
  workpagesRepository
} from "@/lib/repositories";
import type {
  ApprovalRow,
  FlagRow,
  HumanTaskRow,
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceApprovalWorkItem,
  WorkflowWorkspaceFlagWorkItem,
  WorkflowWorkspaceWorkpageAction,
  WorkflowWorkspaceTaskWorkItem,
  WorkflowWorkspaceWorkItem
} from "@/lib/types/contracts";
import type { DrawerPayload } from "@/lib/types/ui";
import { buildTaskArtifacts, buildTaskDetailPayload } from "@/lib/workspace/taskDetailPayload";
import { buildTaskDocumentPreviewCues } from "@/lib/workspace/taskDocumentUi";
import { taskDisplayLabel } from "@/lib/workspace/taskLabels";

type WorkspaceLaneId = "todo" | "in_progress" | "review" | "done";

interface WorkspaceTaskBoardProps {
  workflowRunId: string;
  workspace: WorkflowRunWorkspaceContract;
  detail: WorkflowRunDetailContract;
  onRefresh: () => void;
  onOpenDetails: (payload: DrawerPayload) => void;
}

interface WorkspaceTaskCard {
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

interface WorkspaceApprovalCard {
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

interface WorkspaceFlagCard {
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

type WorkspaceBoardCard = WorkspaceTaskCard | WorkspaceApprovalCard | WorkspaceFlagCard;

const LANE_CONFIG: Array<{ id: WorkspaceLaneId; label: string }> = [
  { id: "todo", label: "To Do" },
  { id: "in_progress", label: "In Progress" },
  { id: "review", label: "Review" },
  { id: "done", label: "Done" }
];

function hasAction(item: WorkflowWorkspaceWorkItem | null, candidates: string[]): boolean {
  if (!item) {
    return false;
  }
  const actions = new Set(item.available_actions.map((action) => action.toLowerCase()));
  return candidates.some((candidate) => actions.has(candidate.toLowerCase()));
}

function workpageActionStateLabel(action: WorkflowWorkspaceWorkpageAction): string {
  if (action.disabled_reason === "schedule_draft_unavailable") {
    return "Schedule draft unavailable for this run yet";
  }
  return action.disabled_reason ?? action.label;
}

function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function humanizeBlockingReason(code: string): string {
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

function initials(input: string): string {
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

function taskTag(task: HumanTaskRow): "Design" | "Backend" | "Frontend" {
  const key = `${task.stage_id} ${task.task_kind}`.toLowerCase();
  if (key.includes("review")) {
    return "Design";
  }
  if (key.includes("exception") || key.includes("stage07") || key.includes("approval")) {
    return "Backend";
  }
  return "Frontend";
}

function laneForTask(task: HumanTaskRow): WorkspaceLaneId {
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

function laneForApproval(approval: ApprovalRow): WorkspaceLaneId {
  return approval.state === "PENDING" ? "review" : "done";
}

function laneForFlag(flag: FlagRow): WorkspaceLaneId {
  return flag.state.toLowerCase() === "closed" ? "done" : "review";
}

function isInteractiveTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    Boolean(
      target.closest(
        "button, a, input, select, textarea, summary, details, label, [role='button']"
      )
    )
  );
}

function taskDetailPayload(
  item: WorkflowWorkspaceTaskWorkItem | null,
  task: HumanTaskRow,
  artifactVersions: WorkflowRunDetailContract["artifact_versions"]
): DrawerPayload {
  return buildTaskDetailPayload({ task, item, artifactVersions });
}

function approvalDetailPayload(
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

function flagDetailPayload(item: WorkflowWorkspaceFlagWorkItem | null, flag: FlagRow): DrawerPayload {
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

export function WorkspaceTaskBoard({
  workflowRunId,
  workspace,
  detail,
  onRefresh,
  onOpenDetails
}: WorkspaceTaskBoardProps): JSX.Element {
  const navigate = useNavigate();
  const claimMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.claim(humanTaskId),
    onSuccess: onRefresh
  });

  const completeMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.complete(humanTaskId),
    onSuccess: onRefresh
  });

  const runStage06ReviewMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.runStage06AgentReview(humanTaskId),
    onSuccess: onRefresh
  });

  const runWeeklyStage04AgentMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.runWeeklyStage04OpenAIAgent(humanTaskId),
    onSuccess: onRefresh
  });

  const approvalMutation = useMutation({
    mutationFn: (payload: {
      approvalId: string;
      responseKind: "approve" | "reject" | "request_changes";
    }) => approvalsRepository.respond(payload.approvalId, payload.responseKind),
    onSuccess: onRefresh
  });

  const workpageActionMutation = useMutation({
    mutationFn: (action: WorkflowWorkspaceWorkpageAction) => {
      if (action.presentation !== "create_then_open" || !action.create_path) {
        throw new Error("Unsupported workspace workpage action");
      }
      return workpagesRepository.createWorkpage(action.create_path, action.subject_context);
    },
    onSuccess: (draft, action) => {
      onRefresh();
      navigate(draft.route, {
        state: { workpageSubjectContext: action.subject_context }
      });
    }
  });

  const uploadApprovalAttachmentMutation = useMutation({
    mutationFn: (payload: { approvalId: string; file: File }) =>
      approvalsRepository.uploadAttachment(payload.approvalId, payload.file),
    onSuccess: onRefresh
  });

  const downloadApprovalAttachmentMutation = useMutation({
    mutationFn: (approvalId: string) => approvalsRepository.downloadLatestAttachment(approvalId)
  });

  const uploadFlagAttachmentMutation = useMutation({
    mutationFn: (payload: { flagId: string; file: File }) =>
      flagsRepository.uploadAttachment(payload.flagId, payload.file),
    onSuccess: onRefresh
  });

  const downloadFlagAttachmentMutation = useMutation({
    mutationFn: (flagId: string) => flagsRepository.downloadLatestAttachment(flagId)
  });

  const mutationError =
    claimMutation.error ??
    completeMutation.error ??
    runStage06ReviewMutation.error ??
    runWeeklyStage04AgentMutation.error ??
    approvalMutation.error ??
    workpageActionMutation.error ??
    uploadApprovalAttachmentMutation.error ??
    downloadApprovalAttachmentMutation.error ??
    uploadFlagAttachmentMutation.error ??
    downloadFlagAttachmentMutation.error;

  const openWorkspaceWorkpage = (action: WorkflowWorkspaceWorkpageAction): void => {
    if (action.state !== "available") {
      return;
    }
    if (action.presentation === "open_route" && action.route) {
      navigate(action.route, {
        state: { workpageSubjectContext: action.subject_context }
      });
      return;
    }
    if (action.presentation === "create_then_open" && action.create_path) {
      workpageActionMutation.mutate(action);
    }
  };

  const taskItemById = useMemo(() => {
    const map = new Map<string, WorkflowWorkspaceTaskWorkItem>();
    [...workspace.user_work, ...workspace.blocking_work].forEach((item) => {
      if (item.item_kind === "human_task") {
        map.set(item.human_task.human_task_id, item);
      }
    });
    return map;
  }, [workspace.blocking_work, workspace.user_work]);

  const approvalItemById = useMemo(() => {
    const map = new Map<string, WorkflowWorkspaceApprovalWorkItem>();
    [...workspace.user_work, ...workspace.blocking_work].forEach((item) => {
      if (item.item_kind === "approval") {
        map.set(item.approval.approval_id, item);
      }
    });
    return map;
  }, [workspace.blocking_work, workspace.user_work]);

  const flagItemById = useMemo(() => {
    const map = new Map<string, WorkflowWorkspaceFlagWorkItem>();
    [...workspace.user_work, ...workspace.blocking_work].forEach((item) => {
      if (item.item_kind === "flag") {
        map.set(item.flag.flag_id, item);
      }
    });
    return map;
  }, [workspace.blocking_work, workspace.user_work]);

  const cards = useMemo<WorkspaceBoardCard[]>(() => {
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
  }, [approvalItemById, detail.approvals, detail.flags, detail.human_tasks, flagItemById, taskItemById]);

  const laneCards = useMemo(() => {
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
  }, [cards]);

  return (
    <section className="workspace-task-board" data-testid="workspace-swimlanes">
      {mutationError ? (
        <StatePanel
          kind="error"
          title="Workspace action failed"
          detail={errorText(mutationError, "Unable to apply action")}
        />
      ) : null}

      <div className="workspace-task-board__grid">
        {LANE_CONFIG.map((lane) => (
          <section
            key={lane.id}
            className="workspace-lane"
            aria-label={lane.label}
            data-testid={`workspace-lane-${lane.id}`}
          >
            <header>
              <h3>{lane.label}</h3>
              <span data-testid={`workspace-lane-count-${lane.id}`}>
                {laneCards[lane.id].length}
              </span>
            </header>

              <div className="workspace-lane__cards">
                {laneCards[lane.id].map((card) => {
                if (card.kind === "task") {
                  const taskBusy =
                    (claimMutation.isPending && claimMutation.variables === card.task.human_task_id) ||
                    (completeMutation.isPending &&
                      completeMutation.variables === card.task.human_task_id) ||
                    (runStage06ReviewMutation.isPending &&
                      runStage06ReviewMutation.variables === card.task.human_task_id) ||
                    (runWeeklyStage04AgentMutation.isPending &&
                      runWeeklyStage04AgentMutation.variables === card.task.human_task_id) ||
                    (workpageActionMutation.isPending &&
                      workpageActionMutation.variables?.subject_context.subject_kind === "human_task" &&
                      workpageActionMutation.variables?.subject_context.subject_id ===
                        card.task.human_task_id);
                  const workpageActions = card.item?.workpage_actions ?? [];

                  const canClaim =
                    hasAction(card.item, ["claim", "claim_human_task"]) ||
                    (card.item === null && card.task.state === "OPEN");
                  const canComplete =
                    hasAction(card.item, ["complete", "complete_human_task"]) ||
                    (card.item === null && card.task.state === "CLAIMED");
                  const canRunStage06Review = hasAction(card.item, [
                    "run_stage06_agent_review",
                    "stage06_agent_review"
                  ]);
                  const canRunWeeklyStage04Agent = hasAction(card.item, [
                    "run_weekly_stage04_openai_agent"
                  ]);
                  const requirementBlocked =
                    (card.item?.missing_required_inputs.length ?? 0) > 0 ||
                    (card.item?.blocking_reason_codes.length ?? 0) > 0;
                  const canCompleteNow = canComplete && !requirementBlocked;
                  const taskArtifacts = buildTaskArtifacts(card.task, detail.artifact_versions);
                  const documentCues = buildTaskDocumentPreviewCues({
                    missing_required_inputs:
                      card.item?.missing_required_inputs ?? card.task.missing_required_inputs ?? [],
                    required_uploads:
                      card.item?.required_uploads ?? card.task.required_uploads ?? [],
                    required_reviews:
                      card.item?.required_reviews ?? card.task.required_reviews ?? [],
                    available_actions:
                      card.item?.available_actions ?? card.task.available_actions ?? [],
                    artifact_count: taskArtifacts.length
                  });

                  const hints: string[] = [];
                  if (!canClaim && card.task.state === "OPEN") {
                    if ((card.item?.blocking_reason_codes ?? []).includes("candidate_role_mismatch")) {
                      const roles = card.task.candidate_roles.join(", ");
                      hints.push(`You cannot claim this task with your current role. Required roles: ${roles}`);
                    } else if (
                      (card.item?.blocking_reason_codes ?? []).includes("claimed_by_other_actor") ||
                      card.task.assignee_actor_id
                    ) {
                      hints.push(
                        `You cannot claim this task because it is claimed by ${card.task.assignee_actor_id ?? "another actor"}`
                      );
                    } else {
                      hints.push("You cannot claim this task from the current account context");
                    }
                  }
                  if (!canCompleteNow) {
                    if (card.task.state === "OPEN") {
                      hints.push("You cannot complete this task until it has been claimed");
                    } else if (
                      (card.item?.blocking_reason_codes ?? []).includes("claimed_by_other_actor") &&
                      card.task.assignee_actor_id
                    ) {
                      hints.push(
                        `You cannot complete this task because it is claimed by ${card.task.assignee_actor_id}`
                      );
                    } else if (
                      (card.item?.missing_required_inputs.length ?? 0) > 0 ||
                      (card.item?.blocking_reason_codes.length ?? 0) > 0
                    ) {
                      hints.push("You cannot complete this task until required uploads/reviews are satisfied");
                    }
                  }
                  if ((card.item?.missing_required_inputs.length ?? 0) > 0) {
                    hints.push(
                      `Missing required inputs: ${card.item?.missing_required_inputs.join(", ")}`
                    );
                  }
                  const nonRequirementBlockingCodes = (card.item?.blocking_reason_codes ?? []).filter(
                    (code) =>
                      !code.startsWith("required_upload_missing:") &&
                      !code.startsWith("required_review_confirmation_missing:")
                  );
                  if (nonRequirementBlockingCodes.length > 0) {
                    hints.push(
                      `Blocked: ${nonRequirementBlockingCodes
                        .map((code) => humanizeBlockingReason(code))
                        .join(", ")}`
                    );
                  }
                  const missingInputHint = hints.length > 0 ? hints.join(" \u00b7 ") : null;
                  const openTaskDetails = (): void => {
                    onOpenDetails(taskDetailPayload(card.item, card.task, detail.artifact_versions));
                  };

                  return (
                    <article
                      key={card.cardId}
                      className="workspace-board-card workspace-board-card--interactive"
                      data-testid="workspace-task-card"
                      tabIndex={0}
                      aria-label={`Open ${card.title} details`}
                      onClick={(event) => {
                        if (isInteractiveTarget(event.target)) {
                          return;
                        }
                        openTaskDetails();
                      }}
                      onKeyDown={(event) => {
                        if (isInteractiveTarget(event.target)) {
                          return;
                        }
                        if (event.key !== "Enter" && event.key !== " ") {
                          return;
                        }
                        event.preventDefault();
                        openTaskDetails();
                      }}
                    >
                      <header>
                        <h4>{card.title}</h4>
                        <details
                          className="workspace-board-card__menu"
                          onClick={(event) => event.stopPropagation()}
                          onKeyDown={(event) => event.stopPropagation()}
                        >
                          <summary aria-label={`Actions for ${card.title}`}>...</summary>
                          <div className="workspace-board-card__actions">
                            {workpageActions.map((action) => (
                              <button
                                key={action.action_id}
                                type="button"
                                className="workspace-board-action"
                                onClick={() => openWorkspaceWorkpage(action)}
                                disabled={
                                  taskBusy ||
                                  action.state !== "available" ||
                                  (action.presentation === "open_route" && !action.route) ||
                                  (action.presentation === "create_then_open" &&
                                    !action.create_path)
                                }
                                title={action.state === "available" ? undefined : workpageActionStateLabel(action)}
                              >
                                {action.label}
                              </button>
                            ))}
                            <button
                              type="button"
                              className="workspace-board-action"
                              onClick={() => claimMutation.mutate(card.task.human_task_id)}
                              disabled={taskBusy || !canClaim}
                            >
                              Claim
                            </button>
                            <button
                              type="button"
                              className="workspace-board-action workspace-board-action--primary"
                              onClick={() => completeMutation.mutate(card.task.human_task_id)}
                              disabled={
                                taskBusy ||
                                !canCompleteNow
                              }
                            >
                              Complete
                            </button>
                            {canRunWeeklyStage04Agent ? (
                              <button
                                type="button"
                                className="workspace-board-action"
                                onClick={() =>
                                  runWeeklyStage04AgentMutation.mutate(card.task.human_task_id)
                                }
                                disabled={taskBusy}
                              >
                                Run Stage04 Build
                              </button>
                            ) : null}
                            {canRunStage06Review ? (
                              <button
                                type="button"
                                className="workspace-board-action"
                                onClick={() =>
                                  runStage06ReviewMutation.mutate(card.task.human_task_id)
                                }
                                disabled={taskBusy}
                              >
                                AI Review Assist
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="workspace-board-action"
                              onClick={openTaskDetails}
                            >
                              Details
                            </button>
                          </div>
                        </details>
                      </header>

                      <div className="workspace-board-card__meta">
                        <span className={`workspace-board-tag workspace-board-tag--${card.tag.toLowerCase()}`}>
                          {card.tag}
                        </span>
                      </div>
                      <TaskDocumentCues cues={documentCues} compact />

                      {card.task.state !== "COMPLETED" ? (
                        <div className="workspace-board-card__quick-actions">
                          <button
                            type="button"
                            className="workspace-board-action"
                            onClick={() => claimMutation.mutate(card.task.human_task_id)}
                            disabled={taskBusy || !canClaim}
                          >
                            Claim
                          </button>
                          <button
                            type="button"
                            className="workspace-board-action workspace-board-action--primary"
                            onClick={() => completeMutation.mutate(card.task.human_task_id)}
                            disabled={taskBusy || !canCompleteNow}
                          >
                            Complete
                          </button>
                        </div>
                      ) : null}

                      <footer>
                        <div className="workspace-avatar-stack">
                          {card.avatars.length === 0 ? (
                            <span className="workspace-avatar">CO</span>
                          ) : (
                            card.avatars.map((avatar, index) => (
                              <span
                                key={`${card.cardId}:avatar:${index}:${avatar}`}
                                className="workspace-avatar"
                                style={{ zIndex: card.avatars.length - index }}
                              >
                                {initials(avatar)}
                              </span>
                            ))
                          )}
                        </div>
                        <span className="workspace-board-counter">{card.primaryCount}</span>
                        <span className="workspace-board-counter">{card.secondaryCount}</span>
                      </footer>

                      {missingInputHint ? (
                        <p className="workspace-board-card__hint">{missingInputHint}</p>
                      ) : null}
                      {workpageActions.some((action) => action.state !== "available") ? (
                        <p className="workspace-board-card__hint">
                          {workpageActions
                            .filter((action) => action.state !== "available")
                            .map((action) => workpageActionStateLabel(action))
                            .join(" · ")}
                        </p>
                      ) : null}
                    </article>
                  );
                }

                if (card.kind === "approval") {
                  const approvalBusy =
                    (approvalMutation.isPending &&
                      approvalMutation.variables?.approvalId === card.approval.approval_id) ||
                    (workpageActionMutation.isPending &&
                      workpageActionMutation.variables?.subject_context.subject_kind === "approval" &&
                      workpageActionMutation.variables?.subject_context.subject_id ===
                        card.approval.approval_id) ||
                    (uploadApprovalAttachmentMutation.isPending &&
                      uploadApprovalAttachmentMutation.variables?.approvalId ===
                        card.approval.approval_id) ||
                    (downloadApprovalAttachmentMutation.isPending &&
                      downloadApprovalAttachmentMutation.variables === card.approval.approval_id);
                  const workpageActions = card.item?.workpage_actions ?? [];

                  const canApprove =
                    hasAction(card.item, ["respond_approve", "approve", "respond_approval"]) ||
                    (card.item === null && card.approval.state === "PENDING");
                  const canReject =
                    hasAction(card.item, ["respond_reject", "reject", "respond_approval"]) ||
                    (card.item === null && card.approval.state === "PENDING");
                  const canRequestChanges =
                    hasAction(card.item, [
                      "respond_request_changes",
                      "request_changes",
                      "respond_approval"
                    ]) || (card.item === null && card.approval.state === "PENDING");
                  const canUpload = hasAction(card.item, ["upload_attachment", "upload_artifact"]);
                  const canDownload = hasAction(card.item, [
                    "download_attachment",
                    "download_artifact",
                    "download_attachments"
                  ]);

                  return (
                    <article
                      key={card.cardId}
                      className="workspace-board-card"
                      data-testid="workspace-task-card"
                    >
                      <header>
                        <h4>{card.title}</h4>
                        <details className="workspace-board-card__menu">
                          <summary aria-label={`Actions for ${card.title}`}>...</summary>
                          <div className="workspace-board-card__actions">
                            {workpageActions.map((action) => (
                              <button
                                key={action.action_id}
                                type="button"
                                className="workspace-board-action"
                                onClick={() => openWorkspaceWorkpage(action)}
                                disabled={
                                  approvalBusy ||
                                  action.state !== "available" ||
                                  (action.presentation === "open_route" && !action.route) ||
                                  (action.presentation === "create_then_open" &&
                                    !action.create_path)
                                }
                                title={action.state === "available" ? undefined : workpageActionStateLabel(action)}
                              >
                                {action.label}
                              </button>
                            ))}
                            <button
                              type="button"
                              className="workspace-board-action workspace-board-action--primary"
                              onClick={() =>
                                approvalMutation.mutate({
                                  approvalId: card.approval.approval_id,
                                  responseKind: "approve"
                                })
                              }
                              disabled={approvalBusy || !canApprove}
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              className="workspace-board-action"
                              onClick={() =>
                                approvalMutation.mutate({
                                  approvalId: card.approval.approval_id,
                                  responseKind: "reject"
                                })
                              }
                              disabled={approvalBusy || !canReject}
                            >
                              Reject
                            </button>
                            <button
                              type="button"
                              className="workspace-board-action"
                              onClick={() =>
                                approvalMutation.mutate({
                                  approvalId: card.approval.approval_id,
                                  responseKind: "request_changes"
                                })
                              }
                              disabled={approvalBusy || !canRequestChanges}
                            >
                              Request Changes
                            </button>
                            <AttachmentActions
                              compact
                              onUpload={
                                canUpload
                                  ? (file) =>
                                      uploadApprovalAttachmentMutation.mutate({
                                        approvalId: card.approval.approval_id,
                                        file
                                      })
                                  : undefined
                              }
                              onDownload={
                                canDownload
                                  ? () =>
                                      downloadApprovalAttachmentMutation.mutate(
                                        card.approval.approval_id
                                      )
                                  : undefined
                              }
                              disabled={approvalBusy}
                            />
                            <button
                              type="button"
                              className="workspace-board-action"
                              onClick={() =>
                                onOpenDetails(approvalDetailPayload(card.item, card.approval))
                              }
                            >
                              Details
                            </button>
                          </div>
                        </details>
                      </header>

                      <div className="workspace-board-card__meta">
                        <span className="workspace-board-tag workspace-board-tag--backend">
                          Backend
                        </span>
                      </div>

                      <footer>
                        <div className="workspace-avatar-stack">
                          {card.avatars.map((avatar, index) => (
                            <span
                              key={`${card.cardId}:avatar:${index}:${avatar}`}
                              className="workspace-avatar"
                              style={{ zIndex: card.avatars.length - index }}
                            >
                              {initials(avatar)}
                            </span>
                          ))}
                        </div>
                        <span className="workspace-board-counter">{card.primaryCount}</span>
                        <span className="workspace-board-counter">{card.secondaryCount}</span>
                      </footer>
                      {workpageActions.some((action) => action.state !== "available") ? (
                        <p className="workspace-board-card__hint">
                          {workpageActions
                            .filter((action) => action.state !== "available")
                            .map((action) => workpageActionStateLabel(action))
                            .join(" · ")}
                        </p>
                      ) : null}
                    </article>
                  );
                }

                const flagBusy =
                  (uploadFlagAttachmentMutation.isPending &&
                    uploadFlagAttachmentMutation.variables?.flagId === card.flag.flag_id) ||
                  (downloadFlagAttachmentMutation.isPending &&
                    downloadFlagAttachmentMutation.variables === card.flag.flag_id);
                const canUpload = hasAction(card.item, ["upload_attachment", "upload_artifact"]);
                const canDownload = hasAction(card.item, [
                  "download_attachment",
                  "download_artifact",
                  "download_attachments"
                ]);

                return (
                  <article
                    key={card.cardId}
                    className="workspace-board-card"
                    data-testid="workspace-task-card"
                  >
                    <header>
                      <h4>{card.title}</h4>
                      <details className="workspace-board-card__menu">
                        <summary aria-label={`Actions for ${card.title}`}>...</summary>
                        <div className="workspace-board-card__actions">
                          <AttachmentActions
                            compact
                            onUpload={
                              canUpload
                                ? (file) =>
                                    uploadFlagAttachmentMutation.mutate({
                                      flagId: card.flag.flag_id,
                                      file
                                    })
                                : undefined
                            }
                            onDownload={
                              canDownload
                                ? () => downloadFlagAttachmentMutation.mutate(card.flag.flag_id)
                                : undefined
                            }
                            disabled={flagBusy}
                          />
                          <button
                            type="button"
                            className="workspace-board-action"
                            onClick={() => onOpenDetails(flagDetailPayload(card.item, card.flag))}
                          >
                            Details
                          </button>
                        </div>
                      </details>
                    </header>

                    <div className="workspace-board-card__meta">
                      <span className="workspace-board-tag workspace-board-tag--backend">
                        Backend
                      </span>
                    </div>

                    <footer>
                      <div className="workspace-avatar-stack">
                        {card.avatars.map((avatar, index) => (
                          <span
                            key={`${card.cardId}:avatar:${index}:${avatar}`}
                            className="workspace-avatar"
                            style={{ zIndex: card.avatars.length - index }}
                          >
                            {initials(avatar)}
                          </span>
                        ))}
                      </div>
                      <span className="workspace-board-counter">{card.primaryCount}</span>
                      <span className="workspace-board-counter">{card.secondaryCount}</span>
                    </footer>
                  </article>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      {cards.length === 0 ? (
        <StatePanel
          kind="empty"
          title="No work currently projected"
          detail={`Run ${workflowRunId} has no task, approval, or flag cards in the current projection.`}
        />
      ) : null}
    </section>
  );
}
