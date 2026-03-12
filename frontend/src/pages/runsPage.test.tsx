import { screen } from "@testing-library/react";

import { RunsPage } from "@/pages/RunsPage";
import { renderRoute } from "@/test/renderRoute";

describe("RunsPage", () => {
  it("links each run to workspace and run detail routes", async () => {
    renderRoute(<RunsPage />, {
      route: "/runs",
      path: "/runs"
    });

    expect(await screen.findByText("Workflow Runs (Legacy Detail Views)")).toBeInTheDocument();
    const workspaceLinks = screen.getAllByRole("link", { name: "Open workspace" });
    const detailLinks = screen.getAllByRole("link", { name: "View run detail" });

    expect(workspaceLinks[0]).toHaveAttribute("href", "/runs/wr-test-001/workspace");
    expect(detailLinks[0]).toHaveAttribute("href", "/runs/wr-test-001");
    expect(workspaceLinks.length).toBeGreaterThan(1);
    expect(detailLinks.length).toBeGreaterThan(1);
  });
});
