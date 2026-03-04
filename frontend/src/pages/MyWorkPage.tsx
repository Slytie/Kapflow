import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { QueueRow } from "@/components/QueueRow";
import { StatePanel } from "@/components/StatePanel";
import { useShellFilters } from "@/app/useShellFilters";
import { humanTasksRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

export function MyWorkPage(): JSX.Element {
  const queryClient = useQueryClient();
  const { filters } = useShellFilters();
  const { open } = useDrawer();

  const refreshQueues = (): void => {
    void Promise.all([
      queryClient.invalidateQueries({ queryKey: ["my-work"] }),
      queryClient.invalidateQueries({ queryKey: ["board-view"] })
    ]);
  };

  const claimMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.claim(humanTaskId),
    onSuccess: refreshQueues
  });

  const completeMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.complete(humanTaskId),
    onSuccess: refreshQueues
  });

  const uploadAttachmentMutation = useMutation({
    mutationFn: (payload: { humanTaskId: string; file: File }) =>
      humanTasksRepository.uploadAttachment(payload.humanTaskId, payload.file),
    onSuccess: refreshQueues
  });

  const downloadAttachmentMutation = useMutation({
    mutationFn: (humanTaskId: string) => humanTasksRepository.downloadLatestAttachment(humanTaskId)
  });

  const query = useQuery({
    queryKey: ["my-work", filters.workflowRunId, filters.state, filters.assignee, filters.query],
    queryFn: () =>
      humanTasksRepository.list({
        workflowRunId: filters.workflowRunId,
        state: filters.state,
        assignee: filters.assignee,
        query: filters.query
      }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const mutationError =
    claimMutation.error ??
    completeMutation.error ??
    uploadAttachmentMutation.error ??
    downloadAttachmentMutation.error;

  if (query.isLoading) {
    return <StatePanel kind="loading" title="Loading my work" detail="Fetching task queue from API." />;
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="My Work failed to load"
        detail={errorText(query.error, "Unable to load task queue")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const data = query.data ?? [];
  if (data.length === 0) {
    return <StatePanel kind="empty" title="No tasks match current filters" detail="Try state or assignee changes." />;
  }

  return (
    <section data-testid="my-work-page">
      <h2>My Work Queue</h2>
      {mutationError ? (
        <StatePanel
          kind="error"
          title="Task action failed"
          detail={errorText(mutationError, "Could not apply task action")}
        />
      ) : null}
      <div className="stack-list">
        {data.map((task) => {
          const taskIsBusy =
            (claimMutation.isPending && claimMutation.variables === task.human_task_id) ||
            (completeMutation.isPending && completeMutation.variables === task.human_task_id) ||
            (uploadAttachmentMutation.isPending &&
              uploadAttachmentMutation.variables?.humanTaskId === task.human_task_id) ||
            (downloadAttachmentMutation.isPending &&
              downloadAttachmentMutation.variables === task.human_task_id);

          return (
            <QueueRow
              key={task.human_task_id}
              title={`${task.stage_id} · ${task.task_kind}`}
              subtitle={`${task.owner_role ?? "unknown"} · ${task.workflow_run_id}`}
              status={task.state}
              onClaim={() => claimMutation.mutate(task.human_task_id)}
              onComplete={() => completeMutation.mutate(task.human_task_id)}
              onUpload={(file) =>
                uploadAttachmentMutation.mutate({ humanTaskId: task.human_task_id, file })
              }
              onDownload={() => downloadAttachmentMutation.mutate(task.human_task_id)}
              actionPending={taskIsBusy}
              onDetails={() =>
                open({
                  title: `${task.stage_id} ${task.task_kind}`,
                  subtitle: task.human_task_id,
                  description: "Compact rows hide descriptions by default; details live in drawer.",
                  fields: [
                    { label: "Assignee", value: task.assignee_actor_id ?? "unassigned" },
                    { label: "Blocked on", value: task.blocked_on_kind ?? "none" },
                    { label: "Task run", value: task.task_run_id }
                  ]
                })
              }
            />
          );
        })}
      </div>
    </section>
  );
}
