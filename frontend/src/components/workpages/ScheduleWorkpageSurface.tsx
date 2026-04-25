import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { DraftVersionTimeline, type DraftVersionTimelineEntry } from "@/components/workpages/DraftVersionTimeline";
import {
  ScheduleHeatmapEditor,
  type ScheduleSickNoShowTarget
} from "@/components/workpages/ScheduleHeatmapEditor";
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

function formatStatusLabel(state: string): string {
  return state
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function statusChipTitle(label: string, state: string): string {
  return `${label}: ${formatStatusLabel(state)}`;
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

function ScheduleHeatmapStatusHeaderExtras({
  dependencies,
  checks
}: {
  dependencies: WorkpageScheduleDependency[];
  checks: WorkpageScheduleCalculations["checks"];
}): JSX.Element {
  return (
    <>
      <section className="schedule-heatmap__header-group" aria-label="Dependency status">
        <div className="schedule-section-help__heading schedule-heatmap__header-group-heading">
          <h3>Dependency status</h3>
          <ScheduleSectionHelp
            heading="Dependency status"
            summary={SCHEDULE_DEPENDENCY_STATUS_SUMMARY}
          />
        </div>
        {dependencies.length > 0 ? (
          <ul className="schedule-dependencies__list schedule-heatmap__chip-list">
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
          <p className="workpage-history__empty schedule-heatmap__header-empty">
            No dependency metadata available.
          </p>
        )}
      </section>

      <section className="schedule-heatmap__header-group" aria-label="Checks">
        <div className="schedule-section-help__heading schedule-heatmap__header-group-heading">
          <h3>Checks</h3>
          <ScheduleSectionHelp heading="Checks" summary={SCHEDULE_CHECKS_SUMMARY} />
        </div>
        {checks.length > 0 ? (
          <ul className="schedule-checks__list schedule-heatmap__chip-list">
            {checks.map((check) => (
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
                  <span className="schedule-pill__meta">{check.blocking ? "Blocking" : "Advisory"}</span>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="workpage-history__empty schedule-heatmap__header-empty">
            No checks emitted yet.
          </p>
        )}
      </section>
    </>
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
  saveAction,
  presentation = "default",
  onMarkSickNoShow,
  sickNoShowDisabled = false,
  sickNoShowPendingKey = null
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
  presentation?: "default" | "quick_edit";
  onMarkSickNoShow?: (target: ScheduleSickNoShowTarget) => void;
  sickNoShowDisabled?: boolean;
  sickNoShowPendingKey?: string | null;
}): JSX.Element {
  const selectedDay = calculations?.selected_day ?? null;
  const selectedServiceDate = selectedDay?.service_date ?? null;
  const availableDriverIds = selectedDay?.available_driver_ids ?? [];
  const isQuickEdit = presentation === "quick_edit";
  const saveBlockedReason =
    isActionBlocked(saveAction) && saveAction?.disabled_reason ? saveAction.disabled_reason : null;
  const checks = calculations?.checks ?? [];
  const showQuickEditPreviewStatus =
    isQuickEdit &&
    Boolean(
      previewStatus?.isDirty ||
        previewStatus?.isPending ||
        previewStatus?.error ||
        previewStatus?.blockedReason ||
        saveBlockedReason
    );
  const heatmap = heatmapSection ? (
    <ScheduleHeatmapEditor
      section={heatmapSection}
      assignmentRows={assignmentRows}
      reserveRows={reserveRows}
      onRowsChange={onRowsChange}
      readOnly={readOnly}
      selectedServiceDate={selectedServiceDate}
      availableDriverIds={availableDriverIds}
      driverMetrics={calculations?.driver_metrics ?? []}
      topBarDays={calculations?.top_bar.days ?? []}
      density={isQuickEdit ? "compact" : "default"}
      headerExtras={<ScheduleHeatmapStatusHeaderExtras dependencies={dependencies} checks={checks} />}
      onMarkSickNoShow={onMarkSickNoShow}
      sickNoShowDisabled={sickNoShowDisabled}
      sickNoShowPendingKey={sickNoShowPendingKey}
    />
  ) : null;

  return (
    <div
      className={`workpage-page__artifact-layout schedule-workpage-surface${
        isQuickEdit ? " schedule-workpage-surface--quick-edit" : ""
      }`}
    >
      <div className="workpage-page__artifact-main schedule-workpage-surface__main">
        {!isQuickEdit && summarySection ? <WorkpageSummaryCardsSection section={summarySection} /> : null}

        {previewStatus && !isQuickEdit ? (
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

        {showQuickEditPreviewStatus && previewStatus ? (
          <section className="schedule-preview-status schedule-preview-status--compact" aria-label="Preview status">
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
            {previewStatus.error ? (
              <span className="schedule-preview-status__error">{previewStatus.error}</span>
            ) : null}
            {!previewStatus.error && previewStatus.blockedReason ? (
              <span className="schedule-preview-status__blocked">{previewStatus.blockedReason}</span>
            ) : null}
          </section>
        ) : null}

        {heatmap}
      </div>

      {!isQuickEdit ? (
        <aside className="workpage-page__artifact-rail schedule-workpage-surface__rail">
          <div className="schedule-workpage-surface__rail-stack">
            {versionRails.map((rail) => (
              <ScheduleVersionRail key={rail.testId} rail={rail} />
            ))}
          </div>
        </aside>
      ) : null}
    </div>
  );
}
