import { useMemo, useState, type ReactNode } from "react";

import { InfoDialog } from "@/components/InfoDialog";
import type {
  ScheduleHybridHeatmapCell,
  ScheduleHybridHeatmapDate,
  ScheduleHybridHeatmapSection
} from "@/lib/workpages/scheduleHybridReality";
import type {
  WorkpageScheduleCalculationTopBarDay,
  WorkpageScheduleDriverMetric,
  WorkpageScheduleHeatmapCell,
  WorkpageScheduleHeatmapDate,
  WorkpageScheduleHeatmapPerson,
  WorkpageScheduleHeatmapSection,
  WorkpageTableRow
} from "@/lib/types/workpages";

type EditableRowKind = "assignment" | "reserve";
type DriverPreferenceState =
  | "open_to_work"
  | "prefer_not_to_work"
  | "definitely_can_not_work"
  | "unset";

interface DerivedHeatmapCell {
  driverId: string;
  serviceDate: string;
  state: "assigned" | "on_call" | "empty";
  rowKind: EditableRowKind | null;
  rowIndex: number | null;
  routeSlotId: string | null;
  projectedMinutes: number | null;
  assignmentStatus: string | null;
  plannedDriverDayState: string | null;
  manualOverride: boolean;
  cellProvenance: "planned_current_week" | "previous_week_reality";
  sourceServiceDate: string;
  realityServiceDate: string | null;
  previousWeekNormalizedState: string | null;
  previousWeekBlockedReasons: string[];
  previousWeekActualMinutes: number | null;
  previousWeekCumulativeWeekMinutes: number | null;
  realitySummaryMinutes: number | null;
  previousWeekRouteId: string | null;
  previousWeekRouteSlotClass: string | null;
  previousWeekSourceRef: string | null;
  previousWeekCallInSickFlag: boolean;
  previousWeekCancellationFlag: boolean;
  previousWeekNonWorkingDayFlag: boolean;
}

interface ArmedCell {
  driverId: string;
  driverName: string;
  serviceDate: string;
  rowKind: EditableRowKind;
  rowIndex: number;
}

interface AvailabilityCellState {
  state: string | null;
  reasonCode: string | null;
  sourceRef: string | null;
}

type HeaderMetricRowKey = "required" | "scheduled" | "on_call" | "available" | "gap";

interface HeaderMetricRow {
  key: HeaderMetricRowKey;
  label: string;
  accessibilityLabel: string;
}

export interface ScheduleRouteDemandPendingCell {
  targetId: string;
  routeId: string;
  driverId: string;
  driverName: string;
  serviceDate: string;
  projectedMinutes: number | null;
}

export interface ScheduleSickNoShowTarget {
  driverId: string;
  driverName: string;
  serviceDate: string;
  serviceDateLabel: string;
  currentState: "assigned" | "on_call" | "empty";
}

function asText(value: unknown): string {
  return typeof value === "string" ? value.trim() : String(value ?? "").trim();
}

function asNumberOrNull(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  const text = asText(value);
  if (!text) {
    return null;
  }
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildServiceDates(
  section: WorkpageScheduleHeatmapSection | ScheduleHybridHeatmapSection,
  assignmentRows: WorkpageTableRow[],
  reserveRows: WorkpageTableRow[]
): Array<WorkpageScheduleHeatmapDate | ScheduleHybridHeatmapDate> {
  if (section.service_dates.length > 0) {
    return section.service_dates;
  }
  const dates = Array.from(
    new Set(
      [...assignmentRows, ...reserveRows]
        .map((row) => asText(row.service_date))
        .filter((serviceDate) => serviceDate.length > 0)
    )
  ).sort();
  return dates.map((serviceDate) => ({
    service_date: serviceDate,
    label: serviceDate,
    weekday_label: serviceDate
  }));
}

function buildPeople(
  section: WorkpageScheduleHeatmapSection | ScheduleHybridHeatmapSection,
  assignmentRows: WorkpageTableRow[],
  reserveRows: WorkpageTableRow[]
): Array<WorkpageScheduleHeatmapPerson> {
  const people = new Map(section.people.map((person) => [person.driver_id, person]));
  for (const row of [...assignmentRows, ...reserveRows]) {
    const driverId = asText(row.assigned_driver_id);
    if (!driverId || people.has(driverId)) {
      continue;
    }
    people.set(driverId, {
      driver_id: driverId,
      driver_name: driverId,
      employment_type: "",
      on_call_eligible: false,
      previous_week_minutes: 0,
      availability_summary: "driver only present in the current draft rows",
      cells: []
    });
  }
  return Array.from(people.values());
}

function isHybridRealityCell(
  cell: WorkpageScheduleHeatmapCell | ScheduleHybridHeatmapCell
): cell is ScheduleHybridHeatmapCell {
  return (cell as ScheduleHybridHeatmapCell).cell_provenance === "previous_week_reality";
}

function isHybridRealityDate(
  serviceDate: WorkpageScheduleHeatmapDate | ScheduleHybridHeatmapDate
): serviceDate is ScheduleHybridHeatmapDate {
  return (
    (serviceDate as ScheduleHybridHeatmapDate).column_provenance ===
    "previous_week_reality"
  );
}

function isHybridReadOnlyDate(
  serviceDate: WorkpageScheduleHeatmapDate | ScheduleHybridHeatmapDate
): serviceDate is ScheduleHybridHeatmapDate {
  return (
    typeof (serviceDate as ScheduleHybridHeatmapDate).read_only === "boolean" &&
    (serviceDate as ScheduleHybridHeatmapDate).read_only
  );
}

function buildCellMap(
  people: WorkpageScheduleHeatmapPerson[],
  assignmentRows: WorkpageTableRow[],
  reserveRows: WorkpageTableRow[]
): Map<string, DerivedHeatmapCell> {
  const cellMap = new Map<string, DerivedHeatmapCell>();
  for (const person of people) {
    for (const cell of person.cells) {
      if (!isHybridRealityCell(cell)) {
        continue;
      }
      cellMap.set(`${cell.service_date}:${person.driver_id}`, {
        driverId: person.driver_id,
        serviceDate: cell.service_date,
        state: "empty",
        rowKind: null,
        rowIndex: null,
        routeSlotId: null,
        projectedMinutes: null,
        assignmentStatus: null,
        plannedDriverDayState: null,
        manualOverride: false,
        cellProvenance: "previous_week_reality",
        sourceServiceDate: cell.source_service_date ?? cell.service_date,
        realityServiceDate: cell.reality_service_date ?? cell.service_date,
        previousWeekNormalizedState: cell.previous_week_normalized_state ?? null,
        previousWeekBlockedReasons: cell.previous_week_blocked_reasons ?? [],
        previousWeekActualMinutes: cell.previous_week_actual_minutes ?? null,
        previousWeekCumulativeWeekMinutes: cell.previous_week_cumulative_week_minutes ?? null,
        realitySummaryMinutes: cell.reality_summary_minutes ?? null,
        previousWeekRouteId: cell.previous_week_route_id ?? null,
        previousWeekRouteSlotClass: cell.previous_week_route_slot_class ?? null,
        previousWeekSourceRef: cell.previous_week_source_ref ?? null,
        previousWeekCallInSickFlag: cell.previous_week_call_in_sick_flag ?? false,
        previousWeekCancellationFlag: cell.previous_week_cancellation_flag ?? false,
        previousWeekNonWorkingDayFlag: cell.previous_week_non_working_day_flag ?? false
      });
    }
  }
  assignmentRows.forEach((row, rowIndex) => {
    const driverId = asText(row.assigned_driver_id);
    const serviceDate = asText(row.service_date);
    if (!driverId || !serviceDate) {
      return;
    }
    if (cellMap.get(`${serviceDate}:${driverId}`)?.cellProvenance === "previous_week_reality") {
      return;
    }
    cellMap.set(`${serviceDate}:${driverId}`, {
      driverId,
      serviceDate,
      state: "assigned",
      rowKind: "assignment",
      rowIndex,
      routeSlotId: asText(row.route_slot_id) || null,
      projectedMinutes: asNumberOrNull(row.projected_minutes),
      assignmentStatus: asText(row.assignment_status) || null,
      plannedDriverDayState: asText(row.planned_driver_day_state) || null,
      manualOverride: asText(row.assignment_status) === "manual_override",
      cellProvenance: "planned_current_week",
      sourceServiceDate: serviceDate,
      realityServiceDate: null,
      previousWeekNormalizedState: null,
      previousWeekBlockedReasons: [],
      previousWeekActualMinutes: null,
      previousWeekCumulativeWeekMinutes: null,
      realitySummaryMinutes: null,
      previousWeekRouteId: null,
      previousWeekRouteSlotClass: null,
      previousWeekSourceRef: null,
      previousWeekCallInSickFlag: false,
      previousWeekCancellationFlag: false,
      previousWeekNonWorkingDayFlag: false
    });
  });
  reserveRows.forEach((row, rowIndex) => {
    const driverId = asText(row.assigned_driver_id);
    const serviceDate = asText(row.service_date);
    if (!driverId || !serviceDate) {
      return;
    }
    const key = `${serviceDate}:${driverId}`;
    if (cellMap.has(key)) {
      return;
    }
    cellMap.set(key, {
      driverId,
      serviceDate,
      state: "on_call",
      rowKind: "reserve",
      rowIndex,
      routeSlotId: asText(row.route_slot_id) || null,
      projectedMinutes: asNumberOrNull(row.projected_minutes),
      assignmentStatus: asText(row.assignment_status) || null,
      plannedDriverDayState: asText(row.planned_driver_day_state) || null,
      manualOverride: asText(row.assignment_status) === "manual_override",
      cellProvenance: "planned_current_week",
      sourceServiceDate: serviceDate,
      realityServiceDate: null,
      previousWeekNormalizedState: null,
      previousWeekBlockedReasons: [],
      previousWeekActualMinutes: null,
      previousWeekCumulativeWeekMinutes: null,
      realitySummaryMinutes: null,
      previousWeekRouteId: null,
      previousWeekRouteSlotClass: null,
      previousWeekSourceRef: null,
      previousWeekCallInSickFlag: false,
      previousWeekCancellationFlag: false,
      previousWeekNonWorkingDayFlag: false
    });
  });
  return cellMap;
}

function buildPreferenceStateMap(
  people: WorkpageScheduleHeatmapPerson[]
): Map<string, DriverPreferenceState> {
  const stateMap = new Map<string, DriverPreferenceState>();
  for (const person of people) {
    for (const cell of person.cells) {
      stateMap.set(
        `${cell.service_date}:${person.driver_id}`,
        normalizePreferenceState(cell.preference_state)
      );
    }
  }
  return stateMap;
}

function buildAvailabilityStateMap(
  people: WorkpageScheduleHeatmapPerson[]
): Map<string, AvailabilityCellState> {
  const stateMap = new Map<string, AvailabilityCellState>();
  for (const person of people) {
    for (const cell of person.cells) {
      stateMap.set(`${cell.service_date}:${person.driver_id}`, {
        state: cell.availability_state ?? null,
        reasonCode: cell.availability_reason_code ?? null,
        sourceRef: cell.availability_source_ref ?? null
      });
    }
  }
  return stateMap;
}

function cloneRows(rows: WorkpageTableRow[]): WorkpageTableRow[] {
  return rows.map((row) => ({ ...row }));
}

function setManualOverride(
  rows: WorkpageTableRow[],
  rowIndex: number,
  driverId: string
): WorkpageTableRow[] {
  return rows.map((row, index) =>
    index === rowIndex
      ? {
          ...row,
          assigned_driver_id: driverId,
          assignment_status: "manual_override"
        }
      : row
  );
}

function buildCellLabel(
  person: WorkpageScheduleHeatmapPerson,
  serviceDate: WorkpageScheduleHeatmapDate,
  cell: DerivedHeatmapCell | null
): string {
  const base = `${person.driver_name} on ${serviceDate.label}`;
  if (!cell) {
    return `${base}: no planned work`;
  }
  const stateLabel = cell.state === "on_call" ? "on call" : "assigned route";
  const overrideLabel = cell.manualOverride ? ", manually overridden" : "";
  return `${base}: ${stateLabel}${overrideLabel}`;
}

function formatDriverHours(hours: number | null | undefined): string {
  return typeof hours === "number" && Number.isFinite(hours) ? `${hours.toFixed(1)} h` : "—";
}

function formatStateLabel(state: string | null | undefined): string {
  const value = asText(state);
  if (!value) {
    return "—";
  }
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function normalizePreferenceState(state: string | null | undefined): DriverPreferenceState {
  const value = asText(state);
  if (
    value === "open_to_work" ||
    value === "prefer_not_to_work" ||
    value === "definitely_can_not_work"
  ) {
    return value;
  }
  return "unset";
}

function buildHeaderMetricRows(
  serviceDates: WorkpageScheduleHeatmapDate[],
  routeDemandUnresolvedCounts: Record<string, number>
): HeaderMetricRow[] {
  const rows: HeaderMetricRow[] = [
    { key: "required", label: "Req", accessibilityLabel: "Required routes" },
    { key: "scheduled", label: "Sched", accessibilityLabel: "Scheduled routes" },
    { key: "on_call", label: "OC", accessibilityLabel: "On-call coverage" },
    { key: "available", label: "Avail", accessibilityLabel: "Available drivers" }
  ];
  if (
    serviceDates.some((serviceDate) => (routeDemandUnresolvedCounts[serviceDate.service_date] ?? 0) > 0)
  ) {
    rows.push({ key: "gap", label: "Gap", accessibilityLabel: "Uncovered route gap" });
  }
  return rows;
}

function formatHeaderMetricValue(
  row: HeaderMetricRow,
  dayStats: WorkpageScheduleCalculationTopBarDay | null,
  unresolvedCount: number
): { visibleValue: string; spokenValue: string; isBlank: boolean } {
  switch (row.key) {
    case "required": {
      const visibleValue =
        typeof dayStats?.routes_required === "number" ? String(dayStats.routes_required) : "—";
      return {
        visibleValue,
        spokenValue: visibleValue === "—" ? "Not available" : visibleValue,
        isBlank: false
      };
    }
    case "scheduled": {
      const visibleValue =
        typeof dayStats?.routes_scheduled === "number" ? String(dayStats.routes_scheduled) : "—";
      return {
        visibleValue,
        spokenValue: visibleValue === "—" ? "Not available" : visibleValue,
        isBlank: false
      };
    }
    case "on_call": {
      if (!dayStats) {
        return {
          visibleValue: "—",
          spokenValue: "Not available",
          isBlank: false
        };
      }
      const scheduled = typeof dayStats.on_call_drivers === "number" ? String(dayStats.on_call_drivers) : "—";
      return {
        visibleValue: `${scheduled} / ${dayStats.on_call_target}`,
        spokenValue:
          scheduled === "—"
            ? `Not available out of ${dayStats.on_call_target}`
            : `${scheduled} out of ${dayStats.on_call_target}`,
        isBlank: false
      };
    }
    case "available": {
      const visibleValue =
        typeof dayStats?.available_driver_count === "number"
          ? String(dayStats.available_driver_count)
          : "—";
      return {
        visibleValue,
        spokenValue: visibleValue === "—" ? "Not available" : visibleValue,
        isBlank: false
      };
    }
    case "gap": {
      if (unresolvedCount > 0) {
        return {
          visibleValue: String(unresolvedCount),
          spokenValue: String(unresolvedCount),
          isBlank: false
        };
      }
      return {
        visibleValue: "\u00a0",
        spokenValue: "No uncovered routes",
        isBlank: true
      };
    }
  }
}

function formatPreferenceStateLabel(state: DriverPreferenceState): string {
  if (state === "open_to_work") {
    return "Open to work";
  }
  if (state === "prefer_not_to_work") {
    return "Prefer not to work";
  }
  if (state === "definitely_can_not_work") {
    return "Cannot work";
  }
  return "Unset";
}

function formatPreviousWeekRealityState(state: string | null | undefined): string {
  switch (asText(state)) {
    case "worked":
      return "Worked";
    case "blocked_previous_week":
      return "Blocked";
    case "available_not_assigned":
      return "Available";
    case "pattern_off":
      return "Pattern off";
    default:
      return "Reality";
  }
}

function previousWeekRealityTone(state: string | null | undefined): string {
  switch (asText(state)) {
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

function formatMinutes(minutes: number | null | undefined): string {
  if (!minutes || minutes <= 0) {
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

function realityFlagsLabel(cell: DerivedHeatmapCell | null): string {
  if (!cell) {
    return "";
  }
  return [
    cell.previousWeekCallInSickFlag ? "Sick" : null,
    cell.previousWeekCancellationFlag ? "Cancelled" : null,
    cell.previousWeekNonWorkingDayFlag ? "Non-working" : null
  ]
    .filter(Boolean)
    .join(", ");
}

function renderRealityCell(input: {
  personName: string;
  serviceDateLabel: string;
  cell: DerivedHeatmapCell | null;
  testId: string;
  badgeLabel: string;
  ariaPrefix: string;
  selectedDay?: boolean;
  useRollingSummary?: boolean;
}): JSX.Element {
  const realityTone = previousWeekRealityTone(input.cell?.previousWeekNormalizedState);
  const realityFlags = realityFlagsLabel(input.cell);
  return (
    <div
      className={`schedule-heatmap__cell schedule-heatmap__cell--readonly schedule-heatmap__cell--reality-${realityTone}${
        input.selectedDay ? " schedule-heatmap__cell--selected-day" : ""
      }`}
      data-testid={input.testId}
      aria-label={`${input.personName} on ${input.serviceDateLabel}: ${input.ariaPrefix} ${formatPreviousWeekRealityState(
        input.cell?.previousWeekNormalizedState
      ).toLowerCase()}`}
    >
      <span className="schedule-heatmap__cell-top">
        <span className="schedule-heatmap__cell-state">
          {formatPreviousWeekRealityState(input.cell?.previousWeekNormalizedState)}
        </span>
        <span className="schedule-heatmap__cell-chip">{input.badgeLabel}</span>
      </span>
      <span className="schedule-heatmap__cell-meta schedule-heatmap__cell-meta--reality">
        <span className="schedule-heatmap__reality-primary-metric">
          {formatMinutes(input.cell?.previousWeekActualMinutes)}
        </span>
        <span className="schedule-heatmap__reality-secondary-metric">
          [{formatMinutes(
            input.useRollingSummary
              ? input.cell?.realitySummaryMinutes
              : input.cell?.previousWeekCumulativeWeekMinutes
          )}]
        </span>
      </span>
      {realityFlags ? (
        <span className="schedule-heatmap__reality-flags">{realityFlags}</span>
      ) : (
        <span className="schedule-heatmap__reality-flags schedule-heatmap__reality-flags--empty">
          No flags
        </span>
      )}
    </div>
  );
}

function isAvailableSelectedDayState(state: string | null | undefined): boolean {
  const value = asText(state).toLowerCase();
  return value === "available" || value === "avoid_if_possible" || value === "on_call_only";
}

function isSickNoShowAvailability(availability: AvailabilityCellState | null | undefined): boolean {
  return availability?.reasonCode === "sick_no_show";
}

function pillToneForState(state: string | null | undefined): string {
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

export function ScheduleHeatmapEditor({
  section,
  assignmentRows,
  reserveRows,
  onRowsChange,
  readOnly = false,
  selectedServiceDateOverride = null,
  selectedServiceDate = null,
  availableDriverIds = [],
  driverMetrics = [],
  topBarDays = [],
  density = "default",
  headerExtras = null,
  onMarkSickNoShow,
  sickNoShowDisabled = false,
  sickNoShowPendingKey = null,
  routeDemandUnresolvedCounts = {},
  routeDemandPendingCells = {},
  onRouteDemandCellToggle
}: {
  section: WorkpageScheduleHeatmapSection | ScheduleHybridHeatmapSection;
  assignmentRows: WorkpageTableRow[];
  reserveRows: WorkpageTableRow[];
  onRowsChange?: (next: { assignmentRows: WorkpageTableRow[]; reserveRows: WorkpageTableRow[] }) => void;
  readOnly?: boolean;
  selectedServiceDateOverride?: string | null;
  selectedServiceDate?: string | null;
  availableDriverIds?: string[];
  driverMetrics?: WorkpageScheduleDriverMetric[];
  topBarDays?: WorkpageScheduleCalculationTopBarDay[];
  density?: "default" | "compact";
  headerExtras?: ReactNode;
  onMarkSickNoShow?: (target: ScheduleSickNoShowTarget) => void;
  sickNoShowDisabled?: boolean;
  sickNoShowPendingKey?: string | null;
  routeDemandUnresolvedCounts?: Record<string, number>;
  routeDemandPendingCells?: Record<string, ScheduleRouteDemandPendingCell>;
  onRouteDemandCellToggle?: (target: {
    driverId: string;
    driverName: string;
    serviceDate: string;
    serviceDateLabel: string;
  }) => string | null;
}): JSX.Element {
  const [armedCell, setArmedCell] = useState<ArmedCell | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const isCompact = density === "compact";

  const serviceDates = useMemo(
    () => buildServiceDates(section, assignmentRows, reserveRows),
    [assignmentRows, reserveRows, section]
  );
  const people = useMemo(
    () => buildPeople(section, assignmentRows, reserveRows),
    [assignmentRows, reserveRows, section]
  );
  const cellMap = useMemo(
    () => buildCellMap(people, assignmentRows, reserveRows),
    [assignmentRows, people, reserveRows]
  );
  const preferenceStateByCell = useMemo(() => buildPreferenceStateMap(people), [people]);
  const availabilityStateByCell = useMemo(() => buildAvailabilityStateMap(people), [people]);
  const driverMetricById = useMemo(
    () => new Map(driverMetrics.map((metric) => [metric.driver_id, metric])),
    [driverMetrics]
  );
  const topBarDayByServiceDate = useMemo(
    () => new Map(topBarDays.map((day) => [day.service_date, day])),
    [topBarDays]
  );
  const headerMetricRows = useMemo(
    () => buildHeaderMetricRows(serviceDates, routeDemandUnresolvedCounts),
    [routeDemandUnresolvedCounts, serviceDates]
  );
  const previousWeekServiceDates = useMemo(
    () => serviceDates.filter((serviceDate) => isHybridRealityDate(serviceDate)),
    [serviceDates]
  );
  const currentWeekServiceDates = useMemo(
    () => serviceDates.filter((serviceDate) => !isHybridRealityDate(serviceDate)),
    [serviceDates]
  );
  const scheduledRegionColumnSpan = 5 + currentWeekServiceDates.length;
  const effectiveSelectedServiceDate = selectedServiceDateOverride ?? selectedServiceDate;
  const effectiveAvailableDriverIds = useMemo(() => {
    if (!selectedServiceDateOverride) {
      return availableDriverIds;
    }
    return people
      .filter((person) =>
        isAvailableSelectedDayState(
          availabilityStateByCell.get(`${effectiveSelectedServiceDate}:${person.driver_id}`)?.state
        )
      )
      .map((person) => person.driver_id);
  }, [
    availabilityStateByCell,
    availableDriverIds,
    effectiveSelectedServiceDate,
    people,
    selectedServiceDateOverride
  ]);
  const headerDescription =
    !isCompact || armedCell
      ? armedCell
        ? `Moving ${armedCell.driverName}. Pick another cell on ${armedCell.serviceDate} to move or swap it.`
        : section.subtitle ??
          (readOnly
            ? "Server-authoritative schedule heatmap. Edit controls stay on draft artifact pages."
            : "Click a filled cell to start moving planned work.")
      : null;

  return (
    <section className={`workpage-panel schedule-heatmap${isCompact ? " schedule-heatmap--compact" : ""}`}>
      <header className="workpage-panel__header schedule-heatmap__header">
        {headerDescription ? (
          <div className="schedule-heatmap__header-copy">
            <p>{headerDescription}</p>
          </div>
        ) : null}
        <div className="schedule-heatmap__header-meta">
          <div className="schedule-heatmap__header-toolbar">
            <section
              className="schedule-heatmap__header-group schedule-heatmap__header-group--legend"
              aria-label="Heatmap legend"
            >
              <span className="schedule-heatmap__legend-label">Legend</span>
              <div className="schedule-heatmap__legend">
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--assigned" />
                  Assigned route
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--reserve" />
                  On call
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--empty" />
                  No planned work
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--manual" />
                  Manual override
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--pending" />
                  Pending route add
                </span>
                <span className="schedule-heatmap__legend-item">
                  <span className="schedule-heatmap__legend-swatch schedule-heatmap__legend-swatch--reality" />
                  Previous-week reality
                </span>
              </div>
            </section>
            {headerExtras}
          </div>
        </div>
      </header>

      {statusMessage ? (
        <p className="schedule-heatmap__status" role="status">
          {statusMessage}
        </p>
      ) : null}

      <div className="schedule-heatmap__wrap">
        <table className="schedule-heatmap__table">
          <thead>
            <tr className="schedule-heatmap__group-header-row">
              <th scope="col" className="schedule-heatmap__group-header schedule-heatmap__group-header--spacer" />
              {previousWeekServiceDates.length > 0 ? (
                <th
                  scope="colgroup"
                  colSpan={previousWeekServiceDates.length}
                  className="schedule-heatmap__group-header schedule-heatmap__group-header--reality"
                >
                  <span className="schedule-heatmap__group-title">Dispatch Reports</span>
                </th>
              ) : null}
              <th
                scope="colgroup"
                colSpan={scheduledRegionColumnSpan}
                className="schedule-heatmap__group-header schedule-heatmap__group-header--scheduled"
              >
                <span className="schedule-heatmap__group-title">Scheduled Routes</span>
              </th>
            </tr>
            <tr className="schedule-heatmap__column-header-row">
              <th scope="col" className="schedule-heatmap__person-header">
                <span aria-hidden="true">Roster</span>
                <strong>People</strong>
              </th>
              {previousWeekServiceDates.map((serviceDate) => {
                const unresolvedCount =
                  routeDemandUnresolvedCounts[serviceDate.service_date] ?? 0;
                const dateHeaderClassName = [
                  "schedule-heatmap__date-header",
                  effectiveSelectedServiceDate === serviceDate.service_date
                    ? "schedule-heatmap__date-header--selected"
                    : "",
                  "schedule-heatmap__date-header--comparison",
                  unresolvedCount > 0 ? "schedule-heatmap__date-header--uncovered" : ""
                ]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <th
                    key={serviceDate.service_date}
                    scope="col"
                    className={dateHeaderClassName}
                  >
                    <span>{serviceDate.weekday_label}</span>
                    <strong>{serviceDate.label}</strong>
                    <div className="schedule-heatmap__comparison-column-copy">
                      <span className="schedule-heatmap__comparison-badge">Reality</span>
                      <small>Read-only prior week</small>
                    </div>
                  </th>
                );
              })}
              <th scope="col" className="schedule-heatmap__metric-header schedule-heatmap__metric-header--hours">
                <span aria-hidden="true">Metrics</span>
                <strong>{isCompact ? "Hrs" : "Hours"}</strong>
              </th>
              <th scope="col" className="schedule-heatmap__metric-header schedule-heatmap__metric-header--routes">
                <span aria-hidden="true">Metrics</span>
                <strong>{isCompact ? "Rt" : "Routes"}</strong>
              </th>
              <th scope="col" className="schedule-heatmap__metric-header schedule-heatmap__metric-header--on-call">
                <span aria-hidden="true">Metrics</span>
                <strong>{isCompact ? "OC" : "On call"}</strong>
              </th>
              <th
                scope="col"
                className="schedule-heatmap__metric-header schedule-heatmap__metric-header--compliance"
              >
                <span aria-hidden="true">Risk</span>
                <strong>{isCompact ? "Risk" : "Compliance"}</strong>
              </th>
              <th
                scope="col"
                aria-label="Day summary metrics"
                className="schedule-heatmap__summary-rail-header"
              >
                <span aria-hidden="true">Summary</span>
                <strong>Metrics</strong>
                <div className="schedule-heatmap__summary-stack" role="list" aria-hidden="true">
                  {headerMetricRows.map((row) => (
                    <div
                      key={row.key}
                      className="schedule-heatmap__summary-row schedule-heatmap__summary-row--label"
                      role="listitem"
                    >
                      {row.label}
                    </div>
                  ))}
                </div>
              </th>
              {currentWeekServiceDates.map((serviceDate, currentWeekIndex) => {
                const isReadOnlyCurrentWeekColumn =
                  isHybridReadOnlyDate(serviceDate);
                const dayStats = topBarDayByServiceDate.get(serviceDate.service_date) ?? null;
                const unresolvedCount =
                  routeDemandUnresolvedCounts[serviceDate.service_date] ?? 0;
                const dateHeaderClassName = [
                  "schedule-heatmap__date-header",
                  "schedule-heatmap__date-header--scheduled",
                  effectiveSelectedServiceDate === serviceDate.service_date
                    ? "schedule-heatmap__date-header--selected"
                    : "",
                  isReadOnlyCurrentWeekColumn
                    ? "schedule-heatmap__date-header--planned-readonly"
                    : "",
                  currentWeekIndex === currentWeekServiceDates.length - 1
                    ? "schedule-heatmap__date-header--scheduled-end"
                    : "",
                  unresolvedCount > 0 ? "schedule-heatmap__date-header--uncovered" : ""
                ]
                  .filter(Boolean)
                  .join(" ");
                return (
                  <th
                    key={serviceDate.service_date}
                    scope="col"
                    className={dateHeaderClassName}
                  >
                    <span>{serviceDate.weekday_label}</span>
                    <strong>{serviceDate.label}</strong>
                    <div
                      className="schedule-heatmap__summary-stack"
                      role="list"
                      aria-label={`Daily stats for ${serviceDate.label}`}
                    >
                      {headerMetricRows.map((row) => {
                        const metricValue = formatHeaderMetricValue(row, dayStats, unresolvedCount);
                        return (
                          <div
                            key={`${serviceDate.service_date}:${row.key}`}
                            className="schedule-heatmap__summary-row"
                            role="listitem"
                          >
                            <span className="visually-hidden">
                              {`${row.accessibilityLabel} for ${serviceDate.label}: ${metricValue.spokenValue}`}
                            </span>
                            <span
                              aria-hidden="true"
                              className={`schedule-heatmap__summary-value${
                                metricValue.isBlank ? " schedule-heatmap__summary-value--blank" : ""
                              }`}
                            >
                              {metricValue.visibleValue}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {people.map((person, personIndex) => {
              const metric = driverMetricById.get(person.driver_id) ?? null;
              const isAvailableOnSelectedDay = effectiveAvailableDriverIds.includes(person.driver_id);
              const personCellClassName = [
                "schedule-heatmap__person-cell",
                isAvailableOnSelectedDay ? "schedule-heatmap__person-cell--available" : "",
                metric?.compliance_state === "fail" ? "schedule-heatmap__person-cell--blocked" : ""
              ]
                .filter(Boolean)
                .join(" ");
              return (
                <tr key={person.driver_id}>
                  <th scope="row" className={personCellClassName}>
                    <div className="schedule-heatmap__person">
                      <strong>{person.driver_name}</strong>
                      {!isCompact ? (
                        <span className="schedule-heatmap__person-meta">
                          {[person.employment_type, person.on_call_eligible ? "on-call eligible" : ""]
                            .filter((value) => value.length > 0)
                            .join(" · ") || "planner roster"}
                        </span>
                      ) : null}
                      {!isCompact && effectiveSelectedServiceDate ? (
                        <span className="schedule-heatmap__person-cues">
                          {isAvailableOnSelectedDay ? "Available on selected day" : "Scheduled on selected day"}
                          {metric?.compliance_state === "fail" ? " · Compliance watch" : ""}
                        </span>
                      ) : null}
                    </div>
                  </th>
                  {previousWeekServiceDates.map((serviceDate) => {
                    const cellKey = `${serviceDate.service_date}:${person.driver_id}`;
                    const cell = cellMap.get(cellKey) ?? null;
                    return (
                      <td key={`${person.driver_id}:${serviceDate.service_date}`}>
                        <div className="schedule-heatmap__cell-wrap">
                          {renderRealityCell({
                            personName: person.driver_name,
                            serviceDateLabel: serviceDate.label,
                            cell,
                            testId: `schedule-heatmap-cell-${serviceDate.service_date}-${person.driver_id}`,
                            badgeLabel: "Reality",
                            ariaPrefix: "previous-week reality",
                            useRollingSummary: false
                          })}
                        </div>
                      </td>
                    );
                  })}
                  <td
                    className={`schedule-heatmap__metric-cell schedule-heatmap__metric-cell--hours${
                      personIndex === people.length - 1
                        ? " schedule-heatmap__scheduled-region-cell--bottom"
                        : ""
                    }`}
                  >
                    <span className="schedule-heatmap__metric-value">
                      {formatDriverHours(metric?.scheduled_hours)}
                    </span>
                  </td>
                  <td
                    className={`schedule-heatmap__metric-cell schedule-heatmap__metric-cell--routes${
                      personIndex === people.length - 1
                        ? " schedule-heatmap__scheduled-region-cell--bottom"
                        : ""
                    }`}
                  >
                    <span className="schedule-heatmap__metric-value">
                      {metric ? String(metric.scheduled_routes) : "—"}
                    </span>
                  </td>
                  <td
                    className={`schedule-heatmap__metric-cell schedule-heatmap__metric-cell--on-call${
                      personIndex === people.length - 1
                        ? " schedule-heatmap__scheduled-region-cell--bottom"
                        : ""
                    }`}
                  >
                    <span className="schedule-heatmap__metric-value">
                      {metric ? String(metric.on_call_shifts) : "—"}
                    </span>
                  </td>
                  <td
                    className={`schedule-heatmap__metric-cell schedule-heatmap__metric-cell--compliance${
                      personIndex === people.length - 1
                        ? " schedule-heatmap__scheduled-region-cell--bottom"
                        : ""
                    }`}
                  >
                    {metric ? (
                      <div className="schedule-heatmap__compliance-cell">
                        {metric.issues.length > 0 ? (
                          <InfoDialog
                            className={`schedule-pill schedule-pill--${pillToneForState(
                              metric.compliance_state
                            )} schedule-heatmap__risk-trigger`}
                            triggerLabel={`Open compliance details for ${person.driver_name}`}
                            dialogTitle={`Compliance details for ${person.driver_name}`}
                            dialogDescription={`${formatStateLabel(
                              metric.compliance_state
                            )} status from backend schedule calculations.`}
                            triggerContent={
                              <>
                                <span>{formatStateLabel(metric.compliance_state)}</span>
                                <span className="schedule-heatmap__risk-trigger-icon" aria-hidden="true">
                                  i
                                </span>
                              </>
                            }
                          >
                            <div className="schedule-heatmap__issue-panel">
                              <p className="schedule-heatmap__issue-description">
                                These compliance issues come directly from backend schedule
                                calculations for this driver.
                              </p>
                              <div className="schedule-heatmap__issue-summary">
                                <span
                                  className={`schedule-pill schedule-pill--${pillToneForState(
                                    metric.compliance_state
                                  )}`}
                                >
                                  {formatStateLabel(metric.compliance_state)}
                                </span>
                                <span>{`${metric.issues.length} issue${
                                  metric.issues.length === 1 ? "" : "s"
                                }`}</span>
                              </div>
                              <ul className="schedule-heatmap__issue-list">
                                {metric.issues.map((issue) => (
                                  <li key={issue}>{issue}</li>
                                ))}
                              </ul>
                            </div>
                          </InfoDialog>
                        ) : (
                          <span
                            className={`schedule-pill schedule-pill--${pillToneForState(
                              metric.compliance_state
                            )}`}
                          >
                            {formatStateLabel(metric.compliance_state)}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="schedule-heatmap__metric-value">—</span>
                    )}
                  </td>
                  {personIndex === 0 ? (
                    <td
                      rowSpan={people.length}
                      aria-hidden="true"
                      className="schedule-heatmap__summary-rail-spacer"
                    />
                  ) : null}
                  {currentWeekServiceDates.map((serviceDate, currentWeekIndex) => {
                    const cellKey = `${serviceDate.service_date}:${person.driver_id}`;
                    const cell = cellMap.get(cellKey) ?? null;
                    const pendingRouteDemandCell = routeDemandPendingCells[cellKey] ?? null;
                    const preferenceState =
                      preferenceStateByCell.get(cellKey) ?? "unset";
                    const availabilityState = availabilityStateByCell.get(cellKey) ?? null;
                    const isComparisonCell = cell?.cellProvenance === "previous_week_reality";
                    const isSickNoShow = isSickNoShowAvailability(availabilityState);
                    const preferenceLabel = formatPreferenceStateLabel(preferenceState);
                    const isArmed =
                      armedCell?.serviceDate === serviceDate.service_date &&
                      armedCell.driverId === person.driver_id;
                    const isSelectedDay = effectiveSelectedServiceDate === serviceDate.service_date;
                    const isAvailableCell =
                      isSelectedDay && effectiveAvailableDriverIds.includes(person.driver_id);
                    const isCurrentWeekReadOnlyCell =
                      !isComparisonCell && isHybridReadOnlyDate(serviceDate);
                    const isCellReadOnly = readOnly || isCurrentWeekReadOnlyCell || isComparisonCell;
                    const sickNoShowPending = sickNoShowPendingKey === cellKey;
                    const sickNoShowActionDisabled =
                      sickNoShowDisabled ||
                      sickNoShowPending ||
                      isSickNoShow ||
                      isCellReadOnly;
                    const visualCellState = pendingRouteDemandCell ? "pending" : cell?.state ?? "empty";
                    const cellStateLabel =
                      visualCellState === "pending"
                        ? "Pending route"
                        : cell?.state === "assigned"
                          ? "Route"
                          : cell?.state === "on_call"
                            ? "On call"
                            : "Open";
                    const scheduledColumnCellClassName = [
                      "schedule-heatmap__scheduled-column-cell",
                      personIndex === people.length - 1
                        ? "schedule-heatmap__scheduled-region-cell--bottom"
                        : "",
                      currentWeekIndex === currentWeekServiceDates.length - 1
                        ? "schedule-heatmap__scheduled-column-cell--end"
                        : ""
                    ]
                      .filter(Boolean)
                      .join(" ");
                    return (
                      <td
                        key={`${person.driver_id}:${serviceDate.service_date}`}
                        className={scheduledColumnCellClassName}
                      >
                        <div className="schedule-heatmap__cell-wrap">
                          {isComparisonCell ? (
                            renderRealityCell({
                              personName: person.driver_name,
                              serviceDateLabel: serviceDate.label,
                              cell,
                              testId: `schedule-heatmap-cell-${serviceDate.service_date}-${person.driver_id}`,
                              badgeLabel: "Report",
                              ariaPrefix: "dispatch report",
                              selectedDay: isSelectedDay,
                              useRollingSummary: true
                            })
                          ) : (
                            <button
                              type="button"
                              className={`schedule-heatmap__cell schedule-heatmap__cell--${
                                visualCellState
                              }${cell?.manualOverride ? " schedule-heatmap__cell--manual" : ""}${
                                isArmed ? " is-armed" : ""
                              }${isSelectedDay ? " schedule-heatmap__cell--selected-day" : ""}${
                                isAvailableCell ? " schedule-heatmap__cell--available" : ""
                              }${metric?.compliance_state === "fail" ? " schedule-heatmap__cell--blocked" : ""}${
                                isSickNoShow ? " schedule-heatmap__cell--sick-no-show" : ""
                              }${isCellReadOnly ? " schedule-heatmap__cell--readonly" : ""}${
                                isCurrentWeekReadOnlyCell
                                  ? " schedule-heatmap__cell--planned-readonly"
                                  : ""
                              }`}
                              data-testid={`schedule-heatmap-cell-${serviceDate.service_date}-${person.driver_id}`}
                              aria-label={
                                isSickNoShow
                                  ? `Sick / No Show: ${person.driver_name} on ${serviceDate.label}`
                                  : pendingRouteDemandCell
                                    ? `${person.driver_name} on ${serviceDate.label}: pending route add for ${pendingRouteDemandCell.routeId}`
                                    : buildCellLabel(person, serviceDate, cell)
                              }
                              aria-pressed={isArmed}
                              aria-disabled={isCellReadOnly}
                              onClick={() => {
                                if (isCellReadOnly || !onRowsChange) {
                                  setStatusMessage(
                                    isCurrentWeekReadOnlyCell
                                      ? "Past current-week days are read-only in this comparison view."
                                      : "This view is read-only. Open a draft artifact to move schedule cells."
                                  );
                                  return;
                                }
                                if (!armedCell) {
                                  if (!cell) {
                                    if (onRouteDemandCellToggle) {
                                      setStatusMessage(
                                        onRouteDemandCellToggle({
                                          driverId: person.driver_id,
                                          driverName: person.driver_name,
                                          serviceDate: serviceDate.service_date,
                                          serviceDateLabel: serviceDate.label
                                        })
                                      );
                                      return;
                                    }
                                    setStatusMessage(
                                      "Pick a planned cell first, then move it to another person on the same day."
                                    );
                                    return;
                                  }
                                  setArmedCell({
                                    driverId: person.driver_id,
                                    driverName: person.driver_name,
                                    serviceDate: serviceDate.service_date,
                                    rowKind: cell.rowKind as EditableRowKind,
                                    rowIndex: cell.rowIndex as number
                                  });
                                  setStatusMessage(null);
                                  return;
                                }

                                if (
                                  armedCell.driverId === person.driver_id &&
                                  armedCell.serviceDate === serviceDate.service_date
                                ) {
                                  setArmedCell(null);
                                  setStatusMessage("Move cleared.");
                                  return;
                                }

                                if (armedCell.serviceDate !== serviceDate.service_date) {
                                  setStatusMessage("Moves stay within the same service day.");
                                  return;
                                }

                                let nextAssignmentRows = cloneRows(assignmentRows);
                                let nextReserveRows = cloneRows(reserveRows);

                                const sourceDriverId = armedCell.driverId;

                                if (!cell) {
                                  if (armedCell.rowKind === "assignment") {
                                    nextAssignmentRows = setManualOverride(
                                      nextAssignmentRows,
                                      armedCell.rowIndex,
                                      person.driver_id
                                    );
                                  } else {
                                    nextReserveRows = setManualOverride(
                                      nextReserveRows,
                                      armedCell.rowIndex,
                                      person.driver_id
                                    );
                                  }
                                  onRowsChange({
                                    assignmentRows: nextAssignmentRows,
                                    reserveRows: nextReserveRows
                                  });
                                  setArmedCell(null);
                                  setStatusMessage(
                                    `${armedCell.driverName} moved to ${person.driver_name} on ${serviceDate.service_date}.`
                                  );
                                  return;
                                }

                                if (armedCell.rowKind === "assignment") {
                                  nextAssignmentRows = setManualOverride(
                                    nextAssignmentRows,
                                    armedCell.rowIndex,
                                    person.driver_id
                                  );
                                } else {
                                  nextReserveRows = setManualOverride(
                                    nextReserveRows,
                                    armedCell.rowIndex,
                                    person.driver_id
                                  );
                                }

                                if (cell.rowKind === "assignment") {
                                  nextAssignmentRows = setManualOverride(
                                    nextAssignmentRows,
                                    cell.rowIndex as number,
                                    sourceDriverId
                                  );
                                } else {
                                  nextReserveRows = setManualOverride(
                                    nextReserveRows,
                                    cell.rowIndex as number,
                                    sourceDriverId
                                  );
                                }

                                onRowsChange({
                                  assignmentRows: nextAssignmentRows,
                                  reserveRows: nextReserveRows
                                });
                                setArmedCell(null);
                                setStatusMessage(
                                  `${armedCell.driverName} and ${person.driver_name} swapped on ${serviceDate.service_date}.`
                                );
                              }}
                            >
                              <span className="schedule-heatmap__cell-top">
                                <span className="schedule-heatmap__cell-state">
                                  {cellStateLabel}
                                </span>
                                {pendingRouteDemandCell ? (
                                  <span className="schedule-heatmap__cell-chip">Pending</span>
                                ) : cell?.manualOverride ? (
                                  <span className="schedule-heatmap__cell-chip">Edited</span>
                                ) : null}
                              </span>
                              <span className="schedule-heatmap__cell-meta">
                                {pendingRouteDemandCell?.projectedMinutes
                                  ? `${pendingRouteDemandCell.projectedMinutes} min`
                                  : cell?.projectedMinutes
                                    ? `${cell.projectedMinutes} min`
                                    : "—"}
                              </span>
                              <span
                                className={`schedule-heatmap__preference-bar schedule-heatmap__preference-bar--${preferenceState}`}
                                data-testid={`schedule-heatmap-preference-${serviceDate.service_date}-${person.driver_id}`}
                                aria-label={`Preference: ${preferenceLabel}`}
                                title={`Preference: ${preferenceLabel}`}
                              />
                            </button>
                          )}
                          {onMarkSickNoShow && !isComparisonCell ? (
                            <button
                              type="button"
                              className="schedule-heatmap__sick-button"
                              disabled={sickNoShowActionDisabled}
                              aria-label={`Mark Sick / No Show: ${person.driver_name} on ${serviceDate.label}`}
                              title={
                                isSickNoShow
                                  ? `${person.driver_name} is already Sick / No Show on ${serviceDate.label}`
                                  : `Mark ${person.driver_name} Sick / No Show on ${serviceDate.label}`
                              }
                              onClick={() => {
                                if (sickNoShowActionDisabled) {
                                  return;
                                }
                                onMarkSickNoShow({
                                  driverId: person.driver_id,
                                  driverName: person.driver_name,
                                  serviceDate: serviceDate.service_date,
                                  serviceDateLabel: serviceDate.label,
                                  currentState: cell?.state ?? "empty"
                                });
                              }}
                            >
                              {sickNoShowPending ? "..." : isSickNoShow ? "Sick / No Show" : "Sick"}
                            </button>
                          ) : null}
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
  );
}
