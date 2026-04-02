import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { RunDetailPage } from "@/pages/RunDetailPage";
import { renderRoute } from "@/test/renderRoute";

describe("RunDetailPage", () => {
  it("renders timeline and tabbed sections coherently", async () => {
    const user = userEvent.setup();
    renderRoute(<RunDetailPage />, {
      route: "/runs/wr-test-001",
      path: "/runs/:workflowRunId"
    });

    expect(await screen.findByRole("tab", { name: "timeline" })).toBeInTheDocument();
    expect(screen.getByText(/workflow.run.created/i)).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "tasks" }));
    expect(screen.getByText("Stage07 · Exception Triage")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "artifacts" }));
    expect(screen.getByText(/schedule.replan_delta.workbook/i)).toBeInTheDocument();
  });
});
