import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type Dispatch, type SetStateAction, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import {
  WorkpageFrame,
  WorkpageHistorySection,
  WorkpageNotePanelSection,
  WorkpageSummaryCardsSection
} from "@/components/workpages/WorkpageContent";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { workpagesRepository } from "@/lib/repositories";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import { replaceWorkpageActionRefArtifactVersionId } from "@/lib/workspace/workpageActionRef";
import type { WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageArtifactHistory,
  WorkpageDriverPreferencesAction,
  WorkpageDriverPreferencesDriverRow,
  WorkpageDriverPreferencesGrid,
  WorkpageDriverPreferencesScheduleImpact,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel
} from "@/lib/types/workpages";

const PREFERENCE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "", label: "Unset" },
  { value: "open_to_work", label: "Open to work" },
  { value: "prefer_not_to_work", label: "Prefer not to work" },
  { value: "definitely_can_not_work", label: "Definitely cannot work" }
];

function driverPreferencesLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/driver-preferences-v0`;
}

function scheduleLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0`;
}

function scheduleArtifactRoute(workflowRunId: string, artifactVersionId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`;
}

function workpageBackRoute(workflowRunId?: string): { href: string; label: string } {
  return workflowRunId
    ? { href: `/runs/${workflowRunId}`, label: "Back to run detail" }
    : { href: "/demo/logistics", label: "Back to logistics demo" };
}

function findSummarySection(
  sections: WorkpageContract["workpage"]["sections"]
): WorkpageSummaryCardsSectionModel | null {
  return (
    sections.find(
      (section): section is WorkpageSummaryCardsSectionModel => section.kind === "summary_cards"
    ) ?? null
  );
}

function findNoteSection(
  sections: WorkpageContract["workpage"]["sections"]
): WorkpageNotePanelSectionModel | null {
  return (
    sections.find(
      (section): section is WorkpageNotePanelSectionModel => section.kind === "note_panel"
    ) ?? null
  );
}

function findHistorySection(
  sections: WorkpageContract["workpage"]["sections"]
): WorkpageHistorySectionModel | null {
  return (
    sections.find(
      (section): section is WorkpageHistorySectionModel => section.kind === "history_stub"
    ) ?? null
  );
}

function findDriverPreferencesAction(
  contract: WorkpageContract | undefined,
  matcher: (action: WorkpageDriverPreferencesAction) => boolean
): WorkpageDriverPreferencesAction | null {
  const match =
    contract?.actions.find(
      (action) =>
        action.workpage_kind === "driver-preferences-v0" &&
        matcher(action as WorkpageDriverPreferencesAction)
    ) ?? null;
  return match ? (match as WorkpageDriverPreferencesAction) : null;
}

function driverRowsSignature(rows: WorkpageDriverPreferencesDriverRow[]): string {
  return JSON.stringify(
    rows.map((row) => ({
      driver_id: row.driver_id,
      preferences_by_weekday: row.preferences_by_weekday
    }))
  );
}

function useEditableDriverPreferencesGrid(
  contract: WorkpageContract | undefined
): {
  driverRows: WorkpageDriverPreferencesDriverRow[];
  setDriverRows: Dispatch<SetStateAction<WorkpageDriverPreferencesDriverRow[]>>;
} {
  const [driverRows, setDriverRows] = useState<WorkpageDriverPreferencesDriverRow[]>([]);
  const resetKey = useMemo(
    () =>
      [
        contract?.freshness.source_version ?? "",
        contract?.artifact_context?.artifact_version_id ?? "",
        driverRowsSignature(contract?.preference_grid?.drivers ?? [])
      ].join(":"),
    [contract]
  );

  useEffect(() => {
    setDriverRows((contract?.preference_grid?.drivers ?? []).map((row) => ({
      ...row,
      preferences_by_weekday: { ...row.preferences_by_weekday }
    })));
  }, [contract, resetKey]);

  return { driverRows, setDriverRows };
}

function DriverPreferencesScheduleImpactBanner({
  scheduleImpact,
  workflowRunId
}: {
  scheduleImpact: WorkpageDriverPreferencesScheduleImpact | null;
  workflowRunId: string;
}): JSX.Element | null {
  if (!scheduleImpact) {
    return null;
  }
  const latestScheduleDraftArtifactVersionId =
    scheduleImpact.latest_schedule_draft_artifact_version_id;
  const scheduleDraftRoute =
    latestScheduleDraftArtifactVersionId
      ? scheduleArtifactRoute(workflowRunId, latestScheduleDraftArtifactVersionId)
      : null;
  const stateCopy: Record<string, { title: string; detail: string }> = {
    aligned: {
      title: "Latest schedule draft is aligned",
      detail:
        "The latest schedule draft is already pinned to the current advisory preferences snapshot."
    },
    drifted: {
      title: "Latest schedule draft shows soft drift",
      detail:
        "The latest schedule draft still points at an older preferences snapshot. The drift is advisory only."
    },
    not_pinned: {
      title: "Latest schedule draft is not pinned",
      detail:
        "The latest schedule draft does not yet carry a pinned preferences snapshot. Save remains allowed because preferences are soft."
    },
    no_draft: {
      title: "No schedule draft exists yet",
      detail:
        "Preferences snapshots save independently. A schedule draft has not been created for this run yet."
    },
    no_snapshot: {
      title: "No preferences snapshot exists yet",
      detail:
        "Create the first preferences snapshot when the team is ready to record advisory weekly posture."
    }
  };
  const details =
    stateCopy[scheduleImpact.schedule_state] ??
    stateCopy[scheduleImpact.dependency_state] ?? {
      title: "Schedule advisory status available",
      detail: "The backend reported the latest soft dependency posture for this schedule draft."
    };

  return (
    <section className="workpage-panel route-demand-impact-banner" data-testid="driver-preferences-schedule-impact">
      <header className="workpage-panel__header">
        <h2>Schedule impact</h2>
        <p>{details.detail}</p>
      </header>
      <div className="route-demand-impact-banner__grid">
        <article>
          <strong>Status</strong>
          <p>{details.title}</p>
        </article>
        <article>
          <strong>Dependency state</strong>
          <p>{scheduleImpact.dependency_state}</p>
        </article>
        <article>
          <strong>Latest schedule draft</strong>
          <p>{latestScheduleDraftArtifactVersionId ?? "No draft yet"}</p>
        </article>
        <article>
          <strong>Latest snapshot</strong>
          <p>{scheduleImpact.latest_driver_preferences_artifact_version_id ?? "No snapshot yet"}</p>
        </article>
      </div>
      <div className="action-cluster">
        {scheduleDraftRoute ? (
          <Link className="link-button" to={scheduleDraftRoute}>
            Open latest schedule draft
          </Link>
        ) : (
          <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
            Open schedule landing
          </Link>
        )}
      </div>
    </section>
  );
}

function DriverPreferencesHistoryRail({
  artifactHistory,
  currentArtifactVersionId
}: {
  artifactHistory: WorkpageArtifactHistory | null;
  currentArtifactVersionId?: string;
}): JSX.Element {
  const historyEntries = artifactHistory?.entries ?? [];
  return (
    <section className="workpage-panel" data-testid="driver-preferences-history-rail">
      <header className="workpage-panel__header">
        <h2>Recent preferences snapshots</h2>
        <p>The history rail stays within backend-authored immutable driver-preferences snapshot lineage for this weekly run.</p>
      </header>
      {historyEntries.length > 0 ? (
        <div className="route-demand-history-list">
          {historyEntries.map((entry) => {
            const isCurrent = entry.artifact_version_id === currentArtifactVersionId;
            return (
              <Link
                key={entry.artifact_version_id}
                className={`route-demand-history-list__item${
                  isCurrent ? " route-demand-history-list__item--current" : ""
                }`}
                data-testid={`driver-preferences-history-${entry.artifact_version_id}`}
                to={entry.route}
              >
                <strong>{isCurrent ? "Current snapshot" : entry.artifact_version_id}</strong>
                <span>{entry.created_at}</span>
                <span>{entry.lineage_note ?? "Driver-preferences snapshot"}</span>
              </Link>
            );
          })}
        </div>
      ) : (
        <p className="workpage-history__empty">No driver-preferences snapshots are available yet.</p>
      )}
    </section>
  );
}

function DriverPreferencesGridEditor({
  weekdays,
  driverRows,
  setDriverRows,
  readOnly
}: {
  weekdays: WorkpageDriverPreferencesGrid["weekdays"];
  driverRows: WorkpageDriverPreferencesDriverRow[];
  setDriverRows: Dispatch<SetStateAction<WorkpageDriverPreferencesDriverRow[]>>;
  readOnly: boolean;
}): JSX.Element {
  return (
    <section className="workpage-panel" data-testid="driver-preferences-grid">
      <header className="workpage-panel__header">
        <h2>Weekly preference grid</h2>
        <p>Each cell captures weekly day-of-week guidance only. Unset means no recorded preference.</p>
      </header>
      {driverRows.length > 0 ? (
        <div className="workpage-table__wrap">
          <table className="workpage-table">
            <thead>
              <tr>
                <th scope="col">Driver</th>
                {weekdays.map((weekday) => (
                  <th key={weekday} scope="col">
                    {weekday.toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {driverRows.map((row) => (
                <tr key={row.driver_id}>
                  <td>
                    <strong>{row.driver_name}</strong>
                    <div className="schedule-driver-metrics__subtext">
                      {row.driver_id} · {row.employment_type || "Unknown employment"}
                    </div>
                  </td>
                  {weekdays.map((weekday) => (
                    <td key={`${row.driver_id}-${weekday}`}>
                      <select
                        aria-label={`${row.driver_name} ${weekday}`}
                        className="workpage-form__control"
                        disabled={readOnly}
                        value={row.preferences_by_weekday[weekday] ?? ""}
                        onChange={(event) => {
                          const nextValue = event.target.value || null;
                          setDriverRows((currentRows) =>
                            currentRows.map((currentRow) =>
                              currentRow.driver_id === row.driver_id
                                ? {
                                    ...currentRow,
                                    preferences_by_weekday: {
                                      ...currentRow.preferences_by_weekday,
                                      [weekday]: nextValue
                                    }
                                  }
                                : currentRow
                            )
                          );
                        }}
                      >
                        {PREFERENCE_OPTIONS.map((option) => (
                          <option key={option.label} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="workpage-history__empty">No drivers are available in this weekly preferences scope yet.</p>
      )}
    </section>
  );
}

export function LogisticsDriverPreferencesWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  const query = useQuery({
    queryKey: ["workpages", "driver-preferences-v0", "run", workflowRunId],
    queryFn: () => workpagesRepository.driverPreferencesForRun(workflowRunId ?? ""),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const createAction = findDriverPreferencesAction(query.data, (action) => action.kind === "create_snapshot");
  const openLatestAction = findDriverPreferencesAction(query.data, (action) => action.kind === "open_latest");
  const createMutation = useMutation({
    mutationFn: (payload: { createPath: string; actionRef: WorkpageDriverPreferencesAction["action_ref"] }) =>
      workpagesRepository.createWorkpage(payload.createPath, payload.actionRef ?? undefined),
    onSuccess: (created, payload) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, created.workflow_run_id);
      navigate(created.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            payload.actionRef ?? null,
            created.artifact_version_id
          )
        }
      });
    }
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading driver preferences workpage"
        detail="Fetching the workflow-run-backed driver preferences landing page."
      />
    );
  }

  if (query.isError || !query.data || !workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="Driver preferences workpage failed to load"
        detail={errorText(query.error, "Unable to load the workflow-run-backed driver preferences workpage.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const contract = query.data;
  const summarySection = findSummarySection(contract.workpage.sections);
  const noteSection = findNoteSection(contract.workpage.sections);
  const historySection = findHistorySection(contract.workpage.sections);
  const backRoute = workpageBackRoute(workflowRunId);

  return (
    <WorkpageFrame
      eyebrow="Driver Preferences"
      description="A weekly Sunday-Saturday advisory snapshot surface for soft schedule cues and history."
      summaryItems={[
        `Week ${String(contract.workpage.summary.planning_week_id ?? "unknown")}`,
        `${String(contract.workpage.summary.driver_count ?? 0)} drivers`,
        `${String(contract.workpage.summary.explicit_preference_count ?? 0)} recorded preferences`,
        "Run-backed landing"
      ]}
      model={contract.workpage}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching || createMutation.isPending}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId="driver-preferences-workpage-page"
      metadataPresentation="dialog"
      infoDialogTitle="Driver preferences context"
      sourceDescription="Workflow-run-backed landing surface over the latest immutable preferences snapshot when one exists."
      heroSupportText="Preference snapshots stay advisory only and never create refresh tasks."
      heroActions={
        <div className="action-cluster">
          {openLatestAction?.route ? (
            <Link className="link-button" to={openLatestAction.route}>
              Open latest snapshot
            </Link>
          ) : null}
          {createAction?.create_path ? (
            <button
              type="button"
              className="action-btn action-btn--positive"
              disabled={createMutation.isPending}
              onClick={() =>
                createMutation.mutate({
                  createPath: createAction.create_path ?? "",
                  actionRef: createAction.action_ref
                })
              }
            >
              {createMutation.isPending ? "Creating preferences snapshot..." : "Create preferences snapshot"}
            </button>
          ) : null}
          <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
            Open schedule landing
          </Link>
        </div>
      }
      infoDialogContent={
        <>
          {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
          {historySection ? <WorkpageHistorySection section={historySection} /> : null}
        </>
      }
      backLink={backRoute.href}
      backLabel={backRoute.label}
    >
      {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}
      <DriverPreferencesScheduleImpactBanner
        scheduleImpact={contract.schedule_impact as WorkpageDriverPreferencesScheduleImpact | null}
        workflowRunId={workflowRunId}
      />
      <section className="workpage-panel workpage-panel--callout">
        <header className="workpage-panel__header">
          <h2>Snapshot lifecycle</h2>
          <p>
            The first snapshot is created explicitly on demand. New cells start unset and remain advisory only.
          </p>
        </header>
      </section>
    </WorkpageFrame>
  );
}

export function LogisticsDriverPreferencesArtifactWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { workflowRunId, artifactVersionId } = useParams<{
    workflowRunId: string;
    artifactVersionId: string;
  }>();
  const query = useQuery({
    queryKey: ["workpages", "driver-preferences-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () =>
      workpagesRepository.driverPreferencesArtifact(workflowRunId ?? "", artifactVersionId ?? ""),
    enabled: Boolean(workflowRunId && artifactVersionId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const contract = query.data;
  const saveAction = findDriverPreferencesAction(contract, (action) => action.kind === "save");
  const { driverRows, setDriverRows } = useEditableDriverPreferencesGrid(contract);
  const baseSignature = useMemo(
    () => driverRowsSignature(contract?.preference_grid?.drivers ?? []),
    [contract]
  );
  const currentSignature = useMemo(() => driverRowsSignature(driverRows), [driverRows]);
  const hasUnsavedEdits = baseSignature !== currentSignature;
  const submitMutation = useMutation({
    mutationFn: () =>
      workpagesRepository.submitDriverPreferencesArtifactAtPath(
        saveAction?.submit_path ?? "",
        artifactVersionId ?? "",
        {
            driverRows: driverRows.map((row) => ({
              driver_id: row.driver_id,
              preferences_by_weekday: row.preferences_by_weekday
            }))
        },
        saveAction?.action_ref ?? undefined
      ),
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      navigate(submitted.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            saveAction?.action_ref ?? null,
            submitted.artifact_version_id
          )
        }
      });
    }
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading driver preferences snapshot"
        detail="Fetching the immutable driver-preferences snapshot projection."
      />
    );
  }

  if (query.isError || !contract || !workflowRunId || !artifactVersionId) {
    return (
      <StatePanel
        kind="error"
        title="Driver preferences snapshot failed to load"
        detail={errorText(query.error, "Unable to load the artifact-backed driver preferences snapshot.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const summarySection = findSummarySection(contract.workpage.sections);
  const noteSection = findNoteSection(contract.workpage.sections);
  const historySection = findHistorySection(contract.workpage.sections);
  const backRoute = workpageBackRoute(workflowRunId);
  const readOnly = contract.artifact_state?.editable === false || saveAction?.state !== "available";

  return (
    <WorkpageFrame
      eyebrow="Driver Preferences Snapshot"
      description="An artifact-backed weekly advisory snapshot lane with immutable history and explicit save into a new snapshot version."
      summaryItems={[
        `Week ${String(contract.workpage.summary.planning_week_id ?? "unknown")}`,
        `Artifact ${artifactVersionId}`,
        `${String(contract.workpage.summary.driver_count ?? 0)} drivers`,
        readOnly ? "Read-only history" : "Editable snapshot"
      ]}
      model={contract.workpage}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching || submitMutation.isPending}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId="driver-preferences-artifact-workpage-page"
      metadataPresentation="dialog"
      infoDialogTitle="Driver preferences snapshot context"
      sourceDescription="Artifact-backed projection of an immutable weekly advisory preferences snapshot."
      heroTitleActions={
        <button
          type="button"
          className="action-btn action-btn--positive"
          disabled={readOnly || !hasUnsavedEdits || submitMutation.isPending}
          onClick={() => submitMutation.mutate()}
        >
          {submitMutation.isPending ? "Saving snapshot..." : "Save snapshot"}
        </button>
      }
      heroSupportText="Saving creates the next immutable driver-preferences snapshot and leaves schedule truth untouched."
      heroActions={
        <div className="action-cluster">
          <Link className="link-button" to={driverPreferencesLandingRoute(workflowRunId)}>
            Back to preferences landing
          </Link>
          <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
            Open schedule landing
          </Link>
        </div>
      }
      infoDialogContent={
        <>
          {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
          {historySection ? <WorkpageHistorySection section={historySection} /> : null}
        </>
      }
      backLink={backRoute.href}
      backLabel={backRoute.label}
    >
      {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}
      <DriverPreferencesScheduleImpactBanner
        scheduleImpact={contract.schedule_impact as WorkpageDriverPreferencesScheduleImpact | null}
        workflowRunId={workflowRunId}
      />
      <DriverPreferencesGridEditor
        weekdays={contract.preference_grid?.weekdays ?? ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]}
        driverRows={driverRows}
        setDriverRows={setDriverRows}
        readOnly={readOnly}
      />
      <DriverPreferencesHistoryRail
        artifactHistory={contract.artifact_history}
        currentArtifactVersionId={artifactVersionId}
      />
    </WorkpageFrame>
  );
}
