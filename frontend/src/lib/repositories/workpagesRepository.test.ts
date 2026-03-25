import { workpagesRepository } from "@/lib/repositories";

describe("workpagesRepository", () => {
  it("returns isolated HTTP-backed schedule and EOD workpage contracts", async () => {
    const schedule = await workpagesRepository.schedule();
    const scheduleAgain = await workpagesRepository.schedule();
    const eod = await workpagesRepository.eod();

    schedule.workpage.summary.planning_week_id = "mutated";

    expect(scheduleAgain.workpage.summary.planning_week_id).toBe("PW-2026-W13");
    expect(scheduleAgain.source.mode).toBe("demo");
    expect(scheduleAgain.freshness.source_version).toBe("weekly_stage04_actual_ops_lab_v2");
    expect(eod.workpage.summary.service_date).toBe("2026-03-16");
    expect(eod.source.primary_dataset_key).toBe("reporting.upd_draft.workbook");
    expect(scheduleAgain.workpage.sections.length).toBeGreaterThan(0);
    expect(eod.workpage.sections.length).toBeGreaterThan(0);
  });
});
