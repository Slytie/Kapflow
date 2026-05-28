import {
  buildHybridScheduleReality,
  currentServiceDateInTimeZone,
  elapsedCurrentWeekServiceDates,
  previousWeekRealityDateByCurrentWeekDate,
  resolveOperationalWeekStart,
  resolveScheduleComparisonContext,
  SCHEDULE_SERVICE_TIMEZONE
} from "@/lib/workpages/scheduleHybridReality";
import type { SchedulePreviousWeekRealityContract } from "@/lib/types/contracts";
import type { WorkpageScheduleHeatmapSection } from "@/lib/types/workpages";

function addDays(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function buildHeatmapSection(operationalWeekStart = "2026-03-22"): WorkpageScheduleHeatmapSection {
  const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const serviceDates = weekdayLabels.map((weekdayLabel, index) => {
    const serviceDate = addDays(operationalWeekStart, index);
    return {
      service_date: serviceDate,
      label: serviceDate,
      weekday_label: weekdayLabel
    };
  });
  return {
    kind: "schedule_heatmap",
    title: "Planned schedule heatmap",
    service_dates: serviceDates,
    people: [
      {
        driver_id: "driver-1",
        driver_name: "Driver 1",
        employment_type: "FT",
        on_call_eligible: true,
        previous_week_minutes: 1200,
        availability_summary: "Available",
        cells: serviceDates.map((serviceDate, index) => ({
          service_date: serviceDate.service_date,
          state: "assigned",
          row_kind: "assignment",
          route_slot_id: `route-${index + 1}`,
          projected_minutes: 480 + index * 10,
          assignment_status: "scheduled",
          planned_driver_day_state: "scheduled",
          manual_override: false
        }))
      }
    ]
  };
}

function buildPreviousWeekReality(
  previousWeekStart = "2026-03-15",
  operationalWeekStart = "2026-03-22"
): SchedulePreviousWeekRealityContract {
  const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const serviceDates = weekdayLabels.map((weekdayLabel, index) => {
    const serviceDate = addDays(previousWeekStart, index);
    return {
      service_date: serviceDate,
      label: serviceDate,
      weekday_label: weekdayLabel
    };
  });
  return {
    artifact_context: {} as never,
    source: {} as never,
    freshness: {} as never,
    previous_week_reality: {
      workflow_run_id: "wr-weekly-001",
      schedule_artifact_version_id: "av-schedule-artifact-001",
      actual_hours_artifact_version_id: "av-actual-hours-001",
      planning_week_id: "2026-W13",
      operational_week_start: operationalWeekStart,
      previous_week_start: previousWeekStart,
      previous_week_end: addDays(previousWeekStart, 6),
      service_dates: serviceDates,
      drivers: [
        {
          driver_id: "driver-1",
          driver_name: "Driver 1",
          employment_type: "FT",
          on_call_eligible: true,
          availability_summary: "Available",
          previous_week_minutes: 1200,
          cells: serviceDates.map((serviceDate, index) => ({
            service_date: serviceDate.service_date,
            state: "worked",
            normalized_state: "worked",
            blocked_reasons: [],
            actual_minutes: 60 * (index + 1),
            cumulative_week_minutes: ((index + 1) * (index + 2) * 60) / 2,
            route_id: `prev-route-${index + 1}`,
            route_slot_class: "AM",
            source_ref: `reality:${index + 1}`,
            call_in_sick_flag: false,
            cancellation_flag: false,
            non_working_day_flag: false
          }))
        }
      ],
      day_summaries: [],
      activity_rows: [],
      note: "Pinned previous-week reality snapshot."
    }
  };
}

describe("scheduleHybridReality helpers", () => {
  it("derives the current service date in the schedule service timezone", () => {
    expect(
      currentServiceDateInTimeZone(
        new Date("2026-03-25T19:00:00Z"),
        SCHEDULE_SERVICE_TIMEZONE
      )
    ).toBe("2026-03-25");
  });

  it("returns no elapsed dates on Sunday", () => {
    expect(
      elapsedCurrentWeekServiceDates({
        operationalWeekStart: "2026-03-22",
        currentServiceDate: "2026-03-22"
      })
    ).toEqual([]);
  });

  it("returns elapsed dates through Tuesday on Wednesday", () => {
    expect(
      elapsedCurrentWeekServiceDates({
        operationalWeekStart: "2026-03-22",
        currentServiceDate: "2026-03-25"
      })
    ).toEqual(["2026-03-22", "2026-03-23", "2026-03-24"]);
  });

  it("returns elapsed dates through Friday on Saturday", () => {
    expect(
      elapsedCurrentWeekServiceDates({
        operationalWeekStart: "2026-03-22",
        currentServiceDate: "2026-03-28"
      })
    ).toEqual([
      "2026-03-22",
      "2026-03-23",
      "2026-03-24",
      "2026-03-25",
      "2026-03-26",
      "2026-03-27"
    ]);
  });

  it("maps elapsed current-week dates to the previous week by weekday offset", () => {
    expect(
      previousWeekRealityDateByCurrentWeekDate({
        operationalWeekStart: "2026-03-22",
        currentWeekServiceDates: ["2026-03-22", "2026-03-23", "2026-03-24"]
      })
    ).toEqual({
      "2026-03-22": "2026-03-15",
      "2026-03-23": "2026-03-16",
      "2026-03-24": "2026-03-17"
    });
  });

  it("uses the selected-day fallback for historical demo weeks", () => {
    expect(
      resolveScheduleComparisonContext({
        summaryOperationalWeekStart: "2026-03-22",
        heatmapSection: buildHeatmapSection(),
        currentServiceDate: "2026-05-26",
        fallbackServiceDate: "2026-03-24"
      })
    ).toMatchObject({
      operationalWeekStart: "2026-03-22",
      displayedWeekRelation: "historical_demo_week",
      comparisonServiceDate: "2026-03-24",
      shouldShowPreviousWeekComparison: true
    });
  });

  it("keeps future weeks on planned schedule mode even when the selected day is inside the displayed week", () => {
    expect(
      resolveScheduleComparisonContext({
        summaryOperationalWeekStart: "2026-03-29",
        heatmapSection: buildHeatmapSection("2026-03-29"),
        currentServiceDate: "2026-03-25",
        fallbackServiceDate: "2026-03-31"
      })
    ).toMatchObject({
      operationalWeekStart: "2026-03-29",
      displayedWeekRelation: "future_week",
      comparisonServiceDate: null,
      shouldShowPreviousWeekComparison: true
    });
  });

  it("uses the visible heatmap week when the summary operational week is stale", () => {
    expect(
      resolveOperationalWeekStart({
        summaryOperationalWeekStart: "2026-03-02",
        heatmapSection: {
          kind: "schedule_heatmap",
          title: "Planned schedule heatmap",
          service_dates: [
            {
              service_date: "2026-03-22",
              label: "2026-03-22",
              weekday_label: "Sun"
            },
            {
              service_date: "2026-03-23",
              label: "2026-03-23",
              weekday_label: "Mon"
            },
            {
              service_date: "2026-03-24",
              label: "2026-03-24",
              weekday_label: "Tue"
            }
          ],
          people: []
        }
      })
    ).toBe("2026-03-22");
  });

  it("builds a chronological previous-week then current-week column order", () => {
    const hybrid = buildHybridScheduleReality({
      calculations: {
        selected_day: {
          service_date: "2026-03-24",
          available_driver_ids: []
        }
      } as never,
      heatmapSection: buildHeatmapSection(),
      operationalWeekStart: "2026-03-22",
      reality: buildPreviousWeekReality(),
      comparisonMode: "current_week",
      comparisonServiceDate: "2026-03-24"
    });

    expect(hybrid?.heatmapSection.service_dates.map((serviceDate) => serviceDate.service_date)).toEqual([
      "2026-03-15",
      "2026-03-16",
      "2026-03-17",
      "2026-03-18",
      "2026-03-19",
      "2026-03-20",
      "2026-03-21",
      "2026-03-22",
      "2026-03-23",
      "2026-03-24",
      "2026-03-25",
      "2026-03-26",
      "2026-03-27",
      "2026-03-28"
    ]);
    expect(hybrid?.heatmapSection.service_dates.map((serviceDate) => serviceDate.column_provenance)).toEqual([
      "previous_week_reality",
      "previous_week_reality",
      "previous_week_reality",
      "previous_week_reality",
      "previous_week_reality",
      "previous_week_reality",
      "previous_week_reality",
      "planned_current_week",
      "planned_current_week",
      "planned_current_week",
      "planned_current_week",
      "planned_current_week",
      "planned_current_week",
      "planned_current_week"
    ]);
  });

  it("marks only prior current-week days as read-only and keeps the selected day visible", () => {
    const hybrid = buildHybridScheduleReality({
      calculations: {
        selected_day: {
          service_date: "2026-03-24",
          available_driver_ids: []
        }
      } as never,
      heatmapSection: buildHeatmapSection(),
      operationalWeekStart: "2026-03-22",
      reality: buildPreviousWeekReality(),
      comparisonMode: "current_week",
      comparisonServiceDate: "2026-03-24"
    });

    const currentWeekColumns =
      hybrid?.heatmapSection.service_dates.filter(
        (serviceDate) => serviceDate.column_provenance === "planned_current_week"
      ) ?? [];

    expect(currentWeekColumns.map((serviceDate) => [serviceDate.service_date, serviceDate.read_only])).toEqual([
      ["2026-03-22", true],
      ["2026-03-23", true],
      ["2026-03-24", false],
      ["2026-03-25", false],
      ["2026-03-26", false],
      ["2026-03-27", false],
      ["2026-03-28", false]
    ]);
    expect(
      hybrid?.heatmapSection.people[0]?.cells
        .filter((cell) => ["2026-03-22", "2026-03-23", "2026-03-24"].includes(cell.service_date))
        .map((cell) => [
          cell.service_date,
          cell.cell_provenance,
          cell.reality_service_date,
          cell.previous_week_actual_minutes,
          cell.reality_summary_minutes
        ])
    ).toEqual([
      ["2026-03-22", "previous_week_reality", "2026-03-15", 60, 1680],
      ["2026-03-23", "previous_week_reality", "2026-03-16", 120, 1680],
      ["2026-03-24", "planned_current_week", undefined, undefined, undefined]
    ]);
    expect(hybrid?.heatmapSection.people[0]?.cells[0]?.previous_week_cumulative_week_minutes).toBe(60);
    expect(hybrid?.heatmapSection.people[0]?.cells[1]?.previous_week_cumulative_week_minutes).toBe(180);
    expect(hybrid?.selectedServiceDateOverride).toBe("2026-03-24");
  });

  it("keeps future scheduled-week cells planned while still showing the previous-week comparison block", () => {
    const futureOperationalWeekStart = "2026-03-29";
    const hybrid = buildHybridScheduleReality({
      calculations: {
        selected_day: {
          service_date: "2026-03-31",
          available_driver_ids: []
        }
      } as never,
      heatmapSection: buildHeatmapSection(futureOperationalWeekStart),
      operationalWeekStart: futureOperationalWeekStart,
      reality: buildPreviousWeekReality("2026-03-22", futureOperationalWeekStart),
      comparisonMode: "future_week",
      comparisonServiceDate: null
    });

    expect(hybrid?.elapsedCurrentWeekServiceDates).toEqual([]);
    expect(
      hybrid?.heatmapSection.service_dates.map((serviceDate) => [
        serviceDate.service_date,
        serviceDate.column_provenance,
        serviceDate.read_only
      ])
    ).toEqual([
      ["2026-03-22", "previous_week_reality", true],
      ["2026-03-23", "previous_week_reality", true],
      ["2026-03-24", "previous_week_reality", true],
      ["2026-03-25", "previous_week_reality", true],
      ["2026-03-26", "previous_week_reality", true],
      ["2026-03-27", "previous_week_reality", true],
      ["2026-03-28", "previous_week_reality", true],
      ["2026-03-29", "planned_current_week", false],
      ["2026-03-30", "planned_current_week", false],
      ["2026-03-31", "planned_current_week", false],
      ["2026-04-01", "planned_current_week", false],
      ["2026-04-02", "planned_current_week", false],
      ["2026-04-03", "planned_current_week", false],
      ["2026-04-04", "planned_current_week", false]
    ]);
    expect(
      hybrid?.heatmapSection.people[0]?.cells
        .filter((cell) => ["2026-03-29", "2026-03-30", "2026-03-31"].includes(cell.service_date))
        .map((cell) => [cell.service_date, cell.cell_provenance, cell.reality_service_date])
    ).toEqual([
      ["2026-03-29", "planned_current_week", undefined],
      ["2026-03-30", "planned_current_week", undefined],
      ["2026-03-31", "planned_current_week", undefined]
    ]);
  });
});
