import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState
} from "react";
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
import { apiConfig, getApiViewerSession } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { isApiClientError } from "@/lib/api/httpClient";
import { approvalsRepository, humanTasksRepository, workpagesRepository } from "@/lib/repositories";
import type {
  ApprovalRow,
  HumanTaskRow,
  WorkpageContract,
  WorkpageEodIntakeTask,
  WorkflowWorkspaceRequiredUpload
} from "@/lib/types/contracts";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import {
  mergeWorkpageActionRef,
  replaceWorkpageActionRefArtifactVersionId,
  resolveWorkpageActionRef
} from "@/lib/workspace/workpageActionRef";
import type {
  WorkpageEodAction,
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

function eodLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/eod-v0`;
}

function workpageBackRoute(workflowRunId: string): { href: string; label: string } {
  return { href: `/runs/${workflowRunId}`, label: "Back to run detail" };
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function fileNameServiceDate(fileName: string | null | undefined): string | null {
  if (!fileName) {
    return null;
  }
  const match = fileName.match(/\b(\d{4}-\d{2}-\d{2})\b/);
  return match?.[1] ?? null;
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

function requiredUpload(
  artifactKind: string,
  artifactRole: "official_input" | "evidence"
): WorkflowWorkspaceRequiredUpload {
  return {
    dataset_key: artifactKind,
    template_id: null,
    artifact_kind: artifactKind,
    artifact_role: artifactRole,
    required: true,
    required_count: 1,
    current_count: 0,
    status: "missing"
  };
}

function hasActorRole(role: string | null | undefined): boolean {
  if (!role) {
    return false;
  }
  return getApiViewerSession()?.actor_roles.includes(role) ?? false;
}

function latestEodDraftArtifactVersionId(contract: WorkpageContract | undefined): string | null {
  if (contract?.draft_resolution?.state !== "latest_draft_available") {
    return null;
  }
  return contract.draft_resolution.latest_artifact_version_id;
}

function reviewConfirmed(task: HumanTaskRow | null): boolean {
  const pendingReviews = task?.required_reviews?.filter((review) => review.status !== "confirmed") ?? [];
  return pendingReviews.length === 0 && Boolean(task?.can_confirm_review === false || task?.state === "COMPLETED" || task?.required_reviews?.length);
}

function latestDispatchReviewTask(tasks: HumanTaskRow[]): HumanTaskRow | null {
  const candidates = tasks
    .filter((task) => task.stage_id === "Stage04" && task.task_kind === "final_packet_review")
    .sort((left, right) => {
      if (left.generation !== right.generation) {
        return right.generation - left.generation;
      }
      return right.created_at.localeCompare(left.created_at);
    });
  return candidates[0] ?? null;
}

function pendingDispatchApproval(approvals: ApprovalRow[]): ApprovalRow | null {
  const candidates = approvals
    .filter((approval) => approval.state === "PENDING" && approval.scope_ref === "Stage04")
    .sort((left, right) => {
      if (left.generation !== right.generation) {
        return right.generation - left.generation;
      }
      return right.requested_at.localeCompare(left.requested_at);
    });
  return candidates[0] ?? null;
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

function findEodSubmitAction(contract: WorkpageContract | undefined): WorkpageEodAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageEodAction =>
        action.workpage_kind === "eod-v0" && action.kind === "submit_artifact"
    ) ?? null
  );
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
  layout?: "page" | "embedded";
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
  layout = "page",
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

      {tableSections.map((section) => (
        <WorkpageTableSection key={section.table_id} section={section} />
      ))}

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
      layout={layout}
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

interface DispatchReportArtifactEditorProps {
  workflowRunId: string;
  artifactVersionId: string;
  layout?: "page" | "embedded";
  testId?: string;
  onArtifactVersionChange?: (artifactVersionId: string) => void;
}

function DispatchReportArtifactEditor({
  workflowRunId,
  artifactVersionId,
  layout = "page",
  testId,
  onArtifactVersionChange
}: DispatchReportArtifactEditorProps): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const query = useQuery({
    queryKey: ["workpages", "eod-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () => workpagesRepository.eodArtifact(workflowRunId, artifactVersionId),
    enabled: Boolean(artifactVersionId && workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
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
  const submitAction = findEodSubmitAction(query.data);
  const submitMutation = useMutation({
    mutationFn: () => {
      const carriedActionRef = resolveWorkpageActionRef(location.state, {
        workflowRunId,
        workpageKind: "eod-v0",
        artifactVersionId
      });
      const actionRef = mergeWorkpageActionRef(
        submitAction?.action_ref ?? null,
        carriedActionRef ?? null
      );
      return workpagesRepository.submitEodArtifact(
        workflowRunId,
        artifactVersionId,
        {
          formValues: formState,
          checklistValues: orderedChecklistSubmitValues(checklistSection, checklistState)
        },
        actionRef
      );
    },
    onSuccess: (submitted) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      if (onArtifactVersionChange) {
        onArtifactVersionChange(submitted.artifact_version_id);
        return;
      }
      const carriedActionRef = resolveWorkpageActionRef(location.state, {
        workflowRunId,
        workpageKind: "eod-v0",
        artifactVersionId
      });
      const nextActionRef = replaceWorkpageActionRefArtifactVersionId(
        mergeWorkpageActionRef(submitAction?.action_ref ?? null, carriedActionRef ?? null),
        submitted.artifact_version_id
      );
      navigate(submitted.route, {
        state: {
          workpageActionRef: nextActionRef
        }
      });
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

  function openArtifactVersion(nextArtifactVersionId: string, route: string | null): void {
    if (onArtifactVersionChange) {
      onArtifactVersionChange(nextArtifactVersionId);
      return;
    }
    if (!route) {
      return;
    }
    navigate(route);
  }

  return (
    <DispatchReportWorkpageView
      contract={contract}
      testId={testId ?? (layout === "embedded" ? "dispatch-report-quick-edit-editor" : "dispatch-report-artifact-workpage-page")}
      sourceDescription="Artifact-backed projection of an immutable Stage03 reporting workbook draft. Submit creates a new superseding workbook artifact version."
      summaryLabel={layout === "embedded" ? "Embedded draft review" : `Artifact ${artifactVersionId}`}
      backLink={layout === "page" ? backRoute.href : undefined}
      backLabel={layout === "page" ? backRoute.label : undefined}
      editable={true}
      layout={layout}
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
        layout === "page" ? (
          <Link className="link-button" to={eodLandingRoute(workflowRunId)}>
            Back to query landing
          </Link>
        ) : undefined
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
                {onArtifactVersionChange ? (
                  <button
                    type="button"
                    className="link-button"
                    onClick={() =>
                      openArtifactVersion(
                        submitConflict.latestArtifactVersionId,
                        submitConflict.route
                      )
                    }
                  >
                    Open latest draft
                  </button>
                ) : (
                  <Link className="link-button" to={submitConflict.route}>
                    Open latest draft
                  </Link>
                )}
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
                {onArtifactVersionChange ? (
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => openArtifactVersion(latestArtifactVersionId, staleOrConflictRoute)}
                  >
                    Open latest draft
                  </button>
                ) : (
                  <Link className="link-button" to={staleOrConflictRoute}>
                    Open latest draft
                  </Link>
                )}
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
    mutationFn: () =>
      workpagesRepository.createEodDraftForRun(
        workflowRunId,
        query.data?.draft_resolution?.create_action_ref ?? undefined
      ),
    onSuccess: (draft) => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      navigate(draft.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            query.data?.draft_resolution?.create_action_ref,
            draft.artifact_version_id
          )
        }
      });
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
                <Link
                  className="link-button"
                  to={latestDraftRoute}
                  state={{
                    workpageActionRef: query.data.draft_resolution?.open_action_ref ?? undefined
                  }}
                >
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

export function DispatchReportCloseoutModal({
  workflowRunId,
  onClose
}: {
  workflowRunId: string;
  onClose: () => void;
}): JSX.Element {
  const navigate = useNavigate();
  const titleId = useId();
  const descriptionId = useId();
  const queryClient = useQueryClient();
  const [activeWorkflowRunId, setActiveWorkflowRunId] = useState(workflowRunId);
  const [selectedWorkbookFile, setSelectedWorkbookFile] = useState<File | null>(null);
  const [selectedServiceDate, setSelectedServiceDate] = useState("");
  const [activeArtifactVersionId, setActiveArtifactVersionId] = useState<string | null>(null);
  const [approvalReason, setApprovalReason] = useState("");
  const [finalizedMessage, setFinalizedMessage] = useState<string | null>(null);

  const landingQuery = useQuery({
    queryKey: ["workpages", "eod-v0", "landing", activeWorkflowRunId],
    queryFn: () => workpagesRepository.eodForRun(activeWorkflowRunId),
    enabled: Boolean(activeWorkflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const tasksQuery = useQuery({
    queryKey: ["human-tasks", "dispatch-reporting", activeWorkflowRunId],
    queryFn: () => humanTasksRepository.list({ workflowRunId: activeWorkflowRunId }),
    enabled: Boolean(activeWorkflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const approvalsQuery = useQuery({
    queryKey: ["approvals", activeWorkflowRunId, "dispatch-reporting-closeout"],
    queryFn: () => approvalsRepository.list({ workflowRunId: activeWorkflowRunId }),
    enabled: Boolean(activeWorkflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });

  const latestDraftArtifactVersionId = latestEodDraftArtifactVersionId(landingQuery.data);
  const reviewTask = latestDispatchReviewTask(tasksQuery.data ?? []);
  const approval = pendingDispatchApproval(approvalsQuery.data ?? []);
  const canRespondApproval = approval ? hasActorRole(approval.required_role) : false;
  const activeRunLogicalDate = landingQuery.data?.run_context?.logical_date ?? "";
  const selectedWorkbookFileDate = fileNameServiceDate(selectedWorkbookFile?.name);
  const selectedDateDiffersFromFileName =
    Boolean(selectedWorkbookFileDate) &&
    Boolean(selectedServiceDate) &&
    selectedWorkbookFileDate !== selectedServiceDate;
  const selectedDateTargetsDifferentRun =
    Boolean(selectedServiceDate) &&
    Boolean(activeRunLogicalDate) &&
    selectedServiceDate !== activeRunLogicalDate;

  useEffect(() => {
    setActiveWorkflowRunId(workflowRunId);
  }, [workflowRunId]);

  useEffect(() => {
    if (!latestDraftArtifactVersionId) {
      return;
    }
    setActiveArtifactVersionId((current) =>
      current && current === latestDraftArtifactVersionId ? current : latestDraftArtifactVersionId
    );
  }, [latestDraftArtifactVersionId]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  useEffect(() => {
    setApprovalReason("");
    setFinalizedMessage(null);
  }, [activeWorkflowRunId]);

  useEffect(() => {
    if (!selectedWorkbookFile || selectedServiceDate) {
      return;
    }
    const fallbackDate = activeRunLogicalDate;
    const nextServiceDate = fileNameServiceDate(selectedWorkbookFile.name) ?? fallbackDate;
    if (nextServiceDate) {
      setSelectedServiceDate(nextServiceDate);
    }
  }, [activeRunLogicalDate, selectedServiceDate, selectedWorkbookFile]);

  async function refreshCloseoutQueries(targetWorkflowRunId = activeWorkflowRunId): Promise<void> {
    const workflowRunIds = Array.from(
      new Set([workflowRunId, activeWorkflowRunId, targetWorkflowRunId].filter(Boolean))
    );
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["workpages"] }),
      queryClient.invalidateQueries({ queryKey: ["human-tasks"] }),
      queryClient.invalidateQueries({ queryKey: ["approvals"] }),
      ...workflowRunIds.map((runId) => invalidateWorkspaceViews(queryClient, runId))
    ]);
    if (targetWorkflowRunId !== activeWorkflowRunId) {
      const targetLanding = await queryClient.fetchQuery({
        queryKey: ["workpages", "eod-v0", "landing", targetWorkflowRunId],
        queryFn: () => workpagesRepository.eodForRun(targetWorkflowRunId)
      });
      const latestArtifactVersionId = latestEodDraftArtifactVersionId(targetLanding);
      if (latestArtifactVersionId) {
        setActiveArtifactVersionId(latestArtifactVersionId);
      }
      return;
    }
    const [landingResult] = await Promise.all([
      landingQuery.refetch(),
      tasksQuery.refetch(),
      approvalsQuery.refetch()
    ]);
    const latestArtifactVersionId = latestEodDraftArtifactVersionId(landingResult.data);
    if (latestArtifactVersionId) {
      setActiveArtifactVersionId(latestArtifactVersionId);
    }
  }

  async function ensureClaimedTask(task: HumanTaskRow): Promise<HumanTaskRow> {
    if (task.state === "OPEN") {
      await humanTasksRepository.claim(task.human_task_id);
      return humanTasksRepository.get(task.human_task_id);
    }
    return task;
  }

  const importMutation = useMutation({
    mutationFn: async (): Promise<WorkpageEodIntakeTask> => {
      if (!selectedWorkbookFile) {
        throw new Error("Choose a route-activity workbook before importing.");
      }
      if (!selectedServiceDate) {
        throw new Error("Choose the reporting service date before importing.");
      }
      const intakeTask = await workpagesRepository.ensureEodIntakeTaskForRun(activeWorkflowRunId, {
        serviceDate: selectedServiceDate
      });
      if (intakeTask.human_task_state === "OPEN") {
        await humanTasksRepository.claim(intakeTask.human_task_id);
      }
      await humanTasksRepository.uploadRequiredResponse(
        intakeTask.human_task_id,
        requiredUpload("reporting.eos_raw.workbook", "official_input"),
        selectedWorkbookFile,
        {
          metadataJson: {
            service_date: selectedServiceDate
          }
        }
      );
      await humanTasksRepository.complete(intakeTask.human_task_id);
      return intakeTask;
    },
    onSuccess: async (intakeTask) => {
      const nextWorkflowRunId =
        intakeTask.target_workflow_run_id || intakeTask.workflow_run_id || activeWorkflowRunId;
      const nextRoute = intakeTask.target_route || eodLandingRoute(nextWorkflowRunId);
      setSelectedWorkbookFile(null);
      setSelectedServiceDate("");
      setFinalizedMessage(null);
      if (nextWorkflowRunId !== activeWorkflowRunId) {
        setActiveArtifactVersionId(null);
        setActiveWorkflowRunId(nextWorkflowRunId);
        await refreshCloseoutQueries(nextWorkflowRunId);
        navigate(nextRoute);
        return;
      }
      await refreshCloseoutQueries(nextWorkflowRunId);
      if (window.location.pathname !== nextRoute) {
        navigate(nextRoute);
      }
    }
  });

  const confirmReviewMutation = useMutation({
    mutationFn: async (): Promise<void> => {
      if (!reviewTask || !activeArtifactVersionId) {
        throw new Error("The latest draft must be available before review can be confirmed.");
      }
      const claimedTask = await ensureClaimedTask(reviewTask);
      await humanTasksRepository.confirmReview(claimedTask.human_task_id, [activeArtifactVersionId]);
    },
    onSuccess: async () => {
      await refreshCloseoutQueries();
    }
  });

  const completeReviewMutation = useMutation({
    mutationFn: async (): Promise<void> => {
      if (!reviewTask) {
        throw new Error("The Stage04 review task is not available yet.");
      }
      const claimedTask = await ensureClaimedTask(reviewTask);
      await humanTasksRepository.complete(claimedTask.human_task_id);
    },
    onSuccess: async () => {
      await refreshCloseoutQueries();
    }
  });

  const approvalMutation = useMutation({
    mutationFn: async (input: {
      responseKind: "approve" | "reject" | "request_changes";
      responseReason?: string;
    }): Promise<ApprovalRow> => {
      if (!approval) {
        throw new Error("The manager approval is not available yet.");
      }
      return approvalsRepository.respond(
        approval.approval_id,
        input.responseKind,
        input.responseReason
      );
    },
    onSuccess: async (_response, variables) => {
      setFinalizedMessage(
        variables.responseKind === "approve"
          ? "Dispatch reporting packet finalized and the planning handoff has been requested."
          : variables.responseKind === "request_changes"
            ? "Manager changes were requested. Update the latest draft and repeat the review handoff."
            : "Dispatch reporting packet was rejected."
      );
      await refreshCloseoutQueries();
    }
  });

  return (
    <div
      className="quick-edit-backdrop route-demand-quick-edit-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="quick-edit-modal route-demand-quick-edit-modal dispatch-report-closeout-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <header className="quick-edit-modal__header route-demand-quick-edit-modal__header">
          <div>
            <p className="timeline-page__eyebrow">Dispatch closeout</p>
            <h2 id={titleId}>Upload route activity</h2>
            <p id={descriptionId}>
              Import the daily workbook, review the generated EOD draft, confirm the latest draft
              review, and complete the canonical approval loop without leaving the workpage.
            </p>
          </div>
          <button type="button" className="action-btn" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="quick-edit-modal__body route-demand-quick-edit-modal__body">
          <section className="workpage-panel" data-testid="dispatch-closeout-import-panel">
            <header className="workpage-panel__header">
              <h2>1. Import route activity</h2>
              <p>
                Upload the raw EOS workbook to the Stage01 intake task. Completing intake seeds the
                latest immutable EOD draft for review.
              </p>
            </header>
            <label className="workpage-form__field">
              <span>Route-activity workbook</span>
              <input
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(event) => {
                  const nextFile = event.target.files?.[0] ?? null;
                  setSelectedWorkbookFile(nextFile);
                  setSelectedServiceDate(
                    nextFile
                      ? (fileNameServiceDate(nextFile.name) ?? activeRunLogicalDate)
                      : ""
                  );
                }}
              />
            </label>
            {selectedWorkbookFile ? (
              <label className="workpage-form__field">
                <span>Service date</span>
                <input
                  type="date"
                  value={selectedServiceDate}
                  onChange={(event) => {
                    setSelectedServiceDate(event.target.value);
                  }}
                />
              </label>
            ) : null}
            {selectedDateDiffersFromFileName ? (
              <p>
                The selected service date will be used instead of the workbook file name date.
              </p>
            ) : null}
            {selectedDateTargetsDifferentRun ? (
              <p>
                Import will continue on the reporting run for <strong>{selectedServiceDate}</strong>.
              </p>
            ) : null}
            <div className="action-cluster">
              <button
                type="button"
                className="action-btn action-btn--positive"
                disabled={!selectedWorkbookFile || !selectedServiceDate || importMutation.isPending}
                onClick={() => importMutation.mutate()}
              >
                {importMutation.isPending ? "Importing workbook..." : "Import route activity"}
              </button>
            </div>
            {latestDraftArtifactVersionId ? (
              <p data-testid="dispatch-closeout-latest-draft">
                Latest draft ready: <strong>{latestDraftArtifactVersionId}</strong>
              </p>
            ) : (
              <p>No imported EOD draft is available for this run yet.</p>
            )}
            {importMutation.isError ? (
              <StatePanel
                kind="error"
                title="Route-activity import failed"
                detail={errorText(importMutation.error, "Unable to complete the Stage01 intake flow.")}
              />
            ) : null}
          </section>

          <section className="workpage-panel" data-testid="dispatch-closeout-draft-panel">
            <header className="workpage-panel__header">
              <h2>2. Review and submit the latest draft</h2>
              <p>
                Work directly in the artifact-backed EOD editor. Each submit creates a new immutable
                draft version and keeps the closeout flow pinned to the newest artifact.
              </p>
            </header>
            {landingQuery.isLoading && !activeArtifactVersionId ? (
              <StatePanel
                kind="loading"
                title="Loading draft context"
                detail="Resolving the latest dispatch-reporting draft for this run."
              />
            ) : activeArtifactVersionId ? (
              <DispatchReportArtifactEditor
                workflowRunId={activeWorkflowRunId}
                artifactVersionId={activeArtifactVersionId}
                layout="embedded"
                onArtifactVersionChange={setActiveArtifactVersionId}
              />
            ) : (
              <StatePanel
                kind="loading"
                title="Draft not ready yet"
                detail="Import the workbook first, or wait for the latest EOD draft to resolve."
              />
            )}
          </section>

          <section className="workpage-panel" data-testid="dispatch-closeout-review-panel">
            <header className="workpage-panel__header">
              <h2>3. Complete draft review handoff</h2>
              <p>
                Confirm the latest draft review, then complete the Stage04 review task to request
                manager approval.
              </p>
            </header>
            {tasksQuery.isLoading && !reviewTask ? (
              <StatePanel
                kind="loading"
                title="Loading review task"
                detail="Resolving the latest Stage04 review task for this reporting run."
              />
            ) : reviewTask ? (
              <>
                <p>
                  Review task status: <strong>{reviewTask.state}</strong>
                </p>
                <p>
                  Draft review confirmation:{" "}
                  <strong>{reviewConfirmed(reviewTask) ? "Confirmed" : "Still required"}</strong>
                </p>
                <div className="action-cluster">
                  <button
                    type="button"
                    className="action-btn"
                    disabled={!activeArtifactVersionId || confirmReviewMutation.isPending}
                    onClick={() => confirmReviewMutation.mutate()}
                  >
                    {confirmReviewMutation.isPending
                      ? "Confirming review..."
                      : "Confirm latest draft review"}
                  </button>
                  <button
                    type="button"
                    className="action-btn action-btn--positive"
                    disabled={completeReviewMutation.isPending}
                    onClick={() => completeReviewMutation.mutate()}
                  >
                    {completeReviewMutation.isPending
                      ? "Completing review..."
                      : "Complete review task"}
                  </button>
                </div>
                {confirmReviewMutation.isError ? (
                  <StatePanel
                    kind="error"
                    title="Review confirmation failed"
                    detail={errorText(
                      confirmReviewMutation.error,
                      "Unable to confirm review for the latest draft."
                    )}
                  />
                ) : null}
                {completeReviewMutation.isError ? (
                  <StatePanel
                    kind="error"
                    title="Review completion failed"
                    detail={errorText(
                      completeReviewMutation.error,
                      "Unable to complete the Stage04 review task."
                    )}
                  />
                ) : null}
              </>
            ) : (
              <p>The review task will appear here after Stage01 intake completes.</p>
            )}
          </section>

          <section className="workpage-panel" data-testid="dispatch-closeout-approval-panel">
            <header className="workpage-panel__header">
              <h2>4. Respond to manager approval</h2>
              <p>
                Approval stays canonical. Approving here finalizes the reporting packet and triggers
                the weekly-planning actual-hours handoff.
              </p>
            </header>
            {finalizedMessage ? (
              <section className="workpage-panel workpage-panel--callout">
                <header className="workpage-panel__header">
                  <h2>Closeout updated</h2>
                  <p>{finalizedMessage}</p>
                </header>
              </section>
            ) : null}
            {approval ? (
              <>
                <p>
                  Pending approval: <strong>{approval.approval_kind}</strong> for role{" "}
                  <strong>{approval.required_role.replace(/_/g, " ")}</strong>
                </p>
                {!canRespondApproval ? (
                  <StatePanel
                    kind="error"
                    title="Approval role required"
                    detail="The current viewer session cannot respond to this approval. Switch to an actor with the required manager role to finish closeout in this popup."
                  />
                ) : null}
                <label className="workpage-form__field">
                  <span>Approval note</span>
                  <textarea
                    value={approvalReason}
                    onChange={(event) => {
                      setApprovalReason(event.target.value);
                    }}
                    placeholder="Optional note for the approval response"
                  />
                </label>
                <div className="action-cluster">
                  <button
                    type="button"
                    className="action-btn action-btn--positive"
                    disabled={!canRespondApproval || approvalMutation.isPending}
                    onClick={() =>
                      approvalMutation.mutate({
                        responseKind: "approve",
                        responseReason: approvalReason || undefined
                      })
                    }
                  >
                    {approvalMutation.isPending ? "Submitting approval..." : "Approve final packet"}
                  </button>
                  <button
                    type="button"
                    className="action-btn"
                    disabled={!canRespondApproval || approvalMutation.isPending}
                    onClick={() =>
                      approvalMutation.mutate({
                        responseKind: "request_changes",
                        responseReason: approvalReason || undefined
                      })
                    }
                  >
                    Request changes
                  </button>
                  <button
                    type="button"
                    className="action-btn"
                    disabled={!canRespondApproval || approvalMutation.isPending}
                    onClick={() =>
                      approvalMutation.mutate({
                        responseKind: "reject",
                        responseReason: approvalReason || undefined
                      })
                    }
                  >
                    Reject
                  </button>
                </div>
                {approvalMutation.isError ? (
                  <StatePanel
                    kind="error"
                    title="Approval response failed"
                    detail={errorText(
                      approvalMutation.error,
                      "Unable to respond to the manager approval."
                    )}
                  />
                ) : null}
              </>
            ) : (
              <p>
                {reviewTask?.state === "COMPLETED"
                  ? "Waiting for the pending approval to refresh."
                  : "Complete the review task to request manager approval."}
              </p>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}

export function DispatchReportArtifactWorkpagePage(): JSX.Element {
  const { artifactVersionId, workflowRunId } = useParams<{
    artifactVersionId: string;
    workflowRunId: string;
  }>();
  if (!workflowRunId || !artifactVersionId) {
    return (
      <StatePanel
        kind="error"
        title="Artifact-backed EOD route is unavailable"
        detail="Open EOD drafts from a canonical workflow-run route."
      />
    );
  }
  return (
    <DispatchReportArtifactEditor
      workflowRunId={workflowRunId}
      artifactVersionId={artifactVersionId}
    />
  );
}
