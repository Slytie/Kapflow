import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { mutationLog } from "@/test/api/handlers";

describe("LogisticsDemoPage", () => {
  it("opens a task drawer from the unified board without leaving the logistics demo route", async () => {
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

    const openTasksLane = within(page).getByLabelText("Open Tasks");
    await user.click(
      within(openTasksLane).getByRole("button", { name: /Stage03 planning_feedback_review/i })
    );

    expect(window.location.pathname).toBe("/demo/logistics");
    expect(await screen.findByLabelText("Task context")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Claim" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open run details" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001"
    );
  });

  it("runs task actions from the drawer and refreshes story lanes after success", async () => {
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
    const openTasksLane = within(page).getByLabelText("Open Tasks");
    await user.click(
      within(openTasksLane).getByRole("button", { name: /Stage03 planning_feedback_review/i })
    );

    await user.click(await screen.findByRole("button", { name: "Claim" }));

    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-weekly-001");
    });
    await waitFor(() => {
      expect(within(within(page).getByLabelText("Open Tasks")).queryByText(/Stage03 planning_feedback_review/i)).not.toBeInTheDocument();
      expect(within(within(page).getByLabelText("Claimed Tasks")).getByText(/Stage03 planning_feedback_review/i)).toBeInTheDocument();
    });
    expect(await screen.findByRole("button", { name: "Complete" })).toBeInTheDocument();
  });

  it("shows artifact download affordance in the drawer for linked task artifacts", async () => {
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
    const claimedLane = within(page).getByLabelText("Claimed Tasks");
    await user.click(
      within(claimedLane).getByRole("button", { name: /Stage01 dispatch_seed_intake/i })
    );

    expect(await screen.findByRole("heading", { name: /Task Artifacts/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
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
