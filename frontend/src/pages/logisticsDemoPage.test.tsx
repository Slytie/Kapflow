import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";

describe("LogisticsDemoPage", () => {
  it("renders family graph, unified board, linked runs, outputs, and handoff activity", async () => {
    const user = userEvent.setup();
    const currentContext = getApiRequestContextHeaders();
    setApiRequestContextHeaders({
      ...currentContext,
      actorId: "human:frontend-operator",
      actorType: "human",
      actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
    });
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    expect(within(page).getByTestId("workflow-graph")).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Unified Action Board" })).toBeInTheDocument();
    expect(within(page).getByLabelText("Open Exceptions")).toBeInTheDocument();
    expect(within(page).getByLabelText("Open Tasks")).toBeInTheDocument();
    const weeklyRunLinks = within(page).getAllByRole("link", { name: "wr-weekly-001" });
    expect(weeklyRunLinks.some((link) => link.getAttribute("href") === "/runs/wr-weekly-001")).toBe(
      true
    );
    expect(within(page).getByRole("heading", { name: "Official Outputs Summary" })).toBeInTheDocument();
    expect(within(page).getByText("weekly_seed_to_live_dispatch")).toBeInTheDocument();

    await user.click(within(page).getAllByRole("button", { name: "Open task pane" })[0]);
    expect(await screen.findByLabelText("Task context")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Claim|Complete/ })).toBeInTheDocument();
  });

  it("uses logistics story as the primary app route and removes legacy schedule labels from navigation", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);

    expect(await screen.findByTestId("logistics-demo-page")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Logistics Demo" })).toHaveAttribute(
      "href",
      "/demo/logistics"
    );
    expect(screen.queryByRole("link", { name: "Schedule Board (Legacy)" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Runs (Legacy Views)" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Timeline (Legacy View)" })).not.toBeInTheDocument();
  });
});
