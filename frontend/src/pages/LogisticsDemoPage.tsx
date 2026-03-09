import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { LaneColumn } from "@/components/LaneColumn";
import { StatePanel } from "@/components/StatePanel";
import { WorkflowGraph } from "@/components/WorkflowGraph";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { logisticsStoryRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";
import type {
  LogisticsStoryBoardWorkItem,
  LogisticsThreeWorkflowStoryContract,
  WorkflowWorkspaceFreshness,
  WorkflowWorkspaceGraphEdge,
  WorkflowWorkspaceGraphNode
} from "@/lib/types/contracts";

const DEMO_TABS = ["Logistics Family Process"];
const MODULE_LAYOUT: Record<string, { row: number; column: number; label: string; runGroup: StoryRunGroupKey }> = {
  dispatch_reporting: {
    row: 0,
    column: 0,
    label: "Dispatch Reporting",
    runGroup: "dispatch_reporting"
  },
  weekly_schedule_planning: {
    row: 0,
    column: 1,
    label: "Weekly Schedule Planning",
    runGroup: "weekly_schedule_planning"
  },
  live_dispatch: {
    row: 0,
    column: 2,
    label: "Live Dispatch",
    runGroup: "live_dispatch"
  }
};

const RUN_GROUPS: Array<{ key: StoryRunGroupKey; label: string }> = [
  { key: "dispatch_reporting", label: "Dispatch Reporting" },
  { key: "weekly_schedule_planning", label: "Weekly Schedule Planning" },
  { key: "live_dispatch", label: "Live Dispatch" }
];

type StoryRunGroupKey =
  | "weekly_schedule_planning"
  | "live_dispatch"
  | "dispatch_reporting";

function normalizeStatus(input: string): string {
  return input.trim().toLowerCase();
}

function graphStatusForModule(
  moduleStatus: string,
  runStates: string[]
): WorkflowWorkspaceGraphNode["status"] {
  const normalizedRunStates = runStates.map(normalizeStatus);
  if (
    normalizedRunStates.some((state) =>
      new Set(["open", "ready", "in_progress", "claimed", "pending", "triage", "blocked"]).has(
        state
      )
    )
  ) {
    return "in_progress";
  }
  if (normalizedRunStates.length > 0) {
    return "completed";
  }

  const normalizedModuleStatus = normalizeStatus(moduleStatus);
  if (["blocked", "error", "failed", "warning"].includes(normalizedModuleStatus)) {
    return "warning";
  }
  if (["active", "ready", "enabled"].includes(normalizedModuleStatus)) {
    return "ready";
  }
  return "not_started";
}

function graphNodes(story: LogisticsThreeWorkflowStoryContract): WorkflowWorkspaceGraphNode[] {
  return story.family_graph.modules.map((module, index) => {
    const moduleLayout = MODULE_LAYOUT[module.module_id] ?? {
      row: 0,
      column: index,
      label: module.module_id,
      runGroup: "weekly_schedule_planning" as StoryRunGroupKey
    };
    const runStates = story.linked_workflow_runs[moduleLayout.runGroup].map((run) => run.state);
    return {
      node_id: module.module_id,
      stage_id: module.workflow_id,
      label: moduleLayout.label,
      status: graphStatusForModule(module.status, runStates),
      row: moduleLayout.row,
      column: moduleLayout.column,
      is_blocking: false,
      responsibility_summary:
        runStates.length > 0 ? `${runStates.length} linked run${runStates.length === 1 ? "" : "s"}` : "No linked runs",
      responsibility_detail: module.activation_policy
    };
  });
}

function graphEdges(story: LogisticsThreeWorkflowStoryContract): WorkflowWorkspaceGraphEdge[] {
  return story.family_graph.edges.map((edge) => ({
    edge_id: edge.edge_id,
    from_node_id: edge.source_module_id,
    to_node_id: edge.target_module_id,
    edge_kind: edge.handoff_mode === "notify_only" ? "branch" : "linear",
    label: edge.handoff_mode
  }));
}

function storyFreshness(story: LogisticsThreeWorkflowStoryContract): WorkflowWorkspaceFreshness {
  return {
    status: story.freshness.latest_event_recorded_at ? "fresh" : "unknown",
    as_of: story.freshness.latest_event_recorded_at ?? story.freshness.generated_at,
    note: `story generated at ${story.freshness.generated_at}`
  };
}

function stateBadgeClass(state: string): string {
  const normalized = normalizeStatus(state);
  if (["completed", "responded", "closed", "resolved"].includes(normalized)) {
    return "status-badge status-badge--success";
  }
  if (["open", "claimed", "pending", "triage", "blocked", "ready", "in_progress"].includes(normalized)) {
    return "status-badge status-badge--active";
  }
  return "status-badge status-badge--default";
}

function groupedBoardItems(story: LogisticsThreeWorkflowStoryContract): Map<string, LogisticsStoryBoardWorkItem[]> {
  const byLane = new Map<string, LogisticsStoryBoardWorkItem[]>();
  for (const item of story.board.work_items) {
    const existing = byLane.get(item.lane) ?? [];
    existing.push(item);
    byLane.set(item.lane, existing);
  }
  return byLane;
}

function boardItemMeta(item: LogisticsStoryBoardWorkItem): string {
  if (item.item_type === "human_task") {
    return `${item.stage_id ?? "stage"} · ${item.task_kind ?? "task"}`;
  }
  if (item.item_type === "approval") {
    return `${item.approval_kind ?? "approval"} · ${item.scope_ref ?? "scope"}`;
  }
  return `${item.kind ?? "flag"} · ${item.severity ?? "severity"}`;
}

function boardItemActions(item: LogisticsStoryBoardWorkItem): string {
  if (item.available_actions.length === 0) {
    return "none";
  }
  return item.available_actions.join(", ");
}

export function LogisticsDemoPage(): JSX.Element {
  const { open } = useDrawer();
  const [searchParams] = useSearchParams();
  const planningWeekId = searchParams.get("planning_week_id")?.trim() || "PW-2026-W10";
  const serviceDateId = searchParams.get("service_date_id")?.trim() || undefined;

  const query = useQuery({
    queryKey: ["logistics-demo-story", planningWeekId, serviceDateId],
    queryFn: () =>
      logisticsStoryRepository.view({
        planningWeekId,
        serviceDateId
      }),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const story = query.data;
  const graph = useMemo(
    () =>
      story
        ? {
            nodes: graphNodes(story),
            edges: graphEdges(story)
          }
        : { nodes: [], edges: [] },
    [story]
  );
  const boardItemsByLane = useMemo(() => (story ? groupedBoardItems(story) : new Map()), [story]);
  const sortedBoardLanes = useMemo(
    () => (story ? [...story.board.lanes].sort((left, right) => left.position - right.position) : []),
    [story]
  );

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading logistics demo story"
        detail="Fetching canonical three-workflow story payload."
      />
    );
  }

  if (query.isError) {
    return (
      <StatePanel
        kind="error"
        title="Logistics story failed to load"
        detail={errorText(query.error, "Unable to load logistics three-workflow story")}
        onRetry={() => void query.refetch()}
      />
    );
  }

  if (!story) {
    return <StatePanel kind="empty" title="No logistics story payload available" />;
  }

  return (
    <section className="logistics-demo-page" data-testid="logistics-demo-page">
      <header className="logistics-demo-page__header">
        <div>
          <p className="timeline-page__eyebrow">Primary Operator Entrypoint</p>
          <h2>Logistics Three-Workflow Demo</h2>
          <p>
            Planning week {story.partitions.planning_week_id} · Service dates {story.partitions.service_date_ids.join(", ")}
          </p>
        </div>
      </header>

      <WorkflowGraph
        nodes={graph.nodes}
        edges={graph.edges}
        freshness={storyFreshness(story)}
        latestEventSequence={story.freshness.latest_event_sequence}
        selectedWorkflowTab={DEMO_TABS[0]}
        tabs={DEMO_TABS}
        showStepBadge={false}
      />

      <section className="logistics-demo-page__panel">
        <header className="logistics-demo-page__panel-header">
          <h3>Linked Workflow Runs</h3>
          <p>{story.linked_workflow_runs.summary.weekly_schedule_planning_count + story.linked_workflow_runs.summary.live_dispatch_count + story.linked_workflow_runs.summary.dispatch_reporting_count} runs in story scope</p>
        </header>
        <div className="logistics-demo-page__run-groups">
          {RUN_GROUPS.map((group) => {
            const runs = story.linked_workflow_runs[group.key];
            return (
              <article key={group.key} className="logistics-demo-page__run-group">
                <h4>{group.label}</h4>
                {runs.length === 0 ? <p>No runs linked.</p> : null}
                <ul>
                  {runs.map((run) => (
                    <li key={run.workflow_run_id}>
                      <Link className="link-button" to={`/runs/${run.workflow_run_id}`}>
                        {run.workflow_run_id}
                      </Link>
                      {" "}
                      · {run.state} · {run.partition_key}
                    </li>
                  ))}
                </ul>
              </article>
            );
          })}
        </div>
      </section>

      <section className="logistics-demo-page__panel">
        <header className="logistics-demo-page__panel-header">
          <h3>Unified Action Board</h3>
          <p>{story.board.summary.work_item_count} items across weekly, live, and reporting runs</p>
        </header>
        <div className="board-grid board-grid--story">
          {sortedBoardLanes.map((lane) => {
            const items: LogisticsStoryBoardWorkItem[] = boardItemsByLane.get(lane.lane) ?? [];
            return (
              <LaneColumn key={lane.lane} title={lane.label} count={lane.item_count}>
                {items.length === 0 ? <p className="logistics-demo-page__empty-lane">No work in lane.</p> : null}
                {items.map((item) => (
                  <article key={item.item_id} className="logistics-demo-page__board-item">
                    <header>
                      <h4>{item.title}</h4>
                      <span className={stateBadgeClass(item.state)}>{item.state}</span>
                    </header>
                    <p>{boardItemMeta(item)}</p>
                    <p>{item.workflow_id}</p>
                    <p>Actions: {boardItemActions(item)}</p>
                    {item.item_type === "human_task" ? (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() =>
                          open({
                            title: item.title,
                            subtitle: item.subject_id,
                            description: "Inspect and run task actions in the drawer.",
                            fields: [
                              { label: "Workflow", value: item.workflow_id },
                              { label: "Workflow run", value: item.workflow_run_id }
                            ],
                            task: {
                              human_task_id: item.subject_id,
                              workflow_run_id: item.workflow_run_id,
                              task_run_id: "loading",
                              stage_id: item.stage_id ?? "unknown",
                              task_kind: item.task_kind ?? "unknown",
                              state: item.state,
                              assignee_actor_id: null,
                              assignee_actor_type: null,
                              owner_role: item.owner_role ?? null,
                              available_actions: item.available_actions,
                              blocking_reason_codes: item.blocking_reason_codes,
                              missing_required_inputs: item.missing_required_inputs
                            },
                            artifact_sources: [
                              {
                                workflow_run_id: item.workflow_run_id,
                                subject_kind: "human_task",
                                subject_id: item.subject_id,
                                source_label: "Task attachment"
                              }
                            ]
                          })
                        }
                      >
                        Open task pane
                      </button>
                    ) : null}
                    <Link className="link-button" to={`/runs/${item.workflow_run_id}`}>
                      Open run details
                    </Link>
                  </article>
                ))}
              </LaneColumn>
            );
          })}
        </div>
      </section>

      <section className="logistics-demo-page__insights">
        <article className="logistics-demo-page__panel">
          <header className="logistics-demo-page__panel-header">
            <h3>Official Outputs Summary</h3>
            <p>{story.official_outputs.summary.official_output_artifact_count} official artifacts</p>
          </header>
          <ul className="logistics-demo-page__compact-list">
            {Object.entries(story.official_outputs.summary.artifact_kind_counts).map(([artifactKind, count]) => (
              <li key={artifactKind}>
                {artifactKind}: {count}
              </li>
            ))}
          </ul>
        </article>

        <article className="logistics-demo-page__panel">
          <header className="logistics-demo-page__panel-header">
            <h3>Handoff Activity</h3>
            <p>{story.handoff_activity.summary.edge_execution_count} edge executions</p>
          </header>
          <ul className="logistics-demo-page__compact-list">
            {story.handoff_activity.edges.map((edge) => (
              <li key={edge.edge_id}>
                <strong>{edge.edge_id}</strong>
                {" "}
                · executions {edge.execution_count}
                {" "}
                · coherence failures {edge.coherence_failed_count}
                {" "}
                · statuses{" "}
                {Object.entries(edge.status_counts)
                  .map(([status, count]) => `${status}:${count}`)
                  .join(", ") || "none"}
              </li>
            ))}
          </ul>
        </article>
      </section>
    </section>
  );
}
