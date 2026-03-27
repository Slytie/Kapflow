import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";
import { server } from "@/test/api/server";

function buildScheduleArtifactPayload(
  artifactVersionId: string,
  workflowRunId = "wr-weekly-001"
): Record<string, unknown> {
  const payload = structuredClone(scheduleArtifactStateSnapshot.workpage_state);
  payload.freshness.generated_at = "2026-03-25T09:15:00Z";
  payload.freshness.source_version = artifactVersionId;
  payload.source.source_artifact_version_id = artifactVersionId;
  payload.artifact_context.artifact_version_id = artifactVersionId;
  payload.artifact_context.workflow_run_id = workflowRunId;
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
    { label: "Supersedes", value: "Initial Stage04 draft" },
    { label: "Latest draft in chain", value: artifactVersionId }
  ];
  return payload;
}

describe("LogisticsScheduleArtifactWorkpagePage", () => {
  it(
    "opens the latest draft from the run-backed landing, submits a superseding version, and downloads JSON",
    async () => {
      const user = userEvent.setup();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

    await user.click(await screen.findByRole("link", { name: "Open editable draft" }));
    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();

    const assignmentDriverInput = screen.getByRole("textbox", {
      name: "Route assignments Assigned Driver Id 1"
    });
    const assignmentStatusInput = screen.getByRole("textbox", {
      name: "Route assignments Assignment Status 1"
    });
    const reserveDriverInput = screen.getByRole("textbox", {
      name: "Reserve posture Assigned Driver Id 1"
    });
    const reserveStatusInput = screen.getByRole("textbox", {
      name: "Reserve posture Assignment Status 1"
    });

    await user.clear(assignmentDriverInput);
    await user.type(assignmentDriverInput, "DRV-MANUAL-77");
    await user.clear(assignmentStatusInput);
    await user.type(assignmentStatusInput, "manual_override");
    await user.clear(reserveDriverInput);
    await user.type(reserveDriverInput, "DRV-MANUAL-88");
    await user.clear(reserveStatusInput);
    await user.type(reserveStatusInput, "manual_override");

    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
      );
    });

    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Route assignments Assigned Driver Id 1" })).toHaveValue(
      "DRV-MANUAL-77"
    );
    expect(screen.getByRole("textbox", { name: "Route assignments Assignment Status 1" })).toHaveValue(
      "manual_override"
    );
    expect(screen.getByRole("textbox", { name: "Reserve posture Assigned Driver Id 1" })).toHaveValue(
      "DRV-MANUAL-88"
    );
    expect(screen.getByRole("textbox", { name: "Reserve posture Assignment Status 1" })).toHaveValue(
      "manual_override"
    );

    const historyPanel = screen.getByRole("heading", { name: "Recent draft versions" }).closest("section");
    expect(historyPanel).not.toBeNull();
    expect(within(historyPanel as HTMLElement).getByText("av-schedule-artifact-002")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("av-schedule-artifact-001")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Download draft JSON" }));
      await waitFor(() => {
        expect(mutationLog()).toContain("artifact-download-bin:av-schedule-artifact-002");
      });
    },
    25000
  );

  it("reopens the previous draft from history and shows the stale-version guidance", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    await user.click(await screen.findByRole("link", { name: "Open editable draft" }));
    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
      );
    });

    await user.click(screen.getByRole("link", { name: "Open previous draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
    });
    expect(await screen.findByRole("heading", { name: "Latest draft available" })).toBeInTheDocument();
  });

  it("shows conflict reopen UX and keeps local edits until the operator navigates", async () => {
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
                latest_artifact_version_id: "av-schedule-artifact-latest",
                workflow_run_id: "wr-weekly-001",
                route:
                  "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-latest"
              }
            }
          },
          { status: 409 }
        )
      ),
      http.get("*/api/v1/workpages/artifacts/av-schedule-artifact-latest", () =>
        HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-latest"))
      )
    );

    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    await user.click(await screen.findByRole("link", { name: "Open editable draft" }));
    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();

    const assignmentDriverInput = screen.getByRole("textbox", {
      name: "Route assignments Assigned Driver Id 1"
    });
    await user.clear(assignmentDriverInput);
    await user.type(assignmentDriverInput, "DRV-CONFLICT-11");

    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    expect(await screen.findByRole("heading", { name: "Latest draft already exists" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Route assignments Assigned Driver Id 1" })).toHaveValue(
      "DRV-CONFLICT-11"
    );

    await user.click(screen.getByRole("link", { name: "Open latest draft" }));

    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-latest"
    );
  }, 10000);

  it("drops mismatched workspace subject context when submitting schedule drafts directly", async () => {
    const user = userEvent.setup();
    const submitBodies: Array<Record<string, unknown>> = [];
    server.use(
      http.get("*/api/v1/workpages/artifacts/av-schedule-artifact-001", () =>
        HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-001"))
      ),
      http.post("*/api/v1/workpages/artifacts/:artifactVersionId/submit", async ({ params, request }) => {
        submitBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({
          status: "ok",
          command: "api.workpages.artifact.submit",
          submitted: {
            workflow_run_id: "wr-weekly-001",
            artifact_version_id: "av-schedule-artifact-010",
            supersedes_artifact_version_id: String(params.artifactVersionId),
            route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-010"
          }
        });
      }),
      http.get("*/api/v1/workpages/artifacts/av-schedule-artifact-010", () =>
        HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-010"))
      )
    );

    window.history.pushState(
      {
        workpageSubjectContext: {
          subject_kind: "human_task",
          subject_id: "ht-stage04-001",
          workflow_run_id: "wr-other-run"
        }
      },
      "",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
    render(<App />);

    await screen.findByTestId("schedule-artifact-workpage-page");
    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-010"
      );
    });

    expect(submitBodies).toHaveLength(1);
    expect(submitBodies[0]).not.toHaveProperty("subject_link");
  });
});
