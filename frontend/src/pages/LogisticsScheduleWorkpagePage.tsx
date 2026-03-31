import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import { ScheduleArtifactAdvancedInfo } from "@/components/workpages/ScheduleArtifactAdvancedInfo";
import { ScheduleHeatmapEditor } from "@/components/workpages/ScheduleHeatmapEditor";
import {
  WorkpageFrame,
  WorkpageHistorySection,
  WorkpageNotePanelSection,
  WorkpageSummaryCardsSection,
  WorkpageTableSection
} from "@/components/workpages/WorkpageContent";
import { WorkpageFormSection } from "@/components/workpages/WorkpageFormSection";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { isApiClientError } from "@/lib/api/httpClient";
import { workpagesRepository } from "@/lib/repositories";
import type { ArtifactVersionRow, WorkpageContract } from "@/lib/types/contracts";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import { resolveWorkpageSubjectContext } from "@/lib/workspace/workpageSubjectContext";
import type {
  WorkpageFormSection as WorkpageFormSectionModel,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageScheduleHeatmapSection as WorkpageScheduleHeatmapSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableRow,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";
import {
  buildEditableSectionResetKey,
  buildFormState,
  type WorkpageFormState
} from "@/lib/workpages/state";

function findTableSection(
  sections: WorkpageTableSectionModel[],
  tableId: string
): WorkpageTableSectionModel | null {
  return sections.find((section) => section.table_id === tableId) ?? null;
}

function findHeatmapSection(
  sections: WorkpageContract["workpage"]["sections"]
): WorkpageScheduleHeatmapSectionModel | null {
  return (
    sections.find(
      (section): section is WorkpageScheduleHeatmapSectionModel => section.kind === "schedule_heatmap"
    ) ?? null
  );
}

function buildTableSectionResetKey(
  contract: WorkpageContract,
  section: WorkpageTableSectionModel
): string {
  return [
    contract.workpage.workpage_id,
    contract.workpage.version,
    contract.freshness.source_version,
    section.table_id,
    section.columns.map((column) => column.key).join(","),
    section.rows.length
  ].join("|");
}

function scheduleLandingRoute(workflowRunId?: string): string {
  return workflowRunId
    ? `/runs/${workflowRunId}/workpages/schedule-v0`
    : "/demo/logistics/workpages/schedule-v0";
}

function scheduleArtifactRoute(artifactVersionId: string, workflowRunId?: string): string {
  return `/runs/${workflowRunId ?? "unknown"}/workpages/schedule-v0/artifacts/${artifactVersionId}`;
}

function workpageBackRoute(workflowRunId?: string): { href: string; label: string } {
  return workflowRunId
    ? { href: `/runs/${workflowRunId}`, label: "Back to run detail" }
    : { href: "/demo/logistics", label: "Back to logistics demo" };
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function workpageConflictDetails(error: unknown): {
  artifactVersionId: string;
  latestArtifactVersionId: string;
  workflowRunId: string;
  route: string;
} | null {
  if (!isApiClientError(error) || error.code !== "workpage_artifact_conflict" || !error.details) {
    return null;
  }
  const artifactVersionId = asString(error.details.artifact_version_id);
  const latestArtifactVersionId = asString(error.details.latest_artifact_version_id);
  const workflowRunId = asString(error.details.workflow_run_id);
  const route = asString(error.details.route);
  if (!artifactVersionId || !latestArtifactVersionId || !workflowRunId || !route) {
    return null;
  }
  return {
    artifactVersionId,
    latestArtifactVersionId,
    workflowRunId,
    route
  };
}

function useEditableScheduleArtifactRows(
  contract: WorkpageContract | undefined,
  assignmentSection: WorkpageTableSectionModel | null,
  reserveSection: WorkpageTableSectionModel | null
): {
  assignmentRows: WorkpageTableRow[];
  setAssignmentRows: Dispatch<SetStateAction<WorkpageTableRow[]>>;
  reserveRows: WorkpageTableRow[];
  setReserveRows: Dispatch<SetStateAction<WorkpageTableRow[]>>;
} {
  const [assignmentRows, setAssignmentRows] = useState<WorkpageTableRow[]>([]);
  const [reserveRows, setReserveRows] = useState<WorkpageTableRow[]>([]);
  const lastResetKeyRef = useRef<string | null>(null);
  const resetKey = useMemo(() => {
    if (!contract || !assignmentSection || !reserveSection) {
      return null;
    }
    return [
      contract.freshness.source_version,
      contract.artifact_context?.artifact_version_id ?? "",
      buildTableSectionResetKey(contract, assignmentSection),
      buildTableSectionResetKey(contract, reserveSection)
    ].join(":");
  }, [contract, assignmentSection, reserveSection]);

  useEffect(() => {
    if (!assignmentSection || !reserveSection || !resetKey) {
      lastResetKeyRef.current = null;
      setAssignmentRows([]);
      setReserveRows([]);
      return;
    }
    if (lastResetKeyRef.current === resetKey) {
      return;
    }
    lastResetKeyRef.current = resetKey;
    setAssignmentRows(assignmentSection.rows.map((row) => ({ ...row })));
    setReserveRows(reserveSection.rows.map((row) => ({ ...row })));
  }, [assignmentSection, reserveSection, resetKey]);

  return {
    assignmentRows,
    setAssignmentRows,
    reserveRows,
    setReserveRows
  };
}

interface LogisticsScheduleWorkpageViewProps {
  contract: WorkpageContract;
  sourceDescription: string;
  summaryLabel: string;
  testId: string;
  backLink?: string;
  backLabel?: string;
  heroActions?: ReactNode;
  preContent?: ReactNode;
  onRefresh: () => void;
  isRefreshing: boolean;
}

function LogisticsScheduleWorkpageView({
  contract,
  sourceDescription,
  summaryLabel,
  testId,
  backLink,
  backLabel,
  heroActions,
  preContent,
  onRefresh,
  isRefreshing
}: LogisticsScheduleWorkpageViewProps): JSX.Element {
  const model = contract.workpage;
  const summarySection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageSummaryCardsSectionModel => section.kind === "summary_cards"
      ) ?? null,
    [model]
  );
  const noteSection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageNotePanelSectionModel => section.kind === "note_panel"
      ) ?? null,
    [model]
  );
  const historySection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageHistorySectionModel => section.kind === "history_stub"
      ) ?? null,
    [model]
  );
  const tableSections = useMemo(
    () =>
      model.sections.filter(
        (section): section is WorkpageTableSectionModel => section.kind === "table"
      ) ?? [],
    [model]
  );
  const formSection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageFormSectionModel => section.kind === "form"
      ) ?? null,
    [model]
  );
  const [formState, setFormState] = useState<WorkpageFormState>({});
  const lastFormResetKeyRef = useRef<string | null>(null);
  const formResetKey = useMemo(() => {
    if (!contract || !formSection) {
      return null;
    }
    return buildEditableSectionResetKey(contract.workpage, contract.freshness.source_version, formSection);
  }, [contract, formSection]);

  useEffect(() => {
    if (!formSection || !formResetKey) {
      lastFormResetKeyRef.current = null;
      setFormState({});
      return;
    }
    if (lastFormResetKeyRef.current === formResetKey) {
      return;
    }
    lastFormResetKeyRef.current = formResetKey;
    setFormState(buildFormState(formSection));
  }, [formResetKey, formSection]);

  return (
    <WorkpageFrame
      eyebrow="Weekly Planning Review"
      description="A workflow-backed weekly planning review for bounded what-if exploration and draft-artifact handoff."
      summaryItems={[
        `Week ${String(model.summary.planning_week_id ?? "unknown")}`,
        String(model.summary.operational_week_start ?? "unknown"),
        String(model.summary.station_code ?? model.summary.source_bundle_id ?? "—"),
        summaryLabel
      ]}
      model={model}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={onRefresh}
      isRefreshing={isRefreshing}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId={testId}
      metadataPresentation="dialog"
      infoDialogTitle="Weekly planning context"
      sourceDescription={sourceDescription}
      heroActions={heroActions}
      infoDialogContent={
        <>
          {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
          {historySection ? <WorkpageHistorySection section={historySection} /> : null}
        </>
      }
      backLink={backLink}
      backLabel={backLabel}
    >
      {preContent}

      {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}

      {findTableSection(tableSections, "day_demand") ? (
        <WorkpageTableSection section={findTableSection(tableSections, "day_demand") as WorkpageTableSectionModel} />
      ) : null}

      {findTableSection(tableSections, "selected_day_preview") ? (
        <WorkpageTableSection
          section={findTableSection(tableSections, "selected_day_preview") as WorkpageTableSectionModel}
        />
      ) : null}

      {findTableSection(tableSections, "driver_roster") ? (
        <WorkpageTableSection section={findTableSection(tableSections, "driver_roster") as WorkpageTableSectionModel} />
      ) : null}

      {formSection ? (
        <WorkpageFormSection
          section={formSection}
          values={formState}
          onChange={(fieldKey, value) => {
            setFormState((current) => ({
              ...current,
              [fieldKey]: value
            }));
          }}
        />
      ) : null}
    </WorkpageFrame>
  );
}

export function LogisticsScheduleWorkpagePage(): JSX.Element {
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  const isRunBacked = Boolean(workflowRunId);
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0", "landing", workflowRunId ?? "demo"],
    queryFn: () =>
      workflowRunId
        ? workpagesRepository.scheduleForRun(workflowRunId)
        : workpagesRepository.schedule(),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const historyQuery = useQuery({
    queryKey: ["workpages", "schedule-v0", "history", workflowRunId],
    queryFn: () => workpagesRepository.listScheduleDraftHistory(workflowRunId ?? ""),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading schedule workpage"
        detail={
          isRunBacked
            ? "Fetching the workflow-run-backed schedule workpage."
            : "Fetching the backend demo workpage query."
        }
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage failed to load"
        detail={errorText(
          query.error,
          isRunBacked
            ? "Unable to load the workflow-run-backed schedule workpage."
            : "Unable to load the schedule workpage demo query."
        )}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const latestDraft = historyQuery.data?.[0] ?? null;
  const backRoute = workpageBackRoute(workflowRunId);

  return (
    <LogisticsScheduleWorkpageView
      contract={query.data}
      testId="schedule-workpage-page"
      sourceDescription={
        isRunBacked
          ? "Workflow-run-backed schedule projection served from canonical weekly Stage04 source artifacts."
          : "Backend demo query served from repo-native workflow example bundles."
      }
      summaryLabel={isRunBacked ? "Run-backed preview" : "Query preview"}
      backLink={backRoute.href}
      backLabel={backRoute.label}
      onRefresh={() => {
        void query.refetch();
        if (workflowRunId) {
          void historyQuery.refetch();
        }
      }}
      isRefreshing={query.isFetching || historyQuery.isFetching}
      preContent={
        isRunBacked ? (
          <>
            {historyQuery.isError ? (
              <StatePanel
                kind="error"
                title="Latest draft lookup failed"
                detail={errorText(
                  historyQuery.error,
                  "Unable to resolve the latest schedule draft artifact for this run."
                )}
              />
            ) : null}
            {!historyQuery.isError && historyQuery.isLoading ? (
              <section className="workpage-panel workpage-panel--callout">
                <header className="workpage-panel__header">
                  <h2>Checking for editable draft</h2>
                  <p>Resolving the latest Stage04 draft weekly schedule artifact for this run.</p>
                </header>
              </section>
            ) : null}
            {!historyQuery.isError && !historyQuery.isLoading && latestDraft ? (
              <section className="workpage-panel workpage-panel--callout">
                <header className="workpage-panel__header">
                  <h2>Editable draft available</h2>
                  <p>
                    This landing page remains the canonical review surface. Reopen the newest
                    Stage04 draft workbook artifact when you need bounded draft edits.
                  </p>
                </header>
                <div className="action-cluster">
                  <Link
                    className="link-button"
                    to={scheduleArtifactRoute(latestDraft.artifact_version_id, workflowRunId)}
                  >
                    Open editable draft
                  </Link>
                </div>
              </section>
            ) : null}
            {!historyQuery.isError && !historyQuery.isLoading && !latestDraft ? (
              <section className="workpage-panel workpage-panel--callout">
                <header className="workpage-panel__header">
                  <h2>No editable draft artifact yet</h2>
                  <p>
                    The Stage04 draft weekly schedule artifact is not available for this run yet.
                    Stay on the landing page until the canonical draft artifact exists.
                  </p>
                </header>
              </section>
            ) : null}
          </>
        ) : null
      }
    />
  );
}

export function LogisticsScheduleArtifactWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [pendingNavigationRoute, setPendingNavigationRoute] = useState<string | null>(null);
  const { artifactVersionId, workflowRunId } = useParams<{
    artifactVersionId: string;
    workflowRunId: string;
  }>();
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () => workpagesRepository.scheduleArtifact(artifactVersionId ?? ""),
    enabled: Boolean(artifactVersionId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const artifactWorkflowRunId = workflowRunId ?? query.data?.artifact_context?.workflow_run_id ?? "";
  const historyQuery = useQuery({
    queryKey: ["workpages", "schedule-v0", "history", artifactWorkflowRunId],
    queryFn: () => workpagesRepository.listScheduleDraftHistory(artifactWorkflowRunId),
    enabled: artifactWorkflowRunId.length > 0,
    refetchInterval: apiConfig.pollIntervalMs
  });

  const model = query.data?.workpage;
  const summarySection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageSummaryCardsSectionModel => section.kind === "summary_cards"
      ) ?? null,
    [model]
  );
  const noteSection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageNotePanelSectionModel => section.kind === "note_panel"
      ) ?? null,
    [model]
  );
  const historySection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageHistorySectionModel => section.kind === "history_stub"
      ) ?? null,
    [model]
  );
  const heatmapSection = useMemo(() => (model ? findHeatmapSection(model.sections) : null), [model]);
  const tableSections = useMemo(
    () =>
      model?.sections.filter(
        (section): section is WorkpageTableSectionModel => section.kind === "table"
      ) ?? [],
    [model]
  );
  const dayDemandSection = useMemo(
    () => findTableSection(tableSections, "day_demand"),
    [tableSections]
  );
  const selectedDaySection = useMemo(
    () => findTableSection(tableSections, "selected_day_preview"),
    [tableSections]
  );
  const driverRosterSection = useMemo(
    () => findTableSection(tableSections, "driver_roster"),
    [tableSections]
  );
  const assignmentSection = useMemo(
    () => findTableSection(tableSections, "assignment_rows"),
    [tableSections]
  );
  const reserveSection = useMemo(
    () => findTableSection(tableSections, "reserve_rows"),
    [tableSections]
  );
  const iterationSection = useMemo(
    () => findTableSection(tableSections, "iteration_deltas"),
    [tableSections]
  );
  const { assignmentRows, setAssignmentRows, reserveRows, setReserveRows } =
    useEditableScheduleArtifactRows(query.data, assignmentSection, reserveSection);
  const submitMutation = useMutation({
    mutationFn: () =>
      workpagesRepository.submitScheduleArtifact(artifactVersionId ?? "", {
        rows: assignmentRows,
        reserveRows
      }, resolveWorkpageSubjectContext(location.state, { workflowRunId: artifactWorkflowRunId })),
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      setPendingNavigationRoute(submitted.route);
    }
  });
  const downloadMutation = useMutation({
    mutationFn: (currentArtifactVersionId: string) =>
      workpagesRepository.downloadScheduleArtifactJson(currentArtifactVersionId)
  });

  useEffect(() => {
    if (!pendingNavigationRoute) {
      return;
    }
    navigate(pendingNavigationRoute, { state: location.state });
    setPendingNavigationRoute(null);
  }, [location.state, navigate, pendingNavigationRoute]);

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading schedule draft artifact"
        detail="Fetching the immutable Stage04 draft weekly schedule artifact projection."
      />
    );
  }

  if (
    query.isError ||
    !query.data ||
    !artifactVersionId ||
    !heatmapSection ||
    !assignmentSection ||
    !reserveSection ||
    !iterationSection
  ) {
    return (
      <StatePanel
        kind="error"
        title="Schedule draft artifact failed to load"
        detail={errorText(query.error, "Unable to load the artifact-backed schedule draft.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const contract = query.data;
  const artifactContext = contract.artifact_context;
  const latestArtifactVersionId =
    artifactContext?.latest_in_chain_artifact_version_id ?? artifactVersionId;
  const latestRoute = scheduleArtifactRoute(latestArtifactVersionId, workflowRunId);
  const recentDraftHistory: ArtifactVersionRow[] = historyQuery.data ?? [];
  const isStaleArtifact = latestArtifactVersionId !== artifactVersionId;
  const submitConflict = workpageConflictDetails(submitMutation.error);
  const staleOrConflictRoute = submitConflict?.route ?? (isStaleArtifact ? latestRoute : null);
  const backRoute = workpageBackRoute(workflowRunId);

  return (
    <WorkpageFrame
      eyebrow="Weekly Schedule Draft Artifact"
      description="A bounded Stage04 draft workbook edit lane. Submit creates a new immutable draft weekly schedule artifact version without publishing or crossing into live dispatch."
      summaryItems={[
        `Week ${String(contract.workpage.summary.planning_week_id ?? "unknown")}`,
        `Artifact ${artifactVersionId}`,
        `${String(contract.workpage.summary.route_assignment_count ?? 0)} assignments`,
        String(contract.workpage.summary.source_bundle_id ?? "—")
      ]}
      model={contract.workpage}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={() => {
        void query.refetch();
        if (artifactWorkflowRunId.length > 0) {
          void historyQuery.refetch();
        }
      }}
      isRefreshing={
        query.isFetching || historyQuery.isFetching || submitMutation.isPending || downloadMutation.isPending
      }
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId="schedule-artifact-workpage-page"
      metadataPresentation="dialog"
      infoDialogTitle="Schedule draft context"
      sourceDescription="Artifact-backed projection of an immutable Stage04 draft weekly schedule workbook. Submit creates a new superseding schedule draft artifact version."
      heroActions={
        <>
          <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
            Back to query landing
          </Link>
          <button
            type="button"
            className="action-btn"
            disabled={downloadMutation.isPending}
            onClick={() => downloadMutation.mutate(artifactVersionId)}
          >
            {downloadMutation.isPending ? "Downloading draft JSON..." : "Download draft JSON"}
          </button>
        </>
      }
      infoDialogContent={
        <ScheduleArtifactAdvancedInfo
          noteSection={noteSection}
          historySection={historySection}
          assignmentSection={assignmentSection}
          reserveSection={reserveSection}
          iterationSection={iterationSection}
          artifactContext={artifactContext}
          artifactRouteFor={(nextArtifactVersionId) =>
            scheduleArtifactRoute(nextArtifactVersionId, workflowRunId)
          }
        />
      }
      backLink={backRoute.href}
      backLabel={backRoute.label}
    >
      {submitConflict ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Latest draft already exists</h2>
            <p>
              This base schedule artifact has already been superseded. Keep your local edits for
              now, then reopen the latest draft artifact before submitting again.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={submitConflict.route}>
              Open latest draft
            </Link>
          </div>
        </section>
      ) : null}

      {!submitConflict && isStaleArtifact && staleOrConflictRoute ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Latest draft available</h2>
            <p>
              This artifact version is no longer the latest draft in the chain. Reopen the latest
              version before submitting more changes.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={staleOrConflictRoute}>
              Open latest draft
            </Link>
          </div>
        </section>
      ) : null}

      {submitMutation.isError && !submitConflict ? (
        <StatePanel
          kind="error"
          title="Draft submit failed"
          detail={errorText(submitMutation.error, "Unable to submit the artifact-backed schedule draft.")}
        />
      ) : null}

      {downloadMutation.isError ? (
        <StatePanel
          kind="error"
          title="Draft JSON download failed"
          detail={errorText(downloadMutation.error, "Unable to download the schedule draft artifact.")}
        />
      ) : null}

      <section className="workpage-panel workpage-panel--callout">
        <header className="workpage-panel__header">
          <h2>Draft actions</h2>
          <p>
            Submit creates a new immutable `planning.draft_weekly_schedule.workbook` version in the
            same run lineage. No publish, pointer promotion, or daily-dispatch materialization
            happens from this surface.
          </p>
        </header>
        <div className="action-cluster">
          <button
            type="button"
            className="action-btn action-btn--positive"
            disabled={submitMutation.isPending || isStaleArtifact}
            onClick={() => submitMutation.mutate()}
          >
            {submitMutation.isPending ? "Submitting draft..." : "Submit draft"}
          </button>
        </div>
      </section>

      {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}

      <ScheduleHeatmapEditor
        section={heatmapSection}
        assignmentRows={assignmentRows}
        reserveRows={reserveRows}
        onRowsChange={({ assignmentRows: nextAssignmentRows, reserveRows: nextReserveRows }) => {
          setAssignmentRows(nextAssignmentRows);
          setReserveRows(nextReserveRows);
        }}
      />

      {dayDemandSection ? <WorkpageTableSection section={dayDemandSection} /> : null}

      {selectedDaySection ? <WorkpageTableSection section={selectedDaySection} /> : null}

      {driverRosterSection ? <WorkpageTableSection section={driverRosterSection} /> : null}

      {artifactContext ? (
        <section className="workpage-panel">
          <header className="workpage-panel__header">
            <h2>Recent draft versions</h2>
            <p>
              Recent immutable `planning.draft_weekly_schedule.workbook` versions for this weekly
              planning run. Reopen adjacent draft states without leaving the schedule workpage
              surface.
            </p>
          </header>

          {historyQuery.isError ? (
            <section className="workpage-panel workpage-panel--callout">
              <header className="workpage-panel__header">
                <h2>Recent draft history unavailable</h2>
                <p>
                  {errorText(
                    historyQuery.error,
                    "Unable to load recent schedule draft history for this run."
                  )}
                </p>
              </header>
            </section>
          ) : null}

          {!historyQuery.isError && historyQuery.isLoading ? (
            <p>Loading recent draft history…</p>
          ) : null}

          {!historyQuery.isError && !historyQuery.isLoading && recentDraftHistory.length === 0 ? (
            <p>No recent schedule draft versions found for this run.</p>
          ) : null}

          {!historyQuery.isError && recentDraftHistory.length > 0 ? (
            <div className="workpage-history">
              {recentDraftHistory.map((artifact) => {
                const route = scheduleArtifactRoute(artifact.artifact_version_id, workflowRunId);
                const isCurrent = artifact.artifact_version_id === artifactVersionId;
                const isLatest = artifact.artifact_version_id === latestArtifactVersionId;
                const label = isCurrent
                  ? "Open current draft"
                  : isLatest
                    ? "Open latest draft"
                    : "Open draft";
                return (
                  <article
                    key={artifact.artifact_version_id}
                    className="workpage-history__item"
                    data-testid={`schedule-draft-history-${artifact.artifact_version_id}`}
                  >
                    <strong>{artifact.artifact_version_id}</strong>
                    <p>{artifact.created_at}</p>
                    <p>{artifact.lineage_note ?? "Schedule draft artifact version."}</p>
                    <div className="action-cluster">
                      <Link className="link-button" to={route}>
                        {label}
                      </Link>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </section>
      ) : null}
    </WorkpageFrame>
  );
}
