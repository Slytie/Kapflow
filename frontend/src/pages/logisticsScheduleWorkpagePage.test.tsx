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
  it("renders inside the logistics shell, shows backend metadata, and keeps what-if edits local across refresh", async () => {
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
    expect(
      within(page).getByText(
        "Backend demo query served from repo-native workflow example bundles."
      )
    ).toBeInTheDocument();
    expect(within(page).getByText("weekly_stage04_actual_ops_lab_v3")).toBeInTheDocument();
    expect(within(page).getByText("Composite source bundle")).toBeInTheDocument();
    expect(screen.getByLabelText("Secondary detail routes")).toBeInTheDocument();
    expect(screen.queryByText(/Server-authoritative view backed by HITL HTTP query contracts/i)).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("all or wr-...")).not.toBeInTheDocument();

    const sickCallsFieldset = screen.getByText("Scenario sick calls").closest("fieldset");
    expect(sickCallsFieldset).not.toBeNull();

    await user.click(within(sickCallsFieldset as HTMLElement).getByRole("checkbox", { name: "Parampreet Singh" }));
    await user.clear(screen.getByRole("spinbutton", { name: /Scenario added routes/i }));
    await user.type(screen.getByRole("spinbutton", { name: /Scenario added routes/i }), "2");
    await user.type(screen.getByRole("textbox", { name: /Planner note/i }), "Late-request what-if");

    expect(within(sickCallsFieldset as HTMLElement).getByRole("checkbox", { name: "Parampreet Singh" })).toBeChecked();
    expect(screen.getByRole("spinbutton", { name: /Scenario added routes/i })).toHaveValue(2);
    expect(screen.getByRole("textbox", { name: /Planner note/i })).toHaveValue("Late-request what-if");

    await user.click(screen.getByRole("button", { name: "Refresh" }));

    expect(within(sickCallsFieldset as HTMLElement).getByRole("checkbox", { name: "Parampreet Singh" })).toBeChecked();
    expect(screen.getByRole("spinbutton", { name: /Scenario added routes/i })).toHaveValue(2);
    expect(screen.getByRole("textbox", { name: /Planner note/i })).toHaveValue("Late-request what-if");
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

  it("renders the canonical run-backed schedule page and keeps local edits across refresh", async () => {
    const user = userEvent.setup();
    let responseCount = 0;
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", ({ params }) => {
        responseCount += 1;
        const payload = structuredClone(scheduleRunWorkpageStateSnapshot.workpage_state);
        payload.freshness.generated_at =
          responseCount === 1 ? "2026-03-25T08:10:00Z" : "2026-03-25T08:10:30Z";
        payload.run_context.workflow_run_id = String(params.workflowRunId);
        payload.run_context.activation_key = `snapshot:${String(params.workflowRunId)}:weekly`;
        return HttpResponse.json(payload);
      })
    );
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    const page = await screen.findByTestId("schedule-workpage-page");
    expect(within(page).getByText("run_projection")).toBeInTheDocument();
    expect(
      within(page).getByText(/Workflow-run-backed schedule projection served from canonical weekly Stage04 source artifacts/i)
    ).toBeInTheDocument();

    const sickCallsFieldset = screen.getByText("Scenario sick calls").closest("fieldset");
    expect(sickCallsFieldset).not.toBeNull();

    await user.click(within(sickCallsFieldset as HTMLElement).getByRole("checkbox", { name: "Parampreet Singh" }));
    await user.type(screen.getByRole("textbox", { name: /Planner note/i }), "Run-backed what-if");
    await user.click(screen.getByRole("button", { name: "Refresh" }));

    expect(within(sickCallsFieldset as HTMLElement).getByRole("checkbox", { name: "Parampreet Singh" })).toBeChecked();
    expect(screen.getByRole("textbox", { name: /Planner note/i })).toHaveValue("Run-backed what-if");
  });
});
