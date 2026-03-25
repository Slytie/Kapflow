import { workpagesRepository } from "@/lib/repositories";

describe("workpagesRepository", () => {
  it("returns isolated schedule and EOD view models", async () => {
    const schedule = await workpagesRepository.scheduleExample();
    const scheduleAgain = await workpagesRepository.scheduleExample();
    const eod = await workpagesRepository.eodExample();

    schedule.summary.planning_week_id = "mutated";

    expect(scheduleAgain.summary.planning_week_id).toBe("PW-2026-W13");
    expect(eod.summary.service_date).toBe("2026-03-16");
    expect(scheduleAgain.sections.length).toBeGreaterThan(0);
    expect(eod.sections.length).toBeGreaterThan(0);
  });
});
