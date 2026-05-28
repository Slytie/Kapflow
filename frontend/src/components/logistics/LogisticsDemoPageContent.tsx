import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import { WorkflowGraph } from "@/components/WorkflowGraph";
import { InfoDialog } from "@/components/InfoDialog";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import {
  artifactLabel,
  DEFAULT_LOGISTICS_PLANNING_WEEK_ID,
  moduleDisplayLabel,
  moduleRunRefs,
  normalizedLogisticsDemoRunId,
  runRefSummary,
  runRowsForStory,
  visibleLogisticsFamilyModules,
  workflowIdToModuleId
} from "@/lib/logistics/familyStory";
import { logisticsStoryRepository, workflowRunsRepository } from "@/lib/repositories";
import { useDrawer } from "@/lib/state/drawerContext";
import type { LogisticsStoryFamilyModule } from "@/lib/types/contracts";
import {
  buildStageNodeDrawerPayload,
  graphNodesWithResponsibility,
  workspaceTab
} from "@/lib/workspace/runWorkspaceGraph";

function canonicalLauncherRoute(input: {
  workflowId: string;
  workflowRunId: string;
}): string | null {
  if (input.workflowId === "weekly_schedule_planning.v1") {
    return `/runs/${input.workflowRunId}/workpages/schedule-v0`;
  }
  if (input.workflowId === "dispatch_reporting.v1") {
    return `/runs/${input.workflowRunId}/workpages/eod-v0`;
  }
  return null;
}

function launcherPrimaryLabel(workflowId: string): string | null {
  if (workflowId === "weekly_schedule_planning.v1") {
    return "Open schedule workpage";
  }
  if (workflowId === "dispatch_reporting.v1") {
    return "Open EOD workpage";
  }
  return null;
}

function launcherDescription(module: LogisticsStoryFamilyModule): string {
  if (module.workflow_id === "weekly_schedule_planning.v1") {
    return "This demo shell launches the canonical weekly schedule workpage. If the walkthrough run is still at intake, the shell switches to the review-ready weekly run for schedule and route-demand editing.";
  }
  if (module.workflow_id === "dispatch_reporting.v1") {
    return "This demo shell now launches the canonical end-of-day workpage for the selected run instead of creating or submitting drafts inline.";
  }
  return "This demo shell now launches the canonical workpage for the selected run.";
}

function LogisticsModuleLauncherCard({
  module,
  workflowRunId,
  runSummary,
  runState,
  partitionKey,
  workflowVersion
}: {
  module: LogisticsStoryFamilyModule;
  workflowRunId: string;
  runSummary: string;
  runState: string | null;
  partitionKey: string | null;
  workflowVersion: string | null;
}): JSX.Element {
  const moduleId = workflowIdToModuleId(module.workflow_id) ?? module.module_id;
  const primaryRoute = canonicalLauncherRoute({
    workflowId: module.workflow_id,
    workflowRunId
  });
  const primaryLabel = launcherPrimaryLabel(module.workflow_id);
  return (
    <section
      className="workpage-panel workpage-panel--note"
      data-testid={`logistics-module-launcher-${moduleId}`}
    >
      <header className="workpage-panel__header">
        <p className="timeline-page__eyebrow">Canonical launcher</p>
        <h2>{moduleDisplayLabel(module)}</h2>
        <p>{launcherDescription(module)}</p>
      </header>

      <div className="logistics-demo-page__detail-kpis">
        <span>{runSummary}</span>
        {runState ? <span>{runState}</span> : null}
        {partitionKey ? <span>{partitionKey}</span> : null}
      </div>

      {module.selection_summary.trim().length > 0 ? (
        <p className="logistics-demo-page__dialog-summary-copy">{module.selection_summary}</p>
      ) : null}

      <dl className="logistics-demo-page__selection-fields logistics-demo-page__selection-fields--grid">
        <div>
          <dt>Workflow</dt>
          <dd>{module.workflow_id}</dd>
        </div>
        <div>
          <dt>Workflow run</dt>
          <dd>{workflowRunId}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{runState ?? module.status}</dd>
        </div>
        <div>
          <dt>Version</dt>
          <dd>{workflowVersion ?? "unknown"}</dd>
        </div>
      </dl>

      <div className="action-cluster">
        {primaryRoute && primaryLabel ? (
          <Link
            className="link-button"
            to={primaryRoute}
          >
            {primaryLabel}
          </Link>
        ) : null}
        <Link className="link-button" to={`/runs/${workflowRunId}/workspace`}>
          Open full workspace
        </Link>
        <Link className="link-button" to={`/runs/${workflowRunId}`}>
          Open run detail (secondary)
        </Link>
      </div>
    </section>
  );
}

export function LogisticsDemoPage(): JSX.Element {
  const { open } = useDrawer();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const planningWeekId =
    searchParams.get("planning_week_id")?.trim() || DEFAULT_LOGISTICS_PLANNING_WEEK_ID;
  const serviceDateId = searchParams.get("service_date_id")?.trim() || undefined;
  const [selectedDrilldownNodeId, setSelectedDrilldownNodeId] = useState<string | null>(null);
  const selectedModuleIdParam = searchParams.get("module")?.trim() || null;
  const selectedRunIdParam = searchParams.get("workflow_run_id")?.trim() || null;

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
      return new Map();
    }
    return new Map(runRowsForStory(story).map((run) => [run.workflow_run_id, run]));
  }, [story]);
  const visibleModules = useMemo(
    () => (story ? visibleLogisticsFamilyModules(story) : []),
    [story]
  );

  const selectedModule = useMemo(() => {
    if (!story) {
      return null;
    }
    if (selectedModuleIdParam) {
      return (
        visibleModules.find(
          (module) => module.module_id === selectedModuleIdParam
        ) ??
        visibleModules[0] ??
        null
      );
    }
    return visibleModules[0] ?? null;
  }, [selectedModuleIdParam, story, visibleModules]);

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

  const selectedDrilldownRunId = useMemo(() => {
    return normalizedLogisticsDemoRunId(
      selectedModule,
      selectedModuleRuns,
      selectedRunIdParam
    );
  }, [selectedModule, selectedModuleRuns, selectedRunIdParam]);

  useEffect(() => {
    if (!story || !selectedModule) {
      return;
    }
    const nextParams = new URLSearchParams(searchParams);
    let changed = false;
    if (nextParams.get("planning_week_id") !== planningWeekId) {
      nextParams.set("planning_week_id", planningWeekId);
      changed = true;
    }
    if (nextParams.get("module") !== selectedModule.module_id) {
      nextParams.set("module", selectedModule.module_id);
      changed = true;
    }
    if (selectedDrilldownRunId) {
      if (nextParams.get("workflow_run_id") !== selectedDrilldownRunId) {
        nextParams.set("workflow_run_id", selectedDrilldownRunId);
        changed = true;
      }
    } else if (nextParams.has("workflow_run_id")) {
      nextParams.delete("workflow_run_id");
      changed = true;
    }
    if (changed) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [
    planningWeekId,
    searchParams,
    selectedDrilldownRunId,
    selectedModule,
    setSearchParams,
    story
  ]);

  useEffect(() => {
    setSelectedDrilldownNodeId(null);
  }, [selectedModule?.module_id, selectedDrilldownRunId]);

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

  const selectedDrilldownRun = useMemo(
    () =>
      selectedDrilldownRunId
        ? selectedModuleRuns.find(({ ref }) => ref.workflow_run_id === selectedDrilldownRunId) ?? null
        : null,
    [selectedDrilldownRunId, selectedModuleRuns]
  );

  const prefetchDrilldown = (workflowRunId: string): void => {
    if (!selectedModuleRuns.some(({ ref }) => ref.workflow_run_id === workflowRunId)) {
      return;
    }
    const targetWorkflowRunId =
      normalizedLogisticsDemoRunId(selectedModule, selectedModuleRuns, workflowRunId) ??
      workflowRunId;
    void queryClient.prefetchQuery({
      queryKey: ["logistics-drilldown-workspace", targetWorkflowRunId],
      queryFn: () => workflowRunsRepository.workspace(targetWorkflowRunId)
    });
    void queryClient.prefetchQuery({
      queryKey: ["logistics-drilldown-detail", targetWorkflowRunId],
      queryFn: () => workflowRunsRepository.detail(targetWorkflowRunId)
    });
  };

  const selectDrilldownRun = (workflowRunId: string): void => {
    if (!selectedModuleRuns.some(({ ref }) => ref.workflow_run_id === workflowRunId)) {
      return;
    }
    const targetWorkflowRunId =
      normalizedLogisticsDemoRunId(selectedModule, selectedModuleRuns, workflowRunId) ??
      workflowRunId;
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("planning_week_id", planningWeekId);
    if (selectedModule) {
      nextParams.set("module", selectedModule.module_id);
    }
    nextParams.set("workflow_run_id", targetWorkflowRunId);
    setSearchParams(nextParams);
  };

  const openFamilyArtifactDrawer = (module: LogisticsStoryFamilyModule): void => {
    if (module.artifact_refs.length === 0) {
      return;
    }
    open({
      title: moduleDisplayLabel(module),
      subtitle: "Family node artifacts",
      description: "Download linked family-node artifacts without leaving the logistics demo shell.",
      fields: [
        { label: "Workflow", value: module.workflow_id },
        { label: "Partition kind", value: module.partition_kind },
        { label: "Activation policy", value: module.activation_policy },
        { label: "Status", value: module.status }
      ],
      downloadable_artifacts: module.artifact_refs.map((artifactRef) => ({
        artifact_version_id: artifactRef.artifact_version_id,
        label: artifactLabel(artifactRef),
        source_label: artifactRef.source_label
      }))
    });
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

  if (visibleModules.length === 0) {
    return (
      <StatePanel
        kind="empty"
        title="No logistics demo modules available"
        detail="Weekly Schedule Planning and Dispatch Reporting are the only remaining shell modules."
      />
    );
  }

  return (
    <section className="logistics-demo-page" data-testid="logistics-demo-page">
      <section className="logistics-demo-page__panel" data-testid="logistics-module-detail-panel">
        {selectedModule ? (
          <div className="logistics-demo-page__detail-stack">
            <section className="logistics-demo-page__detail-summary">
              <div className="logistics-demo-page__detail-heading">
                <h4>{moduleDisplayLabel(selectedModule)}</h4>
                <InfoDialog
                  triggerLabel={`Open info for ${moduleDisplayLabel(selectedModule)}`}
                  dialogTitle={`${moduleDisplayLabel(selectedModule)} info`}
                  dialogDescription="Family-node metadata, run drill-down, and artifact access for the selected logistics module."
                >
                  <div className="logistics-demo-page__dialog-stack">
                    <section className="workpage-panel workpage-panel--note">
                      <header className="workpage-panel__header">
                        <h2>Selected module</h2>
                        <p>Summary and technical node metadata for the current family module.</p>
                      </header>
                      {selectedModule.selection_summary.trim().length > 0 ? (
                        <p className="logistics-demo-page__dialog-summary-copy">
                          {selectedModule.selection_summary}
                        </p>
                      ) : null}
                      <div className="logistics-demo-page__detail-kpis">
                        <span>{`${selectedModuleRuns.length} linked run${selectedModuleRuns.length === 1 ? "" : "s"}`}</span>
                        <span>{`${selectedModule.artifact_refs.length} downloadable artifact${selectedModule.artifact_refs.length === 1 ? "" : "s"}`}</span>
                      </div>
                      <dl className="logistics-demo-page__selection-fields logistics-demo-page__selection-fields--grid">
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
                        <div>
                          <dt>Linked runs</dt>
                          <dd>{selectedModuleRuns.length}</dd>
                        </div>
                        <div>
                          <dt>Downloadable artifacts</dt>
                          <dd>{selectedModule.artifact_refs.length}</dd>
                        </div>
                      </dl>
                    </section>

                    <section className="workpage-panel workpage-panel--note">
                      <header className="workpage-panel__header">
                        <h2>Artifacts</h2>
                        <p>Family-level artifacts stay available here without occupying the launcher surface.</p>
                      </header>
                      <div className="logistics-demo-page__artifact-link-section">
                        {selectedModule.artifact_refs.length === 0 ? (
                          <p>No family-node artifacts linked.</p>
                        ) : (
                          <button
                            type="button"
                            className="link-button"
                            onClick={() => openFamilyArtifactDrawer(selectedModule)}
                          >
                            View family node artifacts
                          </button>
                        )}
                      </div>
                    </section>

                    <section className="workpage-panel workpage-panel--note">
                      <header className="workpage-panel__header">
                        <h2>Workflow Run Drill-Down</h2>
                        <p>Choose the linked workflow run that should drive the launcher surface and drill-down graph.</p>
                      </header>
                      <div className="logistics-demo-page__run-drilldown">
                        {selectedModuleRuns.length === 0 ? <p>No drill-down runs available.</p> : null}
                        {selectedModuleRuns.length === 1 ? (
                          <div>
                            <p>{runRefSummary(selectedModuleRuns[0].ref, selectedModuleRuns[0].run)}</p>
                            <p>Single linked run selected automatically.</p>
                          </div>
                        ) : null}
                        {selectedModuleRuns.length > 1 ? (
                          <div className="logistics-demo-page__run-chooser" aria-label="Run chooser">
                            <p>
                              {selectedModule.workflow_id === "weekly_schedule_planning.v1"
                                ? "Choose a workflow run to inspect. Weekly workpages switch to the review-ready run until the walkthrough run has Stage04 outputs."
                                : "Choose a workflow run to open drill-down."}
                            </p>
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
                                  selectDrilldownRun(ref.workflow_run_id);
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
                      </div>
                    </section>
                  </div>
                </InfoDialog>
              </div>
            </section>

            <div className="logistics-demo-page__detail-main">
              {!selectedDrilldownRunId ? (
                <StatePanel
                  kind="empty"
                  title="Choose a workflow run"
                  detail="Pick a linked run in the summary above to load launcher links and drill-down here."
                />
              ) : (
                <LogisticsModuleLauncherCard
                  module={selectedModule}
                  workflowRunId={selectedDrilldownRunId}
                  runSummary={
                    selectedDrilldownRun
                      ? runRefSummary(selectedDrilldownRun.ref, selectedDrilldownRun.run)
                      : selectedDrilldownRunId
                  }
                  runState={selectedDrilldownRun?.run?.state ?? null}
                  partitionKey={
                    selectedDrilldownRun?.run?.partition_key ??
                    selectedDrilldownRun?.ref.partition_key ??
                    null
                  }
                  workflowVersion={selectedDrilldownRun?.run?.workflow_version ?? null}
                />
              )}
            </div>
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
