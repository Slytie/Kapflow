import {
  currentServiceDateInTimeZone,
  elapsedCurrentWeekServiceDates,
  previousWeekRealityDateByCurrentWeekDate,
  SCHEDULE_SERVICE_TIMEZONE
} from "@/lib/workpages/scheduleHybridReality";

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
});
