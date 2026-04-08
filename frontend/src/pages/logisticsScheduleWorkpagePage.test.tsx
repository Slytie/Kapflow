import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import scheduleRunWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_run_state.json";
import { App } from "@/app/App";
import {
  SCHEDULE_CHECKS_SUMMARY,
  SCHEDULE_CHECK_ITEM_SUMMARIES,
  SCHEDULE_DEPENDENCY_ITEM_SUMMARIES,
  SCHEDULE_DEPENDENCY_STATUS_SUMMARY
} from "@/components/workpages/ScheduleWorkpageSurface";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { server } from "@/test/api/server";
import { mutationLog } from "@/test/api/handlers";

function setFrontendOperatorContext(): void {
  const currentContext = getApiRequestContextHeaders();
  setApiRequestContextHeaders({
    ...currentContext,
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  });
}

function overviewHeadingOrder(container: HTMLElement): string[] {
  const overview = container.querySelector(".schedule-workpage-surface__overview");
  expect(overview).not.toBeNull();
  return within(overview as HTMLElement)
    .getAllByRole("heading", { level: 2 })
    .map((heading) => heading.textContent ?? "");
}

function heatmapSection(container: HTMLElement): HTMLElement {
  const section = within(container).getByRole("heading", { name: "Planned schedule heatmap" }).closest("section");
  if (!section) {
    throw new Error("Heatmap section not found");
  }
  return section as HTMLElement;
}

function driverHeatmapRow(section: HTMLElement, driverName: string): HTMLElement {
  const row = within(section).getByText(driverName).closest("tr");
  if (!row) {
    throw new Error(`Heatmap row not found for ${driverName}`);
  }
  return row as HTMLElement;
}

describe("LogisticsScheduleWorkpagePage", () => {
  it(
    "renders the canonical run-backed surface as read-only and keeps metadata behind info",
    async () => {
      const user = userEvent.setup();
      let responseCount = 0;
      server.use(
        http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params }) => {
          responseCount += 1;
          const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
            string,
            any
          >;
          payload.freshness.generated_at =
            responseCount === 1 ? "2026-03-25T08:00:00Z" : "2026-03-25T08:00:30Z";
          payload.run_context.workflow_run_id = String(params.workflowRunId);
          return HttpResponse.json(payload);
        })
      );
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      const page = await screen.findByTestId("schedule-workpage-page");
      const titleActions = page.querySelector(".workpage-page__hero-title-actions");
      expect(titleActions).not.toBeNull();
      expect(within(page).getByRole("heading", { name: "Weekly schedule review" })).toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Capacity bar" })).toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Selected day" })).toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Dependency status" })).toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Checks" })).toBeInTheDocument();
      expect(overviewHeadingOrder(page)).toEqual(["Dependency status", "Checks", "Selected day"]);
      expect(within(page).getByRole("heading", { name: "Planned schedule heatmap" })).toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Driver metrics" })).not.toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Accepted history" })).toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();
      expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("spinbutton", { name: /Scenario added routes/i })).not.toBeInTheDocument();
      const dependencySection = within(page)
        .getByRole("heading", { name: "Dependency status" })
        .closest("section");
      expect(dependencySection).not.toBeNull();
      expect(within(dependencySection as HTMLElement).getByText("Route Slot Requirements")).toBeInTheDocument();
      const routeSlotRequirementsChip = within(dependencySection as HTMLElement).getByText(
        "Route Slot Requirements"
      );
      expect(routeSlotRequirementsChip.getAttribute("title")).toContain(
        SCHEDULE_DEPENDENCY_ITEM_SUMMARIES.route_slot_requirements
      );
      expect(
        within(dependencySection as HTMLElement).queryByText("planning.route_slot_requirements.workbook")
      ).not.toBeInTheDocument();
      const checksSection = within(page).getByRole("heading", { name: "Checks" }).closest("section");
      expect(checksSection).not.toBeNull();
      expect(
        within(checksSection as HTMLElement).getByText("Routes within scheduled capacity")
      ).toBeInTheDocument();
      const scheduledCapacityChip = within(checksSection as HTMLElement).getByText(
        "Routes within scheduled capacity"
      );
      expect(scheduledCapacityChip.getAttribute("title")).toContain(
        SCHEDULE_CHECK_ITEM_SUMMARIES.scheduled_capacity
      );
      expect(within(checksSection as HTMLElement).getAllByText("Blocking").length).toBeGreaterThan(0);
      expect(within(checksSection as HTMLElement).queryByText(/^pass$/i)).not.toBeInTheDocument();
      expect(within(checksSection as HTMLElement).queryByText(/^warn$/i)).not.toBeInTheDocument();
      expect(within(checksSection as HTMLElement).queryByText(/^fail$/i)).not.toBeInTheDocument();
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      expect(screen.queryByText(SCHEDULE_DEPENDENCY_STATUS_SUMMARY)).not.toBeInTheDocument();
      expect(screen.queryByText(SCHEDULE_CHECKS_SUMMARY)).not.toBeInTheDocument();
      const dependencySummaryButton = within(dependencySection as HTMLElement).getByRole("button", {
        name: "Show summary for Dependency status"
      });
      const checksSummaryButton = within(checksSection as HTMLElement).getByRole("button", {
        name: "Show summary for Checks"
      });
      await user.hover(dependencySummaryButton);
      expect(await screen.findByRole("tooltip")).toHaveTextContent(SCHEDULE_DEPENDENCY_STATUS_SUMMARY);
      await user.unhover(dependencySummaryButton);
      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
      act(() => {
        checksSummaryButton.focus();
      });
      expect(await screen.findByRole("tooltip")).toHaveTextContent(SCHEDULE_CHECKS_SUMMARY);
      act(() => {
        checksSummaryButton.blur();
      });
      await waitFor(() => {
        expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      });
      expect(within(titleActions as HTMLElement).getByRole("link", { name: "Open route demand" })).toBeInTheDocument();
      expect(within(titleActions as HTMLElement).getByRole("button", { name: "Create preferences snapshot" })).toBeInTheDocument();
      const heatmap = heatmapSection(page);
      expect(within(heatmap).getByRole("columnheader", { name: /Hours/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /Routes/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /On call/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /Compliance/i })).toBeInTheDocument();
      const abhirajRow = driverHeatmapRow(heatmap, "Abhiraj Singh");
      expect(within(abhirajRow).getByText("25.5 h")).toBeInTheDocument();
      expect(within(abhirajRow).getByText("Pref Unset")).toBeInTheDocument();
      expect(within(abhirajRow).getByText("Avail Available")).toBeInTheDocument();
      expect(within(abhirajRow).getByText("Fail")).toBeInTheDocument();
      expect(mutationLog()).toEqual([]);
    },
    90000
  );

  it("shows an error state and retries the canonical run-backed query", async () => {
    const user = userEvent.setup();
    let attempts = 0;
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", () => {
        attempts += 1;
        if (attempts <= 2) {
          return HttpResponse.json(
            {
              status: "error",
              error: {
                code: "workpage_unavailable",
                message: "schedule run unavailable"
              }
            },
            { status: 503 }
          );
        }
        return HttpResponse.json(scheduleRunWorkpageStateSnapshot.workpage_state);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(
      await screen.findByText("Schedule workpage failed to load", {}, { timeout: 4000 })
    ).toBeInTheDocument();
    expect(screen.getByText(/workpage_unavailable: schedule run unavailable/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
  });

  it(
    "renders the canonical run-backed schedule page as read-only while exposing the latest draft CTA",
    async () => {
      let responseCount = 0;
      server.use(
        http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params }) => {
          responseCount += 1;
          const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
            string,
            any
          >;
          payload.freshness.generated_at =
            responseCount === 1 ? "2026-03-25T08:10:00Z" : "2026-03-25T08:10:30Z";
          payload.run_context.workflow_run_id = String(params.workflowRunId);
          payload.run_context.activation_key = `snapshot:${String(params.workflowRunId)}:weekly`;
          payload.actions = [
            {
              action_id: "workpage.schedule-v0.open_latest_draft",
              artifact_version_id: "av-schedule-artifact-001",
              kind: "open_latest_draft",
              label: "Open schedule draft",
              route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001",
              state: "available",
              workpage_kind: "schedule-v0"
            },
            {
              action_id: "workpage.route-demand-v0.open_latest",
              artifact_version_id: "av-route-demand-artifact-001",
              kind: "open_latest",
              label: "Open route demand",
              route: "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001",
              state: "available",
              workpage_kind: "route-demand-v0"
            },
            {
              action_id: "workpage.driver-preferences-v0.create_snapshot",
              action_ref: {
                action_id: "workpage.driver-preferences-v0.create_snapshot",
                artifact_version_id: null,
                subject: null,
                workflow_run_id: "wr-weekly-001",
                workpage_kind: "driver-preferences-v0"
              },
              artifact_version_id: null,
              create_path: "/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0/snapshots",
              kind: "create_snapshot",
              label: "Create preferences snapshot",
              route: null,
              state: "available",
              workpage_kind: "driver-preferences-v0"
            }
          ];
          return HttpResponse.json(payload);
        })
      );
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      const page = await screen.findByTestId("schedule-workpage-page");
      const titleActions = page.querySelector(".workpage-page__hero-title-actions");
      expect(titleActions).not.toBeNull();
      expect(within(page).queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();
      expect(within(titleActions as HTMLElement).getByRole("link", { name: "Open editable draft" })).toHaveAttribute(
        "href",
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
      expect(within(titleActions as HTMLElement).getByRole("link", { name: "Open route demand" })).toHaveAttribute(
        "href",
        "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001"
      );
      expect(within(titleActions as HTMLElement).getByRole("button", { name: "Create preferences snapshot" })).toBeInTheDocument();
      expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Capacity bar" })).toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();

    },
    60000
  );

  it("shows the latest Stage04 draft handoff on the run-backed landing and navigates to the canonical artifact route", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Open editable draft" }));

    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
  });

  it("uses the schedule-side route-demand handoff without client-derived routing", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Open route demand" }));

    expect(await screen.findByTestId("route-demand-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001"
    );
  });

  it(
    "uses the schedule-side driver-preferences handoff and renders backend preference cues",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      const page = await screen.findByTestId("schedule-workpage-page");
      expect(within(page).getByText("Unset")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Create preferences snapshot" }));

      await waitFor(() => {
        expect(window.location.pathname).toBe(
          "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-001"
        );
      });
      expect(await screen.findByTestId("driver-preferences-artifact-workpage-page")).toBeInTheDocument();
    },
    25000
  );
});
