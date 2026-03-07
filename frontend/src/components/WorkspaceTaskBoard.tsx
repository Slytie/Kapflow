import { type ChangeEvent, useId, useMemo, useRef } from "react";
import { useMutation } from "@tanstack/react-query";

import { AttachmentActions } from "@/components/AttachmentActions";
import { StatePanel } from "@/components/StatePanel";
import { errorText } from "@/lib/api/errorText";
import {
  approvalsRepository,
  flagsRepository,
  humanTasksRepository,
  templatesRepository
} from "@/lib/repositories";
import type {
  ApprovalRow,
  ArtifactVersionRow,
  FlagRow,
  HumanTaskRow,
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceApprovalWorkItem,
  WorkflowWorkspaceFlagWorkItem,
  WorkflowWorkspaceRequiredUpload,
  WorkflowWorkspaceTaskWorkItem,
  WorkflowWorkspaceWorkItem
} from "@/lib/types/contracts";
import type { DrawerArtifact, DrawerPayload } from "@/lib/types/ui";

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

interface RequiredUploadActionsProps {
  requirement: WorkflowWorkspaceRequiredUpload;
  disabled: boolean;
  onUpload: (file: File) => void;
  onDownloadTemplate?: () => void;
}

function RequiredUploadActions({
  requirement,
  disabled,
  onUpload,
  onDownloadTemplate
}: RequiredUploadActionsProps): JSX.Element {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const inputId = useId();

  const openFilePicker = (): void => {
    if (disabled) {
      return;
    }
    inputRef.current?.click();
  };

  const onInputChanged = (event: ChangeEvent<HTMLInputElement>): void => {
    const file = event.currentTarget.files?.[0];
    if (file) {
      onUpload(file);
    }
    event.currentTarget.value = "";
  };

  return (
    <div className="workspace-required-upload-actions">
      <input
        id={inputId}
        ref={inputRef}
        type="file"
        onChange={onInputChanged}
        tabIndex={-1}
        style={{ display: "none" }}
      />
      <button
        type="button"
        className="workspace-board-action"
        onClick={openFilePicker}
        disabled={disabled}
      >
        Upload Response
      </button>
      <button
        type="button"
        className="workspace-board-action"
        onClick={onDownloadTemplate}
        disabled={disabled || !onDownloadTemplate || !requirement.template_id}
      >
        Download Template
      </button>
    </div>
  );
}

function hasAction(item: WorkflowWorkspaceWorkItem | null, candidates: string[]): boolean {
  if (!item) {
    return false;
  }
  const actions = new Set(item.available_actions.map((action) => action.toLowerCase()));
  return candidates.some((candidate) => actions.has(candidate.toLowerCase()));
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

function _artifactFileName(artifact: ArtifactVersionRow): string | null {
  const fileName = artifact.metadata_json?.file_name;
  if (typeof fileName === "string" && fileName.length > 0) {
    return fileName;
  }
  return null;
}

function _taskArtifacts(
  task: HumanTaskRow,
  artifactVersions: WorkflowRunDetailContract["artifact_versions"]
): DrawerArtifact[] {
  const byArtifactVersionId = new Map<string, DrawerArtifact>();

  for (const artifact of artifactVersions) {
    const links = artifact.links ?? [];
    const linkedToHumanTask = links.some(
      (link) => link.subject_kind === "human_task" && link.subject_id === task.human_task_id
    );
    const linkedToTaskRun = links.some(
      (link) => link.subject_kind === "task_run" && link.subject_id === task.task_run_id
    );
    const createdByTaskRun = artifact.task_run_id === task.task_run_id;
    if (!linkedToHumanTask && !linkedToTaskRun && !createdByTaskRun) {
      continue;
    }

    const sourceLabel = linkedToHumanTask ? "Task attachment" : "Step output";
    byArtifactVersionId.set(artifact.artifact_version_id, {
      artifact_version_id: artifact.artifact_version_id,
      artifact_kind: artifact.artifact_kind,
      artifact_role: artifact.artifact_role ?? null,
      media_type: artifact.media_type,
      created_at: artifact.created_at,
      file_name: _artifactFileName(artifact),
      source_label: sourceLabel
    });
  }

  return Array.from(byArtifactVersionId.values()).sort((left, right) =>
    right.created_at.localeCompare(left.created_at)
  );
}

function taskDetailPayload(
  item: WorkflowWorkspaceTaskWorkItem | null,
  task: HumanTaskRow,
  artifactVersions: WorkflowRunDetailContract["artifact_versions"]
): DrawerPayload {
  const artifacts = _taskArtifacts(task, artifactVersions);
  return {
    title: `${task.stage_id} ${humanize(task.task_kind)}`,
    subtitle: task.human_task_id,
    description:
      "Task details remain drawer-first so cards can stay dense and synchronized with the graph.",
    fields: [
      { label: "State", value: task.state },
      { label: "Owner role", value: task.owner_role ?? "n/a" },
      { label: "Assignee", value: task.assignee_actor_id ?? "unassigned" },
      { label: "Available actions", value: item?.available_actions.join(", ") || "none" },
      {
        label: "Missing required inputs",
        value: item?.missing_required_inputs.join(", ") || "none"
      },
      { label: "Artifacts", value: String(artifacts.length) }
    ],
    artifacts,
    artifact_sources: [
      {
        workflow_run_id: task.workflow_run_id,
        subject_kind: "human_task",
        subject_id: task.human_task_id,
        source_label: "Task attachment"
      },
      {
        workflow_run_id: task.workflow_run_id,
        subject_kind: "task_run",
        subject_id: task.task_run_id,
        source_label: "Step output"
      }
    ]
  };
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
  const claimMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.claim(humanTaskId),
    onSuccess: onRefresh
  });

  const completeMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.complete(humanTaskId),
    onSuccess: onRefresh
  });

  const confirmReviewMutation = useMutation({
    mutationFn: (payload: { humanTaskId: string; reviewedArtifactVersionIds: string[] }) =>
      humanTasksRepository.confirmReview(payload.humanTaskId, payload.reviewedArtifactVersionIds),
    onSuccess: onRefresh
  });

  const runStage06ReviewMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.runStage06AgentReview(humanTaskId),
    onSuccess: onRefresh
  });

  const approvalMutation = useMutation({
    mutationFn: (payload: {
      approvalId: string;
      responseKind: "approve" | "reject" | "request_changes";
    }) => approvalsRepository.respond(payload.approvalId, payload.responseKind),
    onSuccess: onRefresh
  });

  const uploadTaskAttachmentMutation = useMutation({
    mutationFn: (payload: { humanTaskId: string; file: File }) =>
      humanTasksRepository.uploadAttachment(payload.humanTaskId, payload.file),
    onSuccess: onRefresh
  });

  const uploadRequiredResponseMutation = useMutation({
    mutationFn: (payload: {
      humanTaskId: string;
      requirement: WorkflowWorkspaceRequiredUpload;
      file: File;
    }) =>
      humanTasksRepository.uploadRequiredResponse(
        payload.humanTaskId,
        payload.requirement,
        payload.file
      ),
    onSuccess: onRefresh
  });

  const downloadTemplateMutation = useMutation({
    mutationFn: (templateId: string) => templatesRepository.download(templateId)
  });

  const openDraftMutation = useMutation({
    mutationFn: (artifactVersionId: string) =>
      humanTasksRepository.openDraftArtifact(artifactVersionId)
  });

  const downloadTaskAttachmentMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.downloadLatestAttachment(humanTaskId)
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
    confirmReviewMutation.error ??
    runStage06ReviewMutation.error ??
    approvalMutation.error ??
    uploadTaskAttachmentMutation.error ??
    uploadRequiredResponseMutation.error ??
    downloadTemplateMutation.error ??
    openDraftMutation.error ??
    downloadTaskAttachmentMutation.error ??
    uploadApprovalAttachmentMutation.error ??
    downloadApprovalAttachmentMutation.error ??
    uploadFlagAttachmentMutation.error ??
    downloadFlagAttachmentMutation.error;

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
        title: humanize(task.task_kind),
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
                  const requiredUploads = card.item?.required_uploads ?? [];
                  const requiredReviews = card.item?.required_reviews ?? [];
                  const reviewArtifactVersionIds = requiredReviews
                    .map((review) => review.reviewed_artifact_version_id)
                    .filter((value): value is string => Boolean(value));
                  const hasPendingReviewConfirmation = requiredReviews.some(
                    (review) => review.status === "pending_confirmation"
                  );
                  const taskBusy =
                    (claimMutation.isPending && claimMutation.variables === card.task.human_task_id) ||
                    (completeMutation.isPending &&
                      completeMutation.variables === card.task.human_task_id) ||
                    (confirmReviewMutation.isPending &&
                      confirmReviewMutation.variables?.humanTaskId === card.task.human_task_id) ||
                    (runStage06ReviewMutation.isPending &&
                      runStage06ReviewMutation.variables === card.task.human_task_id) ||
                    (uploadTaskAttachmentMutation.isPending &&
                      uploadTaskAttachmentMutation.variables?.humanTaskId ===
                        card.task.human_task_id) ||
                    (uploadRequiredResponseMutation.isPending &&
                      uploadRequiredResponseMutation.variables?.humanTaskId ===
                        card.task.human_task_id) ||
                    downloadTemplateMutation.isPending ||
                    openDraftMutation.isPending ||
                    (downloadTaskAttachmentMutation.isPending &&
                      downloadTaskAttachmentMutation.variables === card.task.human_task_id);

                  const canClaim =
                    hasAction(card.item, ["claim", "claim_human_task"]) ||
                    (card.item === null && card.task.state === "OPEN");
                  const canComplete =
                    hasAction(card.item, ["complete", "complete_human_task"]) ||
                    (card.item === null && card.task.state === "CLAIMED");
                  const canUpload = hasAction(card.item, ["upload_attachment", "upload_artifact"]);
                  const canDownload = hasAction(card.item, [
                    "download_attachment",
                    "download_artifact",
                    "download_attachments"
                  ]);
                  const canRunStage06Review = hasAction(card.item, [
                    "run_stage06_agent_review",
                    "stage06_agent_review"
                  ]);
                  const canConfirmReview = hasAction(card.item, ["confirm_review"]);
                  const requirementBlocked =
                    (card.item?.missing_required_inputs.length ?? 0) > 0 ||
                    (card.item?.blocking_reason_codes.length ?? 0) > 0;
                  const canCompleteNow = canComplete && !requirementBlocked;

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
                            <AttachmentActions
                              compact
                              onUpload={
                                canUpload
                                  ? (file) =>
                                      uploadTaskAttachmentMutation.mutate({
                                        humanTaskId: card.task.human_task_id,
                                        file
                                      })
                                  : undefined
                              }
                              onDownload={
                                canDownload
                                  ? () =>
                                      downloadTaskAttachmentMutation.mutate(card.task.human_task_id)
                                  : undefined
                              }
                              disabled={taskBusy}
                            />
                            <button
                              type="button"
                              className="workspace-board-action"
                              onClick={() =>
                                onOpenDetails(
                                  taskDetailPayload(card.item, card.task, detail.artifact_versions)
                                )
                              }
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

                      {requiredUploads.length > 0 ? (
                        <div className="workspace-board-card__requirements">
                          {requiredUploads.map((requirement, index) => (
                            <div
                              key={`${card.cardId}:required-upload:${index}:${requirement.dataset_key}`}
                              className="workspace-board-card__requirement"
                            >
                              <p>
                                Required upload: {requirement.dataset_key} ({requirement.status})
                              </p>
                              <RequiredUploadActions
                                requirement={requirement}
                                disabled={taskBusy}
                                onUpload={(file) =>
                                  uploadRequiredResponseMutation.mutate({
                                    humanTaskId: card.task.human_task_id,
                                    requirement,
                                    file
                                  })
                                }
                                onDownloadTemplate={
                                  requirement.template_id
                                    ? () => downloadTemplateMutation.mutate(requirement.template_id as string)
                                    : undefined
                                }
                              />
                            </div>
                          ))}
                        </div>
                      ) : null}

                      {requiredReviews.length > 0 ? (
                        <div className="workspace-board-card__requirements">
                          {requiredReviews.map((requirement, index) => (
                            <div
                              key={`${card.cardId}:required-review:${index}:${requirement.artifact_kind}`}
                              className="workspace-board-card__requirement"
                            >
                              <p>Required review: {requirement.artifact_kind} ({requirement.status})</p>
                              <div className="workspace-required-upload-actions">
                                <button
                                  type="button"
                                  className="workspace-board-action"
                                  onClick={() => {
                                    if (requirement.reviewed_artifact_version_id) {
                                      openDraftMutation.mutate(requirement.reviewed_artifact_version_id);
                                    }
                                  }}
                                  disabled={taskBusy || !requirement.reviewed_artifact_version_id}
                                >
                                  Open Draft
                                </button>
                                <button
                                  type="button"
                                  className="workspace-board-action"
                                  onClick={() =>
                                    confirmReviewMutation.mutate({
                                      humanTaskId: card.task.human_task_id,
                                      reviewedArtifactVersionIds: reviewArtifactVersionIds
                                    })
                                  }
                                  disabled={
                                    taskBusy ||
                                    !canConfirmReview ||
                                    !hasPendingReviewConfirmation ||
                                    reviewArtifactVersionIds.length === 0
                                  }
                                >
                                  Confirm Reviewed
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : null}

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
                    </article>
                  );
                }

                if (card.kind === "approval") {
                  const approvalBusy =
                    (approvalMutation.isPending &&
                      approvalMutation.variables?.approvalId === card.approval.approval_id) ||
                    (uploadApprovalAttachmentMutation.isPending &&
                      uploadApprovalAttachmentMutation.variables?.approvalId ===
                        card.approval.approval_id) ||
                    (downloadApprovalAttachmentMutation.isPending &&
                      downloadApprovalAttachmentMutation.variables === card.approval.approval_id);

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
