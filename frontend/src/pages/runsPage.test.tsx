import { screen } from "@testing-library/react";

import { RunsPage } from "@/pages/RunsPage";
import { renderRoute } from "@/test/renderRoute";

describe("RunsPage", () => {
  it("links each run to workspace and run detail routes", async () => {
    renderRoute(<RunsPage />, {
      route: "/runs",
      path: "/runs"
    });

    expect(await screen.findByText("Workflow Runs")).toBeInTheDocument();
    const workspaceLink = screen.getByRole("link", { name: "Open workspace" });
    const detailLink = screen.getByRole("link", { name: "View run detail" });

    expect(workspaceLink).toHaveAttribute("href", "/runs/wr-test-001/workspace");
    expect(detailLink).toHaveAttribute("href", "/runs/wr-test-001");
  });
});
