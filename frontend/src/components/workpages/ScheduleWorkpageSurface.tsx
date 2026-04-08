import { useEffect, useId, useRef, useState } from "react";
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

export const SCHEDULE_DEPENDENCY_STATUS_SUMMARY =
  "Shows whether the schedule is grounded in the planning inputs it depends on. Use it to confirm that required baselines like route slot requirements, approved availability, driver capabilities, and recent actual hours are present and in sync before you review or save.";

export const SCHEDULE_CHECKS_SUMMARY =
  "Shows the validation results calculated from the current schedule and its dependencies, including capacity, on-call coverage, hard assignment rules, and preference alignment. Blocking checks need attention before the schedule is ready; advisory checks are review cues.";

export const SCHEDULE_DEPENDENCY_ITEM_SUMMARIES: Record<string, string> = {
  route_slot_requirements:
    "The required route slots and route counts for the planning week. This is the demand baseline the schedule is expected to cover.",
  approved_availability:
    "The approved can-work and cannot-work availability decisions for each driver. Only approved availability should shape the weekly plan.",
  driver_capabilities:
    "The driver qualification and eligibility baseline, including who can cover the route patterns or roles the week requires.",
  actual_hours:
    "Recent worked-hours truth carried forward from dispatch actuals so workload and WHC checks use real recent effort.",
  driver_preferences:
    "An advisory weekly preference snapshot showing where drivers want or do not want work. It supports review, but it is not hard scheduling truth."
};

export const SCHEDULE_CHECK_ITEM_SUMMARIES: Record<string, string> = {
  scheduled_capacity:
    "Confirms each service day has enough scheduled route assignments to cover the required route demand.",
  on_call_buffer:
    "Checks whether the planned on-call pool meets the reserve coverage target for the week.",
  hard_constraint_compliance:
    "Checks the draft against non-negotiable assignment rules such as availability, rolling-hours limits, and pinned-baseline constraints.",
  driver_preferences_alignment:
    "Highlights where the plan conflicts with driver preference signals. This is advisory guidance for review rather than a hard block."
};

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

function statusChipSummaryTitle(label: string, state: string, summary?: string): string {
  if (!summary) {
    return statusChipTitle(label, state);
  }
  return `${statusChipTitle(label, state)}. ${summary}`;
}

function ScheduleSectionHelp({
  heading,
  summary
}: {
  heading: string;
  summary: string;
}): JSX.Element {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const tooltipId = useId();

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handlePointerDown = (event: MouseEvent | TouchEvent): void => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.blur();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  return (
    <span
      ref={containerRef}
      className="schedule-section-help"
      onMouseEnter={() => {
        setIsOpen(true);
      }}
      onMouseLeave={() => {
        setIsOpen(false);
      }}
    >
      <button
        ref={triggerRef}
        type="button"
        className="info-button schedule-section-help__button"
        aria-label={`Show summary for ${heading}`}
        aria-describedby={isOpen ? tooltipId : undefined}
        onFocus={() => {
          setIsOpen(true);
        }}
        onBlur={(event) => {
          if (!containerRef.current?.contains(event.relatedTarget as Node | null)) {
            setIsOpen(false);
          }
        }}
        onClick={() => {
          setIsOpen((current) => !current);
        }}
      >
        i
      </button>
      {isOpen ? (
        <span id={tooltipId} role="tooltip" className="schedule-section-help__tooltip">
          {summary}
        </span>
      ) : null}
    </span>
  );
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
              <div className="schedule-section-help__heading">
                <h2>Dependency status</h2>
                <ScheduleSectionHelp
                  heading="Dependency status"
                  summary={SCHEDULE_DEPENDENCY_STATUS_SUMMARY}
                />
              </div>
              <p>Hard inputs stay visible so operators can see drift or missing baselines before save.</p>
            </header>
            {dependencies.length > 0 ? (
              <ul className="schedule-dependencies__list">
                {dependencies.map((dependency) => (
                  <li key={dependency.dependency_key} className="schedule-dependencies__item">
                    <span
                      className={`schedule-pill schedule-pill--label schedule-pill--${pillToneForDependency(dependency.state)}`}
                      aria-label={statusChipSummaryTitle(
                        formatDependencyLabel(dependency.dependency_key),
                        dependency.state,
                        SCHEDULE_DEPENDENCY_ITEM_SUMMARIES[dependency.dependency_key]
                      )}
                      title={statusChipSummaryTitle(
                        formatDependencyLabel(dependency.dependency_key),
                        dependency.state,
                        SCHEDULE_DEPENDENCY_ITEM_SUMMARIES[dependency.dependency_key]
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
              <div className="schedule-section-help__heading">
                <h2>Checks</h2>
                <ScheduleSectionHelp heading="Checks" summary={SCHEDULE_CHECKS_SUMMARY} />
              </div>
              <p>Compliance and coverage checks stay visible while you review or preview changes.</p>
            </header>
            {(calculations?.checks ?? []).length > 0 ? (
              <ul className="schedule-checks__list">
                {calculations?.checks.map((check) => (
                  <li key={check.check_id} className="schedule-checks__item">
                    <span
                      className={`schedule-pill schedule-pill--label schedule-pill--${pillToneForDriverState(check.state)}`}
                      aria-label={statusChipSummaryTitle(
                        check.label,
                        check.state,
                        SCHEDULE_CHECK_ITEM_SUMMARIES[check.check_id]
                      )}
                      title={statusChipSummaryTitle(
                        check.label,
                        check.state,
                        SCHEDULE_CHECK_ITEM_SUMMARIES[check.check_id]
                      )}
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
            driverMetrics={calculations?.driver_metrics ?? []}
          />
        ) : null}
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
