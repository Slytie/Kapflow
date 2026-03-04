import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { QueueRow } from "@/components/QueueRow";
import { StatePanel } from "@/components/StatePanel";
import { TimelineRow } from "@/components/TimelineRow";
import { useShellFilters } from "@/app/useShellFilters";
import { timelineRepository, workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";

type RunTab = "timeline" | "tasks" | "approvals" | "artifacts" | "exceptions";

export function RunDetailPage(): JSX.Element {
  const params = useParams<{ workflowRunId: string }>();
  const { filters } = useShellFilters();
  const { open } = useDrawer();
  const [tab, setTab] = useState<RunTab>("timeline");

  const workflowRunId = params.workflowRunId;

  const detailQuery = useQuery({
    queryKey: ["run-detail", workflowRunId],
    queryFn: () => workflowRunsRepository.detail(workflowRunId),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const timelineQuery = useQuery({
    queryKey: ["run-timeline", workflowRunId, filters.query],
    queryFn: () => timelineRepository.list({ workflowRunId, query: filters.query }),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (!workflowRunId) {
    return <StatePanel kind="empty" title="No workflow run id" detail="Select a run from the runs page." />;
  }

  if (detailQuery.isLoading || timelineQuery.isLoading) {
    return <StatePanel kind="loading" title="Loading run detail" detail="Fetching run detail and timeline." />;
  }

  if (detailQuery.isError) {
    return (
      <StatePanel
        kind="error"
        title="Run detail failed to load"
        detail={errorText(detailQuery.error, "Unable to load workflow run detail")}
        onRetry={() => void detailQuery.refetch()}
      />
    );
  }

  if (timelineQuery.isError) {
    return (
      <StatePanel
        kind="error"
        title="Run timeline failed to load"
        detail={errorText(timelineQuery.error, "Unable to load timeline events")}
        onRetry={() => void timelineQuery.refetch()}
      />
    );
  }

  const detail = detailQuery.data;
  const timeline = timelineQuery.data;

  if (!detail || !timeline) {
    return <StatePanel kind="empty" title="No run detail available" />;
  }

  return (
    <section data-testid="run-detail-page">
      <header className="run-detail-header">
        <h2>{detail.workflow_run.workflow_run_id}</h2>
        <p>{detail.workflow_run.workflow_id} · {detail.workflow_run.partition_key}</p>
      </header>

      <div className="tabs" role="tablist" aria-label="Run detail tabs">
        {(["timeline", "tasks", "approvals", "artifacts", "exceptions"] as RunTab[]).map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={tab === name}
            className={tab === name ? "active" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>

      {tab === "timeline" ? (
        <div className="stack-list">
          {timeline.map((event) => (
            <TimelineRow
              key={event.eventId}
              row={event}
              onDetails={() =>
                open({
                  title: event.eventType,
                  subtitle: event.eventId,
                  description: "Detailed event payload.",
                  fields: [
                    { label: "Sequence", value: String(event.sequenceNo) },
                    { label: "Actor", value: event.actorId },
                    { label: "Subject", value: event.subject }
                  ]
                })
              }
            />
          ))}
        </div>
      ) : null}

      {tab === "tasks" ? (
        <div className="stack-list">
          {detail.human_tasks.map((task) => (
            <QueueRow
              key={task.human_task_id}
              title={`${task.stage_id} · ${task.task_kind}`}
              subtitle={task.human_task_id}
              status={task.state}
              onDetails={() =>
                open({
                  title: `${task.stage_id} ${task.task_kind}`,
                  subtitle: task.human_task_id,
                  fields: [
                    { label: "Task run", value: task.task_run_id },
                    { label: "State", value: task.state },
                    { label: "Assignee", value: task.assignee_actor_id ?? "unassigned" }
                  ]
                })
              }
            />
          ))}
        </div>
      ) : null}

      {tab === "approvals" ? (
        <ul>
          {detail.approvals.map((approval) => (
            <li key={approval.approval_id}>{approval.approval_id} · {approval.state}</li>
          ))}
        </ul>
      ) : null}

      {tab === "artifacts" ? (
        <ul>
          {detail.artifact_versions.map((artifact) => (
            <li key={artifact.artifact_version_id}>{artifact.artifact_kind} · {artifact.artifact_version_id}</li>
          ))}
        </ul>
      ) : null}

      {tab === "exceptions" ? (
        <ul>
          {detail.flags.map((flag) => (
            <li key={flag.flag_id}>{flag.summary} · {flag.severity}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
