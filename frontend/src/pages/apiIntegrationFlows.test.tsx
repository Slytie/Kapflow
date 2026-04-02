import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@testing-library/react";

import { App } from "@/app/App";
import { forceForbiddenResponses, mutationLog } from "@/test/api/handlers";
import { ApprovalsPage } from "@/pages/ApprovalsPage";
import { BoardPage } from "@/pages/BoardPage";
import { renderRoute } from "@/test/renderRoute";

describe("Frontend API integration flows", () => {
  it("claiming a task from drawer hits mutation path and updates filtered queue", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/my-work?run=wr-test-001&state=OPEN");
    render(<App />);

    expect(await screen.findByText("Stage06 · Information Request")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Details" }));
    await user.click(await screen.findByRole("button", { name: "Claim" }));

    expect(await screen.findByText(/No actionable tasks for current user/i)).toBeInTheDocument();
    expect(mutationLog()).toContain("claim:ht-open-001");
  });

  it("completing a claimed task from drawer hits mutation path and updates filtered queue", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/my-work?run=wr-test-001&state=CLAIMED");
    render(<App />);

    expect(await screen.findByText("Stage06 · Review Packet")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Details" }));
    await user.click(await screen.findByRole("button", { name: "Complete Task" }));

    expect(await screen.findByText(/No actionable tasks for current user/i)).toBeInTheDocument();
    expect(mutationLog()).toContain("complete:ht-claimed-002");
  });

  it("responding to an approval hits mutation path and updates pending queue", async () => {
    const user = userEvent.setup();
    renderRoute(<ApprovalsPage />, {
      route: "/approvals?run=wr-test-001&state=PENDING",
      path: "/approvals"
    });

    expect(await screen.findByText("Approval Queue")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Approve" })[0]);

    expect(await screen.findByText(/No approvals in scope/i)).toBeInTheDocument();
    expect(mutationLog()).toContain("respond:ap-pending-001:approve");
  });

  it("forbidden/cross-scope API responses are surfaced to users", async () => {
    forceForbiddenResponses(true);
    renderRoute(<BoardPage />, {
      route: "/board?run=wr-test-001",
      path: "/board"
    });

    expect(await screen.findByText(/Board failed to load/i)).toBeInTheDocument();
    expect(screen.getByText(/workflow_run_not_found/i)).toBeInTheDocument();
  });

  it("repeated refetches preserve board structure", async () => {
    const view = renderRoute(<BoardPage />, {
      route: "/board?run=wr-test-001",
      path: "/board"
    });

    expect(await screen.findByLabelText("Unclaimed")).toBeInTheDocument();
    const firstCount = screen.getAllByRole("button", { name: "Details" }).length;

    view.rerender(<BoardPage />);

    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Details" }).length).toBe(firstCount);
    });
  });
});
