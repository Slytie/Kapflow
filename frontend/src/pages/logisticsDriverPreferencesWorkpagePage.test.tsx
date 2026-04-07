import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { workpagesRepository } from "@/lib/repositories";
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

describe("LogisticsDriverPreferencesWorkpagePage", () => {
  it("renders the run-backed landing and creates the first immutable snapshot", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/driver-preferences-v0");
    render(<App />);

    const page = await screen.findByTestId("driver-preferences-workpage-page");
    expect(within(page).getByRole("heading", { name: "Preference grid" })).toBeInTheDocument();
    expect(
      within(page).getByRole("button", { name: /Abhiraj Singh on 2026-03-23:/i })
    ).toHaveAttribute("aria-disabled", "true");
    expect(within(page).getByRole("heading", { name: "Snapshot lifecycle" })).toBeInTheDocument();
    expect(
      within(page).getByRole("button", { name: "Create preferences snapshot" })
    ).toBeInTheDocument();

    await user.click(within(page).getByRole("button", { name: "Create preferences snapshot" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-001"
      );
    });
    expect(await screen.findByTestId("driver-preferences-artifact-workpage-page")).toBeInTheDocument();
  });

  it("edits the weekly grid, saves a new immutable snapshot version, and keeps history within the snapshot chain", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    await workpagesRepository.createWorkpage(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0/snapshots"
    );
    window.history.pushState(
      {},
      "",
      "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-001"
    );
    render(<App />);

    const page = await screen.findByTestId("driver-preferences-artifact-workpage-page");
    expect(within(page).getByRole("button", { name: "Save snapshot" })).toBeDisabled();
    expect(within(page).getByTestId("driver-preferences-history-rail")).toBeInTheDocument();
    const mondayCell = within(page).getByRole("button", {
      name: /Abhiraj Singh on 2026-03-23:/i
    });
    expect(mondayCell).toHaveAttribute("aria-disabled", "false");

    const initialAriaLabel = mondayCell.getAttribute("aria-label") ?? "";
    const initialState = initialAriaLabel.split(": ").at(-1) ?? "";
    const nextStateLabel: Record<string, string> = {
      "Open to work": "Prefer not to work",
      "Prefer not to work": "Definitely cannot work",
      "Definitely cannot work": "Unset",
      Unset: "Open to work"
    };
    await user.click(mondayCell);
    await waitFor(() => {
      expect(mondayCell).toHaveAttribute(
        "aria-label",
        expect.stringContaining(nextStateLabel[initialState] ?? "Open to work")
      );
    });
    expect(within(page).getByRole("button", { name: "Save snapshot" })).toBeEnabled();

    await user.click(within(page).getByRole("button", { name: "Save snapshot" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-002"
      );
    });

    const refreshedPage = await screen.findByTestId("driver-preferences-artifact-workpage-page");
    expect(within(refreshedPage).getByTestId("driver-preferences-history-rail")).toBeInTheDocument();
    expect(
      within(refreshedPage).getByTestId("driver-preferences-history-av-driver-preferences-artifact-002")
    ).toBeInTheDocument();
    expect(
      within(refreshedPage).getByTestId("driver-preferences-history-av-driver-preferences-artifact-001")
    ).toBeInTheDocument();
    expect(
      within(refreshedPage).getByTestId("driver-preferences-schedule-impact")
    ).toBeInTheDocument();
    expect(mutationLog()).toContain(
      "workpage-driver-preferences-artifact-submit:av-driver-preferences-artifact-001:av-driver-preferences-artifact-002"
    );
  });
});
