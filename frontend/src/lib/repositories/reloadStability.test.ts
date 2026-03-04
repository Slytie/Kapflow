import { boardRepository } from "@/lib/repositories";

describe("Reload stability", () => {
  it("returns stable board structure on repeated reloads", async () => {
    const first = await boardRepository.view({ workflowRunId: "wr-test-001" });
    const second = await boardRepository.view({ workflowRunId: "wr-test-001" });

    expect(JSON.stringify(first)).toEqual(JSON.stringify(second));
  });
});
