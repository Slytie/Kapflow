import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { LegacyScheduleNotice } from "@/components/LegacyScheduleNotice";
import { QueueRow } from "@/components/QueueRow";
import { StatePanel } from "@/components/StatePanel";
import { TimelineRow } from "@/components/TimelineRow";
import { useShellFilters } from "@/app/useShellFilters";
import { timelineRepository, workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";
import { buildTaskDocumentPreviewCues } from "@/lib/workspace/taskDocumentUi";
import { taskDisplayHeading } from "@/lib/workspace/taskLabels";

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

  const hasWorkspaceSurface = detail.workflow_run.workflow_id !== "live_dispatch.v1";

  return (
    <section data-testid="run-detail-page">
      <LegacyScheduleNotice surface="Run detail" />
      <header className="run-detail-header">
        <h2>{detail.workflow_run.workflow_run_id}</h2>
        <p>{detail.workflow_run.workflow_id} · {detail.workflow_run.partition_key}</p>
        <div className="run-links">
          <Link className="link-button" to="/demo/logistics">
            Open logistics demo
          </Link>
          {hasWorkspaceSurface ? (
            <Link className="link-button" to={`/runs/${workflowRunId}/workspace`}>
              Open workspace
            </Link>
          ) : null}
          <Link className="link-button" to="/official-outputs">
            Open official outputs
          </Link>
        </div>
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
              title={taskDisplayHeading(task)}
              subtitle={task.human_task_id}
              status={task.state}
              documentCues={buildTaskDocumentPreviewCues(task)}
              onDetails={() =>
                open({
                  title: taskDisplayHeading(task),
                  subtitle: task.human_task_id,
                  description: "Run detail task context opens in the centered task modal.",
                  fields: [
                    { label: "Task run", value: task.task_run_id },
                    { label: "State", value: task.state },
                    { label: "Assignee", value: task.assignee_actor_id ?? "unassigned" }
                  ],
                  task: {
                    human_task_id: task.human_task_id,
                    workflow_run_id: task.workflow_run_id,
                    task_run_id: task.task_run_id,
                    stage_id: task.stage_id,
                    task_kind: task.task_kind,
                    state: task.state,
                    created_at: task.created_at,
                    updated_at: task.updated_at,
                    assignee_actor_id: task.assignee_actor_id,
                    assignee_actor_type: task.assignee_actor_type,
                    owner_role: task.owner_role,
                    candidate_roles: task.candidate_roles ?? [],
                    linked_approval_id: task.linked_approval_id,
                    blocked_on_kind: task.blocked_on_kind,
                    blocked_on_ref: task.blocked_on_ref,
                    available_actions: task.available_actions ?? [],
                    blocking_reason_codes: task.blocking_reason_codes ?? [],
                    missing_required_inputs: task.missing_required_inputs ?? [],
                    required_uploads: task.required_uploads ?? [],
                    required_reviews: task.required_reviews ?? [],
                    workpage_actions: task.workpage_actions ?? [],
                    is_composite: task.is_composite ?? false,
                    expansion_kind: task.expansion_kind ?? "none",
                    subgraph_ref: task.subgraph_ref ?? null
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
