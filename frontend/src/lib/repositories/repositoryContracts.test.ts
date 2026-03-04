import {
  approvalsRepository,
  boardRepository,
  flagsRepository,
  humanTasksRepository,
  pointersRepository,
  timelineRepository,
  workflowRunsRepository
} from "@/lib/repositories";

describe("Repository contract compatibility", () => {
  it("loads API contract shapes through repository adapters", async () => {
    const [tasks, approvals, flags, runs, pointers, timeline, board] = await Promise.all([
      humanTasksRepository.list({ workflowRunId: "wr-test-001" }),
      approvalsRepository.list({ workflowRunId: "wr-test-001" }),
      flagsRepository.list({ workflowRunId: "wr-test-001" }),
      workflowRunsRepository.list(),
      pointersRepository.list({ workflowRunId: "wr-test-001" }),
      timelineRepository.list({ workflowRunId: "wr-test-001" }),
      boardRepository.view({ workflowRunId: "wr-test-001" })
    ]);

    expect(Array.isArray(tasks)).toBe(true);
    expect(Array.isArray(approvals)).toBe(true);
    expect(Array.isArray(flags)).toBe(true);
    expect(Array.isArray(runs)).toBe(true);
    expect(Array.isArray(pointers)).toBe(true);
    expect(Array.isArray(timeline)).toBe(true);
    expect(board.lanes.length).toBe(5);
    expect(runs[0]?.workflow_run_id).toBe("wr-test-001");
  });
});
