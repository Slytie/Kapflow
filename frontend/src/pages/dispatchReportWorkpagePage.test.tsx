import { render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import eodRunWorkpageStateSnapshot from "@fixtures/workpage_eod_v0_run_state.json";
import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";
import { server } from "@/test/api/server";
import { buildEodArtifactWorkpageState } from "@/test/workpages/eodArtifactFixture";

function buildArtifactPayload(
  artifactVersionId: string,
  workflowRunId = "wr-eod-artifact-001"
): Record<string, unknown> {
  const payload = buildEodArtifactWorkpageState({
    artifactVersionId,
    workflowRunId,
    latestArtifactVersionId: artifactVersionId,
    supersedesArtifactVersionId: null,
    supersededByArtifactVersionId: null,
    generatedAt: "2026-03-25T09:00:00Z"
  });
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
      expect(window.location.pathname).toBe(
        "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-002"
      );
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

  it("loads recent draft history from workflow-run artifacts and reopens adjacent draft versions", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0");
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Create editable draft" }));
    await screen.findByTestId("dispatch-report-artifact-workpage-page");
    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-002"
      );
    });

    const historyHeading = await screen.findByRole("heading", { name: "Recent draft versions" });
    const historyPanel = historyHeading.closest("section");
    expect(historyPanel).not.toBeNull();
    expect(within(historyPanel as HTMLElement).getByText("Current draft")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Previous draft")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Current")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Latest")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Superseded")).toBeInTheDocument();

    await user.click(within(historyPanel as HTMLElement).getByRole("link", { name: /Previous draft/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
      );
    });
    expect(await screen.findByRole("heading", { name: "Latest draft available" })).toBeInTheDocument();
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
                route: "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-latest"
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
      "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-latest"
    );
  });

  it("renders the artifact-backed route directly under the logistics shell", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/workpages/artifacts/av-direct-001", () =>
        HttpResponse.json(buildArtifactPayload("av-direct-001"))
      )
    );

    window.history.pushState({}, "", "/demo/logistics/workpages/eod-v0/artifacts/av-direct-001");
    render(<App />);

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.queryByText("Secondary detail routes")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open secondary detail routes" }));
    const shellInfoDialog = await screen.findByRole("dialog", { name: "Secondary detail routes" });
    expect(within(shellInfoDialog).getByRole("link", { name: "Run Details" })).toHaveAttribute(
      "href",
      "/runs"
    );
    expect(window.location.pathname).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-direct-001");
  });

  it("submits canonical artifact drafts with carried workspace subject context and refresh invalidation", async () => {
    const user = userEvent.setup();
    const submitBodies: Array<Record<string, unknown>> = [];
    const invalidateSpy = vi.spyOn(QueryClient.prototype, "invalidateQueries");
    server.use(
      http.get("*/api/v1/workpages/artifacts/av-eod-artifact-001", () =>
        HttpResponse.json(buildArtifactPayload("av-eod-artifact-001"))
      ),
      http.post("*/api/v1/workpages/artifacts/:artifactVersionId/submit", async ({ params, request }) => {
        submitBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({
          status: "ok",
          command: "api.workpages.artifact.submit",
          submitted: {
            workflow_run_id: "wr-eod-artifact-001",
            artifact_version_id: "av-eod-artifact-010",
            supersedes_artifact_version_id: String(params.artifactVersionId),
            route: "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-010"
          }
        });
      }),
      http.get("*/api/v1/workpages/artifacts/av-eod-artifact-010", () =>
        HttpResponse.json(buildArtifactPayload("av-eod-artifact-010"))
      )
    );

    window.history.pushState(
      {
        usr: {
          workpageSubjectContext: {
            subject_kind: "approval",
            subject_id: "ap-stage04-001",
            workflow_run_id: "wr-eod-artifact-001"
          }
        },
        key: "default",
        idx: 0
      },
      "",
      "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
    );
    render(<App />);

    await screen.findByTestId("dispatch-report-artifact-workpage-page");
    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-010"
      );
    });

    expect(submitBodies).toHaveLength(1);
    expect(submitBodies[0]).toMatchObject({
      subject_link: {
        subject_kind: "approval",
        subject_id: "ap-stage04-001"
      }
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["workpages"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["run-workspace", "wr-eod-artifact-001"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["run-detail", "wr-eod-artifact-001"] });
    invalidateSpy.mockRestore();
  });

  it("renders the canonical run-backed landing with a latest-draft handoff", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0", ({ params }) => {
        const payload = structuredClone(eodRunWorkpageStateSnapshot.workpage_state);
        payload.run_context.workflow_run_id = String(params.workflowRunId);
        payload.run_context.activation_key = `snapshot:${String(params.workflowRunId)}:dispatch-reporting`;
        payload.draft_resolution.latest_artifact_version_id = "av-run-latest-001";
        payload.draft_resolution.artifact_route = `/runs/${String(params.workflowRunId)}/workpages/eod-v0/artifacts/av-run-latest-001`;
        payload.freshness.source_version = "av-run-latest-001";
        payload.source.source_refs = [
          "/api/v1/artifacts/av-reporting-eos-001",
          "/api/v1/artifacts/av-reporting-actuals-001",
          "/api/v1/artifacts/av-run-latest-001"
        ];
        return HttpResponse.json(payload);
      }),
      http.get("*/api/v1/workpages/artifacts/av-run-latest-001", () =>
        HttpResponse.json(buildArtifactPayload("av-run-latest-001", "wr-reporting-001"))
      )
    );

    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
    render(<App />);

    const page = await screen.findByTestId("dispatch-report-workpage-page");
    expect(within(page).getByRole("heading", { name: "End-of-day report" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open latest draft" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create editable draft" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Open latest draft" }));

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-run-latest-001"
    );
  });
});
