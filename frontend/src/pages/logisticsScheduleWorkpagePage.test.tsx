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
import {
  expectHeatmapHeaderStatusGroups,
  expectHeatmapPreferenceBars,
  expectSelectedDateHeaderStats,
  scheduleHeatmapSectionIn as heatmapSection
} from "./logisticsScheduleTestHelpers";

function setFrontendOperatorContext(): void {
  const currentContext = getApiRequestContextHeaders();
  setApiRequestContextHeaders({
    ...currentContext,
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  });
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
    "renders the canonical run-backed surface without the redundant landing hero",
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
      expect(page.querySelector(".workpage-page__hero")).toBeNull();
      expect(within(page).queryByRole("heading", { name: "Weekly schedule review" })).not.toBeInTheDocument();
      expect(within(page).queryByText("Weekly Planning Review")).not.toBeInTheDocument();
      expect(
        within(page).queryByText(
          "This landing page stays read-only. Open the backend-selected latest draft when you need live preview and save controls."
        )
      ).not.toBeInTheDocument();
      expect(
        within(page).queryByText(
          "A workflow-backed weekly planning review for bounded draft navigation, live schedule context, and backend-authored metrics."
        )
      ).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open editable draft" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open route demand" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open driver preferences" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Capacity bar" })).not.toBeInTheDocument();
      const { dependencyGroup, checksGroup } = expectHeatmapHeaderStatusGroups(page);
      expect(within(page).getByRole("heading", { name: "Planned schedule heatmap" })).toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Driver metrics" })).not.toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Accepted history" })).toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();
      expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("spinbutton", { name: /Scenario added routes/i })).not.toBeInTheDocument();
      const routeSlotRequirementsChip = within(dependencyGroup).getByText("Route Slot Requirements");
      expect(routeSlotRequirementsChip.getAttribute("title")).toContain(
        SCHEDULE_DEPENDENCY_ITEM_SUMMARIES.route_slot_requirements
      );
      expect(
        within(dependencyGroup).queryByText("planning.route_slot_requirements.workbook")
      ).not.toBeInTheDocument();
      const scheduledCapacityChip = within(checksGroup).getByText("Routes within scheduled capacity");
      expect(scheduledCapacityChip.getAttribute("title")).toContain(
        SCHEDULE_CHECK_ITEM_SUMMARIES.scheduled_capacity
      );
      expect(within(checksGroup).getAllByText("Blocking").length).toBeGreaterThan(0);
      expect(within(checksGroup).queryByText(/^pass$/i)).not.toBeInTheDocument();
      expect(within(checksGroup).queryByText(/^warn$/i)).not.toBeInTheDocument();
      expect(within(checksGroup).queryByText(/^fail$/i)).not.toBeInTheDocument();
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      expect(screen.queryByText(SCHEDULE_DEPENDENCY_STATUS_SUMMARY)).not.toBeInTheDocument();
      expect(screen.queryByText(SCHEDULE_CHECKS_SUMMARY)).not.toBeInTheDocument();
      const dependencySummaryButton = within(dependencyGroup).getByRole("button", {
        name: "Show summary for Dependency status"
      });
      const checksSummaryButton = within(checksGroup).getByRole("button", {
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
      const heatmap = heatmapSection(page);
      expectSelectedDateHeaderStats(page);
      expectHeatmapPreferenceBars(page);
      expect(within(heatmap).getByRole("columnheader", { name: /Hours/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /Routes/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /On call/i })).toBeInTheDocument();
      expect(within(heatmap).getByRole("columnheader", { name: /Compliance/i })).toBeInTheDocument();
      const abhirajRow = driverHeatmapRow(heatmap, "Abhiraj Singh");
      expect(within(abhirajRow).getByText("25.5 h")).toBeInTheDocument();
      expect(within(abhirajRow).queryByText("Pref Unset")).not.toBeInTheDocument();
      expect(within(abhirajRow).queryByText("Avail Available")).not.toBeInTheDocument();
      const riskTrigger = within(abhirajRow).getByRole("button", {
        name: "Open compliance details for Abhiraj Singh"
      });
      expect(riskTrigger).toHaveClass("schedule-heatmap__risk-trigger");
      expect(riskTrigger).toHaveTextContent("Fail");
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
    "renders the canonical run-backed schedule page without landing hero CTAs",
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
      expect(page.querySelector(".workpage-page__hero")).toBeNull();
      expect(within(page).queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open editable draft" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("link", { name: "Open route demand" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("button", { name: "Create preferences snapshot" })).not.toBeInTheDocument();
      expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
      expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Capacity bar" })).not.toBeInTheDocument();
      expect(within(page).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();

    },
    60000
  );

  it("opens the latest Stage04 draft from the top chrome quick-edit action", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Editable draft available" })).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Edit weekly schedule" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "Edit weekly schedule" }));

    const dialog = await screen.findByRole("dialog", { name: "Edit weekly schedule" });
    expect(dialog).toHaveClass("schedule-quick-edit-modal");
    const editor = await within(dialog).findByTestId("schedule-quick-edit-editor");
    expect(within(editor).getByRole("heading", { name: "Weekly Schedule Draft" })).toBeInTheDocument();
    expect(within(editor).queryByText("Weekly Schedule Draft Artifact")).not.toBeInTheDocument();
    expect(within(editor).queryByRole("heading", { name: "Capacity bar" })).not.toBeInTheDocument();
    expect(within(editor).queryByRole("heading", { name: "Draft lineage" })).not.toBeInTheDocument();
    expectHeatmapHeaderStatusGroups(editor);
    expect(heatmapSection(editor)).toHaveClass("schedule-heatmap--compact");
    expectSelectedDateHeaderStats(editor);
    expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
  });

  it("opens route-demand editing from the top chrome without client-derived routing", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Edit route demand" })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: "Edit route demand" }));

    const dialog = await screen.findByRole("dialog", { name: "Edit route demand" });
    expect(await within(dialog).findByTestId("route-demand-quick-edit-editor")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
  });

  it(
    "opens driver preferences from the top chrome without inline preference pills",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      const page = await screen.findByTestId("schedule-workpage-page");
      expect(within(heatmapSection(page)).queryByText("Pref Unset")).not.toBeInTheDocument();
      expect(within(heatmapSection(page)).getByText("Abhiraj Singh")).toBeInTheDocument();
      expectHeatmapPreferenceBars(page);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: "Drivers" })).toBeEnabled();
      });
      await user.click(screen.getByRole("button", { name: "Drivers" }));

      const dialog = await screen.findByRole("dialog", { name: "Drivers" });
      await user.click(within(dialog).getByRole("button", { name: "Create preferences snapshot" }));

      expect(await within(dialog).findByTestId("driver-preferences-quick-edit-editor")).toBeInTheDocument();
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
    },
    25000
  );
});
