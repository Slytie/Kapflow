import {
  buildEndOfDayWorkpageViewModel,
  buildScheduleWorkpageViewModel
} from "@/lib/workpages/exampleViewModels";

describe("workpage view-model builders", () => {
  it("builds the schedule example as a weekly-planning review surface", () => {
    const model = buildScheduleWorkpageViewModel();

    expect(model.workflow_id).toBe("weekly_schedule_planning.v1");
    expect(model.dataset_key).toBe("planning.input_bundle.doc");
    expect(model.summary.planning_week_id).toBe("PW-2026-W13");
    expect(model.sections.some((section) => section.kind === "note_panel")).toBe(true);
    expect(
      model.validation.warnings.some((warning) => warning.includes("live dispatch truth"))
    ).toBe(true);
  });

  it("builds the end-of-day example from one consistent 2026-03-16 source family", () => {
    const model = buildEndOfDayWorkpageViewModel();

    expect(model.workflow_id).toBe("dispatch_reporting.v1");
    expect(model.dataset_key).toBe("reporting.upd_draft.workbook");
    expect(
      Object.values(model.source_examples).every((path) => path.includes("2026_03_16") || path.includes("2026-03-16"))
    ).toBe(true);
    expect(model.summary.service_date).toBe("2026-03-16");
    expect(model.sections.some((section) => section.kind === "checklist")).toBe(true);
  });
});
