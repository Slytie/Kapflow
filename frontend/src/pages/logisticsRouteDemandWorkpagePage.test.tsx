import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import routeDemandRunWorkpageStateSnapshot from "@fixtures/workpage_route_demand_v0_run_state.json";
import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
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
  const visibleWeekDate = "2026-03-28";
  const futureVisibleWeekDate = "2026-03-29";

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
    const editor = await within(dialog).findByTestId("route-demand-quick-edit-editor");
    expect(within(editor).getByRole("heading", { name: "Daily route demand" })).toBeInTheDocument();
    expect(within(editor).queryByText("Route Demand Artifact")).not.toBeInTheDocument();
    expect(
      within(editor).queryByText(/Plus\/minus controls adjust backend-owned daily route counts/i)
    ).not.toBeInTheDocument();
    expect(
      within(editor).queryByText(/bounded route-demand editor over immutable weekly route-demand workbooks/i)
    ).not.toBeInTheDocument();
    expect(within(editor).getByTestId("route-demand-horizon-summary")).toHaveTextContent(
      "7 service days"
    );
    expect(within(editor).getByTestId("route-demand-horizon-summary")).toHaveTextContent(
      "2026-03-22 to 2026-03-28"
    );
    expect(within(editor).queryByRole("heading", { name: "Week 1" })).not.toBeInTheDocument();
    expect(within(editor).queryByRole("heading", { name: "Week 2" })).not.toBeInTheDocument();
    expect(within(editor).queryByText(/^Artifact /i)).not.toBeInTheDocument();
    expect(within(editor).queryByText(/^\d+ planned routes$/i)).not.toBeInTheDocument();
    expect(within(editor).queryByTestId("route-demand-schedule-impact")).not.toBeInTheDocument();
    expect(within(editor).queryByTestId("workpage-summary-section")).not.toBeInTheDocument();
    expect(within(editor).queryByTestId("route-demand-history-rail")).not.toBeInTheDocument();
    expect(within(editor).queryByText("Raw route-demand table")).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save route demand" })).toBeDisabled();
    expect(within(dialog).getByTestId(`route-demand-count-${visibleWeekDate}`)).toHaveTextContent(
      "17"
    );
    const initialCount = Number(
      within(dialog).getByTestId(`route-demand-count-${visibleWeekDate}`).textContent ?? "0"
    );

    await user.click(
      within(dialog).getByRole("button", {
        name: `Increase planned routes for ${visibleWeekDate}`
      })
    );

    expect(within(dialog).getByTestId(`route-demand-count-${visibleWeekDate}`)).toHaveTextContent(
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
    expect(within(page).getByRole("button", { name: "Add a week" })).toBeInTheDocument();
    expect(within(page).getByTestId(`route-demand-count-${visibleWeekDate}`)).toHaveTextContent(
      "17"
    );
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
    expect(within(page).getByRole("button", { name: "Add a week" })).toBeInTheDocument();
    expect(within(page).getByTestId(`route-demand-count-${visibleWeekDate}`)).toHaveTextContent(
      "17"
    );
    const initialCount = Number(
      within(page).getByTestId(`route-demand-count-${visibleWeekDate}`).textContent ?? "0"
    );

    await user.click(
      within(page).getByRole("button", {
        name: `Increase planned routes for ${visibleWeekDate}`
      })
    );

    expect(within(page).getByTestId(`route-demand-count-${visibleWeekDate}`)).toHaveTextContent(
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
    expect(screen.getByTestId(`route-demand-count-${visibleWeekDate}`)).toHaveTextContent(
      String(initialCount + 1)
    );
    expect(screen.getByText("Latest schedule draft is stale")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open latest schedule draft" })[0]).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
    expect(mutationLog()).toContain(
      "workpage-route-demand-artifact-submit:av-route-demand-artifact-001:av-route-demand-artifact-002"
    );
  });

  it("adds the next week, posts save-and-run to /save-and-run, and opens the weekly schedule quick edit", async () => {
    const user = userEvent.setup();
    const requestedSaveAndRunPaths: string[] = [];
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/wr-weekly-002/schedule-v0", () => {
        const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state) as Record<
          string,
          any
        >;
        payload.run_context.workflow_run_id = "wr-weekly-002";
        payload.actions = payload.actions.filter(
          (action: Record<string, unknown>) => action.kind !== "open_latest_draft"
        );
        payload.artifact_state.latest_artifact_version_id = null;
        return HttpResponse.json(payload);
      }),
      http.get(
        "*/api/v1/workpages/workflow-runs/wr-weekly-002/schedule-v0/artifacts/av-schedule-artifact-target",
        () => {
          const payload = structuredClone(scheduleArtifactStateSnapshot.workpage_state) as Record<
            string,
            any
          >;
          payload.artifact_context.workflow_run_id = "wr-weekly-002";
          payload.artifact_context.artifact_version_id = "av-schedule-artifact-target";
          payload.artifact_context.latest_in_chain_artifact_version_id =
            "av-schedule-artifact-target";
          payload.freshness.source_version = "av-schedule-artifact-target";
          payload.workpage.source_artifact_version_id = "av-schedule-artifact-target";
          payload.source.source_artifact_version_id = "av-schedule-artifact-target";
          return HttpResponse.json(payload);
        }
      ),
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/artifacts/:artifactVersionId/save-and-run",
        async ({ request, params }) => {
          requestedSaveAndRunPaths.push(new URL(request.url).pathname);
          await new Promise((resolve) => setTimeout(resolve, 50));
          return HttpResponse.json({
            status: "ok",
            command: "api.workpages.route_demand.save_and_run",
            submitted: {
              artifact_version_id: "av-route-demand-artifact-003",
              supersedes_artifact_version_id: String(params.artifactVersionId),
              workflow_run_id: String(params.workflowRunId),
              route:
                "/runs/wr-weekly-002/workpages/route-demand-v0/artifacts/av-route-demand-artifact-003",
              target_workflow_run_id: "wr-weekly-002",
              target_schedule_route: "/runs/wr-weekly-002/workpages/schedule-v0",
              target_schedule_artifact_version_id: "av-schedule-artifact-target"
            }
          });
        }
      )
    );

    setFrontendOperatorContext();
    window.history.pushState(
      {},
      "",
      "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001"
    );
    render(<App />);

    const currentPage = await screen.findByTestId("route-demand-artifact-workpage-page");
    await user.click(within(currentPage).getByRole("button", { name: "Add a week" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-002/workpages/route-demand-v0/artifacts/av-route-demand-artifact-002"
      );
    });

    const futurePage = await screen.findByTestId("route-demand-artifact-workpage-page");
    expect(within(futurePage).getByTestId(`route-demand-count-${futureVisibleWeekDate}`)).toHaveTextContent(
      "0"
    );

    await user.click(
      within(futurePage).getByRole("button", {
        name: `Increase planned routes for ${futureVisibleWeekDate}`
      })
    );

    await user.click(
      within(futurePage).getByRole("button", { name: "Save and run scheduling agent" })
    );

    await waitFor(() => {
      expect(screen.getAllByText("Agent working").length).toBeGreaterThan(0);
    });

    await waitFor(() => {
      expect(window.location.pathname).toBe("/runs/wr-weekly-002/workpages/schedule-v0");
    });

    expect(
      await screen.findByRole("dialog", { name: "Edit Weekly Schedule" })
    ).toBeInTheDocument();
    expect(requestedSaveAndRunPaths).toEqual([
      "/api/v1/workpages/workflow-runs/wr-weekly-002/route-demand-v0/artifacts/av-route-demand-artifact-002/save-and-run"
    ]);
    expect(
      mutationLog().some((entry) => entry.startsWith("workpage-route-demand-artifact-submit:"))
    ).toBe(false);
  }, 30000);

  it("closes the route-demand popup and automatically opens the future weekly schedule popup after canonical save-and-run success", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Edit route demand" }));

    const routeDemandDialog = await screen.findByRole("dialog", { name: "Edit route demand" });
    await user.click(within(routeDemandDialog).getByRole("button", { name: "Add a week" }));

    const futureEditor = await screen.findByTestId("route-demand-quick-edit-editor");
    await user.click(
      within(futureEditor).getByRole("button", {
        name: `Increase planned routes for ${futureVisibleWeekDate}`
      })
    );
    await user.click(
      within(futureEditor).getByRole("button", { name: "Save and run scheduling agent" })
    );

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Edit route demand" })).not.toBeInTheDocument();
    });
    expect(
      await screen.findByRole("dialog", { name: "Edit Weekly Schedule" })
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/runs/wr-weekly-002/workpages/schedule-v0");
  }, 30000);

  it("shows an inline error when save-and-run fails and stays on the future route-demand artifact", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/artifacts/:artifactVersionId/save-and-run",
        () =>
          HttpResponse.json(
            {
              status: "error",
              error: {
                code: "stage04_claimed_by_other",
                message: "Stage04 is currently claimed by another actor."
              }
            },
            { status: 409 }
          )
      )
    );

    setFrontendOperatorContext();
    window.history.pushState(
      {},
      "",
      "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-001"
    );
    render(<App />);

    const currentPage = await screen.findByTestId("route-demand-artifact-workpage-page");
    await user.click(within(currentPage).getByRole("button", { name: "Add a week" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-002/workpages/route-demand-v0/artifacts/av-route-demand-artifact-002"
      );
    });

    const futurePage = await screen.findByTestId("route-demand-artifact-workpage-page");
    await user.click(
      within(futurePage).getByRole("button", {
        name: `Increase planned routes for ${futureVisibleWeekDate}`
      })
    );
    await user.click(
      within(futurePage).getByRole("button", { name: "Save and run scheduling agent" })
    );

    const errorPanel = await screen.findByTestId("route-demand-mutation-error");
    expect(errorPanel).toHaveTextContent("Action failed");
    expect(errorPanel).toHaveTextContent("Stage04 is currently claimed by another actor.");
    expect(window.location.pathname).toBe(
      "/runs/wr-weekly-002/workpages/route-demand-v0/artifacts/av-route-demand-artifact-002"
    );
    expect(screen.getByTestId("route-demand-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Edit Weekly Schedule" })).not.toBeInTheDocument();
  }, 30000);
});
