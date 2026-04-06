import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type Dispatch, type ReactNode, type SetStateAction, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import {
  DraftVersionTimeline,
  draftVersionPrimaryLabel
} from "@/components/workpages/DraftVersionTimeline";
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
import { isApiClientError } from "@/lib/api/httpClient";
import { workpagesRepository } from "@/lib/repositories";
import type { WorkpageContract } from "@/lib/types/contracts";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import { resolveWorkpageSubjectContext } from "@/lib/workspace/workpageSubjectContext";
import type {
  WorkpageChecklistSection as WorkpageChecklistSectionModel,
  WorkpageFormSection as WorkpageFormSectionModel,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";
import {
  buildEditableSectionResetKey,
  buildChecklistState,
  buildFormState,
  type WorkpageChecklistState,
  type WorkpageFormState
} from "@/lib/workpages/state";

function findTableSection(
  sections: WorkpageTableSectionModel[],
  tableId: string
): WorkpageTableSectionModel | null {
  return sections.find((section) => section.table_id === tableId) ?? null;
}

function eodLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/eod-v0`;
}

function workpageBackRoute(workflowRunId: string): { href: string; label: string } {
  return { href: `/runs/${workflowRunId}`, label: "Back to run detail" };
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

interface DispatchReportWorkpageViewProps {
  contract: WorkpageContract;
  testId: string;
  sourceDescription: string;
  summaryLabel: string;
  backLink?: string;
  backLabel?: string;
  heroTitleActions?: ReactNode;
  heroSupportText?: ReactNode;
  heroActions?: ReactNode;
  stickyTitleBar?: boolean;
  preContent?: ReactNode;
  sideRail?: ReactNode;
  editable: boolean;
  formState?: WorkpageFormState;
  checklistState?: WorkpageChecklistState;
  onFormChange?: (fieldKey: string, value: WorkpageFormState[string]) => void;
  onChecklistToggle?: (itemId: string, checked: boolean) => void;
  onChecklistNoteChange?: (itemId: string, note: string) => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

function DispatchReportWorkpageView({
  contract,
  testId,
  sourceDescription,
  summaryLabel,
  backLink,
  backLabel,
  heroTitleActions,
  heroSupportText,
  heroActions,
  stickyTitleBar = false,
  preContent,
  sideRail,
  editable,
  formState = {},
  checklistState = {},
  onFormChange = () => undefined,
  onChecklistToggle = () => undefined,
  onChecklistNoteChange = () => undefined,
  onRefresh,
  isRefreshing
}: DispatchReportWorkpageViewProps): JSX.Element {
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
  const checklistSection = useMemo(
    () =>
      model.sections.find(
        (section): section is WorkpageChecklistSectionModel => section.kind === "checklist"
      ) ?? null,
    [model]
  );

  const mainContent = (
    <>
      {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}

      {findTableSection(tableSections, "route_actuals") ? (
        <WorkpageTableSection section={findTableSection(tableSections, "route_actuals") as WorkpageTableSectionModel} />
      ) : null}

      <div className="workpage-page__grid workpage-page__grid--two-column">
        {formSection ? (
          <WorkpageFormSection
            section={formSection}
            values={formState}
            onChange={onFormChange}
            readOnly={!editable}
          />
        ) : null}
        {checklistSection ? (
          <WorkpageChecklistSection
            section={checklistSection}
            values={checklistState}
            onToggle={onChecklistToggle}
            onNoteChange={onChecklistNoteChange}
            readOnly={!editable}
          />
        ) : null}
      </div>

      {historySection ? <WorkpageHistorySection section={historySection} /> : null}
    </>
  );

  return (
    <WorkpageFrame
      eyebrow="Dispatch Reporting Draft"
      description="A bounded EOD workpage for route actual review, closeout capture, and UPD draft posture."
      summaryItems={[
        `Service date ${model.summary.service_date}`,
        `${model.summary.station_code}`,
        `${model.summary.dsp_name}`,
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
      infoDialogTitle={editable ? "EOD draft context" : "Dispatch reporting context"}
      sourceDescription={sourceDescription}
      infoDialogContent={noteSection ? <WorkpageNotePanelSection section={noteSection} /> : undefined}
      heroTitleActions={heroTitleActions}
      heroSupportText={heroSupportText}
      heroActions={heroActions}
      stickyTitleBar={stickyTitleBar}
      backLink={backLink}
      backLabel={backLabel}
    >
      {preContent}
      {sideRail ? (
        <div className="workpage-page__artifact-layout">
          <div className="workpage-page__artifact-main">{mainContent}</div>
          <aside className="workpage-page__artifact-rail">{sideRail}</aside>
        </div>
      ) : (
        mainContent
      )}
    </WorkpageFrame>
  );
}

export function DispatchReportWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  if (!workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="End-of-day workpage route is unavailable"
        detail="Open dispatch-reporting workpages from a canonical workflow-run route."
      />
    );
  }
  const query = useQuery({
    queryKey: ["workpages", "eod-v0", "landing", workflowRunId],
    queryFn: () => workpagesRepository.eodForRun(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const createDraftMutation = useMutation({
    mutationFn: () => workpagesRepository.createEodDraftForRun(workflowRunId),
    onSuccess: (draft) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      navigate(draft.route);
    }
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading end-of-day workpage"
        detail="Fetching the workflow-run-backed dispatch-reporting landing workpage."
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <StatePanel
        kind="error"
        title="End-of-day workpage failed to load"
        detail={errorText(query.error, "Unable to load the workflow-run-backed dispatch-reporting landing workpage.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const latestDraftRoute =
    query.data.draft_resolution?.state === "latest_draft_available"
      ? query.data.draft_resolution.artifact_route
      : null;
  const backRoute = workpageBackRoute(workflowRunId);

  return (
    <DispatchReportWorkpageView
      contract={query.data}
      testId="dispatch-report-workpage-page"
      sourceDescription="Workflow-run-backed dispatch-reporting landing with latest-draft resolution over a canonical reporting run."
      summaryLabel="Run-backed preview"
      backLink={backRoute.href}
      backLabel={backRoute.label}
      editable={false}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching || createDraftMutation.isPending}
      preContent={
        <>
          {createDraftMutation.isError ? (
            <StatePanel
              kind="error"
              title="Editable draft creation failed"
              detail={errorText(createDraftMutation.error, "Unable to create an editable EOD draft.")}
            />
          ) : null}
          {latestDraftRoute ? (
            <section className="workpage-panel workpage-panel--callout">
              <header className="workpage-panel__header">
                <h2>Latest draft available</h2>
                <p>
                  This landing page already resolved the newest editable workbook-backed draft for
                  this reporting run. Reopen that draft before making closeout or UPD review edits.
                </p>
              </header>
              <div className="action-cluster">
                <Link className="link-button" to={latestDraftRoute}>
                  Open latest draft
                </Link>
              </div>
            </section>
          ) : (
            <section className="workpage-panel workpage-panel--callout">
              <header className="workpage-panel__header">
                <h2>Create editable draft</h2>
                <p>
                  This landing page is a read-only preview. Create an immutable workbook-backed
                  draft before making closeout or UPD review edits.
                </p>
              </header>
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
            </section>
          )}
        </>
      }
    />
  );
}

export function DispatchReportArtifactWorkpagePage(): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const { artifactVersionId, workflowRunId } = useParams<{
    artifactVersionId: string;
    workflowRunId: string;
  }>();
  if (!workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="Artifact-backed EOD route is unavailable"
        detail="Open EOD drafts from a canonical workflow-run route."
      />
    );
  }
  const query = useQuery({
    queryKey: ["workpages", "eod-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () => workpagesRepository.eodArtifact(workflowRunId, artifactVersionId ?? ""),
    enabled: Boolean(artifactVersionId && workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const artifactWorkflowRunId = workflowRunId;
  const model = query.data?.workpage;
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
  const { formState, setFormState, checklistState, setChecklistState } = useEditableEodState(
    query.data,
    formSection,
    checklistSection
  );
  const submitMutation = useMutation({
    mutationFn: () =>
      workpagesRepository.submitEodArtifact(
        artifactWorkflowRunId,
        artifactVersionId ?? "",
        {
          formValues: formState,
          checklistValues: orderedChecklistSubmitValues(checklistSection, checklistState)
        },
        resolveWorkpageSubjectContext(location.state, { workflowRunId: artifactWorkflowRunId })
      ),
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      navigate(submitted.route, { state: location.state });
    }
  });
  const downloadMutation = useMutation({
    mutationFn: (currentArtifactVersionId: string) =>
      workpagesRepository.downloadEodArtifactWorkbook(currentArtifactVersionId)
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading artifact-backed EOD draft"
        detail="Fetching the immutable workbook-backed EOD workpage projection."
      />
    );
  }

  if (query.isError || !query.data || !artifactVersionId) {
    return (
      <StatePanel
        kind="error"
        title="Artifact-backed EOD draft failed to load"
        detail={errorText(query.error, "Unable to load the artifact-backed EOD draft.")}
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
  const previousArtifactVersionId = artifactContext?.supersedes_artifact_version_id ?? null;
  const artifactHistory = contract.artifact_history;
  const recentDraftHistory = artifactHistory?.entries ?? [];
  const latestRoute =
    recentDraftHistory.find((artifact) => artifact.artifact_version_id === latestArtifactVersionId)
      ?.route ?? null;
  const isStaleArtifact = latestArtifactVersionId !== artifactVersionId;
  const submitConflict = workpageConflictDetails(submitMutation.error);
  const staleOrConflictRoute = submitConflict?.route ?? (isStaleArtifact ? latestRoute : null);
  const backRoute = workpageBackRoute(workflowRunId);

  return (
    <DispatchReportWorkpageView
      contract={contract}
      testId="dispatch-report-artifact-workpage-page"
      sourceDescription="Artifact-backed projection of an immutable Stage03 reporting workbook draft. Submit creates a new superseding workbook artifact version."
      summaryLabel={`Artifact ${artifactVersionId}`}
      backLink={backRoute.href}
      backLabel={backRoute.label}
      editable={true}
      formState={formState}
      checklistState={checklistState}
      onFormChange={(fieldKey, value) => {
        setFormState((current) => ({
          ...current,
          [fieldKey]: value
        }));
      }}
      onChecklistToggle={(itemId, checked) => {
        setChecklistState((current) => ({
          ...current,
          [itemId]: {
            ...(current[itemId] ?? { selected: false, note: "" }),
            selected: checked
          }
        }));
      }}
      onChecklistNoteChange={(itemId, note) => {
        setChecklistState((current) => ({
          ...current,
          [itemId]: {
            ...(current[itemId] ?? { selected: false, note: "" }),
            note
          }
        }));
      }}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching || submitMutation.isPending || downloadMutation.isPending}
      heroTitleActions={
        <>
          <button
            type="button"
            className="action-btn action-btn--positive"
            disabled={submitMutation.isPending || isStaleArtifact}
            onClick={() => submitMutation.mutate()}
          >
            {submitMutation.isPending ? "Submitting draft..." : "Submit draft"}
          </button>
          <button
            type="button"
            className="action-btn"
            disabled={downloadMutation.isPending}
            onClick={() => downloadMutation.mutate(artifactVersionId)}
          >
            {downloadMutation.isPending ? "Downloading workbook..." : "Download workbook"}
          </button>
        </>
      }
      heroActions={
        <Link className="link-button" to={eodLandingRoute(workflowRunId)}>
          Back to query landing
        </Link>
      }
      heroSupportText="Submit creates a new immutable workbook artifact version. The current draft remains authoritative until you explicitly submit."
      stickyTitleBar
      sideRail={
        artifactContext ? (
          <section
            className="workpage-panel workpage-page__artifact-rail-panel"
            data-testid="dispatch-report-draft-history-rail"
          >
            <header className="workpage-panel__header">
              <h2>Recent draft versions</h2>
              <p>
                Backend-authored immutable `reporting.upd_draft.workbook` lineage for this
                reporting run. Use these links to reopen adjacent draft states without leaving the
                canonical EOD workpage surface.
              </p>
            </header>

            {recentDraftHistory.length === 0 ? (
              <p className="workpage-history__empty">
                No recent draft history is available for this reporting run yet.
              </p>
            ) : null}

            {recentDraftHistory.length > 0 ? (
              <DraftVersionTimeline
                ariaLabel="Recent reporting draft versions"
                entries={recentDraftHistory.map((artifact) => ({
                  artifactVersionId: artifact.artifact_version_id,
                  createdAt: artifact.created_at,
                  label: draftVersionPrimaryLabel(artifact.artifact_version_id, {
                    currentArtifactVersionId: artifactVersionId,
                    previousArtifactVersionId:
                      artifactHistory?.previous_artifact_version_id ?? previousArtifactVersionId
                  }),
                  isCurrent: artifact.artifact_version_id === artifactVersionId,
                  isLatest:
                    artifact.artifact_version_id ===
                    (artifactHistory?.latest_artifact_version_id ?? latestArtifactVersionId),
                  note: artifact.lineage_note,
                  to: artifact.route
                }))}
              />
            ) : null}
          </section>
        ) : null
      }
      preContent={
        <>
          {submitConflict ? (
            <section className="workpage-panel workpage-panel--callout">
              <header className="workpage-panel__header">
                <h2>Latest draft already exists</h2>
                <p>
                  This base artifact has already been superseded. Keep your local edits for now,
                  then reopen the latest artifact-backed draft before submitting again.
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
                  This artifact version is no longer the latest draft in the chain. Reopen the
                  latest version before submitting more changes.
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
              detail={errorText(submitMutation.error, "Unable to submit the artifact-backed draft.")}
            />
          ) : null}

          {downloadMutation.isError ? (
            <StatePanel
              kind="error"
              title="Workbook download failed"
              detail={errorText(downloadMutation.error, "Unable to download the workbook artifact.")}
            />
          ) : null}
        </>
      }
    />
  );
}
