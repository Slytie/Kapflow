import { Link } from "react-router-dom";

import { InfoDialog } from "@/components/InfoDialog";
import { StatePanel } from "@/components/StatePanel";
import {
  artifactLabel,
  moduleDisplayLabel,
  runRefSummary,
  workflowIdToModuleId
} from "@/lib/logistics/familyStory";
import type { LogisticsStoryFamilyModule } from "@/lib/types/contracts";

function canonicalLauncherRoute(input: {
  workflowId: string;
  workflowRunId: string;
}): string {
  if (input.workflowId === "weekly_schedule_planning.v1") {
    return `/runs/${input.workflowRunId}/workpages/schedule-v0`;
  }
  if (input.workflowId === "dispatch_reporting.v1") {
    return `/runs/${input.workflowRunId}/workpages/eod-v0`;
  }
  return `/runs/${input.workflowRunId}/workspace`;
}

function launcherPrimaryLabel(workflowId: string): string {
  if (workflowId === "weekly_schedule_planning.v1") {
    return "Open schedule workpage";
  }
  if (workflowId === "dispatch_reporting.v1") {
    return "Open EOD workpage";
  }
  return "Open full workspace";
}

function launcherDescription(module: LogisticsStoryFamilyModule): string {
  if (module.workflow_id === "weekly_schedule_planning.v1") {
    return "This demo shell now launches the canonical weekly schedule workpage for the selected run instead of editing drafts inline.";
  }
  if (module.workflow_id === "dispatch_reporting.v1") {
    return "This demo shell now launches the canonical end-of-day workpage for the selected run instead of creating or submitting drafts inline.";
  }
  return "This family module stays workspace-first in the current slice. Use the canonical workspace and run detail for intake, review, and approval.";
}

export function LogisticsModuleLauncherCard({
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
  const isWorkspaceFirst = module.workflow_id === "live_dispatch.v1";
  return (
    <section
      className="workpage-panel workpage-panel--note"
      data-testid={`logistics-module-launcher-${moduleId}`}
    >
      <header className="workpage-panel__header">
        <p className="timeline-page__eyebrow">
          {isWorkspaceFirst ? "Workspace-first launcher" : "Canonical launcher"}
        </p>
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
        {isWorkspaceFirst ? null : (
          <Link
            className="link-button"
            to={canonicalLauncherRoute({
              workflowId: module.workflow_id,
              workflowRunId
            })}
          >
            {launcherPrimaryLabel(module.workflow_id)}
          </Link>
        )}
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

interface LogisticsModuleDetailPanelProps {
  selectedModule: LogisticsStoryFamilyModule | null;
  selectedModuleRuns: Array<{ ref: any; run: any }>;
  selectedDrilldownRunId: string | null;
  selectedDrilldownRun: { ref: any; run: any } | null;
  prefetchDrilldown: (workflowRunId: string) => void;
  selectDrilldownRun: (workflowRunId: string) => void;
  openFamilyArtifactDrawer: (module: LogisticsStoryFamilyModule) => void;
}

export function LogisticsModuleDetailPanel({
  selectedModule,
  selectedModuleRuns,
  selectedDrilldownRunId,
  selectedDrilldownRun,
  prefetchDrilldown,
  selectDrilldownRun,
  openFamilyArtifactDrawer
}: LogisticsModuleDetailPanelProps): JSX.Element {
  return (
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
                          View family node artifacts ({selectedModule.artifact_refs.map(artifactLabel).length})
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
                                selectDrilldownRun(ref.workflow_run_id);
                              }}
                            >
                              {runRefSummary(ref, run)}
                            </button>
                          ))}
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
  );
}
