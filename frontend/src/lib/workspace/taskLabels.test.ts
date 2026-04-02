import { taskDisplayHeading, taskDisplayLabel } from "@/lib/workspace/taskLabels";

describe("taskLabels", () => {
  it("maps the demo logistics task names to the new visible labels", () => {
    expect(
      taskDisplayLabel({
        stage_id: "Stage01",
        task_kind: "eos_input_intake"
      })
    ).toBe("End of Day Dispatch Report");
    expect(
      taskDisplayLabel({
        stage_id: "Stage04",
        task_kind: "weekly_input_intake"
      })
    ).toBe("Weekly Scheduling Plan Inputs");
    expect(
      taskDisplayLabel({
        stage_id: "Stage04",
        task_kind: "work_item"
      })
    ).toBe("Weekly Scheduling Agent");
  });

  it("builds headings from the relabeled task names", () => {
    expect(
      taskDisplayHeading({
        stage_id: "Stage04",
        task_kind: "work_item"
      })
    ).toBe("Stage04 · Weekly Scheduling Agent");
  });
});
