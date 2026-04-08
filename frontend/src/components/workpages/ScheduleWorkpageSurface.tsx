import { Link } from "react-router-dom";

import { DraftVersionTimeline, type DraftVersionTimelineEntry } from "@/components/workpages/DraftVersionTimeline";
import { ScheduleHeatmapEditor } from "@/components/workpages/ScheduleHeatmapEditor";
import { WorkpageSummaryCardsSection } from "@/components/workpages/WorkpageContent";
import type {
  WorkpageScheduleAction,
  WorkpageScheduleCalculations,
  WorkpageScheduleDependency,
  WorkpageScheduleHeatmapSection,
  WorkpageSummaryCardsSection as WorkpageSummaryCardsSectionModel,
  WorkpageTableRow
} from "@/lib/types/workpages";

export interface ScheduleVersionRailDefinition {
  testId: string;
  title: string;
  eyebrow: string;
  description: string;
  emptyText: string;
  entries: DraftVersionTimelineEntry[];
  previousRoute?: string | null;
  nextRoute?: string | null;
  previousLabel?: string;
  nextLabel?: string;
}

function pillToneForDependency(state: WorkpageScheduleDependency["state"]): string {
  if (state === "aligned" || state === "resolved") {
    return "success";
  }
  if (state === "drifted" || state === "missing") {
    return "danger";
  }
  return "neutral";
}

function pillToneForDriverState(state: string | undefined): string {
  if (state === "pass" || state === "available") {
    return "success";
  }
  if (state === "fail" || state === "approved_unavailable") {
    return "danger";
  }
  if (state === "warn" || state === "scheduled") {
    return "warn";
  }
  return "neutral";
}

function formatDependencyLabel(key: string): string {
  return key
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function formatDriverHours(hours: number): string {
  return `${hours.toFixed(1)} h`;
}

function formatSelectedDayLabel(serviceDate: string): string {
  const value = new Date(serviceDate);
  if (Number.isNaN(value.getTime())) {
    return serviceDate;
  }
  return value.toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric"
  });
}

function isActionBlocked(action: WorkpageScheduleAction | null | undefined): boolean {
  return action?.state === "blocked" || action?.state === "unavailable";
}

function formatPreferenceLabel(state: string): string {
  return state
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function statusChipTitle(label: string, state: string): string {
  return `${label}: ${formatPreferenceLabel(state)}`;
}

function ScheduleVersionRail({
  rail
}: {
  rail: ScheduleVersionRailDefinition;
}): JSX.Element {
  const previousDisabled = !rail.previousRoute;
  const nextDisabled = !rail.nextRoute;
  return (
    <section className="workpage-panel workpage-page__artifact-rail-panel" data-testid={rail.testId}>
      <header className="workpage-panel__header">
        <p className="timeline-page__eyebrow">{rail.eyebrow}</p>
        <h2>{rail.title}</h2>
        <p>{rail.description}</p>
      </header>

      <div className="schedule-version-rail__controls">
        {rail.previousRoute ? (
          <Link className="link-button" to={rail.previousRoute}>
            {rail.previousLabel ?? "Previous"}
          </Link>
        ) : (
          <span className="schedule-version-rail__hint" aria-disabled={previousDisabled}>
            {rail.previousLabel ?? "Previous unavailable"}
          </span>
        )}
        {rail.nextRoute ? (
          <Link className="link-button" to={rail.nextRoute}>
            {rail.nextLabel ?? "Next"}
          </Link>
        ) : (
          <span className="schedule-version-rail__hint" aria-disabled={nextDisabled}>
            {rail.nextLabel ?? "Next unavailable"}
          </span>
        )}
      </div>

      {rail.entries.length > 0 ? (
        <DraftVersionTimeline ariaLabel={rail.title} entries={rail.entries} />
      ) : (
        <p className="workpage-history__empty">{rail.emptyText}</p>
      )}
    </section>
  );
}

export function ScheduleWorkpageSurface({
  summarySection,
  heatmapSection,
  assignmentRows,
  reserveRows,
  onRowsChange,
  calculations,
  dependencies,
  versionRails,
  readOnly,
  previewStatus,
  saveAction
}: {
  summarySection: WorkpageSummaryCardsSectionModel | null;
  heatmapSection: WorkpageScheduleHeatmapSection | null;
  assignmentRows: WorkpageTableRow[];
  reserveRows: WorkpageTableRow[];
  onRowsChange?: (next: { assignmentRows: WorkpageTableRow[]; reserveRows: WorkpageTableRow[] }) => void;
  calculations: WorkpageScheduleCalculations | null;
  dependencies: WorkpageScheduleDependency[];
  versionRails: ScheduleVersionRailDefinition[];
  readOnly: boolean;
  previewStatus?: {
    isDirty: boolean;
    isPending: boolean;
    error: string | null;
    blockedReason?: string | null;
  };
  saveAction?: WorkpageScheduleAction | null;
}): JSX.Element {
  const selectedDay = calculations?.selected_day ?? null;
  const selectedServiceDate = selectedDay?.service_date ?? null;
  const availableDriverIds = selectedDay?.available_driver_ids ?? [];
  const availablePreferenceBuckets = selectedDay?.available_preference_buckets ?? {
    open_to_work: [],
    prefer_not_to_work: [],
    definitely_can_not_work: [],
    unset: []
  };
  const driverStateById = Object.fromEntries(
    (calculations?.driver_metrics ?? []).map((metric) => [
      metric.driver_id,
      {
        availabilityState: metric.availability_state,
        complianceState: metric.compliance_state
      }
    ])
  );
  const saveBlockedReason =
    isActionBlocked(saveAction) && saveAction?.disabled_reason ? saveAction.disabled_reason : null;

  return (
    <div className="workpage-page__artifact-layout schedule-workpage-surface">
      <div className="workpage-page__artifact-main schedule-workpage-surface__main">
        {summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}

        <section className="workpage-panel schedule-capacity-bar">
          <header className="workpage-panel__header">
            <h2>Capacity bar</h2>
            <p>Server-calculated route, on-call, and staffing posture across the planning week.</p>
          </header>
          {calculations?.top_bar.days.length ? (
            <div className="schedule-capacity-bar__days">
              {calculations.top_bar.days.map((day) => (
                <article
                  key={day.service_date}
                  className={`schedule-capacity-bar__day schedule-capacity-bar__day--${day.capacity_state ?? "neutral"}${
                    selectedServiceDate === day.service_date ? " is-selected" : ""
                  }`}
                >
                  <span className="schedule-capacity-bar__label">{day.weekday_label}</span>
                  <strong>{day.service_date}</strong>
                  <dl className="schedule-capacity-bar__stats">
                    <div>
                      <dt>Required</dt>
                      <dd>{day.routes_required}</dd>
                    </div>
                    <div>
                      <dt>Scheduled</dt>
                      <dd>{day.routes_scheduled ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>On call</dt>
                      <dd>
                        {day.on_call_drivers ?? "—"} / {day.on_call_target}
                      </dd>
                    </div>
                    <div>
                      <dt>Available</dt>
                      <dd>{day.available_driver_count ?? "—"}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          ) : (
            <p className="workpage-history__empty">No capacity calculations available yet.</p>
          )}
        </section>

        {previewStatus ? (
          <section className="workpage-panel schedule-preview-status">
            <header className="workpage-panel__header">
              <h2>Live preview</h2>
              <p>Recalculation stays server-authoritative and does not create a new artifact until save.</p>
            </header>
            <div className="schedule-preview-status__body">
              <span className={`schedule-pill schedule-pill--${previewStatus.isPending ? "warn" : previewStatus.isDirty ? "success" : "neutral"}`}>
                {previewStatus.isPending
                  ? "Recalculating"
                  : previewStatus.isDirty
                    ? "Preview applied"
                    : "No unsaved preview"}
              </span>
              {saveBlockedReason ? (
                <span className="schedule-pill schedule-pill--danger">{saveBlockedReason}</span>
              ) : null}
            </div>
            {previewStatus.error ? (
              <p className="schedule-preview-status__error">{previewStatus.error}</p>
            ) : null}
            {!previewStatus.error && previewStatus.blockedReason ? (
              <p className="schedule-preview-status__blocked">{previewStatus.blockedReason}</p>
            ) : null}
          </section>
        ) : null}

        <div className="schedule-workpage-surface__overview">
          <section className="workpage-panel schedule-dependencies">
            <header className="workpage-panel__header">
              <h2>Dependency status</h2>
              <p>Hard inputs stay visible so operators can see drift or missing baselines before save.</p>
            </header>
            {dependencies.length > 0 ? (
              <ul className="schedule-dependencies__list">
                {dependencies.map((dependency) => (
                  <li key={dependency.dependency_key} className="schedule-dependencies__item">
                    <span
                      className={`schedule-pill schedule-pill--label schedule-pill--${pillToneForDependency(dependency.state)}`}
                      aria-label={statusChipTitle(
                        formatDependencyLabel(dependency.dependency_key),
                        dependency.state
                      )}
                      title={statusChipTitle(
                        formatDependencyLabel(dependency.dependency_key),
                        dependency.state
                      )}
                    >
                      {formatDependencyLabel(dependency.dependency_key)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="workpage-history__empty">No dependency metadata available.</p>
            )}
          </section>

          <section className="workpage-panel schedule-checks">
            <header className="workpage-panel__header">
              <h2>Checks</h2>
              <p>Compliance and coverage checks stay visible while you review or preview changes.</p>
            </header>
            {(calculations?.checks ?? []).length > 0 ? (
              <ul className="schedule-checks__list">
                {calculations?.checks.map((check) => (
                  <li key={check.check_id} className="schedule-checks__item">
                    <span
                      className={`schedule-pill schedule-pill--label schedule-pill--${pillToneForDriverState(check.state)}`}
                      aria-label={statusChipTitle(check.label, check.state)}
                      title={statusChipTitle(check.label, check.state)}
                    >
                      {check.label}
                    </span>
                    <span className="schedule-status-meta">{check.blocking ? "Blocking" : "Advisory"}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="workpage-history__empty">No checks emitted for this surface yet.</p>
            )}
          </section>

          <section className="workpage-panel schedule-selected-day">
            <header className="workpage-panel__header">
              <h2>Selected day</h2>
              <p>Status and operator cues come directly from backend calculations.</p>
            </header>
            {selectedDay ? (
              <div className="schedule-selected-day__content">
                <div className="schedule-selected-day__summary">
                  <strong>{formatSelectedDayLabel(selectedDay.service_date)}</strong>
                  <span>{selectedDay.open_questions ?? "No open questions on this day."}</span>
                </div>
                <dl className="schedule-selected-day__stats">
                  <div>
                    <dt>Routes required</dt>
                    <dd>{selectedDay.routes_required}</dd>
                  </div>
                  <div>
                    <dt>Routes scheduled</dt>
                    <dd>{selectedDay.routes_scheduled ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>On-call drivers</dt>
                    <dd>{selectedDay.on_call_drivers ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>Available drivers</dt>
                    <dd>{selectedDay.available_driver_count ?? selectedDay.drivers_available ?? "—"}</dd>
                  </div>
                </dl>
                <div className="schedule-selected-day__chips">
                  {availableDriverIds.map((driverId) => (
                    <span key={driverId} className="schedule-pill schedule-pill--success">
                      {driverId}
                    </span>
                  ))}
                </div>
                <div className="schedule-selected-day__preference-buckets">
                  {Object.entries(availablePreferenceBuckets).map(([bucketKey, driverIds]) => (
                    <article key={bucketKey} className="schedule-selected-day__preference-bucket">
                      <strong>{formatPreferenceLabel(bucketKey)}</strong>
                      <div className="schedule-selected-day__chips">
                        {driverIds.length > 0 ? (
                          driverIds.map((driverId) => (
                            <span key={`${bucketKey}-${driverId}`} className="schedule-pill schedule-pill--neutral">
                              {driverId}
                            </span>
                          ))
                        ) : (
                          <span className="schedule-selected-day__empty">None</span>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <p className="workpage-history__empty">No selected-day summary available.</p>
            )}
          </section>
        </div>

        {heatmapSection ? (
          <ScheduleHeatmapEditor
            section={heatmapSection}
            assignmentRows={assignmentRows}
            reserveRows={reserveRows}
            onRowsChange={onRowsChange}
            readOnly={readOnly}
            selectedServiceDate={selectedServiceDate}
            availableDriverIds={availableDriverIds}
            driverStateById={driverStateById}
          />
        ) : null}

        <section className="workpage-panel schedule-driver-metrics">
          <header className="workpage-panel__header">
            <h2>Driver metrics</h2>
            <p>Availability and compliance highlighting come from the backend preview or artifact contract.</p>
          </header>
          {(calculations?.driver_metrics ?? []).length > 0 ? (
            <div className="workpage-table__wrap">
              <table className="workpage-table schedule-driver-metrics__table">
                <thead>
                  <tr>
                    <th scope="col">Driver</th>
                    <th scope="col">Hours</th>
                    <th scope="col">Routes</th>
                    <th scope="col">On call</th>
                    <th scope="col">Preference</th>
                    <th scope="col">Availability</th>
                    <th scope="col">Compliance</th>
                    <th scope="col">Issues</th>
                  </tr>
                </thead>
                <tbody>
                  {calculations?.driver_metrics
                    .slice()
                    .sort((left, right) => {
                      if (right.scheduled_routes !== left.scheduled_routes) {
                        return right.scheduled_routes - left.scheduled_routes;
                      }
                      if (right.on_call_shifts !== left.on_call_shifts) {
                        return right.on_call_shifts - left.on_call_shifts;
                      }
                      return left.driver_name.localeCompare(right.driver_name);
                    })
                    .map((metric) => (
                      <tr
                        key={metric.driver_id}
                        className={
                          metric.compliance_state === "fail"
                            ? "schedule-driver-metrics__row schedule-driver-metrics__row--blocked"
                            : metric.availability_state === "available"
                              ? "schedule-driver-metrics__row schedule-driver-metrics__row--available"
                              : "schedule-driver-metrics__row"
                        }
                      >
                        <td>
                          <strong>{metric.driver_name}</strong>
                          <div className="schedule-driver-metrics__subtext">{metric.driver_id}</div>
                        </td>
                        <td>{formatDriverHours(metric.scheduled_hours)}</td>
                        <td>{metric.scheduled_routes}</td>
                        <td>{metric.on_call_shifts}</td>
                        <td>
                          <span className={`schedule-pill schedule-pill--${pillToneForDriverState(metric.preference_state)}`}>
                            {metric.preference_state}
                          </span>
                        </td>
                        <td>
                          <span className={`schedule-pill schedule-pill--${pillToneForDriverState(metric.availability_state)}`}>
                            {metric.availability_state}
                          </span>
                        </td>
                        <td>
                          <span className={`schedule-pill schedule-pill--${pillToneForDriverState(metric.compliance_state)}`}>
                            {metric.compliance_state}
                          </span>
                        </td>
                        <td>{metric.issues.length > 0 ? metric.issues.join(", ") : "—"}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="workpage-history__empty">No driver metrics are available on this surface yet.</p>
          )}
        </section>
      </div>

      <aside className="workpage-page__artifact-rail schedule-workpage-surface__rail">
        <div className="schedule-workpage-surface__rail-stack">
          {versionRails.map((rail) => (
            <ScheduleVersionRail key={rail.testId} rail={rail} />
          ))}
        </div>
      </aside>
    </div>
  );
}
