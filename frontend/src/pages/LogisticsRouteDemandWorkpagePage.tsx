import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type Dispatch, type SetStateAction, useEffect, useId, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

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
import {
  mergeWorkpageActionRef,
  replaceWorkpageActionRefArtifactVersionId,
  resolveWorkpageActionRef
} from "@/lib/workspace/workpageActionRef";
import type { WorkpageContract } from "@/lib/types/contracts";
import type {
  WorkpageAction,
  WorkpageArtifactHistory,
  WorkpageHistorySection as WorkpageHistorySectionModel,
  WorkpageNotePanelSection as WorkpageNotePanelSectionModel,
  WorkpageRouteDemandAction,
  WorkpageRouteDemandDayCard,
  WorkpageRouteDemandScheduleImpact,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableSection as WorkpageTableSectionModel
} from "@/lib/types/workpages";

function routeDemandLandingRoute(workflowRunId: string): string {
  return `/runs/${workflowRunId}/workpages/route-demand-v0`;
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

function findTableSection(
  sections: WorkpageContract["workpage"]["sections"],
  tableId: string
): WorkpageTableSectionModel | null {
  return (
    sections.find(
      (section): section is WorkpageTableSectionModel =>
        section.kind === "table" && section.table_id === tableId
    ) ?? null
  );
}

function isRouteDemandAction(action: WorkpageAction): action is WorkpageRouteDemandAction {
  return action.workpage_kind === "route-demand-v0";
}

function findRouteDemandAction(
  contract: WorkpageContract | undefined,
  matcher: (action: WorkpageRouteDemandAction) => boolean
): WorkpageRouteDemandAction | null {
  return (
    contract?.actions.find(
      (action): action is WorkpageRouteDemandAction => isRouteDemandAction(action) && matcher(action)
    ) ?? null
  );
}

function routeDemandDayCardSignature(dayCards: WorkpageRouteDemandDayCard[]): string {
  return JSON.stringify(
    dayCards.map((card) => ({
      service_date: card.service_date,
      planned_route_count: card.planned_route_count,
      on_call_target: card.on_call_target
    }))
  );
}

function visibleRouteDemandDayCards(
  dayCards: WorkpageRouteDemandDayCard[]
): WorkpageRouteDemandDayCard[] {
  return dayCards.slice(0, 7);
}

function positiveRouteDemandIncreaseCount(
  baseDayCards: WorkpageRouteDemandDayCard[],
  currentDayCards: WorkpageRouteDemandDayCard[]
): number {
  const currentByDate = new Map(
    visibleRouteDemandDayCards(currentDayCards).map((card) => [card.service_date, card])
  );
  return visibleRouteDemandDayCards(baseDayCards).reduce((total, card) => {
    const current = currentByDate.get(card.service_date);
    if (!current) {
      return total;
    }
    return total + Math.max(current.planned_route_count - card.planned_route_count, 0);
  }, 0);
}

function hasPositiveFutureWeekDemand(dayCards: WorkpageRouteDemandDayCard[]): boolean {
  return visibleRouteDemandDayCards(dayCards).some(
    (card) => card.planned_route_count > 0 || card.on_call_target > 0
  );
}

function routeDemandDisabledReasonText(reason: string | null | undefined): string | null {
  if (!reason) {
    return null;
  }
  if (reason === "continue_from_schedule") {
    return "This future week already has weekly schedule draft truth. Continue from the schedule workpage instead of editing route demand here.";
  }
  if (reason === "historical_artifact_read_only") {
    return "This route-demand version is historical and can no longer be edited.";
  }
  return reason;
}

function routeDemandMutationErrorDetail(
  actionLabel: string,
  error: unknown,
  fallback: string
): string {
  return `${actionLabel} failed. ${errorText(error, fallback)}`;
}

function useEditableRouteDemandDayCards(
  contract: WorkpageContract | undefined
): {
  dayCards: WorkpageRouteDemandDayCard[];
  setDayCards: Dispatch<SetStateAction<WorkpageRouteDemandDayCard[]>>;
} {
  const [dayCards, setDayCards] = useState<WorkpageRouteDemandDayCard[]>([]);
  const resetKey = useMemo(
    () =>
      [
        contract?.freshness.source_version ?? "",
        contract?.artifact_context?.artifact_version_id ?? "",
        routeDemandDayCardSignature(contract?.route_demand_calculations?.day_cards ?? [])
      ].join(":"),
    [contract]
  );

  useEffect(() => {
    setDayCards((contract?.route_demand_calculations?.day_cards ?? []).map((card) => ({ ...card })));
  }, [resetKey, contract]);

  return { dayCards, setDayCards };
}

function RouteDemandScheduleImpactBanner({
  contract,
  workflowRunId
}: {
  contract: WorkpageContract;
  workflowRunId?: string;
}): JSX.Element | null {
  const scheduleImpact = contract.schedule_impact;
  const routeDemandScheduleImpact = scheduleImpact as WorkpageRouteDemandScheduleImpact | null;
  if (!routeDemandScheduleImpact) {
    return null;
  }
  const latestScheduleDraftArtifactVersionId =
    routeDemandScheduleImpact.latest_schedule_draft_artifact_version_id;
  const scheduleDraftRoute =
    workflowRunId && latestScheduleDraftArtifactVersionId
      ? scheduleArtifactRoute(workflowRunId, latestScheduleDraftArtifactVersionId)
      : null;
  const stateCopy: Record<string, { title: string; detail: string }> = {
    aligned: {
      title: "Latest schedule draft is aligned",
      detail:
        "The latest schedule draft is already pinned to the latest route-demand artifact for this weekly run."
    },
    drifted: {
      title: "Latest schedule draft is stale",
      detail:
        "The latest schedule draft still points at an older route-demand artifact and needs a refresh before publish."
    },
    awaiting_refresh: {
      title: "Refresh follow-up is open",
      detail:
        "A Stage04 refresh work item is already open for the stale schedule draft. Route-demand save did not mutate any schedule artifact."
    },
    no_draft: {
      title: "No schedule draft exists yet",
      detail:
        "Route-demand edits are saved independently. A schedule draft has not been created for this run yet."
    }
  };
  const stateDetails =
    stateCopy[routeDemandScheduleImpact.schedule_state] ??
    stateCopy[routeDemandScheduleImpact.dependency_state] ??
    {
      title: "Schedule impact available",
      detail: "The backend reported the latest schedule draft posture for this route-demand surface."
    };

  return (
    <section className="workpage-panel route-demand-impact-banner" data-testid="route-demand-schedule-impact">
      <header className="workpage-panel__header">
        <h2>Schedule impact</h2>
        <p>{stateDetails.detail}</p>
      </header>
      <div className="route-demand-impact-banner__grid">
        <article>
          <strong>Status</strong>
          <p>{stateDetails.title}</p>
        </article>
        <article>
          <strong>Dependency state</strong>
          <p>{routeDemandScheduleImpact.dependency_state}</p>
        </article>
        <article>
          <strong>Latest schedule draft</strong>
          <p>{latestScheduleDraftArtifactVersionId ?? "No draft yet"}</p>
        </article>
        <article>
          <strong>Refresh task</strong>
          <p>{routeDemandScheduleImpact.refresh_task?.human_task_id ?? "No refresh task"}</p>
        </article>
      </div>
      <div className="action-cluster">
        {scheduleDraftRoute ? (
          <Link className="link-button" to={scheduleDraftRoute}>
            Open latest schedule draft
          </Link>
        ) : (
          <Link className="link-button" to={workflowRunId ? scheduleLandingRoute(workflowRunId) : "/runs"}>
            Open schedule landing
          </Link>
        )}
      </div>
    </section>
  );
}

function RouteDemandHistoryRail({
  artifactHistory,
  currentArtifactVersionId
}: {
  artifactHistory: WorkpageArtifactHistory | null;
  currentArtifactVersionId?: string;
}): JSX.Element {
  const historyEntries = artifactHistory?.entries ?? [];
  return (
    <section className="workpage-panel" data-testid="route-demand-history-rail">
      <header className="workpage-panel__header">
        <h2>Recent route demand versions</h2>
        <p>The history rail stays within backend-authored immutable route-demand workbook lineage for this weekly run.</p>
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
                data-testid={`route-demand-history-${entry.artifact_version_id}`}
                to={entry.route}
              >
                <strong>{isCurrent ? "Current route demand" : entry.artifact_version_id}</strong>
                <span>{entry.created_at}</span>
                <span>{entry.lineage_note ?? "Route-demand version"}</span>
              </Link>
            );
          })}
        </div>
      ) : (
        <p className="route-demand-history-list__empty">No route-demand history is available yet.</p>
      )}
    </section>
  );
}

function RouteDemandDayCards({
  dayCards,
  editable,
  onIncrement,
  onDecrement,
  onIncrementOnCall,
  onDecrementOnCall,
  showHeader = true
}: {
  dayCards: WorkpageRouteDemandDayCard[];
  editable: boolean;
  onIncrement?: (serviceDate: string) => void;
  onDecrement?: (serviceDate: string) => void;
  onIncrementOnCall?: (serviceDate: string) => void;
  onDecrementOnCall?: (serviceDate: string) => void;
  showHeader?: boolean;
}): JSX.Element {
  const dayCardGroups = useMemo(() => groupRouteDemandDayCards(dayCards), [dayCards]);
  const firstServiceDate = dayCards[0]?.service_date ?? null;
  const lastServiceDate = dayCards[dayCards.length - 1]?.service_date ?? null;

  return (
    <section className="workpage-panel" data-testid="route-demand-day-cards">
      {showHeader ? (
        <header className="workpage-panel__header">
          <h2>Daily route demand</h2>
          <p>
            Route-demand edits change planned daily route counts and on-call targets only.
            Rescue, overflow, and excess-capacity posture stay server-managed.
          </p>
        </header>
      ) : null}
      {firstServiceDate && lastServiceDate ? (
        <div className="route-demand-horizon-summary" data-testid="route-demand-horizon-summary">
          <strong>{dayCards.length} service days</strong>
          <span>{firstServiceDate} to {lastServiceDate}</span>
        </div>
      ) : null}
      <div className="route-demand-week-groups">
        {dayCardGroups.map((group) => (
          <section
            key={group.key}
            className="route-demand-week-group"
            aria-label={`${group.label}: ${group.dateRange}`}
          >
            {dayCardGroups.length > 1 ? (
              <header className="route-demand-week-group__header">
                <h3>{group.label}</h3>
                <span>{group.dateRange}</span>
              </header>
            ) : null}
            <div className="route-demand-day-grid">
              {group.dayCards.map((card) => (
                <article key={card.service_date} className="route-demand-day-card">
                  <header className="route-demand-day-card__header">
                    <div>
                      <p className="route-demand-day-card__eyebrow">{card.weekday_label}</p>
                      <h3>{card.service_date}</h3>
                    </div>
                    {card.delta_from_previous_version ? (
                      <span
                        className={`route-demand-day-card__delta${
                          card.delta_from_previous_version.planned_route_count_delta === 0
                            ? " route-demand-day-card__delta--neutral"
                            : card.delta_from_previous_version.planned_route_count_delta > 0
                              ? " route-demand-day-card__delta--up"
                              : " route-demand-day-card__delta--down"
                        }`}
                      >
                        {card.delta_from_previous_version.planned_route_count_delta >= 0 ? "+" : ""}
                        {card.delta_from_previous_version.planned_route_count_delta}
                      </span>
                    ) : null}
                  </header>
                  <div className="route-demand-day-card__count">
                    <strong>Planned routes</strong>
                    <div className="route-demand-stepper">
                      {editable ? (
                        <button
                          type="button"
                          className="action-btn"
                          aria-label={`Decrease planned routes for ${card.service_date}`}
                          onClick={() => onDecrement?.(card.service_date)}
                          disabled={card.planned_route_count <= 0}
                        >
                          -
                        </button>
                      ) : null}
                      <span data-testid={`route-demand-count-${card.service_date}`}>
                        {card.planned_route_count}
                      </span>
                      {editable ? (
                        <button
                          type="button"
                          className="action-btn"
                          aria-label={`Increase planned routes for ${card.service_date}`}
                          onClick={() => onIncrement?.(card.service_date)}
                        >
                          +
                        </button>
                      ) : null}
                    </div>
                  </div>
                  <dl className="route-demand-day-card__stats">
                    <div>
                      <dt>Standard</dt>
                      <dd>{card.standard_slot_count}</dd>
                    </div>
                    <div>
                      <dt>Early / late</dt>
                      <dd>
                        {card.standard_early_slot_count} / {card.standard_late_slot_count}
                      </dd>
                    </div>
                    <div>
                      <dt>Rescue / overflow</dt>
                      <dd>
                        {card.rescue_slot_count} / {card.overflow_slot_count}
                      </dd>
                    </div>
                    <div>
                      <dt>On-call target</dt>
                      <dd>
                        {editable ? (
                          <div className="route-demand-stepper">
                            <button
                              type="button"
                              className="action-btn"
                              aria-label={`Decrease on-call target for ${card.service_date}`}
                              onClick={() => onDecrementOnCall?.(card.service_date)}
                              disabled={card.on_call_target <= 0}
                            >
                              -
                            </button>
                            <span data-testid={`route-demand-on-call-target-${card.service_date}`}>
                              {card.on_call_target}
                            </span>
                            <button
                              type="button"
                              className="action-btn"
                              aria-label={`Increase on-call target for ${card.service_date}`}
                              onClick={() => onIncrementOnCall?.(card.service_date)}
                            >
                              +
                            </button>
                          </div>
                        ) : (
                          <span data-testid={`route-demand-on-call-target-${card.service_date}`}>
                            {card.on_call_target}
                          </span>
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Excess capacity target</dt>
                      <dd>{card.excess_capacity_target}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

type RouteDemandDayCardGroup = {
  key: string;
  label: string;
  dateRange: string;
  dayCards: WorkpageRouteDemandDayCard[];
};

function groupRouteDemandDayCards(
  dayCards: WorkpageRouteDemandDayCard[]
): RouteDemandDayCardGroup[] {
  const groups: RouteDemandDayCardGroup[] = [];
  for (let index = 0; index < dayCards.length; index += 7) {
    const groupDayCards = dayCards.slice(index, index + 7);
    const firstServiceDate = groupDayCards[0]?.service_date ?? "";
    const lastServiceDate =
      groupDayCards[groupDayCards.length - 1]?.service_date ?? firstServiceDate;
    groups.push({
      key: `${firstServiceDate}-${lastServiceDate}`,
      label: `Week ${Math.floor(index / 7) + 1}`,
      dateRange:
        firstServiceDate === lastServiceDate
          ? firstServiceDate
          : `${firstServiceDate} to ${lastServiceDate}`,
      dayCards: groupDayCards
    });
  }
  return groups;
}

function RouteDemandWorkpageBody({
  contract,
  workflowRunId,
  artifactHistory,
  editableDayCards,
  onIncrement,
  onDecrement,
  onIncrementOnCall,
  onDecrementOnCall,
  presentation = "full"
}: {
  contract: WorkpageContract;
  workflowRunId?: string;
  artifactHistory?: WorkpageArtifactHistory | null;
  editableDayCards?: WorkpageRouteDemandDayCard[];
  onIncrement?: (serviceDate: string) => void;
  onDecrement?: (serviceDate: string) => void;
  onIncrementOnCall?: (serviceDate: string) => void;
  onDecrementOnCall?: (serviceDate: string) => void;
  presentation?: "full" | "daily_only";
}): JSX.Element {
  const summarySection = findSummarySection(contract.workpage.sections);
  const noteSection = findNoteSection(contract.workpage.sections);
  const historySection = findHistorySection(contract.workpage.sections);
  const editable = Boolean(contract.artifact_state?.editable);
  const dayCards = visibleRouteDemandDayCards(
    editableDayCards ?? contract.route_demand_calculations?.day_cards ?? []
  );
  const rawDailyTable = findTableSection(contract.workpage.sections, "route_demand_daily_rows");

  if (presentation === "daily_only") {
    return (
      <RouteDemandDayCards
        dayCards={dayCards}
        editable={editable}
        onIncrement={onIncrement}
        onDecrement={onDecrement}
        onIncrementOnCall={onIncrementOnCall}
        onDecrementOnCall={onDecrementOnCall}
        showHeader={false}
      />
    );
  }

  return (
    <>
      {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}
      <RouteDemandScheduleImpactBanner contract={contract} workflowRunId={workflowRunId} />
      <RouteDemandDayCards
        dayCards={dayCards}
        editable={editable}
        onIncrement={onIncrement}
        onDecrement={onDecrement}
        onIncrementOnCall={onIncrementOnCall}
        onDecrementOnCall={onDecrementOnCall}
      />
      {artifactHistory && workflowRunId ? (
        <RouteDemandHistoryRail
          artifactHistory={artifactHistory}
          currentArtifactVersionId={contract.artifact_context?.artifact_version_id ?? undefined}
        />
      ) : null}
      {noteSection ? <WorkpageNotePanelSection section={noteSection} /> : null}
      {rawDailyTable ? (
        <section className="workpage-panel route-demand-raw-table">
          <header className="workpage-panel__header">
            <h2>Raw route-demand table</h2>
            <p>Backend-authored workbook rows remain visible here for audit and debugging.</p>
          </header>
          <div className="workpage-page__source-grid">
            {rawDailyTable.rows.map((row, index) => (
              <article key={`${row.service_date ?? "day"}-${index}`} className="workpage-page__source-item">
                <strong>{String(row.service_date ?? `Day ${index + 1}`)}</strong>
                <p>{`planned ${String(row.planned_route_count ?? "0")} · standard ${String(
                  row.standard_slot_count ?? "0"
                )} · rescue ${String(row.rescue_slot_count ?? "0")} · overflow ${String(
                  row.overflow_slot_count ?? "0"
                )}`}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {historySection ? <WorkpageHistorySection section={historySection} /> : null}
    </>
  );
}

export function LogisticsRouteDemandWorkpagePage(): JSX.Element {
  const { workflowRunId } = useParams<{ workflowRunId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [createNextWeekErrorMessage, setCreateNextWeekErrorMessage] = useState<string | null>(
    null
  );
  const query = useQuery({
    queryKey: ["workpages", "route-demand-v0", "run", workflowRunId],
    queryFn: () => workpagesRepository.routeDemandForRun(workflowRunId ?? ""),
    enabled: Boolean(workflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const createNextWeekMutation = useMutation({
    mutationFn: (input: { createPath: string; actionRef: WorkpageRouteDemandAction["action_ref"] }) =>
      workpagesRepository.createRouteDemandNextWeekAtPath(
        input.createPath,
        workflowRunId ?? "",
        input.actionRef ?? undefined
      )
  });

  useEffect(() => {
    setCreateNextWeekErrorMessage(null);
  }, [workflowRunId, query.data?.freshness.generated_at]);

  if (!workflowRunId) {
    return (
      <StatePanel
        kind="error"
        title="Route demand route is incomplete"
        detail="A workflow run id is required for route-demand workpages."
      />
    );
  }

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading route demand workpage"
        detail="Fetching the workflow-run-backed route-demand landing page."
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <StatePanel
        kind="error"
        title="Route demand workpage failed to load"
        detail={errorText(query.error, "Unable to load the run-backed route-demand workpage.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const openLatestAction = findRouteDemandAction(
    query.data,
    (action) => action.kind === "open_latest"
  );
  const addNextWeekAction = findRouteDemandAction(
    query.data,
    (action) => action.kind === "add_next_week"
  );
  const backRoute = workpageBackRoute(workflowRunId);

  async function handleAddNextWeekFromLanding(): Promise<void> {
    if (!addNextWeekAction?.create_path) {
      return;
    }
    setCreateNextWeekErrorMessage(null);
    try {
      const carriedActionRef = resolveWorkpageActionRef(location.state, {
        workflowRunId,
        workpageKind: "route-demand-v0",
        artifactVersionId: null
      });
      const actionRef = mergeWorkpageActionRef(
        addNextWeekAction.action_ref ?? null,
        carriedActionRef ?? null
      );
      const created = await createNextWeekMutation.mutateAsync({
        createPath: addNextWeekAction.create_path,
        actionRef: actionRef ?? null
      });
      await queryClient.invalidateQueries({ queryKey: ["workpages"] });
      await queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] });
      await invalidateWorkspaceViews(queryClient, created.workflow_run_id);
      setCreateNextWeekErrorMessage(null);
      navigate(created.route, {
        state: {
          workpageActionRef: actionRef
        }
      });
    } catch (error) {
      setCreateNextWeekErrorMessage(
        routeDemandMutationErrorDetail(
          "Add a week",
          error,
          "Unable to create the next weekly route-demand surface."
        )
      );
    }
  }

  return (
    <WorkpageFrame
      eyebrow="Route Demand Landing"
      description="A read-only weekly landing page for backend-owned route-demand truth. Open the latest immutable artifact when you need to edit final daily counts."
      summaryItems={[
        `Week ${String(query.data.workpage.summary.planning_week_id ?? "unknown")}`,
        `${String(query.data.workpage.summary.service_day_count ?? 0)} service days`,
        `${String(query.data.workpage.summary.planned_route_total ?? 0)} planned routes`
      ]}
      model={query.data.workpage}
      source={query.data.source}
      freshness={query.data.freshness}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching || createNextWeekMutation.isPending}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId="route-demand-workpage-page"
      metadataPresentation="dialog"
      infoDialogTitle="Route demand context"
      sourceDescription="Workflow-run-backed route-demand projection served from the latest canonical Stage04 route-demand artifact for this weekly run."
      backLink={backRoute.href}
      backLabel={backRoute.label}
      heroActions={
        addNextWeekAction?.create_path ? (
          <button
            type="button"
            className="action-btn action-btn--positive"
            disabled={addNextWeekAction.state !== "available" || createNextWeekMutation.isPending}
            onClick={() => {
              void handleAddNextWeekFromLanding();
            }}
          >
            {createNextWeekMutation.isPending ? "Adding week..." : "Add a week"}
          </button>
        ) : undefined
      }
    >
      {createNextWeekErrorMessage ? (
        <section
          className="workpage-panel workpage-panel--callout"
          data-testid="route-demand-mutation-error"
        >
          <header className="workpage-panel__header">
            <h2>Action failed</h2>
            <p>{createNextWeekErrorMessage}</p>
          </header>
        </section>
      ) : null}
      {openLatestAction?.route ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Editable route demand available</h2>
            <p>
              This landing page stays read-only. Open the latest immutable route-demand artifact to
              adjust final daily counts and create a new successor version.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={openLatestAction.route}>
              Open route demand editor
            </Link>
          </div>
        </section>
      ) : null}
      <RouteDemandWorkpageBody contract={query.data} workflowRunId={workflowRunId} />
    </WorkpageFrame>
  );
}

interface RouteDemandArtifactEditorProps {
  workflowRunId: string;
  artifactVersionId: string;
  layout?: "page" | "embedded";
  afterSave?: "navigate" | "close" | "stay";
  onClose?: () => void;
  onArtifactContextChange?: (input: {
    workflowRunId: string;
    artifactVersionId: string;
    afterSave: "navigate" | "close" | "stay";
  }) => void;
}

function RouteDemandArtifactEditor({
  workflowRunId,
  artifactVersionId,
  layout = "page",
  afterSave = "navigate",
  onClose,
  onArtifactContextChange
}: RouteDemandArtifactEditorProps): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["workpages", "route-demand-v0", "artifacts", workflowRunId, artifactVersionId],
    queryFn: () =>
      workpagesRepository.routeDemandArtifact(workflowRunId, artifactVersionId),
    enabled: Boolean(workflowRunId && artifactVersionId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const { dayCards, setDayCards } = useEditableRouteDemandDayCards(query.data);
  const [mutationErrorMessage, setMutationErrorMessage] = useState<string | null>(null);

  const saveAction = findRouteDemandAction(query.data, (action) => action.kind === "save");
  const addNextWeekAction = findRouteDemandAction(
    query.data,
    (action) => action.kind === "add_next_week"
  );
  const saveAndRunAction = findRouteDemandAction(
    query.data,
    (action) => action.kind === "save_and_run"
  );
  const scheduleAction = query.data?.schedule_impact?.latest_schedule_draft_artifact_version_id
    ? {
        route: scheduleArtifactRoute(
          workflowRunId,
          query.data.schedule_impact.latest_schedule_draft_artifact_version_id
        )
      }
    : null;
  const baseSignature = routeDemandDayCardSignature(query.data?.route_demand_calculations?.day_cards ?? []);
  const currentSignature = routeDemandDayCardSignature(dayCards);
  const hasUnsavedEdits = baseSignature !== currentSignature;
  const positiveIncreaseCount = positiveRouteDemandIncreaseCount(
    query.data?.route_demand_calculations?.day_cards ?? [],
    dayCards
  );
  const futureWeekDemandAvailable = hasPositiveFutureWeekDemand(dayCards);
  const latestArtifactVersionId =
    query.data?.artifact_context?.latest_in_chain_artifact_version_id ?? artifactVersionId;
  const latestArtifactRoute =
    query.data?.artifact_history?.entries.find(
      (entry) => entry.artifact_version_id === latestArtifactVersionId
    )?.route ?? null;
  const isStaleArtifact = Boolean(
    latestArtifactVersionId && latestArtifactVersionId !== artifactVersionId
  );
  const futureWeekOption = query.data?.future_week_options[0] ?? null;
  const futureWeekActivation = query.data?.future_week_activation ?? null;
  const isFutureWeekArtifact = !futureWeekOption;
  const submitMutation = useMutation({
    mutationFn: (input: {
      submitPath: string;
      actionRef: WorkpageRouteDemandAction["action_ref"];
    }) =>
      workpagesRepository.submitRouteDemandArtifactAtPath(
        input.submitPath,
        artifactVersionId,
        {
          dailyDemandRows: dayCards.map((card) => ({
            service_date: card.service_date,
            planned_route_count: card.planned_route_count,
            on_call_target: card.on_call_target
          }))
        },
        input.actionRef ?? undefined
      )
  });
  const createNextWeekMutation = useMutation({
    mutationFn: (input: {
      createPath: string;
      actionRef: WorkpageRouteDemandAction["action_ref"];
    }) =>
      workpagesRepository.createRouteDemandNextWeekAtPath(
        input.createPath,
        workflowRunId,
        input.actionRef ?? undefined
      )
  });
  const saveAndRunMutation = useMutation({
    mutationFn: (input: {
      submitPath: string;
      actionRef: WorkpageRouteDemandAction["action_ref"];
    }) =>
      workpagesRepository.saveAndRunRouteDemandArtifactAtPath(
        input.submitPath,
        artifactVersionId,
        {
          dailyDemandRows: dayCards.map((card) => ({
            service_date: card.service_date,
            planned_route_count: card.planned_route_count,
            on_call_target: card.on_call_target
          }))
        },
        input.actionRef ?? undefined
      )
  });

  useEffect(() => {
    setMutationErrorMessage(null);
  }, [workflowRunId, artifactVersionId, query.data?.freshness.generated_at]);

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading route demand artifact"
        detail="Fetching the artifact-backed route-demand editor."
      />
    );
  }

  if (query.isError || !query.data) {
    return (
      <StatePanel
        kind="error"
        title="Route demand artifact failed to load"
        detail={errorText(query.error, "Unable to load the artifact-backed route-demand workpage.")}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const editable = Boolean(query.data.artifact_state?.editable);
  const canSave = editable && !isStaleArtifact && saveAction?.state === "available";
  const canAddNextWeek =
    !isStaleArtifact &&
    addNextWeekAction?.state === "available" &&
    Boolean(addNextWeekAction.create_path);
  const canSaveAndRun =
    !isStaleArtifact &&
    saveAndRunAction?.state === "available" &&
    Boolean(saveAndRunAction.submit_path) &&
    hasUnsavedEdits &&
    (isFutureWeekArtifact ? futureWeekDemandAvailable : positiveIncreaseCount > 0);
  const backRoute = workpageBackRoute(workflowRunId);
  const isMutationPending =
    submitMutation.isPending || createNextWeekMutation.isPending || saveAndRunMutation.isPending;
  const futureWeekStatusText =
    saveAndRunMutation.isPending || futureWeekActivation?.state === "running"
      ? "Agent working"
      : futureWeekActivation?.status_label ?? null;

  function routeDemandActionRef(
    action: WorkpageRouteDemandAction | null,
    targetArtifactVersionId: string | null
  ): WorkpageRouteDemandAction["action_ref"] {
    const carriedActionRef = resolveWorkpageActionRef(location.state, {
      workflowRunId,
      workpageKind: "route-demand-v0",
      artifactVersionId: targetArtifactVersionId
    });
    return mergeWorkpageActionRef(action?.action_ref ?? null, carriedActionRef ?? null) ?? null;
  }

  async function invalidateRouteDemandState(targetWorkflowRunId: string): Promise<void> {
    await queryClient.invalidateQueries({ queryKey: ["workpages"] });
    await queryClient.invalidateQueries({ queryKey: ["logistics-demo-story"] });
    await invalidateWorkspaceViews(queryClient, targetWorkflowRunId);
  }

  async function handleSaveRouteDemand(
    nextAfterSave: "navigate" | "close" | "stay"
  ): Promise<boolean> {
    if (!saveAction?.submit_path) {
      return false;
    }
    setMutationErrorMessage(null);
    try {
      const actionRef = routeDemandActionRef(saveAction, artifactVersionId);
      const submitted = await submitMutation.mutateAsync({
        submitPath: saveAction.submit_path,
        actionRef
      });
      await invalidateRouteDemandState(submitted.workflow_run_id);
      setMutationErrorMessage(null);
      if (nextAfterSave === "close") {
        onClose?.();
        return true;
      }
      if (nextAfterSave === "stay") {
        onArtifactContextChange?.({
          workflowRunId: submitted.workflow_run_id,
          artifactVersionId: submitted.artifact_version_id,
          afterSave: "stay"
        });
        return true;
      }
      navigate(submitted.route, {
        state: {
          workpageActionRef: replaceWorkpageActionRefArtifactVersionId(
            actionRef,
            submitted.artifact_version_id
          )
        }
      });
      return true;
    } catch (error) {
      setMutationErrorMessage(
        routeDemandMutationErrorDetail(
          "Save route demand",
          error,
          "Unable to save the latest route-demand changes."
        )
      );
      return false;
    }
  }

  async function handleAddNextWeek(): Promise<void> {
    if (!addNextWeekAction?.create_path) {
      return;
    }
    if (hasUnsavedEdits) {
      const shouldSaveFirst = window.confirm(
        "Save current route-demand changes before switching to the next week? Press Cancel to discard the current edits and continue."
      );
      if (shouldSaveFirst) {
        const saved = await handleSaveRouteDemand("stay");
        if (!saved) {
          return;
        }
      }
    }
    setMutationErrorMessage(null);
    try {
      const actionRef = routeDemandActionRef(addNextWeekAction, null);
      const created = await createNextWeekMutation.mutateAsync({
        createPath: addNextWeekAction.create_path,
        actionRef
      });
      await invalidateRouteDemandState(created.workflow_run_id);
      setMutationErrorMessage(null);
      if (layout === "embedded" && onArtifactContextChange) {
        onArtifactContextChange({
          workflowRunId: created.workflow_run_id,
          artifactVersionId: created.artifact_version_id,
          afterSave: "stay"
        });
        return;
      }
      navigate(created.route, {
        state: {
          workpageActionRef: actionRef
        }
      });
    } catch (error) {
      setMutationErrorMessage(
        routeDemandMutationErrorDetail(
          "Add a week",
          error,
          "Unable to create the next weekly route-demand surface."
        )
      );
    }
  }

  async function handleSaveAndRun(): Promise<void> {
    if (!saveAndRunAction?.submit_path) {
      return;
    }
    setMutationErrorMessage(null);
    try {
      const actionRef = routeDemandActionRef(saveAndRunAction, artifactVersionId);
      const submitted = await saveAndRunMutation.mutateAsync({
        submitPath: saveAndRunAction.submit_path,
        actionRef
      });
      const targetWorkflowRunId = submitted.target_workflow_run_id ?? submitted.workflow_run_id;
      const targetScheduleRoute =
        submitted.target_schedule_route ?? scheduleLandingRoute(targetWorkflowRunId);
      await invalidateRouteDemandState(targetWorkflowRunId);
      setMutationErrorMessage(null);
      onClose?.();
      navigate(targetScheduleRoute, {
        state: {
          openScheduleQuickEdit: true,
          targetScheduleArtifactVersionId:
            submitted.target_schedule_artifact_version_id ?? null,
          routeDemandCoverageContext: submitted.route_demand_coverage_context ?? null,
          scheduleComparisonModeHint: isFutureWeekArtifact ? "future_week" : null
        }
      });
    } catch (error) {
      setMutationErrorMessage(
        routeDemandMutationErrorDetail(
          saveAndRunAction?.label ?? "Run coverage agent",
          error,
          "Unable to continue from route demand into weekly schedule coverage."
        )
      );
    }
  }

  return (
    <WorkpageFrame
      eyebrow="Route Demand Artifact"
      description="A bounded route-demand editor over immutable weekly route-demand workbooks. Saving creates the next immutable route-demand version and never mutates schedule artifacts."
      summaryItems={[
        `Week ${String(query.data.workpage.summary.planning_week_id ?? "unknown")}`,
        `Artifact ${artifactVersionId}`,
        `${String(query.data.workpage.summary.planned_route_total ?? 0)} planned routes`
      ]}
      model={query.data.workpage}
      source={query.data.source}
      freshness={query.data.freshness}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching || isMutationPending}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId={layout === "embedded" ? "route-demand-quick-edit-editor" : "route-demand-artifact-workpage-page"}
      metadataPresentation="dialog"
      infoDialogTitle="Route demand artifact context"
      sourceDescription="Artifact-backed route-demand projection served from an immutable Stage04 route-demand workbook version."
      heroTitle={layout === "embedded" ? "Daily route demand" : undefined}
      heroPresentation={layout === "embedded" ? "title_only" : "default"}
      heroTitleActions={
        <div className="action-cluster">
          {futureWeekStatusText ? (
            <span className="schedule-pill schedule-pill--warn">{futureWeekStatusText}</span>
          ) : null}
          <button
            type="button"
            className="action-btn action-btn--positive"
            disabled={!canSave || !hasUnsavedEdits || !saveAction?.submit_path || isMutationPending}
            onClick={() => {
              void handleSaveRouteDemand(afterSave);
            }}
          >
            {submitMutation.isPending ? "Saving route demand..." : "Save route demand"}
          </button>
          {saveAndRunAction ? (
            <button
              type="button"
              className="action-btn action-btn--positive"
              disabled={!canSaveAndRun || isMutationPending}
              onClick={() => {
                void handleSaveAndRun();
              }}
            >
              {saveAndRunMutation.isPending
                ? "Agent working"
                : saveAndRunAction.label}
            </button>
          ) : null}
        </div>
      }
      heroSupportText="Plus/minus controls adjust backend-owned daily route counts and on-call targets. Save creates a new route-demand artifact version and leaves schedule artifacts untouched."
      heroActions={
        layout === "page" ? (
          <>
            <Link className="link-button" to={routeDemandLandingRoute(workflowRunId)}>
              Back to route demand landing
            </Link>
            {scheduleAction?.route ? (
              <Link className="link-button" to={scheduleAction.route}>
                Open latest schedule draft
              </Link>
            ) : (
              <Link className="link-button" to={scheduleLandingRoute(workflowRunId)}>
                Open schedule landing
              </Link>
            )}
          </>
        ) : undefined
      }
      backLink={backRoute.href}
      backLabel={backRoute.label}
      layout={layout}
    >
      {mutationErrorMessage ? (
        <section
          className="workpage-panel workpage-panel--callout"
          data-testid="route-demand-mutation-error"
        >
          <header className="workpage-panel__header">
            <h2>Action failed</h2>
            <p>{mutationErrorMessage}</p>
          </header>
        </section>
      ) : null}
      {futureWeekActivation?.state === "failed" ? (
        <section
          className="workpage-panel workpage-panel--callout"
          data-testid="route-demand-activation-failed"
        >
          <header className="workpage-panel__header">
            <h2>Scheduling agent failed</h2>
            <p>
              {futureWeekActivation.error_message ??
                futureWeekActivation.error_code ??
                futureWeekActivation.status_label ??
                "The weekly scheduling agent failed before producing a draft schedule."}
            </p>
          </header>
        </section>
      ) : null}
      {futureWeekOption && addNextWeekAction?.create_path ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Next addable week</h2>
            <p>
              {futureWeekOption.label} ({futureWeekOption.date_range_label}) is the next
              operational week available for route-demand activation.
            </p>
          </header>
          <div className="action-cluster">
            <button
              type="button"
              className="action-btn action-btn--positive"
              disabled={!canAddNextWeek || isMutationPending}
              onClick={() => {
                void handleAddNextWeek();
              }}
            >
              {createNextWeekMutation.isPending ? "Adding week..." : "Add a week"}
            </button>
          </div>
        </section>
      ) : null}
      {isStaleArtifact && latestArtifactRoute ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Latest route demand available</h2>
            <p>
              This route-demand version is historical. Open the latest version in the chain before
              saving additional changes.
            </p>
          </header>
          <div className="action-cluster">
            <Link className="link-button" to={latestArtifactRoute}>
              Open latest route demand
            </Link>
          </div>
        </section>
      ) : null}
      {(saveAction?.state === "blocked" && saveAction.disabled_reason) ||
      (saveAndRunAction?.state === "blocked" && saveAndRunAction.disabled_reason) ? (
        <section className="workpage-panel workpage-panel--callout">
          <header className="workpage-panel__header">
            <h2>Editing is currently blocked</h2>
            <p>
              {routeDemandDisabledReasonText(
                saveAndRunAction?.disabled_reason ?? saveAction?.disabled_reason
              )}
            </p>
          </header>
          {query.data.future_week_activation?.target_schedule_route ? (
            <div className="action-cluster">
              <Link className="link-button" to={query.data.future_week_activation.target_schedule_route}>
                Continue from schedule
              </Link>
            </div>
          ) : null}
        </section>
      ) : null}
      <RouteDemandWorkpageBody
        contract={query.data}
        workflowRunId={workflowRunId}
        artifactHistory={query.data.artifact_history}
        editableDayCards={dayCards}
        presentation={layout === "embedded" ? "daily_only" : "full"}
        onIncrement={(serviceDate) => {
          setDayCards((current) =>
            current.map((card) =>
              card.service_date === serviceDate
                ? { ...card, planned_route_count: card.planned_route_count + 1 }
                : card
            )
          );
        }}
        onDecrement={(serviceDate) => {
          setDayCards((current) =>
            current.map((card) =>
              card.service_date === serviceDate
                ? {
                    ...card,
                    planned_route_count: Math.max(card.planned_route_count - 1, 0)
                  }
                : card
            )
          );
        }}
        onIncrementOnCall={(serviceDate) => {
          setDayCards((current) =>
            current.map((card) =>
              card.service_date === serviceDate
                ? { ...card, on_call_target: card.on_call_target + 1 }
                : card
            )
          );
        }}
        onDecrementOnCall={(serviceDate) => {
          setDayCards((current) =>
            current.map((card) =>
              card.service_date === serviceDate
                ? { ...card, on_call_target: Math.max(card.on_call_target - 1, 0) }
                : card
            )
          );
        }}
      />
    </WorkpageFrame>
  );
}

export function RouteDemandQuickEditModal({
  workflowRunId,
  onClose
}: {
  workflowRunId: string;
  onClose: () => void;
}): JSX.Element {
  const titleId = useId();
  const descriptionId = useId();
  const [activeWorkflowRunId, setActiveWorkflowRunId] = useState(workflowRunId);
  const [activeArtifactVersionId, setActiveArtifactVersionId] = useState<string | null>(null);
  const [activeAfterSave, setActiveAfterSave] = useState<"close" | "stay">("close");
  const query = useQuery({
    queryKey: ["workpages", "route-demand-v0", "run", activeWorkflowRunId],
    queryFn: () => workpagesRepository.routeDemandForRun(activeWorkflowRunId),
    enabled: Boolean(activeWorkflowRunId),
    refetchInterval: apiConfig.pollIntervalMs
  });
  const openLatestAction = findRouteDemandAction(
    query.data,
    (action) => action.kind === "open_latest" && action.state === "available"
  );

  useEffect(() => {
    setActiveWorkflowRunId(workflowRunId);
    setActiveArtifactVersionId(null);
    setActiveAfterSave("close");
  }, [workflowRunId]);

  useEffect(() => {
    if (!activeArtifactVersionId && openLatestAction?.artifact_version_id) {
      setActiveArtifactVersionId(openLatestAction.artifact_version_id);
    }
  }, [activeArtifactVersionId, openLatestAction?.artifact_version_id]);

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
      className="route-demand-quick-edit-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <section
        className="route-demand-quick-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <header className="route-demand-quick-edit-modal__header">
          <div>
            <p className="timeline-page__eyebrow">Quick edit</p>
            <h2 id={titleId}>Edit route demand</h2>
            <p id={descriptionId}>
              Adjust planned daily route counts and on-call targets without leaving the current
              workpage.
            </p>
          </div>
          <button type="button" className="action-btn" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="route-demand-quick-edit-modal__body">
          {query.isLoading ? (
            <StatePanel
              kind="loading"
              title="Loading route demand editor"
              detail="Resolving the latest route-demand artifact for this weekly run."
            />
          ) : query.isError ? (
            <StatePanel
              kind="error"
              title="Route demand editor failed to load"
              detail={errorText(query.error, "Unable to resolve the latest route-demand artifact.")}
              onRetry={() => {
                void query.refetch();
              }}
            />
          ) : activeArtifactVersionId ? (
            <RouteDemandArtifactEditor
              workflowRunId={activeWorkflowRunId}
              artifactVersionId={activeArtifactVersionId}
              layout="embedded"
              afterSave={activeAfterSave}
              onClose={onClose}
              onArtifactContextChange={({ workflowRunId: nextWorkflowRunId, artifactVersionId: nextArtifactVersionId, afterSave: nextAfterSave }) => {
                setActiveWorkflowRunId(nextWorkflowRunId);
                setActiveArtifactVersionId(nextArtifactVersionId);
                setActiveAfterSave(nextAfterSave === "navigate" ? "stay" : nextAfterSave);
              }}
            />
          ) : (
            <StatePanel
              kind="error"
              title="Route demand editor is unavailable"
              detail="No editable route-demand artifact is available for this weekly run yet."
            />
          )}
        </div>
      </section>
    </div>
  );
}

export function LogisticsRouteDemandArtifactWorkpagePage(): JSX.Element {
  const { artifactVersionId, workflowRunId } = useParams<{
    artifactVersionId: string;
    workflowRunId: string;
  }>();

  if (!workflowRunId || !artifactVersionId) {
    return (
      <StatePanel
        kind="error"
        title="Route demand artifact route is incomplete"
        detail="Both the workflow run id and artifact version id are required."
      />
    );
  }

  return (
    <RouteDemandArtifactEditor
      workflowRunId={workflowRunId}
      artifactVersionId={artifactVersionId}
    />
  );
}
