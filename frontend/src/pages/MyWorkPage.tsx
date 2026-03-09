import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { QueueRow } from "@/components/QueueRow";
import { StatePanel } from "@/components/StatePanel";
import { useShellFilters } from "@/app/useShellFilters";
import { humanTasksRepository } from "@/lib/repositories";
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

function isAssignedToCurrentActor(task: HumanTaskRow): boolean {
  return (
    task.assignee_actor_id === apiConfig.actorId &&
    task.assignee_actor_type === apiConfig.actorType
  );
}

function isTaskActionableForCurrentActor(task: HumanTaskRow): boolean {
  if (canClaimTask(task) || canCompleteTask(task)) {
    return true;
  }
  return task.state === "CLAIMED" && isAssignedToCurrentActor(task);
}

function taskActionHint(task: HumanTaskRow, canClaim: boolean, canComplete: boolean): string | undefined {
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
    uploadAttachmentMutation.error ?? downloadAttachmentMutation.error;

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

  const data = (query.data ?? []).filter((task) => isTaskActionableForCurrentActor(task));
  if (data.length === 0) {
    return (
      <StatePanel
        kind="empty"
        title="No actionable tasks for current user"
        detail="Switch active user or adjust filters to view claimable/owned work."
      />
    );
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
            (uploadAttachmentMutation.isPending &&
              uploadAttachmentMutation.variables?.humanTaskId === task.human_task_id) ||
            (downloadAttachmentMutation.isPending &&
              downloadAttachmentMutation.variables === task.human_task_id);
          const canClaim = canClaimTask(task);
          const canComplete = canCompleteTask(task);

          return (
            <QueueRow
              key={task.human_task_id}
              title={`${task.stage_id} · ${task.task_kind}`}
              subtitle={`${task.owner_role ?? "unknown"} · ${task.workflow_run_id}`}
              status={task.state}
              hint={taskActionHint(task, canClaim, canComplete)}
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
                  ],
                  task: {
                    human_task_id: task.human_task_id,
                    workflow_run_id: task.workflow_run_id,
                    task_run_id: task.task_run_id,
                    stage_id: task.stage_id,
                    task_kind: task.task_kind,
                    state: task.state,
                    assignee_actor_id: task.assignee_actor_id,
                    assignee_actor_type: task.assignee_actor_type,
                    owner_role: task.owner_role,
                    candidate_roles: task.candidate_roles ?? [],
                    linked_approval_id: task.linked_approval_id,
                    blocked_on_kind: task.blocked_on_kind,
                    blocked_on_ref: task.blocked_on_ref,
                    available_actions: task.available_actions ?? [],
                    blocking_reason_codes: task.blocking_reason_codes ?? [],
                    missing_required_inputs: task.missing_required_inputs ?? []
                  },
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
                })
              }
            />
          );
        })}
      </div>
    </section>
  );
}
