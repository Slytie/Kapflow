import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import artifactStateSnapshot from "@fixtures/workpage_eod_v0_artifact_state.json";
import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";
import { server } from "@/test/api/server";

function buildArtifactPayload(artifactVersionId: string): Record<string, unknown> {
  const payload = structuredClone(artifactStateSnapshot.workpage_state);
  payload.freshness.generated_at = "2026-03-25T09:00:00Z";
  payload.freshness.source_version = artifactVersionId;
  payload.source.source_artifact_version_id = artifactVersionId;
  payload.artifact_context.artifact_version_id = artifactVersionId;
  payload.artifact_context.download_path = `/api/v1/artifacts/${artifactVersionId}/download.bin`;
  payload.artifact_context.latest_in_chain_artifact_version_id = artifactVersionId;
  payload.artifact_context.supersedes_artifact_version_id = null;
  payload.artifact_context.superseded_by_artifact_version_id = null;
  payload.workpage.source_artifact_version_id = artifactVersionId;
  const history = payload.workpage.sections.find(
    (section) => section.kind === "history_stub"
  ) as { entries: Array<{ label: string; value: string }> };
  history.entries = [
    { label: "Current artifact version", value: artifactVersionId },
    { label: "Supersedes", value: "Initial draft" },
    { label: "Latest draft in chain", value: artifactVersionId }
  ];
  return payload;
}

describe("DispatchReportWorkpagePage", () => {
  it("renders the query landing as a read-only preview and creates an editable draft route", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0");
    render(<App />);

    const page = await screen.findByTestId("dispatch-report-workpage-page");
    expect(within(page).getByRole("heading", { name: "End-of-day report" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create editable draft" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: /Dispatcher comment/i })).toBeDisabled();
    expect(
      within(page).getByText(/Create an editable draft to switch into artifact-backed workbook editing/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create editable draft" }));

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-001");
    expect(screen.getByText("artifact_projection")).toBeInTheDocument();
  });

  it("keeps artifact-backed local edits across refresh when the same artifact version is re-fetched", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0");
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Create editable draft" }));
    const page = await screen.findByTestId("dispatch-report-artifact-workpage-page");
    expect(page).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i }), "36 online");
    await user.click(screen.getAllByRole("button", { name: "Add entry" })[0]);
    await user.type(screen.getByRole("textbox", { name: "Rescues 1" }), "Route CX100 assist");
    await user.type(
      screen.getByRole("textbox", { name: /Dispatcher comment/i }),
      "Draft edits should stay local across refresh."
    );

    await user.click(screen.getByRole("button", { name: "Refresh" }));

    expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toHaveValue(
      "36 online"
    );
    expect(screen.getByRole("textbox", { name: "Rescues 1" })).toHaveValue("Route CX100 assist");
    expect(screen.getByRole("textbox", { name: /Dispatcher comment/i })).toHaveValue(
      "Draft edits should stay local across refresh."
    );
  });

  it("submits the artifact-backed draft, navigates to the superseding route, and downloads the workbook", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0");
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Create editable draft" }));
    await screen.findByTestId("dispatch-report-artifact-workpage-page");

    await user.type(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i }), "38");
    await user.type(
      screen.getByRole("textbox", { name: /Dispatcher comment/i }),
      "Submitted from the artifact-backed page."
    );
    await user.type(screen.getByRole("textbox", { name: /Manager note/i }), "Escalate next morning.");

    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-002");
    });

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toHaveValue("38");
    expect(screen.getByRole("textbox", { name: /Dispatcher comment/i })).toHaveValue(
      "Submitted from the artifact-backed page."
    );
    expect(screen.getByRole("textbox", { name: /Manager note/i })).toHaveValue(
      "Escalate next morning."
    );

    await user.click(screen.getByRole("button", { name: "Download workbook" }));
    await waitFor(() => {
      expect(mutationLog()).toContain("artifact-download-bin:av-eod-artifact-002");
    });
  });

  it("shows conflict reopen UX and preserves local edits until the operator navigates", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/workpages/artifacts/:artifactVersionId/submit", ({ params }) =>
        HttpResponse.json(
          {
            status: "error",
            error: {
              code: "workpage_artifact_conflict",
              message: "artifact-backed workpage already has a newer draft",
              details: {
                artifact_version_id: String(params.artifactVersionId),
                latest_artifact_version_id: "av-eod-artifact-latest",
                workflow_run_id: "wr-eod-artifact-001",
                route: "/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-latest"
              }
            }
          },
          { status: 409 }
        )
      ),
      http.get("*/api/v1/workpages/artifacts/av-eod-artifact-latest", () =>
        HttpResponse.json(buildArtifactPayload("av-eod-artifact-latest"))
      )
    );

    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0");
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Create editable draft" }));
    await screen.findByTestId("dispatch-report-artifact-workpage-page");

    await user.type(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i }), "34");
    await user.type(
      screen.getByRole("textbox", { name: /Dispatcher comment/i }),
      "Keep these edits while the conflict panel is open."
    );

    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    expect(await screen.findByRole("heading", { name: "Latest draft already exists" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toHaveValue("34");
    expect(screen.getByRole("textbox", { name: /Dispatcher comment/i })).toHaveValue(
      "Keep these edits while the conflict panel is open."
    );

    await user.click(screen.getByRole("link", { name: "Open latest draft" }));

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-latest"
    );
  });

  it("renders the artifact-backed route directly under the logistics shell", async () => {
    server.use(
      http.get("*/api/v1/workpages/artifacts/av-direct-001", () =>
        HttpResponse.json(buildArtifactPayload("av-direct-001"))
      )
    );

    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0/artifacts/av-direct-001");
    render(<App />);

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.getByLabelText("Secondary detail routes")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-direct-001");
  });
});
