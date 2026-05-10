import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { workpagesRepository } from "@/lib/repositories";
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

describe("LogisticsDriverPreferencesWorkpagePage", () => {
  it(
    "opens Drivers as a modal, edits a snapshot, saves, and stays on the background page",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
      const driversButton = (await screen.findByText("Drivers")).closest("button") as HTMLButtonElement;
      await waitFor(() => {
        expect(driversButton).toBeEnabled();
      }, { timeout: 10000 });
      await user.click(driversButton);

      const dialog = await screen.findByRole("dialog", { name: "Drivers" });
      expect(dialog).toHaveClass("driver-preferences-quick-edit-modal");
      await user.click(within(dialog).getByRole("button", { name: "Create preferences snapshot" }));
      const editor = await within(dialog).findByTestId("driver-preferences-quick-edit-editor");
      expect(
        within(editor).getByRole("heading", { name: "Driver Preferences Snapshot" })
      ).toBeInTheDocument();
      expect(
        within(editor).queryByText(/Saving creates the next immutable driver-preferences snapshot/i)
      ).not.toBeInTheDocument();
      expect(
        within(editor).queryByText(/artifact-backed weekly advisory snapshot lane/i)
      ).not.toBeInTheDocument();
      expect(within(editor).queryByText(/^Week /i)).not.toBeInTheDocument();
      expect(within(editor).queryByText(/^Artifact /i)).not.toBeInTheDocument();
      expect(within(editor).queryByText(/Editable snapshot/i)).not.toBeInTheDocument();
      const qualitySelect = within(editor).getByRole("combobox", {
        name: "Abhiraj Singh quality"
      });

      expect(within(dialog).getByRole("button", { name: "Save snapshot" })).toBeDisabled();
      await user.selectOptions(qualitySelect, "high");
      await waitFor(() => {
        expect(qualitySelect).toHaveValue("high");
      });
      expect(within(dialog).getByRole("button", { name: "Save snapshot" })).toBeEnabled();

      await user.click(within(dialog).getByRole("button", { name: "Save snapshot" }));

      await waitFor(() => {
        expect(screen.queryByRole("dialog", { name: "Drivers" })).not.toBeInTheDocument();
      });
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
      expect(mutationLog()).toContain(
        "workpage-driver-preferences-create:wr-weekly-001:av-driver-preferences-artifact-001"
      );
      expect(mutationLog()).toContain(
        "workpage-driver-preferences-artifact-submit:av-driver-preferences-artifact-001:av-driver-preferences-artifact-002"
      );
    },
    30000
  );

  it(
    "creates the first driver preferences snapshot from the Drivers modal",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
      const driversButton = (await screen.findByText("Drivers")).closest("button") as HTMLButtonElement;
      await waitFor(() => {
        expect(driversButton).toBeEnabled();
      }, { timeout: 10000 });
      await user.click(driversButton);

      const dialog = await screen.findByRole("dialog", { name: "Drivers" });
      expect(
        await within(dialog).findByRole("heading", { name: "Create the first preferences snapshot" })
      ).toBeInTheDocument();

      await user.click(within(dialog).getByRole("button", { name: "Create preferences snapshot" }));

      expect(await within(dialog).findByTestId("driver-preferences-quick-edit-editor")).toBeInTheDocument();
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
      expect(mutationLog()).toContain(
        "workpage-driver-preferences-create:wr-weekly-001:av-driver-preferences-artifact-001"
      );
    },
    30000
  );

  it(
    "renders the run-backed landing and creates the first immutable snapshot",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/driver-preferences-v0");
      render(<App />);

      const page = await screen.findByTestId("driver-preferences-workpage-page");
      expect(within(page).getByRole("heading", { name: "Preference grid" })).toBeInTheDocument();
      expect(
        within(page).getByRole("button", { name: /Abhiraj Singh on 2026-03-23:/i })
      ).toHaveAttribute("aria-disabled", "true");
      expect(within(page).queryByRole("combobox", { name: "Abhiraj Singh quality" })).not.toBeInTheDocument();
      expect(within(page).getAllByText("Quality: Medium").length).toBeGreaterThan(0);
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
    },
    30000
  );

  it(
    "edits the weekly grid, saves a new immutable snapshot version, and keeps history within the snapshot chain",
    async () => {
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
    },
    30000
  );

  it("treats a quality-only change as dirty and persists it on the artifact page", async () => {
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
    const qualitySelect = within(page).getByRole("combobox", {
      name: "Abhiraj Singh quality"
    });

    expect(within(page).getByRole("button", { name: "Save snapshot" })).toBeDisabled();
    await user.selectOptions(qualitySelect, "high");
    await waitFor(() => {
      expect(qualitySelect).toHaveValue("high");
    });
    expect(within(page).getByRole("button", { name: "Save snapshot" })).toBeEnabled();

    await user.click(within(page).getByRole("button", { name: "Save snapshot" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-002"
      );
    });

    const refreshedPage = await screen.findByTestId("driver-preferences-artifact-workpage-page");
    expect(
      within(refreshedPage).getByRole("combobox", { name: "Abhiraj Singh quality" })
    ).toHaveValue("high");
  }, 30000);

  it("keeps unsaved local edits across same-snapshot refreshes", async () => {
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
    expect(page).toBeInTheDocument();

    const mondayCell = within(page).getByRole("button", {
      name: /Abhiraj Singh on 2026-03-23:/i
    });
    await user.click(mondayCell);

    await waitFor(() => {
      expect(mondayCell).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Prefer not to work")
      );
    });
    expect(within(page).getByRole("button", { name: "Save snapshot" })).toBeEnabled();

    await user.click(
      screen.getByRole("button", { name: /Open info for Weekly driver preferences snapshot/i })
    );
    const infoDialog = await screen.findByRole("dialog", {
      name: "Driver preferences snapshot context"
    });
    await user.click(within(infoDialog).getByRole("button", { name: "Refresh" }));
    await user.click(
      screen.getByRole("button", { name: /Close Driver preferences snapshot context/i })
    );

    expect(
      within(screen.getByTestId("driver-preferences-artifact-workpage-page")).getByRole("button", {
        name: /Abhiraj Singh on 2026-03-23:/i
      })
    ).toHaveAttribute("aria-label", expect.stringContaining("Prefer not to work"));
    expect(screen.getByRole("button", { name: "Save snapshot" })).toBeEnabled();
  }, 30000);

  it("adds an availability exception from the availability panel without clearing unsaved grid edits", async () => {
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
    const mondayCell = within(page).getByRole("button", {
      name: /Abhiraj Singh on 2026-03-23:/i
    });
    await user.click(mondayCell);
    await waitFor(() => {
      expect(mondayCell).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Prefer not to work")
      );
    });
    expect(within(page).getByRole("button", { name: "Save snapshot" })).toBeEnabled();

    const panel = within(page).getByTestId("driver-availability-exceptions-panel");
    const grid = within(page).getByTestId("driver-preferences-grid");
    expect(Boolean(panel.compareDocumentPosition(grid) & Node.DOCUMENT_POSITION_FOLLOWING)).toBe(
      true
    );
    expect(within(panel).getByRole("combobox", { name: "Driver" })).toBeInTheDocument();
    await user.clear(within(panel).getByLabelText("Start date"));
    await user.type(within(panel).getByLabelText("Start date"), "2026-03-24");
    await user.clear(within(panel).getByLabelText("End date"));
    await user.type(within(panel).getByLabelText("End date"), "2026-03-24");
    await user.type(within(panel).getByLabelText("Note"), "Family wedding");
    await user.click(within(panel).getByRole("button", { name: "Save exception" }));

    await waitFor(() => {
      expect(mutationLog()).toContain(
        "workpage-driver-availability-exception-create:wr-weekly-001:ae-driver-availability-001"
      );
    });
    const refreshedPage = await screen.findByTestId("driver-preferences-artifact-workpage-page");
    const refreshedPanel = within(refreshedPage).getByTestId("driver-availability-exceptions-panel");
    const approvedList = within(refreshedPanel).getByRole("list");
    expect(within(refreshedPanel).getByText("Family wedding")).toBeInTheDocument();
    expect(within(approvedList).getByText(/Abhiraj Singh/i)).toBeInTheDocument();
    expect(
      within(refreshedPage).getByRole("button", {
        name: /Abhiraj Singh on 2026-03-23: Prefer not to work/i
      })
    ).toBeInTheDocument();
    expect(within(refreshedPage).getByRole("button", { name: "Save snapshot" })).toBeEnabled();
  }, 30000);

  it("shows later out-of-scope exceptions under Future approved without clearing unsaved grid edits", async () => {
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
    const mondayCell = within(page).getByRole("button", {
      name: /Abhiraj Singh on 2026-03-23:/i
    });
    await user.click(mondayCell);
    await waitFor(() => {
      expect(mondayCell).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Prefer not to work")
      );
    });

    const panel = within(page).getByTestId("driver-availability-exceptions-panel");
    await user.clear(within(panel).getByLabelText("Start date"));
    await user.type(within(panel).getByLabelText("Start date"), "2026-04-30");
    await user.clear(within(panel).getByLabelText("End date"));
    await user.type(within(panel).getByLabelText("End date"), "2026-05-14");
    await user.click(within(panel).getByRole("button", { name: "Save exception" }));

    await waitFor(() => {
      expect(mutationLog()).toContain(
        "workpage-driver-availability-exception-create:wr-weekly-001:ae-driver-availability-001"
      );
    });

    const refreshedPage = await screen.findByTestId("driver-preferences-artifact-workpage-page");
    const refreshedPanel = within(refreshedPage).getByTestId("driver-availability-exceptions-panel");
    expect(
      within(refreshedPanel).getByText("Saved for a later week. Find it under Future approved.")
    ).toBeInTheDocument();
    expect(
      within(refreshedPanel).getByRole("button", { name: "Future approved (1)" })
    ).toHaveAttribute("aria-expanded", "true");
    expect(within(refreshedPanel).getByText("2026-04-30 to 2026-05-14")).toBeInTheDocument();
    expect(within(refreshedPanel).getByText("Not yet attached to a weekly run")).toBeInTheDocument();
    expect(within(refreshedPanel).queryByText("Family wedding")).not.toBeInTheDocument();
    expect(
      within(refreshedPage).getByRole("button", {
        name: /Abhiraj Singh on 2026-03-23: Prefer not to work/i
      })
    ).toBeInTheDocument();
    expect(within(refreshedPage).getByRole("button", { name: "Save snapshot" })).toBeEnabled();
  }, 30000);

  it("shows conflict recovery guidance and keeps local edits visible until the operator opens the latest snapshot", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    await workpagesRepository.createWorkpage(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0/snapshots"
    );
    const basePayload = await workpagesRepository.driverPreferencesArtifact(
      "wr-weekly-001",
      "av-driver-preferences-artifact-001"
    );
    const latestPayload = JSON.parse(
      JSON.stringify(basePayload).replaceAll(
        "av-driver-preferences-artifact-001",
        "av-driver-preferences-artifact-latest"
      )
    ) as typeof basePayload;

    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/artifacts/:artifactVersionId/submit",
        ({ params }) =>
          HttpResponse.json(
            {
              status: "error",
              error: {
                code: "workpage_artifact_conflict",
                message: "artifact-backed workpage already has a newer draft",
                details: {
                  artifact_version_id: String(params.artifactVersionId),
                  latest_artifact_version_id: "av-driver-preferences-artifact-latest",
                  workflow_run_id: "wr-weekly-001",
                  route:
                    "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-latest"
                }
              }
            },
            { status: 409 }
          )
      ),
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/artifacts/av-driver-preferences-artifact-latest",
        () => HttpResponse.json(latestPayload)
      )
    );

    window.history.pushState(
      {},
      "",
      "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-001"
    );
    render(<App />);

    const page = await screen.findByTestId("driver-preferences-artifact-workpage-page");
    const mondayCell = within(page).getByRole("button", {
      name: /Abhiraj Singh on 2026-03-23:/i
    });

    await user.click(mondayCell);
    await waitFor(() => {
      expect(mondayCell).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Prefer not to work")
      );
    });

    await user.click(screen.getByRole("button", { name: "Save snapshot" }));

    expect(
      await screen.findByRole("heading", { name: "Latest snapshot already exists" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Abhiraj Singh on 2026-03-23:/i })
    ).toHaveAttribute("aria-label", expect.stringContaining("Prefer not to work"));
    expect(screen.getByRole("button", { name: "Save snapshot" })).toBeDisabled();

    const reopenLink = screen.getByRole("link", { name: "Open latest snapshot" });
    expect(reopenLink).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-latest"
    );
  }, 30000);
});
