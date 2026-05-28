import type { SchedulePreviousWeekRealityContract } from "@/lib/types/contracts";
import type {
  WorkpageScheduleCalculations,
  WorkpageScheduleHeatmapCell,
  WorkpageScheduleHeatmapDate,
  WorkpageScheduleHeatmapPerson,
  WorkpageScheduleHeatmapSection
} from "@/lib/types/workpages";

export const SCHEDULE_SERVICE_TIMEZONE = "America/Vancouver";

export type ScheduleHybridColumnProvenance =
  | "planned_current_week"
  | "previous_week_reality";

export interface ScheduleHybridHeatmapDate extends WorkpageScheduleHeatmapDate {
  column_provenance: ScheduleHybridColumnProvenance;
  source_service_date: string;
  read_only: boolean;
}

export interface ScheduleHybridHeatmapCell extends WorkpageScheduleHeatmapCell {
  cell_provenance?: ScheduleHybridColumnProvenance;
  source_service_date?: string;
  reality_service_date?: string | null;
  previous_week_normalized_state?: string | null;
  previous_week_blocked_reasons?: string[];
  previous_week_actual_minutes?: number | null;
  previous_week_cumulative_week_minutes?: number | null;
  reality_summary_minutes?: number | null;
  previous_week_route_id?: string | null;
  previous_week_route_slot_class?: string | null;
  previous_week_source_ref?: string | null;
  previous_week_call_in_sick_flag?: boolean;
  previous_week_cancellation_flag?: boolean;
  previous_week_non_working_day_flag?: boolean;
}

export interface ScheduleHybridHeatmapPerson
  extends Omit<WorkpageScheduleHeatmapPerson, "cells"> {
  cells: ScheduleHybridHeatmapCell[];
}

export interface ScheduleHybridHeatmapSection
  extends Omit<WorkpageScheduleHeatmapSection, "service_dates" | "people"> {
  service_dates: ScheduleHybridHeatmapDate[];
  people: ScheduleHybridHeatmapPerson[];
}

export interface ScheduleHybridRealityResult {
  heatmapSection: ScheduleHybridHeatmapSection;
  selectedServiceDateOverride: string | null;
  elapsedCurrentWeekServiceDates: string[];
}

export type ScheduleDisplayedWeekRelation =
  | "no_visible_week"
  | "current_week"
  | "historical_demo_week"
  | "future_week";

export interface ScheduleComparisonContext {
  operationalWeekStart: string | null;
  displayedWeekRelation: ScheduleDisplayedWeekRelation;
  comparisonServiceDate: string | null;
  shouldShowPreviousWeekComparison: boolean;
}

function plannedHybridSection(
  heatmapSection: WorkpageScheduleHeatmapSection
): ScheduleHybridHeatmapSection {
  return {
    ...heatmapSection,
    service_dates: heatmapSection.service_dates.map((serviceDate) => ({
      ...serviceDate,
      column_provenance: "planned_current_week",
      source_service_date: serviceDate.service_date,
      read_only: false
    })),
    people: heatmapSection.people.map((person) => ({
      ...person,
      cells: person.cells.map((cell) => ({
        ...cell,
        cell_provenance: "planned_current_week",
        source_service_date: cell.service_date
      }))
    }))
  };
}

function testCurrentServiceDateOverride(): string | null {
  if (import.meta.env.MODE !== "test") {
    return null;
  }
  const override = (
    globalThis as {
      __COMPANYOS_TEST_CURRENT_SERVICE_DATE__?: unknown;
    }
  ).__COMPANYOS_TEST_CURRENT_SERVICE_DATE__;
  if (typeof override !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(override)) {
    return null;
  }
  return override;
}

function addDays(isoDate: string, days: number): string | null {
  const date = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function operationalWeekServiceDates(operationalWeekStart: string): string[] {
  const dates: string[] = [];
  for (let offset = 0; offset < 7; offset += 1) {
    const serviceDate = addDays(operationalWeekStart, offset);
    if (!serviceDate) {
      return [];
    }
    dates.push(serviceDate);
  }
  return dates;
}

function applyDisplayedRollingRealitySummaries(input: {
  cells: ScheduleHybridHeatmapCell[];
  serviceDates: ScheduleHybridHeatmapDate[];
}): ScheduleHybridHeatmapCell[] {
  return input.cells.map((cell, index) => {
    const serviceDate = input.serviceDates[index] ?? null;
    if (
      !serviceDate ||
      serviceDate.column_provenance !== "planned_current_week" ||
      !serviceDate.read_only ||
      cell.cell_provenance !== "previous_week_reality"
    ) {
      return cell;
    }

    let total = 0;
    let includedCount = 0;
    for (let cursor = index; cursor >= 0 && includedCount < 7; cursor -= 1) {
      const candidate = input.cells[cursor];
      if (candidate?.cell_provenance !== "previous_week_reality") {
        continue;
      }
      total += candidate.previous_week_actual_minutes ?? 0;
      includedCount += 1;
    }

    return {
      ...cell,
      reality_summary_minutes: total
    };
  });
}

function visibleServiceDates(
  heatmapSection: WorkpageScheduleHeatmapSection | null | undefined
): string[] {
  return (heatmapSection?.service_dates ?? [])
    .map((serviceDate) => serviceDate.service_date)
    .filter((serviceDate) => /^\d{4}-\d{2}-\d{2}$/.test(serviceDate));
}

function serviceDateWithinOperationalWeek(
  operationalWeekStart: string,
  serviceDate: string | null | undefined
): boolean {
  if (!serviceDate) {
    return false;
  }
  const weekDates = operationalWeekServiceDates(operationalWeekStart);
  const weekStart = weekDates[0] ?? null;
  const weekEnd = weekDates[weekDates.length - 1] ?? null;
  if (!weekStart || !weekEnd) {
    return false;
  }
  return serviceDate.localeCompare(weekStart) >= 0 && serviceDate.localeCompare(weekEnd) <= 0;
}

function serviceDateFormatter(timeZone: string): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
}

export function currentServiceDateInTimeZone(
  now: Date = new Date(),
  timeZone = SCHEDULE_SERVICE_TIMEZONE
): string {
  const override = testCurrentServiceDateOverride();
  if (override) {
    return override;
  }
  const formatter = serviceDateFormatter(timeZone);
  const parts = formatter.formatToParts(now);
  const year = parts.find((part) => part.type === "year")?.value ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  return `${year}-${month}-${day}`;
}

export function elapsedCurrentWeekServiceDates(input: {
  operationalWeekStart: string;
  currentServiceDate: string;
}): string[] {
  const weekDates = operationalWeekServiceDates(input.operationalWeekStart);
  if (weekDates.length !== 7) {
    return [];
  }
  const weekStart = weekDates[0] ?? "";
  const weekEnd = weekDates[weekDates.length - 1] ?? "";
  if (!weekStart || !weekEnd) {
    return [];
  }
  if (
    input.currentServiceDate.localeCompare(weekStart) < 0 ||
    input.currentServiceDate.localeCompare(weekEnd) > 0
  ) {
    return [];
  }
  return weekDates.filter((serviceDate) => serviceDate.localeCompare(input.currentServiceDate) < 0);
}

export function resolveOperationalWeekStart(input: {
  summaryOperationalWeekStart?: string | null;
  heatmapSection?: WorkpageScheduleHeatmapSection | null;
}): string | null {
  const summaryOperationalWeekStart = input.summaryOperationalWeekStart ?? null;
  const heatmapServiceDates = visibleServiceDates(input.heatmapSection);
  const visibleWeekStart = heatmapServiceDates[0] ?? null;
  if (!summaryOperationalWeekStart) {
    return visibleWeekStart;
  }
  if (!visibleWeekStart) {
    return summaryOperationalWeekStart;
  }
  const summaryWeekDates = new Set(operationalWeekServiceDates(summaryOperationalWeekStart));
  const visibleDatesMatchSummaryWeek = heatmapServiceDates.every((serviceDate) =>
    summaryWeekDates.has(serviceDate)
  );
  return visibleDatesMatchSummaryWeek ? summaryOperationalWeekStart : visibleWeekStart;
}

function resolveDisplayedWeekRelation(input: {
  operationalWeekStart: string | null | undefined;
  currentServiceDate: string;
}): ScheduleDisplayedWeekRelation {
  if (!input.operationalWeekStart) {
    return "no_visible_week";
  }
  if (serviceDateWithinOperationalWeek(input.operationalWeekStart, input.currentServiceDate)) {
    return "current_week";
  }
  const weekDates = operationalWeekServiceDates(input.operationalWeekStart);
  const weekStart = weekDates[0] ?? null;
  const weekEnd = weekDates[weekDates.length - 1] ?? null;
  if (!weekStart || !weekEnd) {
    return "no_visible_week";
  }
  if (weekEnd.localeCompare(input.currentServiceDate) < 0) {
    return "historical_demo_week";
  }
  if (weekStart.localeCompare(input.currentServiceDate) > 0) {
    return "future_week";
  }
  return "no_visible_week";
}

export function resolveScheduleComparisonContext(input: {
  summaryOperationalWeekStart?: string | null;
  heatmapSection?: WorkpageScheduleHeatmapSection | null;
  currentServiceDate: string;
  fallbackServiceDate?: string | null;
}): ScheduleComparisonContext {
  const operationalWeekStart = resolveOperationalWeekStart({
    summaryOperationalWeekStart: input.summaryOperationalWeekStart,
    heatmapSection: input.heatmapSection
  });
  const displayedWeekRelation = resolveDisplayedWeekRelation({
    operationalWeekStart,
    currentServiceDate: input.currentServiceDate
  });
  const fallbackInWeek = serviceDateWithinOperationalWeek(
    operationalWeekStart ?? "",
    input.fallbackServiceDate
  );
  const comparisonServiceDate =
    displayedWeekRelation === "current_week"
      ? input.currentServiceDate
      : displayedWeekRelation === "historical_demo_week" && fallbackInWeek
        ? input.fallbackServiceDate ?? null
        : null;
  return {
    operationalWeekStart,
    displayedWeekRelation,
    comparisonServiceDate,
    shouldShowPreviousWeekComparison: operationalWeekStart !== null
  };
}

export function resolveComparisonServiceDate(input: {
  operationalWeekStart: string | null | undefined;
  currentServiceDate: string;
  fallbackServiceDate?: string | null;
}): string | null {
  const displayedWeekRelation = resolveDisplayedWeekRelation({
    operationalWeekStart: input.operationalWeekStart,
    currentServiceDate: input.currentServiceDate
  });
  if (displayedWeekRelation === "current_week") {
    return input.currentServiceDate;
  }
  if (
    displayedWeekRelation === "historical_demo_week" &&
    serviceDateWithinOperationalWeek(input.operationalWeekStart ?? "", input.fallbackServiceDate)
  ) {
    return input.fallbackServiceDate ?? null;
  }
  return null;
}

export function previousWeekRealityDateByCurrentWeekDate(input: {
  operationalWeekStart: string;
  currentWeekServiceDates: string[];
}): Record<string, string> {
  const weekDates = operationalWeekServiceDates(input.operationalWeekStart);
  const result: Record<string, string> = {};
  for (const serviceDate of input.currentWeekServiceDates) {
    const index = weekDates.indexOf(serviceDate);
    if (index < 0) {
      continue;
    }
    const previousWeekServiceDate = addDays(weekDates[index] ?? "", -7);
    if (previousWeekServiceDate) {
      result[serviceDate] = previousWeekServiceDate;
    }
  }
  return result;
}

function realityCellFromContract(input: {
  reality: SchedulePreviousWeekRealityContract;
  driverId: string;
  realityServiceDate: string;
  sourceServiceDate: string;
  displayServiceDate?: string;
  plannedCell?: WorkpageScheduleHeatmapCell | null;
}): ScheduleHybridHeatmapCell {
  const driver =
    input.reality.previous_week_reality.drivers.find((item) => item.driver_id === input.driverId) ??
    null;
  const cell = driver?.cells.find((item) => item.service_date === input.realityServiceDate) ?? null;
  return {
    service_date: input.displayServiceDate ?? input.realityServiceDate,
    state: "empty",
    row_kind: null,
    route_slot_id: null,
    projected_minutes: null,
    assignment_status: null,
    planned_driver_day_state: null,
    manual_override: false,
    preference_state: input.plannedCell?.preference_state,
    availability_state: input.plannedCell?.availability_state ?? null,
    availability_reason_code: input.plannedCell?.availability_reason_code ?? null,
    availability_source_ref: input.plannedCell?.availability_source_ref ?? null,
    cell_provenance: "previous_week_reality",
    source_service_date: input.sourceServiceDate,
    reality_service_date: input.realityServiceDate,
    previous_week_normalized_state: cell?.normalized_state ?? "pattern_off",
    previous_week_blocked_reasons: cell?.blocked_reasons ?? [],
    previous_week_actual_minutes: cell?.actual_minutes ?? 0,
    previous_week_cumulative_week_minutes: cell?.cumulative_week_minutes ?? 0,
    reality_summary_minutes: null,
    previous_week_route_id: cell?.route_id ?? null,
    previous_week_route_slot_class: cell?.route_slot_class ?? null,
    previous_week_source_ref: cell?.source_ref ?? null,
    previous_week_call_in_sick_flag: cell?.call_in_sick_flag ?? false,
    previous_week_cancellation_flag: cell?.cancellation_flag ?? false,
    previous_week_non_working_day_flag: cell?.non_working_day_flag ?? false
  };
}

function resolveSelectedServiceDateOverride(input: {
  calculations: WorkpageScheduleCalculations | null;
  heatmapSection: WorkpageScheduleHeatmapSection | null;
}): string | null {
  const selectedServiceDate = input.calculations?.selected_day.service_date ?? null;
  const serviceDates = input.heatmapSection?.service_dates ?? [];
  if (!selectedServiceDate) {
    return serviceDates[0]?.service_date ?? null;
  }
  if (serviceDates.some((serviceDate) => serviceDate.service_date === selectedServiceDate)) {
    return selectedServiceDate;
  }
  return serviceDates[0]?.service_date ?? null;
}

export function buildHybridScheduleReality(input: {
  calculations: WorkpageScheduleCalculations | null;
  heatmapSection: WorkpageScheduleHeatmapSection | null;
  operationalWeekStart: string | null | undefined;
  reality: SchedulePreviousWeekRealityContract | null;
  comparisonMode?: ScheduleDisplayedWeekRelation | null;
  comparisonServiceDate?: string | null;
  now?: Date;
  timeZone?: string;
}): ScheduleHybridRealityResult | null {
  if (!input.heatmapSection || !input.operationalWeekStart) {
    return null;
  }

  const selectedServiceDateOverride = resolveSelectedServiceDateOverride({
    calculations: input.calculations,
    heatmapSection: input.heatmapSection
  });
  const currentServiceDate =
    input.comparisonServiceDate ??
    currentServiceDateInTimeZone(input.now ?? new Date(), input.timeZone ?? SCHEDULE_SERVICE_TIMEZONE);
  const shouldSubstituteElapsedCurrentWeekDays =
    input.comparisonMode === "current_week" || input.comparisonMode === "historical_demo_week";
  const readOnlyCurrentWeekServiceDates =
    shouldSubstituteElapsedCurrentWeekDays && input.comparisonServiceDate
      ? elapsedCurrentWeekServiceDates({
          operationalWeekStart: input.operationalWeekStart,
          currentServiceDate
        })
      : [];
  const reality = input.reality;

  if (!reality) {
    return {
      heatmapSection: plannedHybridSection(input.heatmapSection),
      selectedServiceDateOverride,
      elapsedCurrentWeekServiceDates: []
    };
  }

  const currentWeekDates = input.heatmapSection.service_dates;
  const previousWeekRealityDates = previousWeekRealityDateByCurrentWeekDate({
    operationalWeekStart: input.operationalWeekStart,
    currentWeekServiceDates: currentWeekDates.map((serviceDate) => serviceDate.service_date)
  });
  const previousWeekColumns: ScheduleHybridHeatmapDate[] = currentWeekDates.flatMap((serviceDate) => {
    const previousWeekServiceDate = previousWeekRealityDates[serviceDate.service_date];
    if (!previousWeekServiceDate) {
      return [];
    }
    const realityDate =
      reality.previous_week_reality.service_dates.find(
        (item) => item.service_date === previousWeekServiceDate
      ) ?? null;
    return [
      {
        ...serviceDate,
        service_date: previousWeekServiceDate,
        label: realityDate?.label ?? previousWeekServiceDate,
        weekday_label: realityDate?.weekday_label ?? serviceDate.weekday_label,
        is_selected_day: false,
        column_provenance: "previous_week_reality" as const,
        source_service_date: serviceDate.service_date,
        read_only: true
      }
    ];
  });
  const currentWeekColumns: ScheduleHybridHeatmapDate[] = currentWeekDates.map((serviceDate) => ({
    ...serviceDate,
    column_provenance: "planned_current_week" as const,
    source_service_date: serviceDate.service_date,
    read_only: readOnlyCurrentWeekServiceDates.includes(serviceDate.service_date)
  }));
  const serviceDates: ScheduleHybridHeatmapDate[] = [
    ...previousWeekColumns,
    ...currentWeekColumns
  ];

  const people: ScheduleHybridHeatmapPerson[] = input.heatmapSection.people.map((person) => {
    const cellsBySourceServiceDate = new Map(
      person.cells.map((cell) => [cell.service_date, cell])
    );
    const cells = serviceDates.map((serviceDate) => {
      const plannedCell = cellsBySourceServiceDate.get(serviceDate.source_service_date) ?? null;
      const realityServiceDate = previousWeekRealityDates[serviceDate.source_service_date] ?? null;
      if (
        serviceDate.column_provenance === "planned_current_week" &&
        serviceDate.read_only &&
        realityServiceDate
      ) {
        return realityCellFromContract({
          reality,
          driverId: person.driver_id,
          realityServiceDate,
          sourceServiceDate: serviceDate.source_service_date,
          displayServiceDate: serviceDate.service_date,
          plannedCell
        });
      }
      if (serviceDate.column_provenance !== "previous_week_reality") {
        return {
          ...(plannedCell ?? {
            service_date: serviceDate.service_date,
            state: "empty" as const,
            row_kind: null,
            route_slot_id: null,
            projected_minutes: null,
            assignment_status: null,
            planned_driver_day_state: null,
            manual_override: false,
            preference_state: undefined,
            availability_state: null,
            availability_reason_code: null,
            availability_source_ref: null
          }),
          service_date: serviceDate.service_date,
          cell_provenance: "planned_current_week" as const,
          source_service_date: serviceDate.source_service_date
        };
      }
      return realityCellFromContract({
        reality,
        driverId: person.driver_id,
        realityServiceDate: serviceDate.service_date,
        sourceServiceDate: serviceDate.source_service_date,
        displayServiceDate: serviceDate.service_date
      });
    });
    return {
      ...person,
      cells: applyDisplayedRollingRealitySummaries({
        cells,
        serviceDates
      })
    };
  });

  return {
    heatmapSection: {
      ...input.heatmapSection,
      service_dates: serviceDates,
      people
    },
    selectedServiceDateOverride,
    elapsedCurrentWeekServiceDates: readOnlyCurrentWeekServiceDates
  };
}
