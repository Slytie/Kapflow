import { useMemo } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { AttachmentActions } from "@/components/AttachmentActions";
import { StatePanel } from "@/components/StatePanel";
import { TaskDocumentCues } from "@/components/TaskDocumentCues";
import { WorkspaceBoardCard } from "@/components/workspace/WorkspaceBoardCard";
import { errorText } from "@/lib/api/errorText";
import {
  approvalsRepository,
  flagsRepository,
  humanTasksRepository,
  workpagesRepository
} from "@/lib/repositories";
import type {
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceApprovalWorkItem,
  WorkflowWorkspaceFlagWorkItem,
  WorkflowWorkspaceTaskWorkItem,
  WorkflowWorkspaceWorkpageAction
} from "@/lib/types/contracts";
import type { DrawerPayload } from "@/lib/types/ui";
import { buildTaskArtifacts } from "@/lib/workspace/taskDetailPayload";
import { buildTaskDocumentPreviewCues } from "@/lib/workspace/taskDocumentUi";
import {
  actionRefTargetsSubject,
  approvalDetailPayload,
  buildWorkspaceBoardCards,
  buildWorkspaceLaneCards,
  flagDetailPayload,
  hasAction,
  humanizeBlockingReason,
  LANE_CONFIG,
  taskDetailPayload,
  workpageActionStateLabel,
  type WorkspaceBoardCard as WorkspaceBoardCardModel
} from "@/lib/workspace/taskBoardModel";

interface WorkspaceTaskBoardProps {
  workflowRunId: string;
  workspace: WorkflowRunWorkspaceContract;
  detail: WorkflowRunDetailContract;
  onRefresh: () => void;
  onOpenDetails: (payload: DrawerPayload) => void;
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
      return workpagesRepository.createWorkpage(action.create_path, action.action_ref ?? undefined);
    },
    onSuccess: (draft, action) => {
      onRefresh();
      navigate(draft.route, {
        state: {
          workpageActionRef: action.action_ref
            ? {
                ...action.action_ref,
                artifact_version_id: draft.artifact_version_id
              }
            : undefined
        }
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
        state: { workpageActionRef: action.action_ref }
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

  const cards = useMemo<WorkspaceBoardCardModel[]>(
    () =>
      buildWorkspaceBoardCards({
        detail,
        taskItemById,
        approvalItemById,
        flagItemById
      }),
    [approvalItemById, detail, flagItemById, taskItemById]
  );

  const laneCards = useMemo(() => {
    return buildWorkspaceLaneCards(cards);
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
                      actionRefTargetsSubject(
                        workpageActionMutation.variables,
                        "human_task",
                        card.task.human_task_id
                      ));
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
                    <WorkspaceBoardCard
                      key={card.cardId}
                      card={card}
                      onOpen={openTaskDetails}
                      menu={
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
                      }
                      body={
                        <>
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
                        </>
                      }
                      footerHint={missingInputHint}
                      secondaryHint={
                        workpageActions.some((action) => action.state !== "available")
                          ? workpageActions
                              .filter((action) => action.state !== "available")
                              .map((action) => workpageActionStateLabel(action))
                              .join(" · ")
                          : null
                      }
                    />
                  );
                }

                if (card.kind === "approval") {
                  const approvalBusy =
                    (approvalMutation.isPending &&
                      approvalMutation.variables?.approvalId === card.approval.approval_id) ||
                    (workpageActionMutation.isPending &&
                      actionRefTargetsSubject(
                        workpageActionMutation.variables,
                        "approval",
                        card.approval.approval_id
                      )) ||
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
                    <WorkspaceBoardCard
                      key={card.cardId}
                      card={card}
                      menu={
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
                                title={
                                  action.state === "available"
                                    ? undefined
                                    : workpageActionStateLabel(action)
                                }
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
                      }
                      secondaryHint={
                        workpageActions.some((action) => action.state !== "available")
                          ? workpageActions
                              .filter((action) => action.state !== "available")
                              .map((action) => workpageActionStateLabel(action))
                              .join(" · ")
                          : null
                      }
                    />
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
                  <WorkspaceBoardCard
                    key={card.cardId}
                    card={card}
                    menu={
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
                    }
                  />
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
