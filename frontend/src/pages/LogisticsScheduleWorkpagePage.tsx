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
import {
  DraftVersionTimelineEntry,
  draftVersionPrimaryLabel
} from "@/components/workpages/DraftVersionTimeline";
import { ScheduleArtifactAdvancedInfo } from "@/components/workpages/ScheduleArtifactAdvancedInfo";
import {
  ScheduleWorkpageSurface,
  type ScheduleVersionRailDefinition
} from "@/components/workpages/ScheduleWorkpageSurface";
import {
  WorkpageFrame,
  WorkpageHistorySection,
  WorkpageNotePanelSection
} from "@/components/workpages/WorkpageContent";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { isApiClientError } from "@/lib/api/httpClient";
import { workpagesRepository } from "@/lib/repositories";
import type { WorkpageContract, WorkpagePreviewResponse } from "@/lib/types/contracts";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import {
  mergeWorkpageActionRef,
  replaceWorkpageActionRefArtifactVersionId,
  resolveWorkpageActionRef
} from "@/lib/workspace/workpageActionRef";
import type {
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageDriverPreferencesAction,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageRouteDemandAction,
  WorkpageScheduleAction,
  WorkpageScheduleHeatmapSection as WorkpageScheduleHeatmapSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableRow,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";

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

function scheduleLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0`;
}

function workpageBackRoute(workflowRunId: string): { href: string; label: string } {
  return { href: `/runs/${workflowRunId}`, label: "Back to run detail" };
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function rowsSignature(rows: WorkpageTableRow[]): string {
  return JSON.stringify(rows);
}

function findScheduleAction(
  contract: WorkpageContract | undefined,
  matcher: (action: WorkpageScheduleAction) => boolean
): WorkpageScheduleAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageScheduleAction => {
        if (action.workpage_kind !== "schedule-v0") {
          return false;
        }
        return matcher(action as WorkpageScheduleAction);
      }
    ) ?? null
  );
}

function findRouteDemandAction(
  contract: WorkpageContract | undefined
): WorkpageRouteDemandAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageRouteDemandAction =>
        action.workpage_kind === "route-demand-v0"
    ) ?? null
  );
}

function findDriverPreferencesAction(
  contract: WorkpageContract | undefined
): WorkpageDriverPreferencesAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageDriverPreferencesAction =>
        action.workpage_kind === "driver-preferences-v0"
    ) ?? null
  );
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

function buildAcceptedRail(contract: WorkpageContract): ScheduleVersionRailDefinition {
  const acceptedSeries = contract.accepted_series;
  const acceptedEntries = acceptedSeries?.entries ?? [];
  const acceptedEntryById = new Map(acceptedEntries.map((entry) => [entry.artifact_version_id, entry]));
  const latestLogicalDate = acceptedSeries?.entries.reduce<string | null>((current, entry) => {
    if (!current || entry.logical_date > current) {
      return entry.logical_date;
    }
    return current;
  }, null);
  const entries: DraftVersionTimelineEntry[] = (acceptedSeries?.entries ?? []).map((entry) => ({
    artifactVersionId: entry.artifact_version_id,
    createdAt: entry.logical_date,
    label:
      entry.artifact_version_id === acceptedSeries?.current_artifact_version_id
        ? "Current accepted"
        : entry.logical_date,
    isCurrent: entry.artifact_version_id === acceptedSeries?.current_artifact_version_id,
    isLatest: entry.logical_date === latestLogicalDate,
    note: `${entry.partition_key} · ${entry.artifact_kind}`,
    testId: `schedule-accepted-history-${entry.artifact_version_id}`,
    to: entry.route
  }));

  return {
    testId: "schedule-accepted-history-rail",
    title: "Accepted history",
    eyebrow: "Accepted series",
    description: "Accepted navigation stays on accepted weekly history only and never traverses draft lineage.",
    emptyText: "No accepted schedule history is available for this surface yet.",
    entries,
    previousRoute:
      acceptedSeries?.previous_artifact_version_id
        ? acceptedEntryById.get(acceptedSeries.previous_artifact_version_id)?.route ?? null
        : null,
    nextRoute:
      acceptedSeries?.next_artifact_version_id
        ? acceptedEntryById.get(acceptedSeries.next_artifact_version_id)?.route ?? null
        : null,
    previousLabel: "Previous accepted",
    nextLabel: "Next accepted"
  };
}

function buildDraftRail(contract: WorkpageContract): ScheduleVersionRailDefinition {
  const artifactHistory = contract.artifact_history;
  const historyEntries = artifactHistory?.entries ?? [];
  const historyEntryById = new Map(historyEntries.map((entry) => [entry.artifact_version_id, entry]));
  const currentDraftArtifactVersionId = artifactHistory?.current_artifact_version_id ?? "";
  const entries: DraftVersionTimelineEntry[] = historyEntries.map((entry) => {
    return {
      artifactVersionId: entry.artifact_version_id,
      createdAt: entry.created_at,
      label: draftVersionPrimaryLabel(entry.artifact_version_id, {
        currentArtifactVersionId: currentDraftArtifactVersionId,
        previousArtifactVersionId: artifactHistory?.previous_artifact_version_id ?? null
      }),
      isCurrent: entry.artifact_version_id === currentDraftArtifactVersionId,
      isLatest: entry.artifact_version_id === artifactHistory?.latest_artifact_version_id,
      note:
        entry.lineage_note ??
        (entry.supersedes_artifact_version_id
          ? `Supersedes ${entry.supersedes_artifact_version_id}`
          : "Initial schedule draft in this lineage."),
      testId: `schedule-draft-history-${entry.artifact_version_id}`,
      to: entry.route
    };
  });

  return {
    testId: "schedule-draft-history-rail",
    title: "Draft lineage",
    eyebrow: "Draft rail",
    description: "Draft navigation stays within backend-authored draft lineage for this immutable schedule surface.",
    emptyText: "No draft lineage is available on this surface yet.",
    entries,
    previousRoute:
      artifactHistory?.previous_artifact_version_id
        ? historyEntryById.get(artifactHistory.previous_artifact_version_id)?.route ?? null
        : null,
    nextRoute:
      artifactHistory?.next_artifact_version_id
        ? historyEntryById.get(artifactHistory.next_artifact_version_id)?.route ?? null
        : null,
    previousLabel: "Previous draft",
    nextLabel: artifactHistory?.next_artifact_version_id ? "Next draft" : "Latest draft unavailable"
  };
}

const EMPTY_WORKPAGE_MODEL = {
  sections: []
} as unknown as WorkpageContract["workpage"];

function useScheduleSections(contract?: WorkpageContract | null) {
  const model = contract?.workpage ?? EMPTY_WORKPAGE_MODEL;
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
  const heatmapSection = useMemo(() => findHeatmapSection(model.sections), [model]);
  const tableSections = useMemo(
    () =>
      model.sections.filter(
        (section): section is WorkpageTableSectionModel => section.kind === "table"
      ) ?? [],
    [model]
  );
  return {
    summarySection,
    noteSection,
    historySection,
    heatmapSection,
    assignmentSection: findTableSection(tableSections, "assignment_rows"),
    reserveSection: findTableSection(tableSections, "reserve_rows"),
    iterationSection: findTableSection(tableSections, "iteration_deltas")
  };
}

interface LogisticsScheduleWorkpageViewProps {
  contract: WorkpageContract;
  sourceDescription: string;
  summaryLabel: string;
  testId: string;
  backLink?: string;
  backLabel?: string;
  heroTitleActions?: ReactNode;
  heroSupportText?: ReactNode;
  heroActions?: ReactNode;
  stickyTitleBar?: boolean;
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
  heroTitleActions,
  heroSupportText,
  heroActions,
  stickyTitleBar = false,
  preContent,
  onRefresh,
  isRefreshing
}: LogisticsScheduleWorkpageViewProps): JSX.Element {
  const { summarySection, noteSection, historySection, heatmapSection, assignmentSection, reserveSection } =
    useScheduleSections(contract);
  const versionRails = useMemo(
    () => [buildAcceptedRail(contract), buildDraftRail(contract)],
    [contract]
  );

  return (
    <WorkpageFrame
      eyebrow="Weekly Planning Review"
      description="A workflow-backed weekly planning review for bounded draft navigation, live schedule context, and backend-authored metrics."
      summaryItems={[
        `Week ${String(contract.workpage.summary.planning_week_id ?? "unknown")}`,
        String(contract.workpage.summary.operational_week_start ?? "unknown"),
        String(contract.workpage.summary.station_code ?? contract.workpage.summary.source_bundle_id ?? "—"),
        summaryLabel
      ]}
      model={contract.workpage}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={onRefresh}
      isRefreshing={isRefreshing}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId={testId}
      metadataPresentation="dialog"
      infoDialogTitle="Weekly planning context"
      sourceDescription={sourceDescription}
      heroTitleActions={heroTitleActions}
      heroSupportText={heroSupportText}
      heroActions={heroActions}
      stickyTitleBar={stickyTitleBar}
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
      <ScheduleWorkpageSurface
        summarySection={summarySection}
        heatmapSection={heatmapSection}
        assignmentRows={assignmentSection?.rows ?? []}
        reserveRows={reserveSection?.rows ?? []}
        calculations={contract.calculations}
        dependencies={contract.dependencies}
        versionRails={versionRails}
        readOnly
      />
    </WorkpageFrame>
  );
}

export function LogisticsScheduleWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  if (!workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage route is unavailable"
        detail="Open schedule workpages from a canonical workflow-run route."
      />
    );
  }
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0", "landing", workflowRunId],
    queryFn: () => workpagesRepository.scheduleForRun(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const createDriverPreferencesMutation = useMutation({
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
        title="Loading schedule workpage"
        detail="Fetching the workflow-run-backed schedule workpage."
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage failed to load"
        detail={errorText(query.error, "Unable to load the workflow-run-backed schedule workpage.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const openLatestDraftAction = findScheduleAction(
    query.data,
    (action) => action.kind === "open_latest_draft"
  );
  const routeDemandAction = findRouteDemandAction(query.data);
  const driverPreferencesAction = findDriverPreferencesAction(query.data);
  const backRoute = workpageBackRoute(workflowRunId);

  return (
    <LogisticsScheduleWorkpageView
      contract={query.data}
      testId="schedule-workpage-page"
      sourceDescription="Workflow-run-backed schedule projection served from canonical weekly Stage04 source artifacts."
      summaryLabel="Run-backed review"
      backLink={backRoute.href}
      backLabel={backRoute.label}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching}
      preContent={
        openLatestDraftAction?.route && openLatestDraftAction.state === "available" ? (
          <section className="workpage-panel workpage-panel--callout">
            <header className="workpage-panel__header">
              <h2>Editable draft available</h2>
              <p>
                This landing page stays read-only. Open the backend-selected latest draft when you
                need live preview and save controls.
              </p>
            </header>
            <div className="action-cluster">
              <Link className="link-button" to={openLatestDraftAction.route}>
                Open editable draft
              </Link>
              {routeDemandAction?.route ? (
                <Link className="link-button" to={routeDemandAction.route}>
                  Open route demand
                </Link>
              ) : null}
              {driverPreferencesAction?.route ? (
                <Link className="link-button" to={driverPreferencesAction.route}>
                  Open driver preferences
                </Link>
              ) : driverPreferencesAction?.create_path ? (
                <button
                  type="button"
                  className="action-btn"
                  disabled={createDriverPreferencesMutation.isPending}
                  onClick={() =>
                    createDriverPreferencesMutation.mutate({
                      createPath: driverPreferencesAction.create_path ?? "",
                      actionRef: driverPreferencesAction.action_ref
                    })
                  }
                >
                  {createDriverPreferencesMutation.isPending
                    ? "Creating preferences snapshot..."
                    : "Create preferences snapshot"}
                </button>
              ) : null}
            </div>
          </section>
        ) : (
          <section className="workpage-panel workpage-panel--callout">
            <header className="workpage-panel__header">
              <h2>No editable draft artifact yet</h2>
              <p>
                The Stage04 draft weekly schedule artifact is not available for this run yet. Stay
                on the landing page until the canonical draft artifact exists.
              </p>
            </header>
            {routeDemandAction?.route || driverPreferencesAction?.route || driverPreferencesAction?.create_path ? (
              <div className="action-cluster">
                {routeDemandAction?.route ? (
                  <Link className="link-button" to={routeDemandAction.route}>
                    Open route demand
                  </Link>
                ) : null}
                {driverPreferencesAction?.route ? (
                  <Link className="link-button" to={driverPreferencesAction.route}>
                    Open driver preferences
                  </Link>
                ) : driverPreferencesAction?.create_path ? (
                  <button
                    type="button"
                    className="action-btn"
                    disabled={createDriverPreferencesMutation.isPending}
                    onClick={() =>
                      createDriverPreferencesMutation.mutate({
                        createPath: driverPreferencesAction.create_path ?? "",
                        actionRef: driverPreferencesAction.action_ref
                      })
                    }
                  >
                    {createDriverPreferencesMutation.isPending
                      ? "Creating preferences snapshot..."
                      : "Create preferences snapshot"}
                  </button>
                ) : null}
              </div>
            ) : null}
          </section>
        )
      }
    />
  );
}

export function LogisticsScheduleArtifactWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const previewRequestSequenceRef = useRef(0);
  const [previewResponse, setPreviewResponse] =
    useState<WorkpagePreviewResponse["preview"] | null>(null);
  const [previewErrorMessage, setPreviewErrorMessage] = useState<string | null>(null);
  const [isPreviewPending, setIsPreviewPending] = useState(false);
  const { artifactVersionId, workflowRunId } = useParams<{
    artifactVersionId: string;
    workflowRunId: string;
  }>();
  if (!workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="Schedule draft route is unavailable"
        detail="Open schedule drafts from a canonical workflow-run route."
      />
    );
  }
  const query = useQuery({
    queryKey: ["workpages", "schedule-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () => workpagesRepository.scheduleArtifact(workflowRunId, artifactVersionId ?? ""),
    enabled: Boolean(artifactVersionId && workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const contract = query.data;
  const artifactWorkflowRunId = workflowRunId;

  const {
    summarySection,
    noteSection,
    historySection,
    heatmapSection,
    assignmentSection,
    reserveSection,
    iterationSection
  } = useScheduleSections(contract);

  const { assignmentRows, setAssignmentRows, reserveRows, setReserveRows } =
    useEditableScheduleArtifactRows(contract, assignmentSection, reserveSection);
  const previewAction = findScheduleAction(
    contract,
    (action) => action.kind === "preview_recalc" || action.action_id === "workpage.schedule-v0.preview_recalc"
  );
  const saveAction = findScheduleAction(
    contract,
    (action) => action.kind === "submit_artifact" || action.action_id === "workpage.schedule-v0.save_draft"
  );
  const routeDemandAction = findRouteDemandAction(contract);
  const driverPreferencesAction = findDriverPreferencesAction(contract);
  const baseAssignmentSignature = useMemo(
    () => rowsSignature(assignmentSection?.rows ?? []),
    [assignmentSection]
  );
  const baseReserveSignature = useMemo(
    () => rowsSignature(reserveSection?.rows ?? []),
    [reserveSection]
  );
  const assignmentSignature = useMemo(() => rowsSignature(assignmentRows), [assignmentRows]);
  const reserveSignature = useMemo(() => rowsSignature(reserveRows), [reserveRows]);
  const hasUnsavedEdits =
    assignmentSignature !== baseAssignmentSignature || reserveSignature !== baseReserveSignature;
  const submitMutation = useMutation({
    mutationFn: () => {
      const carriedActionRef = resolveWorkpageActionRef(location.state, {
        workflowRunId: artifactWorkflowRunId,
        workpageKind: "schedule-v0",
        artifactVersionId: artifactVersionId ?? ""
      });
      const actionRef = mergeWorkpageActionRef(
        saveAction?.action_ref ?? null,
        carriedActionRef ?? null
      );
      if (saveAction?.submit_path) {
        return workpagesRepository.submitScheduleArtifactAtPath(
          saveAction.submit_path,
          artifactVersionId ?? "",
          {
            rows: assignmentRows,
            reserveRows
          },
          actionRef
        );
      }
      return workpagesRepository.submitScheduleArtifact(
        artifactWorkflowRunId,
        artifactVersionId ?? "",
        {
          rows: assignmentRows,
          reserveRows
        },
        actionRef
      );
    },
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      const carriedActionRef = resolveWorkpageActionRef(location.state, {
        workflowRunId: artifactWorkflowRunId,
        workpageKind: "schedule-v0",
        artifactVersionId: artifactVersionId ?? ""
      });
      navigate(submitted.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            mergeWorkpageActionRef(saveAction?.action_ref ?? null, carriedActionRef ?? null),
            submitted.artifact_version_id
          )
        }
      });
    }
  });
  const downloadMutation = useMutation({
    mutationFn: (currentArtifactVersionId: string) =>
      workpagesRepository.downloadScheduleArtifactJson(currentArtifactVersionId)
  });
  const createDriverPreferencesMutation = useMutation({
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

  useEffect(() => {
    setPreviewResponse(null);
    setPreviewErrorMessage(null);
    setIsPreviewPending(false);
    previewRequestSequenceRef.current += 1;
  }, [artifactVersionId]);

  useEffect(() => {
    previewRequestSequenceRef.current += 1;
    const requestToken = previewRequestSequenceRef.current;

    if (!hasUnsavedEdits) {
      setPreviewResponse(null);
      setPreviewErrorMessage(null);
      setIsPreviewPending(false);
      return;
    }

    if (!previewAction?.preview_path || previewAction.state !== "available") {
      setIsPreviewPending(false);
      return;
    }

    const timer = window.setTimeout(() => {
      setIsPreviewPending(true);
      void workpagesRepository
        .previewScheduleArtifact(previewAction.preview_path ?? "", {
          rows: assignmentRows,
          reserveRows
        })
        .then((response) => {
          if (previewRequestSequenceRef.current !== requestToken) {
            return;
          }
          setPreviewResponse(response.preview);
          setPreviewErrorMessage(null);
        })
        .catch((error) => {
          if (previewRequestSequenceRef.current !== requestToken) {
            return;
          }
          setPreviewErrorMessage(
            errorText(error, "Unable to recalculate the backend-authored schedule preview.")
          );
        })
        .finally(() => {
          if (previewRequestSequenceRef.current === requestToken) {
            setIsPreviewPending(false);
          }
        });
    }, 500);

    return () => {
      window.clearTimeout(timer);
    };
  }, [
    assignmentRows,
    assignmentSignature,
    hasUnsavedEdits,
    previewAction?.preview_path,
    previewAction?.state,
    reserveRows,
    reserveSignature
  ]);

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
    !contract ||
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

  const artifactContext = contract.artifact_context;
  const latestArtifactVersionId =
    artifactContext?.latest_in_chain_artifact_version_id ?? artifactVersionId;
  const latestRoute =
    contract.artifact_history?.entries.find(
      (entry) => entry.artifact_version_id === latestArtifactVersionId
    )?.route ?? null;
  const currentCalculations = previewResponse?.calculations ?? contract.calculations;
  const currentDependencies = previewResponse?.dependencies ?? contract.dependencies;
  const isStaleArtifact = latestArtifactVersionId !== artifactVersionId;
  const submitConflict = workpageConflictDetails(submitMutation.error);
  const staleOrConflictRoute = submitConflict?.route ?? (isStaleArtifact ? latestRoute : null);
  const backRoute = workpageBackRoute(workflowRunId);
  const versionRails = [buildAcceptedRail(contract), buildDraftRail(contract)];
  const previewBlockedReason =
    hasUnsavedEdits && previewAction?.state !== "available"
      ? previewAction?.disabled_reason ?? "Preview recalculation is unavailable for this draft."
      : null;
  const saveDisabled =
    submitMutation.isPending ||
    isStaleArtifact ||
    saveAction?.state !== "available" ||
    !artifactVersionId;

  return (
    <WorkpageFrame
      eyebrow="Weekly Schedule Draft Artifact"
      description="A bounded Stage04 draft workbook edit lane with live backend preview and explicit save into a new immutable draft version."
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
      }}
      isRefreshing={query.isFetching || submitMutation.isPending || downloadMutation.isPending}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId="schedule-artifact-workpage-page"
      metadataPresentation="dialog"
      infoDialogTitle="Schedule draft context"
      sourceDescription="Artifact-backed projection of an immutable Stage04 draft weekly schedule workbook. Save creates a new superseding draft artifact version without publishing."
      heroTitleActions={
        <>
          <button
            type="button"
            className="action-btn action-btn--positive"
            disabled={saveDisabled}
            onClick={() => submitMutation.mutate()}
          >
            {submitMutation.isPending ? "Saving draft..." : "Save draft"}
          </button>
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
      heroSupportText="Live preview recalculates in place. Save creates the next immutable draft in this weekly lineage."
      heroActions={
        <>
          <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
            Back to query landing
          </Link>
          {routeDemandAction?.route ? (
            <Link className="link-button" to={routeDemandAction.route}>
              Open route demand
            </Link>
          ) : null}
          {driverPreferencesAction?.route ? (
            <Link className="link-button" to={driverPreferencesAction.route}>
              Open driver preferences
            </Link>
          ) : driverPreferencesAction?.create_path ? (
            <button
              type="button"
              className="action-btn"
              disabled={createDriverPreferencesMutation.isPending}
              onClick={() =>
                createDriverPreferencesMutation.mutate({
                  createPath: driverPreferencesAction.create_path ?? "",
                  actionRef: driverPreferencesAction.action_ref
                })
              }
            >
              {createDriverPreferencesMutation.isPending
                ? "Creating preferences snapshot..."
                : "Create preferences snapshot"}
            </button>
          ) : null}
        </>
      }
      stickyTitleBar
      infoDialogContent={
        <ScheduleArtifactAdvancedInfo
          noteSection={noteSection}
          historySection={historySection}
          assignmentSection={assignmentSection}
          reserveSection={reserveSection}
          iterationSection={iterationSection}
          artifactContext={artifactContext}
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
              now, then reopen the latest draft artifact before saving again.
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
              version before saving more changes.
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
          title="Draft save failed"
          detail={errorText(submitMutation.error, "Unable to save the artifact-backed schedule draft.")}
        />
      ) : null}

      {downloadMutation.isError ? (
        <StatePanel
          kind="error"
          title="Draft JSON download failed"
          detail={errorText(downloadMutation.error, "Unable to download the schedule draft artifact.")}
        />
      ) : null}

      <ScheduleWorkpageSurface
        summarySection={summarySection}
        heatmapSection={heatmapSection}
        assignmentRows={assignmentRows}
        reserveRows={reserveRows}
        onRowsChange={({ assignmentRows: nextAssignmentRows, reserveRows: nextReserveRows }) => {
          setAssignmentRows(nextAssignmentRows);
          setReserveRows(nextReserveRows);
        }}
        calculations={currentCalculations}
        dependencies={currentDependencies}
        versionRails={versionRails}
        readOnly={false}
        previewStatus={{
          isDirty: hasUnsavedEdits,
          isPending: isPreviewPending,
          error: previewErrorMessage,
          blockedReason: previewBlockedReason
        }}
        saveAction={saveAction}
      />
    </WorkpageFrame>
  );
}
