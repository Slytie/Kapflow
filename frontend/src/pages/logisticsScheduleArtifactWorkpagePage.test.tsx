import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";

import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import { App } from "@/app/App";
import { mutationLog } from "@/test/api/handlers";
import { server } from "@/test/api/server";

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function heatmapSection(): HTMLElement {
  const section = screen.getByRole("heading", { name: "Planned schedule heatmap" }).closest("section");
  if (!section) {
    throw new Error("Heatmap section not found");
  }
  return section as HTMLElement;
}

function heatmapButton(
  section: HTMLElement,
  predicate: (label: string) => boolean
): HTMLButtonElement {
  const button = within(section)
    .getAllByRole("button")
    .find((candidate) => predicate(candidate.getAttribute("aria-label") ?? ""));
  if (!button) {
    throw new Error("Matching heatmap cell not found");
  }
  return button as HTMLButtonElement;
}

function personNameFromLabel(label: string): string {
  return label.split(" on ")[0] ?? label;
}

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
    "opens the latest draft from the run-backed landing, moves planned work in the heatmap, submits a superseding version, and downloads JSON",
    async () => {
      const user = userEvent.setup();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      await user.click(
        await screen.findByRole("link", { name: "Open editable draft" }, { timeout: 5000 })
      );
      const artifactPage = await screen.findByTestId("schedule-artifact-workpage-page");
      const artifactTitleBar = artifactPage.querySelector(".workpage-page__hero-title-bar");
      const artifactHeroActions = artifactPage.querySelector(".workpage-page__hero-actions");
      const draftHistoryRail = within(artifactPage).getByTestId("schedule-draft-history-rail");
      expect(artifactTitleBar).not.toBeNull();
      expect(artifactTitleBar).toHaveClass("workpage-page__hero-title-bar--sticky");
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Submit draft" })
      ).toBeInTheDocument();
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Download draft JSON" })
      ).toBeInTheDocument();
      expect(artifactHeroActions).not.toBeNull();
      expect(
        within(artifactHeroActions as HTMLElement).getByRole("link", { name: "Back to query landing" })
      ).toBeInTheDocument();
      expect(
        within(artifactHeroActions as HTMLElement).queryByRole("button", { name: "Download draft JSON" })
      ).not.toBeInTheDocument();
      expect(draftHistoryRail.closest("aside")).toHaveClass("workpage-page__artifact-rail");
      expect(within(draftHistoryRail).getByRole("heading", { name: "Recent draft versions" })).toBeInTheDocument();
      expect(within(artifactPage).queryByRole("heading", { name: "Draft actions" })).not.toBeInTheDocument();
      const summarySection = within(artifactPage).getByTestId("workpage-summary-section");
      expect(
        within(summarySection).getByRole("heading", { name: "Draft workbook summary" })
      ).toBeInTheDocument();
      expect(
        within(summarySection).getByTestId("workpage-summary-card-route_assignment_count")
      ).toHaveClass("workpage-summary-card");
      expect(within(summarySection).getByText("158")).toBeInTheDocument();

      const heatmap = heatmapSection();
      const sourceCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const targetCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: no planned work")
      );
      const targetName = personNameFromLabel(targetCell.getAttribute("aria-label") ?? "");

      await user.click(sourceCell);
      await user.click(targetCell);

      expect(
        within(heatmap).getByRole("button", {
          name: new RegExp(`^${escapeRegExp(targetName)} on 2026-03-22: assigned route, manually overridden$`)
        })
      ).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Submit draft" }));

      await waitFor(() => {
        expect(window.location.pathname).toBe(
          "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
        );
      });

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
      expect(
        screen.getByRole("button", {
          name: new RegExp(`^${escapeRegExp(targetName)} on 2026-03-22: assigned route, manually overridden$`)
        })
      ).toBeInTheDocument();

      const historyPanel = screen.getByTestId("schedule-draft-history-rail");
      expect(within(historyPanel as HTMLElement).getByText("Current draft")).toBeInTheDocument();
      expect(within(historyPanel as HTMLElement).getByText("Previous draft")).toBeInTheDocument();

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

    await user.click(
      within(screen.getByTestId("schedule-draft-history-av-schedule-artifact-001")).getByRole("link", {
        name: /Previous draft/i
      })
    );

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

    const heatmap = heatmapSection();
    const sourceCell = heatmapButton(
      heatmap,
      (label) => label.includes("2026-03-22: assigned route")
    );
    const targetCell = heatmapButton(
      heatmap,
      (label) => label.includes("2026-03-22: no planned work")
    );
    const targetName = personNameFromLabel(targetCell.getAttribute("aria-label") ?? "");

    await user.click(sourceCell);
    await user.click(targetCell);

    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    expect(await screen.findByRole("heading", { name: "Latest draft already exists" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: new RegExp(`^${escapeRegExp(targetName)} on 2026-03-22: assigned route, manually overridden$`)
      })
    ).toBeInTheDocument();

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

  it(
    "supports same-day assignment to reserve swaps in the heatmap",
    async () => {
      const user = userEvent.setup();
      window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
      render(<App />);

      await user.click(await screen.findByRole("link", { name: "Open editable draft" }));
      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();

      const heatmap = heatmapSection();
      const assignmentCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: assigned route")
      );
      const reserveCell = heatmapButton(
        heatmap,
        (label) => label.includes("2026-03-22: on call")
      );
      const assignmentName = personNameFromLabel(assignmentCell.getAttribute("aria-label") ?? "");
      const reserveName = personNameFromLabel(reserveCell.getAttribute("aria-label") ?? "");

      await user.click(assignmentCell);
      await user.click(reserveCell);

      expect(
        within(heatmap).getByRole("button", {
          name: new RegExp(`^${escapeRegExp(reserveName)} on 2026-03-22: assigned route, manually overridden$`)
        })
      ).toBeInTheDocument();
      expect(
        within(heatmap).getByRole("button", {
          name: new RegExp(`^${escapeRegExp(assignmentName)} on 2026-03-22: on call, manually overridden$`)
        })
      ).toBeInTheDocument();
    },
    10000
  );
});
