import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { LaneColumn } from "@/components/LaneColumn";
import { StatePanel } from "@/components/StatePanel";
import { WorkflowGraph } from "@/components/WorkflowGraph";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { logisticsStoryRepository, workflowRunsRepository } from "@/lib/repositories";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import { useDrawer } from "@/lib/state/drawerContext";
import type {
  LogisticsStoryBoardWorkItem,
  LogisticsStoryFamilyModule,
  LogisticsStoryModuleArtifactRef,
  LogisticsStoryModuleDrilldownRef,
  LogisticsThreeWorkflowStoryContract,
  WorkflowRunRow,
  WorkflowWorkspaceFreshness,
  WorkflowWorkspaceGraphEdge,
  WorkflowWorkspaceGraphNode
} from "@/lib/types/contracts";
import {
  buildStageNodeDrawerPayload,
  graphNodesWithResponsibility,
  workspaceTab
} from "@/lib/workspace/runWorkspaceGraph";

const DEMO_TABS = ["Logistics Family Process"];
const MODULE_LAYOUT: Record<string, { row: number; column: number; label: string }> = {
  dispatch_reporting: {
    row: 0,
    column: 0,
    label: "Dispatch Reporting"
  },
  weekly_schedule_planning: {
    row: 0,
    column: 1,
    label: "Weekly Schedule Planning"
  },
  live_dispatch: {
    row: 0,
    column: 2,
    label: "Live Dispatch"
  }
};

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

function moduleDisplayLabel(module: LogisticsStoryFamilyModule): string {
  return MODULE_LAYOUT[module.module_id]?.label ?? module.module_id;
}

function runRowsForStory(story: LogisticsThreeWorkflowStoryContract): WorkflowRunRow[] {
  return [
    ...story.linked_workflow_runs.dispatch_reporting,
    ...story.linked_workflow_runs.weekly_schedule_planning,
    ...story.linked_workflow_runs.live_dispatch
  ];
}

function moduleRunRefs(module: LogisticsStoryFamilyModule): LogisticsStoryModuleDrilldownRef[] {
  const deduped = new Map<string, LogisticsStoryModuleDrilldownRef>();
  for (const ref of module.drilldown_refs) {
    if (!deduped.has(ref.workflow_run_id)) {
      deduped.set(ref.workflow_run_id, ref);
    }
  }
  return Array.from(deduped.values());
}

function graphNodes(story: LogisticsThreeWorkflowStoryContract): WorkflowWorkspaceGraphNode[] {
  const storyRuns = runRowsForStory(story);
  const runById = new Map(storyRuns.map((run) => [run.workflow_run_id, run]));
  return story.family_graph.modules.map((module, index) => {
    const moduleLayout = MODULE_LAYOUT[module.module_id] ?? {
      row: 0,
      column: index,
      label: module.module_id
    };
    const refs = moduleRunRefs(module);
    const refRunStates = refs
      .map((ref) => runById.get(ref.workflow_run_id)?.state ?? "")
      .filter((state) => state.length > 0);
    const workflowRunStates =
      refRunStates.length > 0
        ? refRunStates
        : storyRuns
            .filter((run) => run.workflow_id === module.workflow_id)
            .map((run) => run.state);
    const runCount = refs.length > 0 ? refs.length : workflowRunStates.length;

    return {
      node_id: module.module_id,
      stage_id: module.workflow_id,
      label: moduleLayout.label,
      status: graphStatusForModule(module.status, workflowRunStates),
      row: moduleLayout.row,
      column: moduleLayout.column,
      is_blocking: false,
      responsibility_summary:
        runCount > 0
          ? `${runCount} linked run${runCount === 1 ? "" : "s"}`
          : "No linked runs",
      responsibility_detail: module.selection_summary || module.activation_policy
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

function artifactLabel(artifactRef: LogisticsStoryModuleArtifactRef): string {
  return artifactRef.label.trim().length > 0 ? artifactRef.label : artifactRef.artifact_version_id;
}

function runRefSummary(
  ref: LogisticsStoryModuleDrilldownRef,
  run: WorkflowRunRow | null
): string {
  if (run) {
    return `${run.workflow_run_id} · ${run.state} · ${run.partition_key}`;
  }
  return `${ref.workflow_run_id} · ${ref.partition_key}`;
}

export function LogisticsDemoPage(): JSX.Element {
  const { open } = useDrawer();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const planningWeekId = searchParams.get("planning_week_id")?.trim() || "PW-2026-W10";
  const serviceDateId = searchParams.get("service_date_id")?.trim() || undefined;
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const [selectedDrilldownRunId, setSelectedDrilldownRunId] = useState<string | null>(null);
  const [selectedDrilldownNodeId, setSelectedDrilldownNodeId] = useState<string | null>(null);
  const [downloadingArtifactVersionId, setDownloadingArtifactVersionId] = useState<string | null>(null);
  const [familyArtifactError, setFamilyArtifactError] = useState<unknown>(null);

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
  const runById = useMemo(() => {
    if (!story) {
      return new Map<string, WorkflowRunRow>();
    }
    return new Map(runRowsForStory(story).map((run) => [run.workflow_run_id, run]));
  }, [story]);
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

  useEffect(() => {
    if (!story) {
      setSelectedModuleId(null);
      return;
    }
    const moduleIds = new Set(story.family_graph.modules.map((module) => module.module_id));
    if (selectedModuleId && moduleIds.has(selectedModuleId)) {
      return;
    }
    setSelectedModuleId(story.family_graph.modules[0]?.module_id ?? null);
  }, [selectedModuleId, story]);

  const selectedModule = useMemo(() => {
    if (!story) {
      return null;
    }
    if (selectedModuleId) {
      return story.family_graph.modules.find((module) => module.module_id === selectedModuleId) ?? null;
    }
    return story.family_graph.modules[0] ?? null;
  }, [selectedModuleId, story]);

  const selectedModuleRefs = useMemo(
    () => (selectedModule ? moduleRunRefs(selectedModule) : []),
    [selectedModule]
  );

  const selectedModuleRuns = useMemo(
    () =>
      selectedModuleRefs.map((ref) => ({
        ref,
        run: runById.get(ref.workflow_run_id) ?? null
      })),
    [runById, selectedModuleRefs]
  );

  const selectedModuleRunIdsKey = useMemo(
    () => selectedModuleRefs.map((ref) => ref.workflow_run_id).join("|"),
    [selectedModuleRefs]
  );

  useEffect(() => {
    const runIds =
      selectedModuleRunIdsKey.trim().length > 0
        ? selectedModuleRunIdsKey.split("|").filter((id) => id.length > 0)
        : [];
    setSelectedDrilldownRunId((current) => {
      if (runIds.length === 0) {
        return null;
      }
      if (runIds.length === 1) {
        return runIds[0];
      }
      if (current && runIds.includes(current)) {
        return current;
      }
      return null;
    });
    setSelectedDrilldownNodeId(null);
    setFamilyArtifactError(null);
  }, [selectedModule?.module_id, selectedModuleRunIdsKey]);

  const drilldownWorkspaceQuery = useQuery({
    queryKey: ["logistics-drilldown-workspace", selectedDrilldownRunId],
    queryFn: () => workflowRunsRepository.workspace(selectedDrilldownRunId as string),
    enabled: Boolean(selectedDrilldownRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const drilldownDetailQuery = useQuery({
    queryKey: ["logistics-drilldown-detail", selectedDrilldownRunId],
    queryFn: () => workflowRunsRepository.detail(selectedDrilldownRunId as string),
    enabled: Boolean(selectedDrilldownRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const drilldownWorkspace = drilldownWorkspaceQuery.data;
  const drilldownDetail = drilldownDetailQuery.data;
  const drilldownGraphNodes = useMemo(() => {
    if (!drilldownWorkspace || !drilldownDetail) {
      return [];
    }
    return graphNodesWithResponsibility(drilldownWorkspace.graph.nodes, drilldownDetail.human_tasks);
  }, [drilldownWorkspace, drilldownDetail]);

  const boardItemsByLane = useMemo(() => (story ? groupedBoardItems(story) : new Map()), [story]);
  const sortedBoardLanes = useMemo(
    () => (story ? [...story.board.lanes].sort((left, right) => left.position - right.position) : []),
    [story]
  );

  const prefetchDrilldown = (workflowRunId: string): void => {
    void queryClient.prefetchQuery({
      queryKey: ["logistics-drilldown-workspace", workflowRunId],
      queryFn: () => workflowRunsRepository.workspace(workflowRunId)
    });
    void queryClient.prefetchQuery({
      queryKey: ["logistics-drilldown-detail", workflowRunId],
      queryFn: () => workflowRunsRepository.detail(workflowRunId)
    });
  };

  const openTaskDrawer = (item: LogisticsStoryBoardWorkItem): void => {
    open({
      title: item.title,
      subtitle: item.subject_id,
      description: "Inspect context and run authoritative task actions without leaving the logistics demo shell.",
      fields: [
        { label: "Workflow", value: item.workflow_id },
        { label: "Workflow run", value: item.workflow_run_id },
        { label: "State", value: item.state },
        { label: "Board lane", value: item.lane },
        { label: "Actions", value: boardItemActions(item) }
      ],
      links: [
        { label: "Open run workspace", to: `/runs/${item.workflow_run_id}/workspace` },
        { label: "Open run detail (secondary)", to: `/runs/${item.workflow_run_id}` }
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
        linked_approval_id: null,
        blocked_on_kind: null,
        blocked_on_ref: null,
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
    });
  };

  const handleDownloadFamilyArtifact = async (
    artifactRef: LogisticsStoryModuleArtifactRef
  ): Promise<void> => {
    setFamilyArtifactError(null);
    setDownloadingArtifactVersionId(artifactRef.artifact_version_id);
    try {
      const downloaded = await onetruthApi.downloadArtifact(artifactRef.artifact_version_id);
      const fileName =
        artifactRef.label && artifactRef.label.length > 0
          ? artifactRef.label
          : artifactRef.artifact_version_id;
      downloadBinaryToFile(downloaded, fileName);
    } catch (error) {
      setFamilyArtifactError(error);
    } finally {
      setDownloadingArtifactVersionId(null);
    }
  };

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
        <div className="logistics-demo-page__header-links">
          <p>Backend demo workpages</p>
          <Link className="link-button" to="/demo/logistics/workpages/schedule-v0">
            Open weekly review workpage
          </Link>
          <Link className="link-button" to="/demo/logistics/workpages/eod-v0">
            Open end-of-day workpage
          </Link>
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
        selectedNodeId={selectedModule?.module_id ?? null}
        onNodeSelect={(node) => {
          setSelectedModuleId(node.node_id);
        }}
      />

      <section className="logistics-demo-page__panel" data-testid="logistics-module-detail-panel">
        <header className="logistics-demo-page__panel-header">
          <h3>Family Node Detail</h3>
          <p>Select a family module to inspect drill-down scope and artifacts</p>
        </header>
        {selectedModule ? (
          <div className="logistics-demo-page__selection-grid">
            <article className="logistics-demo-page__selection-card">
              <h4>{moduleDisplayLabel(selectedModule)}</h4>
              <p>{selectedModule.selection_summary}</p>
              <dl className="logistics-demo-page__selection-fields">
                <div>
                  <dt>Workflow</dt>
                  <dd>{selectedModule.workflow_id}</dd>
                </div>
                <div>
                  <dt>Partition kind</dt>
                  <dd>{selectedModule.partition_kind}</dd>
                </div>
                <div>
                  <dt>Activation policy</dt>
                  <dd>{selectedModule.activation_policy}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>{selectedModule.status}</dd>
                </div>
                <div>
                  <dt>Drill-down mode</dt>
                  <dd>{selectedModule.drilldown_kind}</dd>
                </div>
              </dl>
              <div className="logistics-demo-page__artifact-actions">
                <h5>Family Node Artifacts</h5>
                {selectedModule.artifact_refs.length === 0 ? (
                  <p>No downloadable artifacts linked.</p>
                ) : (
                  <ul>
                    {selectedModule.artifact_refs.map((artifactRef) => (
                      <li key={artifactRef.artifact_version_id}>
                        <button
                          type="button"
                          className="action-btn"
                          onClick={() => void handleDownloadFamilyArtifact(artifactRef)}
                          disabled={downloadingArtifactVersionId === artifactRef.artifact_version_id}
                        >
                          Download {artifactLabel(artifactRef)}
                        </button>
                        <span>{artifactRef.source_label}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {familyArtifactError ? (
                <p className="detail-drawer__error">
                  {errorText(familyArtifactError, "Family artifact download failed")}
                </p>
              ) : null}
            </article>

            <article className="logistics-demo-page__selection-card">
              <h4>Workflow Run Drill-Down</h4>
              {selectedModuleRuns.length === 0 ? <p>No drill-down runs available.</p> : null}
              {selectedModuleRuns.length === 1 ? (
                <div>
                  <p>{runRefSummary(selectedModuleRuns[0].ref, selectedModuleRuns[0].run)}</p>
                  <p>Single linked run selected automatically.</p>
                </div>
              ) : null}
              {selectedModuleRuns.length > 1 ? (
                <div className="logistics-demo-page__run-chooser" aria-label="Run chooser">
                  <p>Choose a workflow run to open drill-down.</p>
                  {selectedModuleRuns.map(({ ref, run }) => (
                    <button
                      key={ref.workflow_run_id}
                      type="button"
                      className={`logistics-demo-page__run-option${selectedDrilldownRunId === ref.workflow_run_id ? " is-selected" : ""}`}
                      aria-pressed={selectedDrilldownRunId === ref.workflow_run_id}
                      onMouseEnter={() => prefetchDrilldown(ref.workflow_run_id)}
                      onFocus={() => prefetchDrilldown(ref.workflow_run_id)}
                      onClick={() => {
                        prefetchDrilldown(ref.workflow_run_id);
                        setSelectedDrilldownRunId(ref.workflow_run_id);
                      }}
                    >
                      {runRefSummary(ref, run)}
                    </button>
                  ))}
                </div>
              ) : null}
              {selectedDrilldownRunId ? (
                <div className="logistics-demo-page__secondary-links">
                  <p>Secondary detail routes</p>
                  <div>
                    <Link className="link-button" to={`/runs/${selectedDrilldownRunId}/workspace`}>
                      Open full workspace
                    </Link>
                    <Link className="link-button" to={`/runs/${selectedDrilldownRunId}`}>
                      Open run detail (secondary)
                    </Link>
                  </div>
                </div>
              ) : null}
            </article>
          </div>
        ) : (
          <p>Select a family node to inspect metadata.</p>
        )}
      </section>

      {selectedDrilldownRunId ? (
        <section className="logistics-demo-page__panel" data-testid="logistics-drilldown-panel">
          <header className="logistics-demo-page__panel-header">
            <h3>Workflow Run Graph Drill-Down</h3>
            <p>{selectedDrilldownRunId}</p>
          </header>
          {drilldownWorkspaceQuery.isLoading || drilldownDetailQuery.isLoading ? (
            <StatePanel
              kind="loading"
              title="Loading workflow drill-down"
              detail="Fetching workflow-run workspace graph projection."
            />
          ) : null}
          {drilldownWorkspaceQuery.isError || drilldownDetailQuery.isError ? (
            <StatePanel
              kind="error"
              title="Workflow drill-down failed to load"
              detail={errorText(
                drilldownWorkspaceQuery.error ?? drilldownDetailQuery.error,
                "Unable to load workflow run workspace"
              )}
              onRetry={() => {
                void drilldownWorkspaceQuery.refetch();
                void drilldownDetailQuery.refetch();
              }}
            />
          ) : null}
          {!drilldownWorkspaceQuery.isLoading &&
          !drilldownDetailQuery.isLoading &&
          !drilldownWorkspaceQuery.isError &&
          !drilldownDetailQuery.isError &&
          drilldownWorkspace &&
          drilldownDetail ? (
            <div data-testid="logistics-demo-drilldown-graph">
              <WorkflowGraph
                nodes={drilldownGraphNodes}
                edges={drilldownWorkspace.graph.edges}
                freshness={drilldownWorkspace.freshness}
                latestEventSequence={drilldownWorkspace.latest_event_sequence}
                selectedWorkflowTab={workspaceTab(drilldownWorkspace.workflow_run.workflow_id)}
                tabs={[workspaceTab(drilldownWorkspace.workflow_run.workflow_id)]}
                showStepBadge={false}
                selectedNodeId={selectedDrilldownNodeId}
                onNodeSelect={(node) => {
                  setSelectedDrilldownNodeId(node.node_id);
                  open(buildStageNodeDrawerPayload(node, drilldownDetail));
                }}
              />
            </div>
          ) : null}
        </section>
      ) : null}

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
                    {item.item_type === "human_task" ? (
                      <button
                        type="button"
                        className="logistics-demo-page__board-item-trigger"
                        onClick={() => openTaskDrawer(item)}
                      >
                        <header>
                          <h4>{item.title}</h4>
                          <span className={stateBadgeClass(item.state)}>{item.state}</span>
                        </header>
                        <p>{boardItemMeta(item)}</p>
                        <p>{item.workflow_id}</p>
                        <p>Actions: {boardItemActions(item)}</p>
                      </button>
                    ) : (
                      <>
                        <header>
                          <h4>{item.title}</h4>
                          <span className={stateBadgeClass(item.state)}>{item.state}</span>
                        </header>
                        <p>{boardItemMeta(item)}</p>
                        <p>{item.workflow_id}</p>
                        <p>Actions: {boardItemActions(item)}</p>
                      </>
                    )}
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
