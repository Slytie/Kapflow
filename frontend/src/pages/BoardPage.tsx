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

              return (
                <TaskCardWide
                  key={item.task.human_task_id}
                  task={item.task}
                  onClaim={() => claimMutation.mutate(item.task.human_task_id)}
                  onComplete={() => completeMutation.mutate(item.task.human_task_id)}
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
