import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { ApprovalCard } from "@/components/ApprovalCard";
import { FlagCard } from "@/components/FlagCard";
import { LaneColumn } from "@/components/LaneColumn";
import { LegacyScheduleNotice } from "@/components/LegacyScheduleNotice";
import { StatePanel } from "@/components/StatePanel";
import { TaskCardWide } from "@/components/TaskCardWide";
import { useShellFilters } from "@/app/useShellFilters";
import {
  approvalsRepository,
  boardRepository,
  flagsRepository
} from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";
import type { HumanTaskRow } from "@/lib/types/contracts";
import { buildTaskDocumentPreviewCues } from "@/lib/workspace/taskDocumentUi";
import { taskDisplayHeading } from "@/lib/workspace/taskLabels";

function hasAction(task: HumanTaskRow, candidates: string[]): boolean {
  const actions = task.available_actions ?? [];
  if (actions.length === 0) {
    return false;
  }
  const actionSet = new Set(actions.map((action) => action.toLowerCase()));
  return candidates.some((candidate) => actionSet.has(candidate.toLowerCase()));
}

function taskActionHint(task: HumanTaskRow): string | undefined {
  const hints: string[] = [];
  const blockingCodes = task.blocking_reason_codes ?? [];
  const missingRequiredInputs = task.missing_required_inputs ?? [];

  if (hasAction(task, ["claim", "claim_human_task", "complete", "complete_human_task"])) {
    hints.push("Open task pane to run claim/complete actions");
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

  const approvalMutation = useMutation({
    mutationFn: (payload: { approvalId: string; responseKind: "approve" | "reject" | "request_changes" }) =>
      approvalsRepository.respond(payload.approvalId, payload.responseKind),
    onSuccess: refreshBoardViews
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
    approvalMutation.error ??
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
    <div className="board-page" data-testid="board-page">
      <LegacyScheduleNotice surface="Board" />
      {mutationError ? (
        <StatePanel
          kind="error"
          title="Action failed"
          detail={errorText(mutationError, "Unable to apply action")}
        />
      ) : null}

      <div className="board-grid">
        {data.lanes.map((lane) => (
          <LaneColumn key={lane.id} title={lane.title} count={lane.items.length}>
            {lane.items.map((item) => {
              if (item.kind === "task") {
                return (
                  <TaskCardWide
                    key={item.task.human_task_id}
                    task={item.task}
                    completeHint={taskActionHint(item.task)}
                    documentCues={buildTaskDocumentPreviewCues(item.task)}
                    onDetails={() =>
                      open({
                        title: taskDisplayHeading(item.task),
                        subtitle: item.task.human_task_id,
                        description: "Extended task context opens in the centered task modal so board cards can stay dense.",
                        fields: [
                          { label: "State", value: item.task.state },
                          { label: "Assignee", value: item.task.assignee_actor_id ?? "unassigned" },
                          { label: "Workflow run", value: item.task.workflow_run_id }
                        ],
                        task: {
                          human_task_id: item.task.human_task_id,
                          workflow_run_id: item.task.workflow_run_id,
                          task_run_id: item.task.task_run_id,
                          stage_id: item.task.stage_id,
                          task_kind: item.task.task_kind,
                          state: item.task.state,
                          created_at: item.task.created_at,
                          updated_at: item.task.updated_at,
                          assignee_actor_id: item.task.assignee_actor_id,
                          assignee_actor_type: item.task.assignee_actor_type,
                          owner_role: item.task.owner_role,
                          candidate_roles: item.task.candidate_roles ?? [],
                          linked_approval_id: item.task.linked_approval_id,
                          blocked_on_kind: item.task.blocked_on_kind,
                          blocked_on_ref: item.task.blocked_on_ref,
                          available_actions: item.task.available_actions ?? [],
                          blocking_reason_codes: item.task.blocking_reason_codes ?? [],
                          missing_required_inputs: item.task.missing_required_inputs ?? [],
                          required_uploads: item.task.required_uploads ?? [],
                          required_reviews: item.task.required_reviews ?? [],
                          workpage_actions: item.task.workpage_actions ?? [],
                          is_composite: item.task.is_composite ?? false,
                          expansion_kind: item.task.expansion_kind ?? "none",
                          subgraph_ref: item.task.subgraph_ref ?? null
                        },
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
    </div>
  );
}
