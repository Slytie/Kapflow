import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import scheduleRunWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_run_state.json";
import scheduleWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_state.json";
import { App } from "@/app/App";
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

describe("LogisticsScheduleWorkpagePage", () => {
  it("renders the redesigned demo surface as read-only and keeps metadata behind info", async () => {
    const user = userEvent.setup();
    let responseCount = 0;
    server.use(
      http.get("*/api/v1/workpages/demo/schedule-v0", () => {
        responseCount += 1;
        const payload = structuredClone(scheduleWorkpageStateSnapshot.workpage_state);
        payload.freshness.generated_at =
          responseCount === 1 ? "2026-03-25T08:00:00Z" : "2026-03-25T08:00:30Z";
        return HttpResponse.json(payload);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics/workpages/schedule-v0");
    render(<App />);

    const page = await screen.findByTestId("schedule-workpage-page");
    expect(within(page).getByRole("heading", { name: "Weekly schedule review" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Capacity bar" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Selected day" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Dependency status" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Checks" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Driver metrics" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Accepted history" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();
    expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("spinbutton", { name: /Scenario added routes/i })).not.toBeInTheDocument();

    expect(
      within(page).queryByText("Backend demo query served from repo-native workflow example bundles.")
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open secondary detail routes" }));
    const shellInfoDialog = await screen.findByRole("dialog", { name: "Secondary detail routes" });
    expect(within(shellInfoDialog).getByRole("link", { name: "Run Details" })).toHaveAttribute(
      "href",
      "/runs"
    );
    await user.click(screen.getByRole("button", { name: /Close Secondary detail routes/i }));

    await user.click(screen.getByRole("button", { name: /Open info for Weekly schedule review/i }));
    const infoDialog = await screen.findByRole("dialog", { name: "Weekly planning context" });
    expect(
      within(infoDialog).getAllByText(
        "Backend demo query served from repo-native workflow example bundles."
      )[0]
    ).toBeInTheDocument();
    expect(within(infoDialog).getByText("weekly_stage04_actual_ops_lab_v3")).toBeInTheDocument();
    await user.click(
      within(infoDialog).getByRole("button", { name: "Refresh" })
    );
    await user.click(screen.getByRole("button", { name: /Close Weekly planning context/i }));

    expect(mutationLog()).toEqual([]);
  });

  it("shows an error state and retries the backend demo query", async () => {
    const user = userEvent.setup();
    let attempts = 0;
    server.use(
      http.get("*/api/v1/workpages/demo/schedule-v0", () => {
        attempts += 1;
        if (attempts <= 2) {
          return HttpResponse.json(
            {
              status: "error",
              error: {
                code: "workpage_unavailable",
                message: "schedule demo unavailable"
              }
            },
            { status: 503 }
          );
        }
        return HttpResponse.json(scheduleWorkpageStateSnapshot.workpage_state);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics/workpages/schedule-v0");
    render(<App />);

    expect(
      await screen.findByText("Schedule workpage failed to load", {}, { timeout: 4000 })
    ).toBeInTheDocument();
    expect(screen.getByText(/workpage_unavailable: schedule demo unavailable/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
  });

  it("renders the canonical run-backed schedule page as read-only while exposing the latest draft CTA", async () => {
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
          }
        ];
        return HttpResponse.json(payload);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    const page = await screen.findByTestId("schedule-workpage-page");
    expect(within(page).getByRole("heading", { name: "Editable draft available" })).toBeInTheDocument();
    expect(within(page).getByRole("link", { name: "Open editable draft" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
    expect(screen.queryByText("Scenario sick calls")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: /Planner note/i })).not.toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Capacity bar" })).toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Open info for Weekly schedule review/i }));
    const infoDialog = await screen.findByRole("dialog", { name: "Weekly planning context" });
    expect(within(infoDialog).getByText("run_projection")).toBeInTheDocument();
    expect(
      within(infoDialog).getAllByText(
        /Workflow-run-backed schedule projection served from canonical weekly Stage04 source artifacts/i
      )[0]
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Close Weekly planning context/i }));
  });

  it("shows the latest Stage04 draft handoff on the run-backed landing and navigates to the canonical artifact route", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Editable draft available" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Open editable draft" }));

    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
  });
});
