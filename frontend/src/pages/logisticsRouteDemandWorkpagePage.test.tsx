import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import routeDemandRunWorkpageStateSnapshot from "@fixtures/workpage_route_demand_v0_run_state.json";
import scheduleRunWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_run_state.json";
import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { mutationLog } from "@/test/api/handlers";
import { server } from "@/test/api/server";

function setFrontendOperatorContext(): void {
  const currentContext = getApiRequestContextHeaders();
  setApiRequestContextHeaders({
    ...currentContext,
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  });
}

describe("LogisticsRouteDemandWorkpagePage", () => {
  it("shows the top chrome weekly actions in operator order on weekly schedule routes", async () => {
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(await screen.findByTestId("actor-switcher")).toBeInTheDocument();
    const navActions = await screen.findByTestId("app-shell-nav-actions");
    const driversButton = await within(navActions).findByRole("button", { name: "Drivers" });
    const scheduleButton = within(navActions).getByRole("button", {
      name: "Edit weekly schedule"
    });
    const editButton = await within(navActions).findByRole("button", {
      name: "Edit route demand"
    });
    const buttons = within(navActions).getAllByRole("button");
    const driversIndex = buttons.indexOf(driversButton);
    const scheduleIndex = buttons.indexOf(scheduleButton);
    const routeDemandIndex = buttons.indexOf(editButton);
    const menuIndex = buttons.findIndex(
      (button) => button.getAttribute("aria-label") === "Open utility menu"
    );

    expect(driversButton).toHaveClass("app-shell__quick-action");
    expect(scheduleButton).toHaveClass("app-shell__quick-action");
    expect(editButton).toHaveClass("app-shell__route-demand-edit");
    expect([driversIndex, scheduleIndex, routeDemandIndex, menuIndex]).toEqual([0, 1, 2, 3]);
  });

  it("edits route demand in a modal, saves through the existing endpoint, and refreshes the schedule page", async () => {
    const user = userEvent.setup();
    let scheduleFetchCount = 0;
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params }) => {
        scheduleFetchCount += 1;
        const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = String(params.workflowRunId);
        payload.freshness.generated_at = `2026-03-25T08:00:${String(scheduleFetchCount).padStart(
          2,
          "0"
        )}Z`;
        return HttpResponse.json(payload);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    await waitFor(() => {
      expect(scheduleFetchCount).toBeGreaterThan(0);
    });
    await user.click(await screen.findByRole("button", { name: "Edit route demand" }));

    const dialog = await screen.findByRole("dialog", { name: "Edit route demand" });
    expect(await within(dialog).findByTestId("route-demand-quick-edit-editor")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save route demand" })).toBeDisabled();
    const initialCount = Number(
      within(dialog).getByTestId("route-demand-count-2026-03-22").textContent ?? "0"
    );

    await user.click(
      within(dialog).getByRole("button", { name: "Increase planned routes for 2026-03-22" })
    );

    expect(within(dialog).getByTestId("route-demand-count-2026-03-22")).toHaveTextContent(
      String(initialCount + 1)
    );
    expect(within(dialog).getByRole("button", { name: "Save route demand" })).toBeEnabled();

    await user.click(within(dialog).getByRole("button", { name: "Save route demand" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Edit route demand" })).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(scheduleFetchCount).toBeGreaterThan(1);
    });
    expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
    expect(mutationLog()).toContain(
      "workpage-route-demand-artifact-submit:av-route-demand-artifact-001:av-route-demand-artifact-002"
    );
  }, 30000);

  it("keeps the top chrome route-demand edit action visible but unavailable when no latest artifact can be resolved", async () => {
    let routeDemandRequestCount = 0;
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0", ({ params }) => {
        routeDemandRequestCount += 1;
        const payload = structuredClone(routeDemandRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = String(params.workflowRunId);
        payload.artifact_state.latest_artifact_version_id = null;
        payload.actions = [];
        return HttpResponse.json(payload);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    await waitFor(() => {
      expect(routeDemandRequestCount).toBeGreaterThan(0);
    });
    const unavailableButton = screen.getByRole("button", {
      name: /Edit route demand unavailable:/i
    });
    expect(unavailableButton).toBeDisabled();
    expect(unavailableButton).toHaveTextContent("Edit route demand");
  }, 30000);

  it("renders the run-backed landing as read-only and opens the latest route-demand artifact", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/route-demand-v0");
    render(<App />);

    const page = await screen.findByTestId("route-demand-workpage-page");
    expect(within(page).getByRole("heading", { name: "Editable route demand available" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Schedule impact" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Daily route demand" })).toBeInTheDocument();
    expect(
      within(page).getByRole("link", { name: "Open route demand editor" })
    ).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001"
    );

    await user.click(within(page).getByRole("link", { name: "Open route demand editor" }));

    expect(await screen.findByTestId("route-demand-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001"
    );
  });

  it("increments daily route demand, saves a new immutable version, and surfaces refresh-follow-up state", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState(
      {},
      "",
      "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001"
    );
    render(<App />);

    const page = await screen.findByTestId("route-demand-artifact-workpage-page");
    expect(within(page).getByRole("button", { name: "Save route demand" })).toBeDisabled();
    const initialCount = Number(
      within(page).getByTestId("route-demand-count-2026-03-22").textContent ?? "0"
    );

    await user.click(
      within(page).getByRole("button", { name: "Increase planned routes for 2026-03-22" })
    );

    expect(within(page).getByTestId("route-demand-count-2026-03-22")).toHaveTextContent(
      String(initialCount + 1)
    );
    expect(within(page).getByRole("button", { name: "Save route demand" })).toBeEnabled();

    await user.click(within(page).getByRole("button", { name: "Save route demand" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-002"
      );
    });

    expect(await screen.findByTestId("route-demand-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.getByText("Refresh follow-up is open")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open latest schedule draft" })[0]).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
    expect(mutationLog()).toContain(
      "workpage-route-demand-artifact-submit:av-route-demand-artifact-001:av-route-demand-artifact-002"
    );
  });
});
