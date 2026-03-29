import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { ApprovalCard } from "@/components/ApprovalCard";
import { FlagCard } from "@/components/FlagCard";
import { StatePanel } from "@/components/StatePanel";
import { TaskCardWide } from "@/components/TaskCardWide";
import { errorText } from "@/lib/api/errorText";
import {
  approvalsRepository,
  flagsRepository,
  humanTasksRepository
} from "@/lib/repositories";
import type {
  WorkflowWorkspaceWorkItem,
  WorkflowWorkspaceApprovalWorkItem,
  WorkflowWorkspaceFlagWorkItem,
  WorkflowWorkspaceTaskWorkItem
} from "@/lib/types/contracts";
import type { DrawerPayload } from "@/lib/types/ui";
import { taskDisplayHeading } from "@/lib/workspace/taskLabels";

type WorkspacePanelMode = "user_work" | "blocking_work";

interface WorkspaceActionPanelProps {
  workflowRunId: string;
  userWork: WorkflowWorkspaceWorkItem[];
  blockingWork: WorkflowWorkspaceWorkItem[];
  onRefresh: () => void;
  onOpenDetails: (payload: DrawerPayload) => void;
}

function hasAction(item: WorkflowWorkspaceWorkItem, candidates: string[]): boolean {
  const actions = new Set(item.available_actions.map((action) => action.toLowerCase()));
  return candidates.some((candidate) => actions.has(candidate.toLowerCase()));
}

function missingInputHint(item: WorkflowWorkspaceTaskWorkItem): string | undefined {
  if (item.missing_required_inputs.length === 0) {
    return undefined;
  }
  return `Missing required inputs: ${item.missing_required_inputs.join(", ")}`;
}

function taskDetailPayload(item: WorkflowWorkspaceTaskWorkItem): DrawerPayload {
  const task = item.human_task;
  return {
    title: taskDisplayHeading(task),
    subtitle: task.human_task_id,
    description:
      "Task details remain drawer-first. Workspace cards stay dense so graph and queue remain synchronized.",
    fields: [
      { label: "State", value: task.state },
      { label: "Owner role", value: task.owner_role ?? "n/a" },
      { label: "Assignee", value: task.assignee_actor_id ?? "unassigned" },
      { label: "Available actions", value: item.available_actions.join(", ") || "none" },
      {
        label: "Missing required inputs",
        value: item.missing_required_inputs.join(", ") || "none"
      }
    ],
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

function approvalDetailPayload(item: WorkflowWorkspaceApprovalWorkItem): DrawerPayload {
  const approval = item.approval;
  const description =
    approval.scope_ref === "Stage04"
      ? "Approval evidence and response context are shown in drawer. Approving this daily review finalizes the workbook and triggers planning feedback automatically."
      : "Approval evidence and response context are shown in drawer.";
  return {
    title: `${approval.approval_kind} ${approval.scope_ref}`,
    subtitle: approval.approval_id,
    description,
    fields: [
      { label: "State", value: approval.state },
      { label: "Required role", value: approval.required_role },
      { label: "Available actions", value: item.available_actions.join(", ") || "none" },
      { label: "Blocking reason", value: item.blocking_reason ?? "none" }
    ]
  };
}

function flagDetailPayload(item: WorkflowWorkspaceFlagWorkItem): DrawerPayload {
  const flag = item.flag;
  return {
    title: flag.summary,
    subtitle: flag.flag_id,
    description: "Flag detail and attachment context are shown in drawer.",
    fields: [
      { label: "State", value: flag.state },
      { label: "Severity", value: flag.severity },
      { label: "Assigned group", value: flag.assigned_group ?? "unassigned" },
      { label: "Available actions", value: item.available_actions.join(", ") || "none" }
    ]
  };
}

export function WorkspaceActionPanel({
  workflowRunId,
  userWork,
  blockingWork,
  onRefresh,
  onOpenDetails
}: WorkspaceActionPanelProps): JSX.Element {
  const [mode, setMode] = useState<WorkspacePanelMode>("user_work");

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

  const uploadTaskAttachmentMutation = useMutation({
    mutationFn: (payload: { humanTaskId: string; file: File }) =>
      humanTasksRepository.uploadAttachment(payload.humanTaskId, payload.file),
    onSuccess: onRefresh
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

  const items = useMemo(
    () => (mode === "user_work" ? userWork : blockingWork),
    [blockingWork, mode, userWork]
  );

  const mutationError =
    claimMutation.error ??
    completeMutation.error ??
    runStage06ReviewMutation.error ??
    runWeeklyStage04AgentMutation.error ??
    approvalMutation.error ??
    uploadTaskAttachmentMutation.error ??
    downloadTaskAttachmentMutation.error ??
    uploadApprovalAttachmentMutation.error ??
    downloadApprovalAttachmentMutation.error ??
    uploadFlagAttachmentMutation.error ??
    downloadFlagAttachmentMutation.error;

  return (
    <section className="workspace-action-panel" data-testid="workspace-action-panel">
      <header>
        <h3>Actionable Work</h3>
        <p>{workflowRunId}</p>
        <div className="workspace-action-panel__tabs" role="tablist" aria-label="Workspace queues">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "user_work"}
            className={mode === "user_work" ? "active" : ""}
            onClick={() => setMode("user_work")}
          >
            My Work ({userWork.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "blocking_work"}
            className={mode === "blocking_work" ? "active" : ""}
            onClick={() => setMode("blocking_work")}
          >
            Blocking Work ({blockingWork.length})
          </button>
        </div>
      </header>

      {mutationError ? (
        <StatePanel
          kind="error"
          title="Workspace action failed"
          detail={errorText(mutationError, "Unable to apply action")}
        />
      ) : null}

      {items.length === 0 ? (
        <StatePanel
          kind="empty"
          title={mode === "user_work" ? "No user work right now" : "No blocking work right now"}
          detail="Polling will refresh this panel automatically."
        />
      ) : (
        <div className="stack-list">
          {items.map((item) => {
            if (item.item_kind === "human_task") {
              const task = item.human_task;
              const taskIsBusy =
                (claimMutation.isPending && claimMutation.variables === task.human_task_id) ||
                (completeMutation.isPending && completeMutation.variables === task.human_task_id) ||
                (runStage06ReviewMutation.isPending &&
                  runStage06ReviewMutation.variables === task.human_task_id) ||
                (runWeeklyStage04AgentMutation.isPending &&
                  runWeeklyStage04AgentMutation.variables === task.human_task_id) ||
                (uploadTaskAttachmentMutation.isPending &&
                  uploadTaskAttachmentMutation.variables?.humanTaskId === task.human_task_id) ||
                (downloadTaskAttachmentMutation.isPending &&
                  downloadTaskAttachmentMutation.variables === task.human_task_id);

              const canClaim = hasAction(item, ["claim", "claim_human_task"]);
              const canComplete = hasAction(item, ["complete", "complete_human_task"]);
              const canUpload = hasAction(item, ["upload_attachment", "upload_artifact"]);
              const canDownload = hasAction(item, [
                "download_attachment",
                "download_artifact",
                "download_attachments"
              ]);
              const canRunStage06Review = hasAction(item, [
                "run_stage06_agent_review",
                "stage06_agent_review"
              ]);
              const canRunWeeklyStage04Agent = hasAction(item, [
                "run_weekly_stage04_openai_agent"
              ]);

              return (
                <TaskCardWide
                  key={item.work_id}
                  task={task}
                  onClaim={canClaim ? () => claimMutation.mutate(task.human_task_id) : undefined}
                  onComplete={canComplete ? () => completeMutation.mutate(task.human_task_id) : undefined}
                  onUpload={
                    canUpload
                      ? (file) =>
                          uploadTaskAttachmentMutation.mutate({
                            humanTaskId: task.human_task_id,
                            file
                          })
                      : undefined
                  }
                  onDownload={
                    canDownload
                      ? () => downloadTaskAttachmentMutation.mutate(task.human_task_id)
                      : undefined
                  }
                  claimDisabled={!canClaim}
                  completeDisabled={!canComplete || item.missing_required_inputs.length > 0}
                  needInfoDisabled
                  completeHint={missingInputHint(item)}
                  extraActions={
                    [
                      ...(canRunWeeklyStage04Agent
                        ? [
                            {
                              key: "weekly-stage04-build",
                              label: "Run Stage04 Build",
                              tone: "default" as const,
                              onClick: () =>
                                runWeeklyStage04AgentMutation.mutate(task.human_task_id),
                              disabled: taskIsBusy
                            }
                          ]
                        : []),
                      ...(canRunStage06Review
                        ? [
                            {
                              key: "stage06-ai-review",
                              label: "AI Review Assist",
                              tone: "default" as const,
                              onClick: () => runStage06ReviewMutation.mutate(task.human_task_id),
                              disabled: taskIsBusy
                            }
                          ]
                        : [])
                    ]
                  }
                  actionPending={taskIsBusy}
                  onDetails={() => onOpenDetails(taskDetailPayload(item))}
                />
              );
            }

            if (item.item_kind === "approval") {
              const approval = item.approval;
              const approvalIsBusy =
                (approvalMutation.isPending &&
                  approvalMutation.variables?.approvalId === approval.approval_id) ||
                (uploadApprovalAttachmentMutation.isPending &&
                  uploadApprovalAttachmentMutation.variables?.approvalId === approval.approval_id) ||
                (downloadApprovalAttachmentMutation.isPending &&
                  downloadApprovalAttachmentMutation.variables === approval.approval_id);

              const canApprove = hasAction(item, [
                "respond_approve",
                "approve",
                "respond_approval"
              ]);
              const canReject = hasAction(item, ["respond_reject", "reject", "respond_approval"]);
              const canRequestInfo = hasAction(item, [
                "respond_request_changes",
                "request_changes",
                "respond_approval"
              ]);
              const canUpload = hasAction(item, ["upload_attachment", "upload_artifact"]);
              const canDownload = hasAction(item, [
                "download_attachment",
                "download_artifact",
                "download_attachments"
              ]);

              return (
                <ApprovalCard
                  key={item.work_id}
                  approval={approval}
                  onApprove={
                    canApprove
                      ? () =>
                          approvalMutation.mutate({
                            approvalId: approval.approval_id,
                            responseKind: "approve"
                          })
                      : undefined
                  }
                  onReject={
                    canReject
                      ? () =>
                          approvalMutation.mutate({
                            approvalId: approval.approval_id,
                            responseKind: "reject"
                          })
                      : undefined
                  }
                  onRequestInfo={
                    canRequestInfo
                      ? () =>
                          approvalMutation.mutate({
                            approvalId: approval.approval_id,
                            responseKind: "request_changes"
                          })
                      : undefined
                  }
                  onUpload={
                    canUpload
                      ? (file) =>
                          uploadApprovalAttachmentMutation.mutate({
                            approvalId: approval.approval_id,
                            file
                          })
                      : undefined
                  }
                  onDownload={
                    canDownload
                      ? () => downloadApprovalAttachmentMutation.mutate(approval.approval_id)
                      : undefined
                  }
                  approveDisabled={!canApprove}
                  rejectDisabled={!canReject}
                  requestInfoDisabled={!canRequestInfo}
                  actionPending={approvalIsBusy}
                  onDetails={() => onOpenDetails(approvalDetailPayload(item))}
                />
              );
            }

            const flag = item.flag;
            const flagIsBusy =
              (uploadFlagAttachmentMutation.isPending &&
                uploadFlagAttachmentMutation.variables?.flagId === flag.flag_id) ||
              (downloadFlagAttachmentMutation.isPending &&
                downloadFlagAttachmentMutation.variables === flag.flag_id);
            const canUpload = hasAction(item, ["upload_attachment", "upload_artifact"]);
            const canDownload = hasAction(item, [
              "download_attachment",
              "download_artifact",
              "download_attachments"
            ]);

            return (
              <FlagCard
                key={item.work_id}
                flag={flag}
                actionPending={flagIsBusy}
                onUpload={
                  canUpload
                    ? (file) =>
                        uploadFlagAttachmentMutation.mutate({
                          flagId: flag.flag_id,
                          file
                        })
                    : undefined
                }
                onDownload={
                  canDownload ? () => downloadFlagAttachmentMutation.mutate(flag.flag_id) : undefined
                }
                onDetails={() => onOpenDetails(flagDetailPayload(item))}
              />
            );
          })}
        </div>
      )}
    </section>
  );
}
