import { screen } from "@testing-library/react";

import { ApprovalsPage } from "@/pages/ApprovalsPage";
import { renderRoute } from "@/test/renderRoute";

describe("ApprovalsPage", () => {
  it("shows queue and selected item workspace layout", async () => {
    renderRoute(<ApprovalsPage />, {
      route: "/approvals?run=wr-test-001",
      path: "/approvals"
    });

    expect(await screen.findByText("Approval Queue")).toBeInTheDocument();
    expect(screen.getByText("Review Workspace")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Approve" }).length).toBeGreaterThan(0);
  });
});
