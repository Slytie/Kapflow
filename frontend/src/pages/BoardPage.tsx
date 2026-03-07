import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { ApprovalCard } from "@/components/ApprovalCard";
import { FlagCard } from "@/components/FlagCard";
import { LaneColumn } from "@/components/LaneColumn";
import { StatePanel } from "@/components/StatePanel";
import { TaskCardWide } from "@/components/TaskCardWide";
import { useShellFilters } from "@/app/useShellFilters";
import {
  approvalsRepository,
  boardRepository,
  flagsRepository,
  humanTasksRepository
} from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";
import type { HumanTaskRow } from "@/lib/types/contracts";

function hasAction(task: HumanTaskRow, candidates: string[]): boolean {
  const actions = task.available_actions ?? [];
  if (actions.length === 0) {
    return false;
  }
  const actionSet = new Set(actions.map((action) => action.toLowerCase()));
  return candidates.some((candidate) => actionSet.has(candidate.toLowerCase()));
}

function roleMatch(task: HumanTaskRow): boolean {
  const candidateRoles = task.candidate_roles ?? [];
  if (candidateRoles.length === 0) {
    return true;
  }
  const actorRoles = new Set(
    apiConfig.actorRoles
      .split(",")
      .map((role) => role.trim())
      .filter(Boolean)
  );
  return candidateRoles.some((role) => actorRoles.has(role));
}

function canClaimTask(task: HumanTaskRow): boolean {
  if (task.available_actions && task.available_actions.length > 0) {
    return hasAction(task, ["claim", "claim_human_task"]);
  }
  return task.state === "OPEN" && !task.assignee_actor_id && roleMatch(task);
}

function canCompleteTask(task: HumanTaskRow): boolean {
  if (task.available_actions && task.available_actions.length > 0) {
    return hasAction(task, ["complete", "complete_human_task"]);
  }
  return (
    task.state === "CLAIMED" &&
    task.assignee_actor_id === apiConfig.actorId &&
    task.assignee_actor_type === apiConfig.actorType
  );
}

function taskActionHint(
  task: HumanTaskRow,
  options: { canClaim: boolean; canComplete: boolean }
): string | undefined {
  const { canClaim, canComplete } = options;
  const hints: string[] = [];
  const blockingCodes = task.blocking_reason_codes ?? [];
  const missingRequiredInputs = task.missing_required_inputs ?? [];

  if (!canClaim && task.state === "OPEN") {
    if (blockingCodes.includes("candidate_role_mismatch")) {
      hints.push(`Cannot claim: requires role ${task.candidate_roles.join(", ")}`);
    } else if (blockingCodes.includes("claimed_by_other_actor") || task.assignee_actor_id) {
      hints.push(`Cannot claim: already claimed by ${task.assignee_actor_id ?? "another actor"}`);
    } else {
      hints.push("Cannot claim with current actor");
    }
  }

  if (!canComplete && task.state === "OPEN") {
    hints.push("Cannot complete: claim task first");
  } else if (!canComplete && task.state === "CLAIMED") {
    if (task.assignee_actor_id && task.assignee_actor_id !== apiConfig.actorId) {
      hints.push(`Cannot complete: claimed by ${task.assignee_actor_id}`);
    } else {
      hints.push("Cannot complete with current actor");
    }
  }

  if (missingRequiredInputs.length > 0) {
    hints.push(`Missing required inputs: ${missingRequiredInputs.join(", ")}`);
  }

  const extraBlocking = blockingCodes.filter(
    (code) =>
      code !== "candidate_role_mismatch" &&
      code !== "claimed_by_other_actor" &&
      !code.startsWith("required_upload_missing:") &&
      !code.startsWith("required_review_confirmation_missing:")
  );
  if (extraBlocking.length > 0) {
    hints.push(`Blocked: ${extraBlocking.join(", ")}`);
  }

  if (hints.length === 0) {
    return undefined;
  }
  return hints.join(" · ");
}

export function BoardPage(): JSX.Element {
  const queryClient = useQueryClient();
  const { filters } = useShellFilters();
  const { open } = useDrawer();

  const refreshBoardViews = (): void => {
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["board-view"] }),
      queryClient.invalidateQueries({ queryKey: ["my-work"] }),
      queryClient.invalidateQueries({ queryKey: ["approvals"] }),
      queryClient.invalidateQueries({ queryKey: ["exceptions"] }),
      queryClient.invalidateQueries({ queryKey: ["runs"] })
    ]);
  };

  const claimMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.claim(humanTaskId),
    onSuccess: refreshBoardViews
  });

  const completeMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.complete(humanTaskId),
    onSuccess: refreshBoardViews
  });

  const approvalMutation = useMutation({
    mutationFn: (payload: { approvalId: string; responseKind: "approve" | "reject" | "request_changes" }) =>
      approvalsRepository.respond(payload.approvalId, payload.responseKind),
    onSuccess: refreshBoardViews
  });

  const uploadTaskAttachmentMutation = useMutation({
    mutationFn: (payload: { humanTaskId: string; file: File }) =>
      humanTasksRepository.uploadAttachment(payload.humanTaskId, payload.file),
    onSuccess: refreshBoardViews
  });

  const downloadTaskAttachmentMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.downloadLatestAttachment(humanTaskId)
  });

  const uploadApprovalAttachmentMutation = useMutation({
    mutationFn: (payload: { approvalId: string; file: File }) =>
      approvalsRepository.uploadAttachment(payload.approvalId, payload.file),
    onSuccess: refreshBoardViews
  });

  const downloadApprovalAttachmentMutation = useMutation({
    mutationFn: (approvalId: string) => approvalsRepository.downloadLatestAttachment(approvalId)
  });

  const uploadFlagAttachmentMutation = useMutation({
    mutationFn: (payload: { flagId: string; file: File }) =>
      flagsRepository.uploadAttachment(payload.flagId, payload.file),
    onSuccess: refreshBoardViews
  });

  const downloadFlagAttachmentMutation = useMutation({
    mutationFn: (flagId: string) => flagsRepository.downloadLatestAttachment(flagId)
  });

  const query = useQuery({
    queryKey: ["board-view", filters.workflowRunId, filters.state, filters.assignee],
    queryFn: () =>
      boardRepository.view({
        workflowRunId: filters.workflowRunId,
        state: filters.state,
        assignee: filters.assignee
      }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const mutationError =
    claimMutation.error ??
    completeMutation.error ??
    approvalMutation.error ??
    uploadTaskAttachmentMutation.error ??
    downloadTaskAttachmentMutation.error ??
    uploadApprovalAttachmentMutation.error ??
    downloadApprovalAttachmentMutation.error ??
    uploadFlagAttachmentMutation.error ??
    downloadFlagAttachmentMutation.error;

  if (query.isLoading) {
    return <StatePanel kind="loading" title="Loading board" detail="Fetching lanes from the runtime API." />;
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Board failed to load"
        detail={errorText(query.error, "Unable to load board data")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const data = query.data;
  if (!data || data.lanes.every((lane) => lane.items.length === 0)) {
    return <StatePanel kind="empty" title="No board work in scope" detail="Try widening filters or scope." />;
  }

  return (
    <div className="board-grid" data-testid="board-page">
      {mutationError ? (
        <StatePanel
          kind="error"
          title="Inline action failed"
          detail={errorText(mutationError, "Unable to apply action")}
        />
      ) : null}

      {data.lanes.map((lane) => (
        <LaneColumn key={lane.id} title={lane.title} count={lane.items.length}>
          {lane.items.map((item) => {
            if (item.kind === "task") {
              const taskIsBusy =
                (claimMutation.isPending && claimMutation.variables === item.task.human_task_id) ||
                (completeMutation.isPending && completeMutation.variables === item.task.human_task_id) ||
                (uploadTaskAttachmentMutation.isPending &&
                  uploadTaskAttachmentMutation.variables?.humanTaskId === item.task.human_task_id) ||
                (downloadTaskAttachmentMutation.isPending &&
                  downloadTaskAttachmentMutation.variables === item.task.human_task_id);
              const canClaim = canClaimTask(item.task);
              const canComplete = canCompleteTask(item.task);

              return (
                <TaskCardWide
                  key={item.task.human_task_id}
                  task={item.task}
                  onClaim={() => claimMutation.mutate(item.task.human_task_id)}
                  onComplete={() => completeMutation.mutate(item.task.human_task_id)}
                  claimDisabled={!canClaim}
                  completeDisabled={!canComplete}
                  completeHint={taskActionHint(item.task, { canClaim, canComplete })}
                  onUpload={(file) =>
                    uploadTaskAttachmentMutation.mutate({
                      humanTaskId: item.task.human_task_id,
                      file
                    })
                  }
                  onDownload={() => downloadTaskAttachmentMutation.mutate(item.task.human_task_id)}
                  actionPending={taskIsBusy}
                  onDetails={() =>
                    open({
                      title: `${item.task.stage_id} ${item.task.task_kind}`,
                      subtitle: item.task.human_task_id,
                      description: "Extended task description stays in drawer to keep board cards dense.",
                      fields: [
                        { label: "State", value: item.task.state },
                        { label: "Assignee", value: item.task.assignee_actor_id ?? "unassigned" },
                        { label: "Workflow run", value: item.task.workflow_run_id }
                      ],
                      artifact_sources: [
                        {
                          workflow_run_id: item.task.workflow_run_id,
                          subject_kind: "human_task",
                          subject_id: item.task.human_task_id,
                          source_label: "Task attachment"
                        },
                        {
                          workflow_run_id: item.task.workflow_run_id,
                          subject_kind: "task_run",
                          subject_id: item.task.task_run_id,
                          source_label: "Step output"
                        }
                      ]
                    })
                  }
                />
              );
            }
            if (item.kind === "approval") {
              const approvalIsBusy =
                (approvalMutation.isPending &&
                  approvalMutation.variables?.approvalId === item.approval.approval_id) ||
                (uploadApprovalAttachmentMutation.isPending &&
                  uploadApprovalAttachmentMutation.variables?.approvalId === item.approval.approval_id) ||
                (downloadApprovalAttachmentMutation.isPending &&
                  downloadApprovalAttachmentMutation.variables === item.approval.approval_id);

              return (
                <ApprovalCard
                  key={item.approval.approval_id}
                  approval={item.approval}
                  onApprove={() =>
                    approvalMutation.mutate({
                      approvalId: item.approval.approval_id,
                      responseKind: "approve"
                    })
                  }
                  onReject={() =>
                    approvalMutation.mutate({
                      approvalId: item.approval.approval_id,
                      responseKind: "reject"
                    })
                  }
                  onRequestInfo={() =>
                    approvalMutation.mutate({
                      approvalId: item.approval.approval_id,
                      responseKind: "request_changes"
                    })
                  }
                  actionPending={approvalIsBusy}
                  onUpload={(file) =>
                    uploadApprovalAttachmentMutation.mutate({
                      approvalId: item.approval.approval_id,
                      file
                    })
                  }
                  onDownload={() =>
                    downloadApprovalAttachmentMutation.mutate(item.approval.approval_id)
                  }
                  onDetails={() =>
                    open({
                      title: `${item.approval.approval_kind} ${item.approval.scope_ref}`,
                      subtitle: item.approval.approval_id,
                      description: "Approval evidence and rationale are reviewed in drawer context.",
                      fields: [
                        { label: "State", value: item.approval.state },
                        { label: "Required role", value: item.approval.required_role },
                        { label: "Response", value: item.approval.response_kind ?? "pending" }
                      ]
                    })
                  }
                />
              );
            }

            const flagIsBusy =
              (uploadFlagAttachmentMutation.isPending &&
                uploadFlagAttachmentMutation.variables?.flagId === item.flag.flag_id) ||
              (downloadFlagAttachmentMutation.isPending &&
                downloadFlagAttachmentMutation.variables === item.flag.flag_id);

            return (
              <FlagCard
                key={item.flag.flag_id}
                flag={item.flag}
                actionPending={flagIsBusy}
                onUpload={(file) =>
                  uploadFlagAttachmentMutation.mutate({
                    flagId: item.flag.flag_id,
                    file
                  })
                }
                onDownload={() => downloadFlagAttachmentMutation.mutate(item.flag.flag_id)}
                onDetails={() =>
                  open({
                    title: item.flag.summary,
                    subtitle: item.flag.flag_id,
                    description: "Flag details and related run pointers are shown here.",
                    fields: [
                      { label: "State", value: item.flag.state },
                      { label: "Severity", value: item.flag.severity },
                      { label: "Run", value: item.flag.workflow_run_id }
                    ]
                  })
                }
              />
            );
          })}
        </LaneColumn>
      ))}
    </div>
  );
}
