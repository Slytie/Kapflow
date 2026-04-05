import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type Dispatch,
  type SetStateAction,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { Link } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import {
  DraftVersionTimeline,
  draftVersionPrimaryLabel
} from "@/components/workpages/DraftVersionTimeline";
import { ScheduleArtifactAdvancedInfo } from "@/components/workpages/ScheduleArtifactAdvancedInfo";
import { ScheduleHeatmapEditor } from "@/components/workpages/ScheduleHeatmapEditor";
import { WorkpageChecklistSection } from "@/components/workpages/WorkpageChecklistSection";
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
import { workpagesRepository } from "@/lib/repositories";
import type { ArtifactVersionRow, WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageChecklistSection as WorkpageChecklistSectionModel,
  WorkpageFormSection as WorkpageFormSectionModel,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageScheduleHeatmapSection as WorkpageScheduleHeatmapSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableRow,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import {
  buildChecklistState,
  buildEditableSectionResetKey,
  buildFormState,
  type WorkpageChecklistState,
  type WorkpageFormState
} from "@/lib/workpages/state";

function scheduleLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0`;
}

function scheduleArtifactRoute(artifactVersionId: string, workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`;
}

function eodLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/eod-v0`;
}

function eodArtifactRoute(artifactVersionId: string, workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/eod-v0/artifacts/${artifactVersionId}`;
}

function extractArtifactVersionIdFromRoute(route: string): string | null {
  const matched = route.match(/\/artifacts\/([^/]+)$/);
  return matched?.[1] ?? null;
}

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

function orderedChecklistSubmitValues(
  section: WorkpageChecklistSectionModel | null,
  checklistState: WorkpageChecklistState
): Array<{
  item_id: string;
  selected: boolean;
  note: string;
}> {
  if (!section) {
    return [];
  }
  return section.items.map((item) => {
    const value = checklistState[item.item_id] ?? {
      selected: item.selected,
      note: item.note
    };
    return {
      item_id: item.item_id,
      selected: value.selected,
      note: value.note
    };
  });
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

function useEditableEodState(
  contract: WorkpageContract | undefined,
  formSection: WorkpageFormSectionModel | null,
  checklistSection: WorkpageChecklistSectionModel | null
): {
  formState: WorkpageFormState;
  setFormState: Dispatch<SetStateAction<WorkpageFormState>>;
  checklistState: WorkpageChecklistState;
  setChecklistState: Dispatch<SetStateAction<WorkpageChecklistState>>;
} {
  const [formState, setFormState] = useState<WorkpageFormState>({});
  const [checklistState, setChecklistState] = useState<WorkpageChecklistState>({});
  const lastFormResetKeyRef = useRef<string | null>(null);
  const lastChecklistResetKeyRef = useRef<string | null>(null);
  const formResetKey = useMemo(() => {
    if (!contract || !formSection) {
      return null;
    }
    return buildEditableSectionResetKey(contract.workpage, contract.freshness.source_version, formSection);
  }, [contract, formSection]);
  const checklistResetKey = useMemo(() => {
    if (!contract || !checklistSection) {
      return null;
    }
    return buildEditableSectionResetKey(
      contract.workpage,
      contract.freshness.source_version,
      checklistSection
    );
  }, [contract, checklistSection]);

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

  useEffect(() => {
    if (!checklistSection || !checklistResetKey) {
      lastChecklistResetKeyRef.current = null;
      setChecklistState({});
      return;
    }
    if (lastChecklistResetKeyRef.current === checklistResetKey) {
      return;
    }
    lastChecklistResetKeyRef.current = checklistResetKey;
    setChecklistState(buildChecklistState(checklistSection));
  }, [checklistResetKey, checklistSection]);

  return {
    formState,
    setFormState,
    checklistState,
    setChecklistState
  };
}

function InlineDraftTimeline({
  history,
  currentArtifactVersionId,
  latestArtifactVersionId,
  previousArtifactVersionId,
  onSelect,
  title
}: {
  history: ArtifactVersionRow[];
  currentArtifactVersionId: string;
  latestArtifactVersionId: string;
  previousArtifactVersionId: string | null;
  onSelect: (artifactVersionId: string) => void;
  title: string;
}): JSX.Element {
  return (
    <DraftVersionTimeline
      ariaLabel={`${title} timeline`}
      variant="sidebar"
      className="inline-workpage-shell__timeline"
      eyebrow="Draft Timeline"
      title={title}
      entries={history.map((artifact) => {
        const isCurrent = artifact.artifact_version_id === currentArtifactVersionId;
        const isLatest = artifact.artifact_version_id === latestArtifactVersionId;
        return {
          artifactVersionId: artifact.artifact_version_id,
          createdAt: artifact.created_at,
          label: draftVersionPrimaryLabel(artifact.artifact_version_id, {
            currentArtifactVersionId,
            previousArtifactVersionId
          }),
          isCurrent,
          isLatest,
          isSelected: isCurrent,
          note: artifact.lineage_note,
          onSelect: () => onSelect(artifact.artifact_version_id)
        };
      })}
    />
  );
}

export function InlineScheduleWorkpage({
  workflowRunId
}: {
  workflowRunId: string;
}): JSX.Element {
  const queryClient = useQueryClient();
  const [selectedArtifactVersionId, setSelectedArtifactVersionId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedArtifactVersionId(null);
  }, [workflowRunId]);

  const historyQuery = useQuery({
    queryKey: ["logistics-inline-workpages", "schedule", workflowRunId, "history"],
    queryFn: () => workpagesRepository.listScheduleDraftHistory(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const latestHistoryArtifactVersionId = historyQuery.data?.[0]?.artifact_version_id ?? null;
  const effectiveArtifactVersionId = selectedArtifactVersionId ?? latestHistoryArtifactVersionId;

  const workpageQuery = useQuery({
    queryKey: [
      "logistics-inline-workpages",
      "schedule",
      workflowRunId,
      effectiveArtifactVersionId ?? "landing"
    ],
    queryFn: () =>
      effectiveArtifactVersionId
        ? workpagesRepository.scheduleArtifact(workflowRunId, effectiveArtifactVersionId)
        : workpagesRepository.scheduleForRun(workflowRunId),
    enabled: !historyQuery.isLoading,
    refetchInterval: apiConfig.pollIntervalMs
  });

  const model = workpageQuery.data?.workpage;
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
    useEditableScheduleArtifactRows(workpageQuery.data, assignmentSection, reserveSection);

  const submitMutation = useMutation({
    mutationFn: () =>
      workpagesRepository.submitScheduleArtifact(workflowRunId, effectiveArtifactVersionId ?? "", {
        rows: assignmentRows,
        reserveRows
      }),
    onSuccess: async (submitted) => {
      setSelectedArtifactVersionId(submitted.artifact_version_id);
      await queryClient.invalidateQueries({
        queryKey: ["logistics-inline-workpages", "schedule", workflowRunId]
      });
      await queryClient.invalidateQueries({ queryKey: ["workpages"] });
      await invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
    }
  });

  const downloadMutation = useMutation({
    mutationFn: (artifactVersionId: string) =>
      workpagesRepository.downloadScheduleArtifactJson(artifactVersionId)
  });

  if (historyQuery.isLoading || workpageQuery.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading schedule workpage"
        detail="Resolving the latest weekly draft and inline workpage surface."
      />
    );
  }

  if (historyQuery.isError || workpageQuery.isError || !workpageQuery.data) {
    return (
      <StatePanel
        kind="error"
        title="Schedule workpage failed to load"
        detail={errorText(
          historyQuery.error ?? workpageQuery.error,
          "Unable to load the inline schedule workpage."
        )}
        onRetry={() => {
          void historyQuery.refetch();
          void workpageQuery.refetch();
        }}
      />
    );
  }

  const contract = workpageQuery.data;
  const isArtifactBacked = Boolean(contract.artifact_context && effectiveArtifactVersionId);
  const currentArtifactVersionId = contract.artifact_context?.artifact_version_id ?? null;
  const latestArtifactVersionId =
    contract.artifact_context?.latest_in_chain_artifact_version_id ??
    latestHistoryArtifactVersionId ??
    currentArtifactVersionId;
  const previousArtifactVersionId = contract.artifact_context?.supersedes_artifact_version_id ?? null;
  const fullRoute = isArtifactBacked && currentArtifactVersionId
    ? scheduleArtifactRoute(currentArtifactVersionId, workflowRunId)
    : scheduleLandingRoute(workflowRunId);

  return (
    <div className="inline-workpage-shell" data-testid="logistics-inline-schedule-workpage">
      <div className="inline-workpage-shell__main">
        <WorkpageFrame
          layout="embedded"
          eyebrow={isArtifactBacked ? "Weekly Schedule Draft Artifact" : "Weekly Schedule Review"}
          description={
            isArtifactBacked
              ? "Review and edit the latest weekly draft inline without leaving the logistics demo shell."
              : "Review the weekly planning landing surface inline. When a draft exists, this pane will switch to the latest editable version automatically."
          }
          summaryItems={[
            `Run ${workflowRunId}`,
            isArtifactBacked && currentArtifactVersionId ? `Artifact ${currentArtifactVersionId}` : "Run-backed preview",
            String(contract.workpage.summary.planning_week_id ?? "—")
          ]}
          model={contract.workpage}
          testId={isArtifactBacked ? "logistics-inline-schedule-artifact" : "logistics-inline-schedule-landing"}
          source={contract.source}
          freshness={contract.freshness}
          sourceDescription={
            isArtifactBacked
              ? "Artifact-backed projection of the immutable weekly draft. Submit creates a new superseding draft and keeps you in the demo shell."
              : "Run-backed weekly planning landing surface for the selected module run."
          }
          onRefresh={() => {
            void historyQuery.refetch();
            void workpageQuery.refetch();
          }}
          isRefreshing={
            historyQuery.isFetching ||
            workpageQuery.isFetching ||
            submitMutation.isPending ||
            downloadMutation.isPending
          }
          pollIntervalMs={apiConfig.pollIntervalMs}
          metadataPresentation="dialog"
          infoDialogTitle={isArtifactBacked ? "Schedule draft context" : "Weekly planning context"}
          heroTitleActions={
            isArtifactBacked && effectiveArtifactVersionId ? (
              <>
                <button
                  type="button"
                  className="action-btn action-btn--positive"
                  disabled={submitMutation.isPending}
                  onClick={() => submitMutation.mutate()}
                >
                  {submitMutation.isPending ? "Submitting draft..." : "Submit draft"}
                </button>
                <button
                  type="button"
                  className="action-btn"
                  disabled={downloadMutation.isPending}
                  onClick={() =>
                    downloadMutation.mutate(currentArtifactVersionId ?? effectiveArtifactVersionId)
                  }
                >
                  {downloadMutation.isPending ? "Downloading draft..." : "Download draft JSON"}
                </button>
              </>
            ) : null
          }
          heroSupportText={
            isArtifactBacked
              ? "Submit creates a new immutable weekly draft artifact and keeps this inline panel on the latest version."
              : undefined
          }
          heroActions={
            <div className="action-cluster">
              <Link className="link-button" to={fullRoute}>
                Open full workpage
              </Link>
            </div>
          }
          stickyTitleBar={isArtifactBacked}
          infoDialogContent={
            isArtifactBacked ? (
              <ScheduleArtifactAdvancedInfo
                noteSection={noteSection}
                historySection={historySection}
                assignmentSection={assignmentSection}
                reserveSection={reserveSection}
                iterationSection={iterationSection}
                artifactContext={contract.artifact_context}
              />
            ) : (
              <>
                {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
                {historySection ? <WorkpageHistorySection section={historySection} /> : null}
              </>
            )
          }
        >
          {submitMutation.isError ? (
            <StatePanel
              kind="error"
              title="Draft submit failed"
              detail={errorText(submitMutation.error, "Unable to submit the inline schedule draft.")}
            />
          ) : null}

          {downloadMutation.isError ? (
            <StatePanel
              kind="error"
              title="Draft JSON download failed"
              detail={errorText(downloadMutation.error, "Unable to download the schedule draft artifact.")}
            />
          ) : null}

          {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}

          {isArtifactBacked && heatmapSection && assignmentSection && reserveSection ? (
            <>
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
            </>
          ) : null}

          {!isArtifactBacked ? (
            <>
              {dayDemandSection ? <WorkpageTableSection section={dayDemandSection} /> : null}
              {selectedDaySection ? <WorkpageTableSection section={selectedDaySection} /> : null}
              {driverRosterSection ? <WorkpageTableSection section={driverRosterSection} /> : null}
            </>
          ) : null}
        </WorkpageFrame>
      </div>
      {isArtifactBacked &&
      currentArtifactVersionId &&
      latestArtifactVersionId &&
      historyQuery.data &&
      historyQuery.data.length > 0 ? (
        <InlineDraftTimeline
          history={historyQuery.data}
          currentArtifactVersionId={currentArtifactVersionId}
          latestArtifactVersionId={latestArtifactVersionId}
          previousArtifactVersionId={previousArtifactVersionId}
          onSelect={setSelectedArtifactVersionId}
          title="Weekly draft versions"
        />
      ) : null}
    </div>
  );
}

export function InlineDispatchReportWorkpage({
  workflowRunId
}: {
  workflowRunId: string;
}): JSX.Element {
  const queryClient = useQueryClient();
  const [selectedArtifactVersionId, setSelectedArtifactVersionId] = useState<string | null>(null);

  useEffect(() => {
    setSelectedArtifactVersionId(null);
  }, [workflowRunId]);

  const historyQuery = useQuery({
    queryKey: ["logistics-inline-workpages", "eod", workflowRunId, "history"],
    queryFn: () => workpagesRepository.listEodDraftHistory(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const latestHistoryArtifactVersionId = historyQuery.data?.[0]?.artifact_version_id ?? null;
  const effectiveArtifactVersionId = selectedArtifactVersionId ?? latestHistoryArtifactVersionId;

  const workpageQuery = useQuery({
    queryKey: [
      "logistics-inline-workpages",
      "eod",
      workflowRunId,
      effectiveArtifactVersionId ?? "landing"
    ],
    queryFn: () =>
      effectiveArtifactVersionId
        ? workpagesRepository.eodArtifact(workflowRunId, effectiveArtifactVersionId)
        : workpagesRepository.eodForRun(workflowRunId),
    enabled: !historyQuery.isLoading,
    refetchInterval: apiConfig.pollIntervalMs
  });

  const createDraftMutation = useMutation({
    mutationFn: () => workpagesRepository.createEodDraftForRun(workflowRunId),
    onSuccess: async (draft) => {
      const artifactVersionId = extractArtifactVersionIdFromRoute(draft.route) ?? draft.artifact_version_id;
      setSelectedArtifactVersionId(artifactVersionId);
      await queryClient.invalidateQueries({
        queryKey: ["logistics-inline-workpages", "eod", workflowRunId]
      });
      await queryClient.invalidateQueries({ queryKey: ["workpages"] });
    }
  });

  const model = workpageQuery.data?.workpage;
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
  const formSection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageFormSectionModel => section.kind === "form"
      ) ?? null,
    [model]
  );
  const checklistSection = useMemo(
    () =>
      model?.sections.find(
        (section): section is WorkpageChecklistSectionModel => section.kind === "checklist"
      ) ?? null,
    [model]
  );
  const tableSections = useMemo(
    () =>
      model?.sections.filter(
        (section): section is WorkpageTableSectionModel => section.kind === "table"
      ) ?? [],
    [model]
  );
  const { formState, setFormState, checklistState, setChecklistState } = useEditableEodState(
    workpageQuery.data,
    formSection,
    checklistSection
  );

  const submitMutation = useMutation({
    mutationFn: () =>
      workpagesRepository.submitEodArtifact(workflowRunId, effectiveArtifactVersionId ?? "", {
        formValues: formState,
        checklistValues: orderedChecklistSubmitValues(checklistSection, checklistState)
      }),
    onSuccess: async (submitted) => {
      setSelectedArtifactVersionId(submitted.artifact_version_id);
      await queryClient.invalidateQueries({
        queryKey: ["logistics-inline-workpages", "eod", workflowRunId]
      });
      await queryClient.invalidateQueries({ queryKey: ["workpages"] });
      await invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
    }
  });

  const downloadMutation = useMutation({
    mutationFn: (artifactVersionId: string) =>
      workpagesRepository.downloadEodArtifactWorkbook(artifactVersionId)
  });

  if (historyQuery.isLoading || workpageQuery.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading EOD workpage"
        detail="Resolving the latest reporting draft and inline workpage surface."
      />
    );
  }

  if (historyQuery.isError || workpageQuery.isError || !workpageQuery.data) {
    return (
      <StatePanel
        kind="error"
        title="EOD workpage failed to load"
        detail={errorText(
          historyQuery.error ?? workpageQuery.error,
          "Unable to load the inline EOD workpage."
        )}
        onRetry={() => {
          void historyQuery.refetch();
          void workpageQuery.refetch();
        }}
      />
    );
  }

  const contract = workpageQuery.data;
  const isArtifactBacked = Boolean(contract.artifact_context && effectiveArtifactVersionId);
  const currentArtifactVersionId = contract.artifact_context?.artifact_version_id ?? null;
  const latestArtifactVersionId =
    contract.artifact_context?.latest_in_chain_artifact_version_id ??
    latestHistoryArtifactVersionId ??
    currentArtifactVersionId;
  const previousArtifactVersionId = contract.artifact_context?.supersedes_artifact_version_id ?? null;
  const fullRoute = isArtifactBacked && currentArtifactVersionId
    ? eodArtifactRoute(currentArtifactVersionId, workflowRunId)
    : eodLandingRoute(workflowRunId);

  return (
    <div className="inline-workpage-shell" data-testid="logistics-inline-eod-workpage">
      <div className="inline-workpage-shell__main">
        <WorkpageFrame
          layout="embedded"
          eyebrow={isArtifactBacked ? "EOD Draft Artifact" : "End-of-Day Review"}
          description={
            isArtifactBacked
              ? "Review and edit the latest reporting draft inline without leaving the logistics demo shell."
              : "Review the dispatch reporting landing surface inline. Create a draft here when one does not exist yet."
          }
          summaryItems={[
            `Run ${workflowRunId}`,
            isArtifactBacked && currentArtifactVersionId ? `Artifact ${currentArtifactVersionId}` : "Run-backed preview",
            String(contract.workpage.summary.service_date ?? "—")
          ]}
          model={contract.workpage}
          testId={isArtifactBacked ? "logistics-inline-eod-artifact" : "logistics-inline-eod-landing"}
          source={contract.source}
          freshness={contract.freshness}
          sourceDescription={
            isArtifactBacked
              ? "Artifact-backed projection of the immutable EOD draft workbook. Submit creates a new superseding draft and keeps you in the demo shell."
              : "Run-backed dispatch reporting landing surface for the selected module run."
          }
          onRefresh={() => {
            void historyQuery.refetch();
            void workpageQuery.refetch();
          }}
          isRefreshing={
            historyQuery.isFetching ||
            workpageQuery.isFetching ||
            createDraftMutation.isPending ||
            submitMutation.isPending ||
            downloadMutation.isPending
          }
          pollIntervalMs={apiConfig.pollIntervalMs}
          metadataPresentation="dialog"
          infoDialogTitle={isArtifactBacked ? "EOD draft context" : "Dispatch reporting context"}
          infoDialogContent={noteSection ? <WorkpageNotePanelSection section={noteSection} /> : undefined}
          heroTitleActions={
            isArtifactBacked && effectiveArtifactVersionId ? (
              <>
                <button
                  type="button"
                  className="action-btn action-btn--positive"
                  disabled={submitMutation.isPending}
                  onClick={() => submitMutation.mutate()}
                >
                  {submitMutation.isPending ? "Submitting draft..." : "Submit draft"}
                </button>
                <button
                  type="button"
                  className="action-btn"
                  disabled={downloadMutation.isPending}
                  onClick={() =>
                    downloadMutation.mutate(currentArtifactVersionId ?? effectiveArtifactVersionId)
                  }
                >
                  {downloadMutation.isPending ? "Downloading workbook..." : "Download workbook"}
                </button>
              </>
            ) : null
          }
          heroSupportText={
            isArtifactBacked
              ? "Submit creates a new immutable reporting draft artifact and keeps this inline panel on the latest version."
              : undefined
          }
          heroActions={
            <div className="action-cluster">
              <Link className="link-button" to={fullRoute}>
                Open full workpage
              </Link>
            </div>
          }
          stickyTitleBar={isArtifactBacked}
        >
          {createDraftMutation.isError ? (
            <StatePanel
              kind="error"
              title="Editable draft creation failed"
              detail={errorText(createDraftMutation.error, "Unable to create an inline editable EOD draft.")}
            />
          ) : null}

          {submitMutation.isError ? (
            <StatePanel
              kind="error"
              title="Draft submit failed"
              detail={errorText(submitMutation.error, "Unable to submit the inline EOD draft.")}
            />
          ) : null}

          {downloadMutation.isError ? (
            <StatePanel
              kind="error"
              title="Workbook download failed"
              detail={errorText(downloadMutation.error, "Unable to download the workbook artifact.")}
            />
          ) : null}

          {!isArtifactBacked ? (
            <section className="workpage-panel workpage-panel--callout">
              <header className="workpage-panel__header">
                <h2>{latestHistoryArtifactVersionId ? "Latest draft available" : "Create editable draft"}</h2>
                <p>
                  {latestHistoryArtifactVersionId
                    ? "This inline panel will automatically follow the latest editable draft. Use the timeline when you want to revisit older versions."
                    : "Create the first editable workbook-backed EOD draft without leaving the logistics demo shell."}
                </p>
              </header>
              {!latestHistoryArtifactVersionId ? (
                <div className="action-cluster">
                  <button
                    type="button"
                    className="action-btn action-btn--positive"
                    disabled={createDraftMutation.isPending}
                    onClick={() => createDraftMutation.mutate()}
                  >
                    {createDraftMutation.isPending ? "Creating draft..." : "Create editable draft"}
                  </button>
                </div>
              ) : null}
            </section>
          ) : null}

          {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}

          {!isArtifactBacked
            ? tableSections.map((section) => <WorkpageTableSection key={section.table_id} section={section} />)
            : null}

          {isArtifactBacked && formSection ? (
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

          {isArtifactBacked && checklistSection ? (
            <WorkpageChecklistSection
              section={checklistSection}
              values={checklistState}
              onToggle={(itemId, checked) => {
                setChecklistState((current) => ({
                  ...current,
                  [itemId]: {
                    ...(current[itemId] ?? { selected: false, note: "" }),
                    selected: checked
                  }
                }));
              }}
              onNoteChange={(itemId, note) => {
                setChecklistState((current) => ({
                  ...current,
                  [itemId]: {
                    ...(current[itemId] ?? { selected: false, note: "" }),
                    note
                  }
                }));
              }}
            />
          ) : null}

          {historySection ? <WorkpageHistorySection section={historySection} /> : null}
        </WorkpageFrame>
      </div>
      {isArtifactBacked &&
      currentArtifactVersionId &&
      latestArtifactVersionId &&
      historyQuery.data &&
      historyQuery.data.length > 0 ? (
        <InlineDraftTimeline
          history={historyQuery.data}
          currentArtifactVersionId={currentArtifactVersionId}
          latestArtifactVersionId={latestArtifactVersionId}
          previousArtifactVersionId={previousArtifactVersionId}
          onSelect={setSelectedArtifactVersionId}
          title="Reporting draft versions"
        />
      ) : null}
    </div>
  );
}
