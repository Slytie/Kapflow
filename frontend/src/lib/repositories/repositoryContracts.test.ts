import {
  approvalsRepository,
  boardRepository,
  flagsRepository,
  humanTasksRepository,
  logisticsStoryRepository,
  pointersRepository,
  templatesRepository,
  timelineRepository,
  workflowRunsRepository
} from "@/lib/repositories";

describe("Repository contract compatibility", () => {
  it("loads API contract shapes through repository adapters", async () => {
    const [tasks, approvals, flags, runs, pointers, timeline, board, workspace, templates, logisticsStory] = await Promise.all([
      humanTasksRepository.list({ workflowRunId: "wr-test-001" }),
      approvalsRepository.list({ workflowRunId: "wr-test-001" }),
      flagsRepository.list({ workflowRunId: "wr-test-001" }),
      workflowRunsRepository.list(),
      pointersRepository.list({ workflowRunId: "wr-test-001" }),
      timelineRepository.list({ workflowRunId: "wr-test-001" }),
      boardRepository.view({ workflowRunId: "wr-test-001" }),
      workflowRunsRepository.workspace("wr-test-001"),
      templatesRepository.list({ workflowId: "schedule_planning.v1", variant: "empty" }),
      logisticsStoryRepository.view({ planningWeekId: "PW-2026-W10" })
    ]);

    expect(Array.isArray(tasks)).toBe(true);
    expect(Array.isArray(approvals)).toBe(true);
    expect(Array.isArray(flags)).toBe(true);
    expect(Array.isArray(runs)).toBe(true);
    expect(Array.isArray(pointers)).toBe(true);
    expect(Array.isArray(timeline)).toBe(true);
    expect(Array.isArray(templates)).toBe(true);
    expect(board.lanes.length).toBe(5);
    expect(runs[0]?.workflow_run_id).toBe("wr-test-001");
    expect(workspace.graph.nodes.length).toBeGreaterThan(0);
    expect(logisticsStory.family_graph.modules.length).toBe(3);
    expect(logisticsStory.family_graph.modules.every((module) => module.node_kind === "module")).toBe(
      true
    );
    expect(
      logisticsStory.family_graph.modules.every((module) =>
        ["none", "workflow_run", "run_group"].includes(module.drilldown_kind)
      )
    ).toBe(true);
    expect(
      logisticsStory.family_graph.modules.every((module) =>
        module.drilldown_refs.every((ref) => ref.workflow_run_id.length > 0)
      )
    ).toBe(true);
    expect(logisticsStory.board.work_items.length).toBeGreaterThan(0);
  });
});
