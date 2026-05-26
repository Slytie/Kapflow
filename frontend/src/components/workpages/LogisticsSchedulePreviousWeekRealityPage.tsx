import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { StatePanel } from "@/components/StatePanel";
import {
  WorkpageFrame,
  WorkpageNotePanelSection,
  WorkpageTableSection
} from "@/components/workpages/WorkpageContent";
import { apiConfig } from "@/lib/api/config";
import { errorText } from "@/lib/api/errorText";
import { isApiClientError } from "@/lib/api/httpClient";
import { workpagesRepository } from "@/lib/repositories";
import type {
  WorkpageSchedulePreviousWeekReality,
  WorkpageSchedulePreviousWeekRealityCell,
  WorkpageViewModel
} from "@/lib/types/workpages";

function scheduleArtifactRoute(workflowRunId: string, artifactVersionId: string): string {
  return `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`;
}

function previousWeekRealityCellTone(normalizedState: string): string {
  switch (normalizedState) {
    case "worked":
      return "worked";
    case "blocked_previous_week":
      return "blocked";
    case "available_not_assigned":
      return "available";
    case "pattern_off":
      return "off";
    default:
      return "neutral";
  }
}

function previousWeekRealityPillTone(normalizedState: string): string {
  switch (normalizedState) {
    case "worked":
      return "success";
    case "blocked_previous_week":
      return "danger";
    case "available_not_assigned":
      return "warn";
    default:
      return "neutral";
  }
}

function previousWeekRealityStateLabel(normalizedState: string): string {
  switch (normalizedState) {
    case "worked":
      return "Worked";
    case "blocked_previous_week":
      return "Blocked";
    case "available_not_assigned":
      return "Available";
    case "pattern_off":
      return "Pattern off";
    default:
      return normalizedState
        ? normalizedState
            .split("_")
            .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
            .join(" ")
        : "Unknown";
  }
}

function minutesLabel(minutes: number): string {
  if (minutes <= 0) {
    return "0m";
  }
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (hours === 0) {
    return `${minutes}m`;
  }
  if (remainder === 0) {
    return `${hours}h`;
  }
  return `${hours}h ${remainder}m`;
}

function flagsLabel(input: {
  callInSick: boolean;
  cancelled: boolean;
  nonWorking: boolean;
}): string {
  return [
    input.callInSick ? "Sick" : null,
    input.cancelled ? "Cancelled" : null,
    input.nonWorking ? "Non-working" : null
  ]
    .filter(Boolean)
    .join(", ");
}

function driverEmploymentLabel(reality: WorkpageSchedulePreviousWeekReality["drivers"][number]): string {
  const employment = reality.employment_type
    ? reality.employment_type
        .split("_")
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
        .join(" ")
    : "Unspecified employment";
  return reality.on_call_eligible ? `${employment} · On-call eligible` : employment;
}

function buildDriverCellMap(
  cells: WorkpageSchedulePreviousWeekRealityCell[]
): Map<string, WorkpageSchedulePreviousWeekRealityCell> {
  return new Map(cells.map((cell) => [cell.service_date, cell]));
}

function renderDaySummaryMetrics(
  reality: WorkpageSchedulePreviousWeekReality,
  serviceDate: string
): JSX.Element | null {
  const summary = reality.day_summaries.find((item) => item.service_date === serviceDate);
  if (!summary) {
    return null;
  }
  return (
    <div className="previous-week-reality__day-metrics" aria-label={`Summary for ${serviceDate}`}>
      <span className="previous-week-reality__day-metric">
        <small>Drv</small>
        <strong>{summary.worked_driver_days}</strong>
      </span>
      <span className="previous-week-reality__day-metric">
        <small>Rt</small>
        <strong>{summary.worked_route_count}</strong>
      </span>
      <span className="previous-week-reality__day-metric">
        <small>Blk</small>
        <strong>{summary.blocked_driver_days}</strong>
      </span>
      <span className="previous-week-reality__day-metric">
        <small>Min</small>
        <strong>{minutesLabel(summary.total_minutes)}</strong>
      </span>
    </div>
  );
}

export function LogisticsSchedulePreviousWeekRealityPage(): JSX.Element {
  const params = useParams<{ workflowRunId: string; artifactVersionId: string }>();
  const workflowRunId = params.workflowRunId ?? "";
  const artifactVersionId = params.artifactVersionId ?? "";
  const query = useQuery({
    queryKey: [
      "workpages",
      "schedule-v0",
      "artifacts",
      workflowRunId,
      artifactVersionId,
      "reality",
      "previous-week"
    ],
    queryFn: () =>
      workpagesRepository.scheduleArtifactPreviousWeekReality(workflowRunId, artifactVersionId),
    enabled: Boolean(workflowRunId && artifactVersionId),
    retry: (failureCount, error) =>
      !(isApiClientError(error) && error.code === "workpage_projection_unavailable") &&
      failureCount < 1,
    refetchInterval: apiConfig.pollIntervalMs
  });

  if (query.isLoading) {
    return (
      <StatePanel
        kind="loading"
        title="Loading previous-week reality"
        detail="Fetching the pinned prior-week actual-hours snapshot for this schedule draft."
      />
    );
  }

  if (query.isError || !query.data || !workflowRunId || !artifactVersionId) {
    const unavailableDetail =
      "This draft does not have a pinned actual-hours snapshot, so previous-week reality is unavailable.";
    const detail =
      isApiClientError(query.error) && query.error.code === "workpage_projection_unavailable"
        ? unavailableDetail
        : errorText(query.error, unavailableDetail);
    return (
      <StatePanel
        kind="error"
        title="Previous-week reality failed to load"
        detail={detail}
        onRetry={() => {
          void query.refetch();
        }}
      />
    );
  }

  const contract = query.data;
  const reality = contract.previous_week_reality;
  const totalWorkedDriverDays = reality.day_summaries.reduce(
    (sum, item) => sum + item.worked_driver_days,
    0
  );
  const totalBlockedDriverDays = reality.day_summaries.reduce(
    (sum, item) => sum + item.blocked_driver_days,
    0
  );
  const totalMinutes = reality.day_summaries.reduce((sum, item) => sum + item.total_minutes, 0);
  const totalWorkedRoutes = reality.day_summaries.reduce(
    (sum, item) => sum + item.worked_route_count,
    0
  );
  const frameModel: WorkpageViewModel = {
    workpage_id: "schedule-v0.previous-week-reality",
    version: 1,
    title: "Previous-week reality",
    mode: "example",
    workflow_id: "weekly_schedule_planning.v1",
    dataset_key: contract.source.primary_dataset_key ?? "planning.actual_hours_snapshot.workbook",
    source_artifact_version_id: contract.source.source_artifact_version_id,
    source_examples: {},
    summary: {
      planning_week_id: reality.planning_week_id,
      previous_week_start: reality.previous_week_start,
      previous_week_end: reality.previous_week_end
    },
    sections: [],
    validation: {
      status: "informational",
      warnings: [reality.note]
    }
  };

  return (
    <WorkpageFrame
      eyebrow=""
      description=""
      summaryItems={[
        `Week ${reality.planning_week_id}`,
        `Artifact ${artifactVersionId}`,
        `${reality.previous_week_start} to ${reality.previous_week_end}`,
        `${totalWorkedDriverDays} worked driver-days`
      ]}
      model={frameModel}
      source={contract.source}
      freshness={contract.freshness}
      onRefresh={() => {
        void query.refetch();
      }}
      isRefreshing={query.isFetching}
      pollIntervalMs={apiConfig.pollIntervalMs}
      testId="schedule-previous-week-reality-page"
      metadataPresentation="dialog"
      infoDialogTitle="Previous-week reality context"
      sourceDescription="Artifact-scoped projection of the pinned actual-hours snapshot referenced by this draft. It preserves the same prior-week reality input used by weekly scheduling."
      heroActions={
        <Link className="link-button" to={scheduleArtifactRoute(workflowRunId, artifactVersionId)}>
          Open schedule draft
        </Link>
      }
      backLink={scheduleArtifactRoute(workflowRunId, artifactVersionId)}
      backLabel="Back to schedule draft"
      stickyTitleBar
    >
      <div
        className="workpage-page__artifact-layout previous-week-reality-page__layout"
        data-testid="schedule-previous-week-reality-layout"
      >
        <div className="workpage-page__artifact-main previous-week-reality-page__main">
          <section
            className="workpage-panel previous-week-reality__surface"
            data-testid="schedule-previous-week-reality-grid"
          >
            <header className="workpage-panel__header previous-week-reality__header">
              <div>
                <p className="schedule-heatmap__eyebrow">Pinned prior-week truth</p>
                <h2>Historical reality grid</h2>
              </div>
            </header>
            <div className="previous-week-reality__wrap">
              <table className="previous-week-reality__grid">
                <thead>
                  <tr>
                    <th scope="col" className="previous-week-reality__driver-header">
                      Driver
                    </th>
                    {reality.service_dates.map((serviceDate) => (
                      <th
                        key={serviceDate.service_date}
                        scope="col"
                        className="previous-week-reality__day-header"
                      >
                        <span>{serviceDate.weekday_label}</span>
                        <strong>{serviceDate.service_date}</strong>
                        {renderDaySummaryMetrics(reality, serviceDate.service_date)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {reality.drivers.map((driver) => {
                    const cellsByServiceDate = buildDriverCellMap(driver.cells);
                    return (
                      <tr key={driver.driver_id}>
                        <th scope="row" className="previous-week-reality__driver">
                          <div className="previous-week-reality__driver-card">
                            <strong>{driver.driver_name}</strong>
                            <div className="previous-week-reality__driver-meta">
                              <span>{driverEmploymentLabel(driver)}</span>
                              <span>{minutesLabel(driver.previous_week_minutes)} prior-week total</span>
                            </div>
                          </div>
                        </th>
                        {reality.service_dates.map((serviceDate) => {
                          const cell = cellsByServiceDate.get(serviceDate.service_date);
                          const tone = previousWeekRealityCellTone(cell?.normalized_state ?? "");
                          const cumulativeWeekMinutesLabel = minutesLabel(
                            cell?.cumulative_week_minutes ?? 0
                          );
                          const flags = cell
                            ? flagsLabel({
                                callInSick: cell.call_in_sick_flag,
                                cancelled: cell.cancellation_flag,
                                nonWorking: cell.non_working_day_flag
                              })
                            : "";
                          return (
                            <td
                              key={`${driver.driver_id}:${serviceDate.service_date}`}
                              className="previous-week-reality__cell-column"
                            >
                              <div
                                className={`previous-week-reality__cell previous-week-reality__cell--${tone}`}
                              >
                                <div className="previous-week-reality__cell-top">
                                  <span
                                    className={`schedule-pill schedule-pill--${previousWeekRealityPillTone(
                                      cell?.normalized_state ?? ""
                                    )} previous-week-reality__state-pill`}
                                  >
                                    {previousWeekRealityStateLabel(cell?.normalized_state ?? "")}
                                  </span>
                                  {flags ? (
                                    <span className="previous-week-reality__flags">{flags}</span>
                                  ) : null}
                                </div>
                                <strong className="previous-week-reality__minutes">
                                  {minutesLabel(cell?.actual_minutes ?? 0)}{" "}
                                  <span className="previous-week-reality__cumulative-minutes">
                                    [{cumulativeWeekMinutesLabel}]
                                  </span>
                                </strong>
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <WorkpageTableSection
            className="previous-week-reality__activity-table"
            section={{
              kind: "table",
              title: "Material prior-week activity",
              table_id: "previous_week_activity_rows",
              columns: [
                { key: "driver_name", label: "Driver" },
                { key: "service_date", label: "Service date" },
                { key: "weekday_label", label: "Day" },
                { key: "normalized_state", label: "Normalized state" },
                { key: "actual_minutes", label: "Minutes" },
                { key: "route_id", label: "Route" },
                { key: "flags", label: "Flags" }
              ],
              rows: reality.activity_rows.map((row) => ({
                driver_name: row.driver_name,
                service_date: row.service_date,
                weekday_label: row.weekday_label,
                normalized_state: row.normalized_state,
                actual_minutes: row.actual_minutes,
                route_id: row.route_id || "—",
                flags:
                  flagsLabel({
                    callInSick: row.call_in_sick_flag,
                    cancelled: row.cancellation_flag,
                    nonWorking: row.non_working_day_flag
                  }) || "—"
              })),
              empty_message:
                "No material previous-week activity rows were found in the pinned snapshot."
            }}
          />
        </div>

        <aside className="workpage-page__artifact-rail previous-week-reality-page__rail">
          <div className="workpage-page__artifact-rail-panel">
            <section
              className="workpage-panel previous-week-reality__daily-summary-panel"
              data-testid="schedule-previous-week-reality-rail-summary"
            >
              <header className="workpage-panel__header">
                <h2>Daily summary</h2>
              </header>
              <div className="previous-week-reality__rail-totals">
                <span className="schedule-pill schedule-pill--success">
                  {totalWorkedDriverDays} worked driver-days
                </span>
                <span className="schedule-pill schedule-pill--danger">
                  {totalBlockedDriverDays} blocked driver-days
                </span>
                <span className="schedule-pill schedule-pill--neutral">
                  {totalWorkedRoutes} worked routes
                </span>
                <span className="schedule-pill schedule-pill--neutral">
                  {minutesLabel(totalMinutes)} total minutes
                </span>
              </div>
              <ul className="previous-week-reality__daily-summary-list">
                {reality.day_summaries.map((item) => (
                  <li key={item.service_date} className="previous-week-reality__daily-summary-item">
                    <div className="previous-week-reality__daily-summary-copy">
                      <strong>{item.weekday_label}</strong>
                      <span>{item.service_date}</span>
                    </div>
                    <div className="previous-week-reality__daily-summary-metrics">
                      <span>{item.worked_driver_days} drv</span>
                      <span>{item.worked_route_count} rt</span>
                      <span>{item.blocked_driver_days} blk</span>
                      <span>{minutesLabel(item.total_minutes)}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </section>

            <WorkpageNotePanelSection
              section={{
                kind: "note_panel",
                title: "Pinned reality note",
                body: reality.note
              }}
            />
          </div>
        </aside>
      </div>
    </WorkpageFrame>
  );
}
