import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type Dispatch,
  type SetStateAction,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState
} from "react";
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
import { isApiClientError } from "@/lib/api/httpClient";
import { workpagesRepository } from "@/lib/repositories";
import { invalidateWorkspaceViews } from "@/lib/workspace/queryInvalidation";
import { replaceWorkpageActionRefArtifactVersionId } from "@/lib/workspace/workpageActionRef";
import type { WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageArtifactHistory,
  WorkpageDriverAvailabilityException,
  WorkpageDriverPreferencesAction,
  WorkpageDriverPreferencesDriverRow,
  WorkpageDriverPreferencesGrid,
  WorkpageDriverPreferencesScheduleImpact,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageScheduleHeatmapDate,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel
} from "@/lib/types/workpages";

type DriverPreferenceState =
  | "open_to_work"
  | "prefer_not_to_work"
  | "definitely_can_not_work"
  | "unset";

const PREFERENCE_STATE_CYCLE: DriverPreferenceState[] = [
  "open_to_work",
  "prefer_not_to_work",
  "definitely_can_not_work",
  "unset"
];
const EMPTY_DRIVER_PREFERENCE_ROWS: WorkpageDriverPreferencesDriverRow[] = [];
const AVAILABILITY_EXCEPTION_REASONS: Array<WorkpageDriverAvailabilityException["reason_code"]> = [
  "wedding",
  "vacation",
  "medical",
  "family",
  "appointment",
  "other"
];

const PREFERENCE_STATE_UI: Record<
  DriverPreferenceState,
  { label: string; shortLabel: string; toneClassName: string; legendSwatchClassName: string }
> = {
  open_to_work: {
    label: "Open to work",
    shortLabel: "Open",
    toneClassName: "driver-preferences-heatmap__cell--open_to_work",
    legendSwatchClassName: "driver-preferences-heatmap__legend-swatch--open_to_work"
  },
  prefer_not_to_work: {
    label: "Prefer not to work",
    shortLabel: "Prefer off",
    toneClassName: "driver-preferences-heatmap__cell--prefer_not_to_work",
    legendSwatchClassName: "driver-preferences-heatmap__legend-swatch--prefer_not_to_work"
  },
  definitely_can_not_work: {
    label: "Definitely cannot work",
    shortLabel: "Cannot",
    toneClassName: "driver-preferences-heatmap__cell--definitely_can_not_work",
    legendSwatchClassName: "driver-preferences-heatmap__legend-swatch--definitely_can_not_work"
  },
  unset: {
    label: "Unset",
    shortLabel: "Unset",
    toneClassName: "driver-preferences-heatmap__cell--unset",
    legendSwatchClassName: "driver-preferences-heatmap__legend-swatch--unset"
  }
};

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

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function formatReasonCode(reasonCode: string): string {
  return reasonCode.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
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

function useEditableDriverPreferencesGrid(
  contract: WorkpageContract | undefined
): {
  driverRows: WorkpageDriverPreferencesDriverRow[];
  setDriverRows: Dispatch<SetStateAction<WorkpageDriverPreferencesDriverRow[]>>;
} {
  const [driverRows, setDriverRows] = useState<WorkpageDriverPreferencesDriverRow[]>([]);
  const lastResetKeyRef = useRef<string | null>(null);
  const sourceRows = contract?.preference_grid?.drivers ?? EMPTY_DRIVER_PREFERENCE_ROWS;
  const resetKey = useMemo(
    () =>
      [
        contract?.freshness.source_version ?? "",
        contract?.artifact_context?.artifact_version_id ?? "",
        driverRowsSignature(sourceRows)
      ].join(":"),
    [contract?.freshness.source_version, contract?.artifact_context?.artifact_version_id, sourceRows]
  );

  useEffect(() => {
    if (!contract) {
      lastResetKeyRef.current = null;
      setDriverRows((currentRows) => (currentRows.length > 0 ? [] : currentRows));
      return;
    }
    if (lastResetKeyRef.current === resetKey) {
      return;
    }
    lastResetKeyRef.current = resetKey;
    setDriverRows(sourceRows.map((row) => ({
      ...row,
      preferences_by_weekday: { ...row.preferences_by_weekday }
    })));
  }, [contract, resetKey, sourceRows]);

  return { driverRows, setDriverRows };
}

function preferenceStateForWeekday(
  row: WorkpageDriverPreferencesDriverRow,
  weekday: WorkpageDriverPreferencesGrid["weekdays"][number]
): DriverPreferenceState {
  return (row.preferences_by_weekday[weekday] ?? "unset") as DriverPreferenceState;
}

function nextPreferenceValue(currentState: DriverPreferenceState): string | null {
  const currentIndex = PREFERENCE_STATE_CYCLE.indexOf(currentState);
  const nextState = PREFERENCE_STATE_CYCLE[(currentIndex + 1) % PREFERENCE_STATE_CYCLE.length];
  return nextState === "unset" ? null : nextState;
}

function fallbackServiceDates(
  weekdays: WorkpageDriverPreferencesGrid["weekdays"]
): WorkpageScheduleHeatmapDate[] {
  return weekdays.map((weekday) => ({
    service_date: weekday,
    label: weekday.toUpperCase(),
    weekday_label: weekday.toUpperCase()
  }));
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

function DriverPreferencesHeatmap({
  serviceDates,
  weekdays,
  driverRows,
  setDriverRows,
  readOnly,
  selectedDriverId,
  onSelectDriver
}: {
  serviceDates: WorkpageScheduleHeatmapDate[];
  weekdays: WorkpageDriverPreferencesGrid["weekdays"];
  driverRows: WorkpageDriverPreferencesDriverRow[];
  setDriverRows?: Dispatch<SetStateAction<WorkpageDriverPreferencesDriverRow[]>> | undefined;
  readOnly: boolean;
  selectedDriverId?: string | null;
  onSelectDriver?: (driver: WorkpageDriverPreferencesDriverRow) => void;
}): JSX.Element {
  return (
    <section className="workpage-panel" data-testid="driver-preferences-grid">
      <header className="workpage-panel__header schedule-heatmap__header">
        <div>
          <h2>Preference grid</h2>
          <p>
            {readOnly
              ? "Read-only weekly advisory posture from the latest snapshot or the seeded initial projection."
              : "Click a driver/day cell to cycle the advisory weekly posture for that service date."}
          </p>
        </div>
        <div className="schedule-heatmap__legend" aria-label="Preference legend">
          {PREFERENCE_STATE_CYCLE.map((state) => (
            <span key={state} className="schedule-heatmap__legend-item">
              <span
                className={`schedule-heatmap__legend-swatch ${PREFERENCE_STATE_UI[state].legendSwatchClassName}`}
              />
              {PREFERENCE_STATE_UI[state].label}
            </span>
          ))}
        </div>
      </header>
      {driverRows.length > 0 ? (
        <div className="schedule-heatmap__wrap">
          <table className="schedule-heatmap__table">
            <thead>
              <tr>
                <th scope="col">Driver</th>
                {serviceDates.map((serviceDate) => (
                  <th key={serviceDate.service_date} scope="col">
                    <span>{serviceDate.weekday_label}</span>
                    <strong>{serviceDate.label}</strong>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {driverRows.map((row) => (
                <tr key={row.driver_id}>
                  <td>
                    <div className="schedule-heatmap__person">
                      <strong>{row.driver_name}</strong>
                      <span>{row.driver_id}</span>
                      <span>
                        {row.employment_type || "Unknown employment"}
                        {row.on_call_eligible ? " · On-call eligible" : ""}
                      </span>
                      {onSelectDriver ? (
                        <button
                          type="button"
                          className="driver-preferences-heatmap__details-button"
                          aria-pressed={selectedDriverId === row.driver_id}
                          onClick={() => onSelectDriver(row)}
                        >
                          Details
                        </button>
                      ) : null}
                    </div>
                  </td>
                  {serviceDates.map((serviceDate, index) => {
                    const weekday = weekdays[index];
                    const state = weekday ? preferenceStateForWeekday(row, weekday) : "unset";
                    const stateUi = PREFERENCE_STATE_UI[state];
                    return (
                      <td key={`${row.driver_id}-${serviceDate.service_date}`}>
                        <button
                          type="button"
                          className={`schedule-heatmap__cell ${stateUi.toneClassName}${readOnly ? " schedule-heatmap__cell--readonly" : ""}`}
                          data-testid={`driver-preferences-cell-${serviceDate.service_date}-${row.driver_id}`}
                          aria-label={`${row.driver_name} on ${serviceDate.service_date}: ${stateUi.label}`}
                          aria-disabled={readOnly}
                          onClick={() => {
                            if (readOnly || !weekday || !setDriverRows) {
                              return;
                            }
                            setDriverRows((currentRows) =>
                              currentRows.map((currentRow) =>
                                currentRow.driver_id === row.driver_id
                                  ? {
                                      ...currentRow,
                                      preferences_by_weekday: {
                                        ...currentRow.preferences_by_weekday,
                                        [weekday]: nextPreferenceValue(
                                          preferenceStateForWeekday(currentRow, weekday)
                                        )
                                      }
                                    }
                                  : currentRow
                              )
                            );
                          }}
                        >
                          <span className="schedule-heatmap__cell-top">
                            <span className="schedule-heatmap__cell-state">{stateUi.shortLabel}</span>
                            {!readOnly ? (
                              <span className="schedule-heatmap__cell-chip">Click to cycle</span>
                            ) : null}
                          </span>
                          <span className="schedule-heatmap__cell-meta">{stateUi.label}</span>
                        </button>
                      </td>
                    );
                  })}
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

interface DriverAvailabilityExceptionDrawerProps {
  workflowRunId: string;
  driver: WorkpageDriverPreferencesDriverRow | null;
  serviceDates: WorkpageScheduleHeatmapDate[];
  exceptions: WorkpageDriverAvailabilityException[];
  addAction: WorkpageDriverPreferencesAction | null;
  hasUnsavedGridEdits: boolean;
}

function DriverAvailabilityExceptionDrawer({
  workflowRunId,
  driver,
  serviceDates,
  exceptions,
  addAction,
  hasUnsavedGridEdits
}: DriverAvailabilityExceptionDrawerProps): JSX.Element {
  const queryClient = useQueryClient();
  const defaultServiceDate = serviceDates[0]?.service_date ?? "";
  const [startDate, setStartDate] = useState(defaultServiceDate);
  const [endDate, setEndDate] = useState(defaultServiceDate);
  const [reasonCode, setReasonCode] =
    useState<WorkpageDriverAvailabilityException["reason_code"]>("wedding");
  const [reasonNote, setReasonNote] = useState("");
  const driverExceptions = useMemo(
    () =>
      exceptions
        .filter((item) => item.driver_id === driver?.driver_id)
        .sort((left, right) => left.start_date.localeCompare(right.start_date)),
    [driver?.driver_id, exceptions]
  );
  useEffect(() => {
    setStartDate(defaultServiceDate);
    setEndDate(defaultServiceDate);
    setReasonCode("wedding");
    setReasonNote("");
  }, [defaultServiceDate, driver?.driver_id]);

  const addMutation = useMutation({
    mutationFn: () => {
      if (!driver) {
        throw new Error("Select a driver before adding an exception.");
      }
      return workpagesRepository.addDriverAvailabilityException(
        workflowRunId,
        {
          driverId: driver.driver_id,
          startDate,
          endDate,
          reasonCode,
          reasonNote
        },
        addAction?.action_ref ?? undefined
      );
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void invalidateWorkspaceViews(queryClient, workflowRunId);
      setReasonNote("");
    }
  });
  const saveDisabled =
    !driver ||
    !startDate ||
    !endDate ||
    addAction?.state !== "available" ||
    addMutation.isPending;

  return (
    <section className="workpage-panel driver-availability-drawer" data-testid="driver-availability-exceptions-drawer">
      <header className="workpage-panel__header">
        <div>
          <h2>Availability exceptions</h2>
          <p>
            {driver
              ? `${driver.driver_name} · ${driver.driver_id}`
              : "Select a driver from the grid."}
          </p>
        </div>
      </header>

      {driver ? (
        <div className="driver-availability-drawer__layout">
          <div className="driver-availability-drawer__list">
            <h3>Upcoming approved</h3>
            {driverExceptions.length > 0 ? (
              <ul>
                {driverExceptions.map((item) => (
                  <li key={item.exception_id}>
                    <strong>
                      {item.start_date === item.end_date
                        ? item.start_date
                        : `${item.start_date} to ${item.end_date}`}
                    </strong>
                    <span>{formatReasonCode(item.reason_code)}</span>
                    {item.reason_note ? <p>{item.reason_note}</p> : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="workpage-history__empty">No approved exceptions for this driver.</p>
            )}
          </div>

          <form
            className="driver-availability-drawer__form"
            onSubmit={(event) => {
              event.preventDefault();
              addMutation.mutate();
            }}
          >
            <h3>Add exception</h3>
            <label>
              <span>Start date</span>
              <input
                type="date"
                value={startDate}
                required
                onChange={(event) => setStartDate(event.target.value)}
              />
            </label>
            <label>
              <span>End date</span>
              <input
                type="date"
                value={endDate}
                required
                onChange={(event) => setEndDate(event.target.value)}
              />
            </label>
            <label>
              <span>Reason</span>
              <select
                value={reasonCode}
                onChange={(event) =>
                  setReasonCode(
                    event.target.value as WorkpageDriverAvailabilityException["reason_code"]
                  )
                }
              >
                {AVAILABILITY_EXCEPTION_REASONS.map((reason) => (
                  <option key={reason} value={reason}>
                    {formatReasonCode(reason)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Note</span>
              <textarea
                value={reasonNote}
                rows={3}
                onChange={(event) => setReasonNote(event.target.value)}
              />
            </label>
            {hasUnsavedGridEdits ? (
              <p className="driver-availability-drawer__hint">Unsaved grid edits remain local.</p>
            ) : null}
            {addMutation.isError ? (
              <StatePanel
                kind="error"
                title="Exception save failed"
                detail={errorText(addMutation.error, "Unable to add availability exception.")}
              />
            ) : null}
            <div className="action-cluster">
              <button type="submit" className="action-btn action-btn--positive" disabled={saveDisabled}>
                {addMutation.isPending ? "Saving exception..." : "Save exception"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
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
      <DriverPreferencesHeatmap
        serviceDates={
          contract.preference_grid?.service_dates?.length
            ? contract.preference_grid.service_dates
            : fallbackServiceDates(
                contract.preference_grid?.weekdays ?? ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
              )
        }
        weekdays={contract.preference_grid?.weekdays ?? ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]}
        driverRows={contract.preference_grid?.drivers ?? []}
        readOnly
      />
      <section className="workpage-panel workpage-panel--callout">
        <header className="workpage-panel__header">
          <h2>Snapshot lifecycle</h2>
          <p>
            The first snapshot is created explicitly on demand. Seeded cells start with deterministic advisory posture and remain soft guidance only.
          </p>
        </header>
      </section>
    </WorkpageFrame>
  );
}

export function DriverPreferencesQuickEditModal({
  workflowRunId,
  onClose
}: {
  workflowRunId: string;
  onClose: () => void;
}): JSX.Element {
  const titleId = useId();
  const descriptionId = useId();
  const queryClient = useQueryClient();
  const [createdArtifactVersionId, setCreatedArtifactVersionId] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["workpages", "driver-preferences-v0", "run", workflowRunId],
    queryFn: () => workpagesRepository.driverPreferencesForRun(workflowRunId),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const openLatestAction = findDriverPreferencesAction(
    query.data,
    (action) =>
      action.kind === "open_latest" &&
      action.state === "available" &&
      Boolean(action.artifact_version_id)
  );
  const createAction = findDriverPreferencesAction(
    query.data,
    (action) =>
      action.kind === "create_snapshot" &&
      action.state === "available" &&
      Boolean(action.create_path)
  );
  const artifactVersionId = createdArtifactVersionId ?? openLatestAction?.artifact_version_id ?? null;
  const createMutation = useMutation({
    mutationFn: (payload: { createPath: string; actionRef: WorkpageDriverPreferencesAction["action_ref"] }) =>
      workpagesRepository.createWorkpage(payload.createPath, payload.actionRef ?? undefined),
    onSuccess: (created) => {
      setCreatedArtifactVersionId(created.artifact_version_id);
      void queryClient.invalidateQueries({ queryKey: ["workpages"] });
      void queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] });
      void invalidateWorkspaceViews(queryClient, created.workflow_run_id);
    }
  });

  useEffect(() => {
    setCreatedArtifactVersionId(null);
  }, [workflowRunId]);

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
        className="quick-edit-modal route-demand-quick-edit-modal driver-preferences-quick-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <header className="quick-edit-modal__header route-demand-quick-edit-modal__header">
          <div>
            <p className="timeline-page__eyebrow">Quick edit</p>
            <h2 id={titleId}>Drivers</h2>
            <p id={descriptionId}>
              Edit the current weekly driver-preferences snapshot without leaving this page.
            </p>
          </div>
          <button type="button" className="action-btn" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="quick-edit-modal__body route-demand-quick-edit-modal__body">
          {query.isLoading ? (
            <StatePanel
              kind="loading"
              title="Loading driver preferences"
              detail="Resolving the latest driver-preferences snapshot for this weekly run."
            />
          ) : query.isError ? (
            <StatePanel
              kind="error"
              title="Driver preferences failed to load"
              detail={errorText(query.error, "Unable to resolve the latest driver preferences snapshot.")}
              onRetry={() => {
                void query.refetch();
              }}
            />
          ) : artifactVersionId ? (
            <DriverPreferencesArtifactEditor
              workflowRunId={workflowRunId}
              artifactVersionId={artifactVersionId}
              layout="embedded"
              afterSave="close"
              onClose={onClose}
            />
          ) : createAction?.create_path ? (
            <section className="workpage-panel workpage-panel--callout">
              <header className="workpage-panel__header">
                <h2>Create the first preferences snapshot</h2>
                <p>
                  Driver editing starts by creating the immutable weekly preferences snapshot for
                  this run. Add-driver support is intentionally deferred to the next driver task.
                </p>
              </header>
              {createMutation.isError ? (
                <StatePanel
                  kind="error"
                  title="Snapshot create failed"
                  detail={errorText(createMutation.error, "Unable to create driver preferences snapshot.")}
                />
              ) : null}
              <div className="action-cluster">
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
                  {createMutation.isPending ? "Creating snapshot..." : "Create preferences snapshot"}
                </button>
              </div>
            </section>
          ) : (
            <StatePanel
              kind="error"
              title="Driver preferences are unavailable"
              detail="No editable driver-preferences snapshot is available for this weekly run yet."
            />
          )}
        </div>
      </section>
    </div>
  );
}

export function LogisticsDriverPreferencesArtifactWorkpagePage(): JSX.Element {
  const { workflowRunId, artifactVersionId } = useParams<{
    workflowRunId: string;
    artifactVersionId: string;
  }>();

  if (!workflowRunId || !artifactVersionId) {
    return (
      <StatePanel
        kind="error"
        title="Driver preferences snapshot route is incomplete"
        detail="Both the workflow run id and artifact version id are required."
      />
    );
  }

  return (
    <DriverPreferencesArtifactEditor
      workflowRunId={workflowRunId}
      artifactVersionId={artifactVersionId}
    />
  );
}

interface DriverPreferencesArtifactEditorProps {
  workflowRunId: string;
  artifactVersionId: string;
  layout?: "page" | "embedded";
  afterSave?: "navigate" | "close";
  onClose?: () => void;
}

function DriverPreferencesArtifactEditor({
  workflowRunId,
  artifactVersionId,
  layout = "page",
  afterSave = "navigate",
  onClose
}: DriverPreferencesArtifactEditorProps): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["workpages", "driver-preferences-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () =>
      workpagesRepository.driverPreferencesArtifact(workflowRunId, artifactVersionId),
    enabled: Boolean(workflowRunId && artifactVersionId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const contract = query.data;
  const saveAction = findDriverPreferencesAction(contract, (action) => action.kind === "save");
  const addExceptionAction = findDriverPreferencesAction(
    contract,
    (action) => action.kind === "add_availability_exception"
  );
  const { driverRows, setDriverRows } = useEditableDriverPreferencesGrid(contract);
  const [selectedDriverId, setSelectedDriverId] = useState<string | null>(null);
  useEffect(() => {
    if (driverRows.length === 0) {
      setSelectedDriverId(null);
      return;
    }
    if (!selectedDriverId || !driverRows.some((row) => row.driver_id === selectedDriverId)) {
      setSelectedDriverId(driverRows[0].driver_id);
    }
  }, [driverRows, selectedDriverId]);
  const selectedDriver =
    driverRows.find((row) => row.driver_id === selectedDriverId) ?? driverRows[0] ?? null;
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
        artifactVersionId,
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
      void queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] });
      void invalidateWorkspaceViews(queryClient, submitted.workflow_run_id);
      if (afterSave === "close") {
        onClose?.();
        return;
      }
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

  if (query.isError || !contract) {
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
  const artifactContext = contract.artifact_context;
  const latestArtifactVersionId =
    artifactContext?.latest_in_chain_artifact_version_id ?? artifactVersionId;
  const latestRoute =
    contract.artifact_history?.entries.find(
      (entry) => entry.artifact_version_id === latestArtifactVersionId
    )?.route ?? null;
  const submitConflict = workpageConflictDetails(submitMutation.error);
  const isStaleArtifact = latestArtifactVersionId !== artifactVersionId;
  const staleOrConflictRoute = submitConflict?.route ?? (isStaleArtifact ? latestRoute : null);
  const readOnly = contract.artifact_state?.editable === false || saveAction?.state !== "available";
  const saveDisabled =
    readOnly || isStaleArtifact || submitConflict !== null || !hasUnsavedEdits || submitMutation.isPending;

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
      testId={
        layout === "embedded"
          ? "driver-preferences-quick-edit-editor"
          : "driver-preferences-artifact-workpage-page"
      }
      metadataPresentation="dialog"
      infoDialogTitle="Driver preferences snapshot context"
      sourceDescription="Artifact-backed projection of an immutable weekly advisory preferences snapshot."
      heroTitleActions={
        <button
          type="button"
          className="action-btn action-btn--positive"
          disabled={saveDisabled}
          onClick={() => submitMutation.mutate()}
        >
          {submitMutation.isPending ? "Saving snapshot..." : "Save snapshot"}
        </button>
      }
      heroSupportText="Saving creates the next immutable driver-preferences snapshot and leaves schedule truth untouched."
      heroActions={
        layout === "page" ? (
          <div className="action-cluster">
            <Link className="link-button" to={driverPreferencesLandingRoute(workflowRunId)}>
              Back to preferences landing
            </Link>
            <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
              Open schedule landing
            </Link>
          </div>
        ) : undefined
      }
      infoDialogContent={
        <>
          {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
          {historySection ? <WorkpageHistorySection section={historySection} /> : null}
        </>
      }
      backLink={backRoute.href}
      backLabel={backRoute.label}
      layout={layout}
      heroTitle={layout === "embedded" ? "Driver Preferences Snapshot" : undefined}
      heroPresentation={layout === "embedded" ? "title_only" : "default"}
    >
      {submitConflict ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Latest snapshot already exists</h2>
            <p>
              This base preferences snapshot has already been superseded. Keep your local edits for
              now, then reopen the latest snapshot before saving again.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={submitConflict.route}>
              Open latest snapshot
            </Link>
          </div>
        </section>
      ) : null}

      {!submitConflict && isStaleArtifact && staleOrConflictRoute ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Latest snapshot available</h2>
            <p>
              This snapshot version is no longer the latest in the chain. Reopen the latest version
              before saving more changes.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={staleOrConflictRoute}>
              Open latest snapshot
            </Link>
          </div>
        </section>
      ) : null}

      {submitMutation.isError && !submitConflict ? (
        <StatePanel
          kind="error"
          title="Snapshot save failed"
          detail={errorText(
            submitMutation.error,
            "Unable to save the artifact-backed driver preferences snapshot."
          )}
        />
      ) : null}

      {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}
      <DriverPreferencesScheduleImpactBanner
        scheduleImpact={contract.schedule_impact as WorkpageDriverPreferencesScheduleImpact | null}
        workflowRunId={workflowRunId}
      />
      <DriverPreferencesHeatmap
        serviceDates={
          contract.preference_grid?.service_dates?.length
            ? contract.preference_grid.service_dates
            : fallbackServiceDates(
                contract.preference_grid?.weekdays ?? ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
              )
        }
        weekdays={contract.preference_grid?.weekdays ?? ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]}
        driverRows={driverRows}
        setDriverRows={setDriverRows}
        readOnly={readOnly}
        selectedDriverId={selectedDriver?.driver_id ?? null}
        onSelectDriver={(driver) => setSelectedDriverId(driver.driver_id)}
      />
      <DriverAvailabilityExceptionDrawer
        workflowRunId={workflowRunId}
        driver={selectedDriver}
        serviceDates={
          contract.preference_grid?.service_dates?.length
            ? contract.preference_grid.service_dates
            : fallbackServiceDates(
                contract.preference_grid?.weekdays ?? ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
              )
        }
        exceptions={contract.driver_availability_exceptions?.items ?? []}
        addAction={addExceptionAction}
        hasUnsavedGridEdits={hasUnsavedEdits}
      />
      <DriverPreferencesHistoryRail
        artifactHistory={contract.artifact_history}
        currentArtifactVersionId={artifactVersionId}
      />
    </WorkpageFrame>
  );
}
