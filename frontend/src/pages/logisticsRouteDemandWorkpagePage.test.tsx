import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
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

describe("LogisticsRouteDemandWorkpagePage", () => {
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
