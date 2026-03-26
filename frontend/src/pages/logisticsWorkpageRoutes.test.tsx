import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";

function setFrontendOperatorContext(): void {
  const currentContext = getApiRequestContextHeaders();
  setApiRequestContextHeaders({
    ...currentContext,
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  });
}

describe("logistics workpage routes", () => {
  it("navigates from the logistics demo shell to the weekly review workpage", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    expect(await screen.findByText("Backend demo workpages")).toBeInTheDocument();
    await user.click(await screen.findByRole("link", { name: "Open weekly review workpage" }));

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/demo/logistics/workpages/schedule-v0");
  });

  it("navigates from the logistics demo shell to the end-of-day workpage", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await user.click(await screen.findByRole("link", { name: "Open EOD preview" }));

    expect(await screen.findByTestId("dispatch-report-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/demo/logistics/workpages/eod-v0");
  });

  it("creates an editable EOD draft directly from the logistics demo shell", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Create editable EOD draft" }));

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-001");
  });
});
