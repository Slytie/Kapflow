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
  workflowRunId = "wr-weekly-001",
  customize?: (payload: Record<string, any>) => void
): Record<string, unknown> {
  const payload = structuredClone(scheduleArtifactStateSnapshot.workpage_state) as Record<string, any>;
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
  payload.artifact_state.current_artifact_version_id = artifactVersionId;
  payload.artifact_state.latest_artifact_version_id = artifactVersionId;
  payload.artifact_history = {
    current_artifact_version_id: artifactVersionId,
    latest_artifact_version_id: artifactVersionId,
    previous_artifact_version_id: null,
    next_artifact_version_id: null,
    entries: [
      {
        artifact_version_id: artifactVersionId,
        workflow_run_id: workflowRunId,
        artifact_kind: "planning.draft_weekly_schedule.workbook",
        created_at: "2026-03-25T09:15:00Z",
        lineage_note: "Initial Stage04 draft weekly schedule artifact.",
        supersedes_artifact_version_id: null,
        route: `/runs/${workflowRunId}/workpages/schedule-v0/artifacts/${artifactVersionId}`
      }
    ]
  };
  payload.draft_lineage.current_artifact_version_id = artifactVersionId;
  payload.draft_lineage.latest_artifact_version_id = artifactVersionId;
  payload.draft_lineage.previous_artifact_version_id = null;
  payload.draft_lineage.recent_versions = [
    {
      artifact_version_id: artifactVersionId,
      supersedes_artifact_version_id: null
    }
  ];
  payload.actions = payload.actions.map((action: Record<string, unknown>) => {
    if (action.kind === "preview_recalc") {
      return {
        ...action,
        artifact_version_id: artifactVersionId,
        preview_path: `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}/preview`,
        action_ref: {
          action_id: String(action.action_id),
          workpage_kind: "schedule-v0",
          workflow_run_id: workflowRunId,
          artifact_version_id: artifactVersionId,
          subject: null
        }
      };
    }
    if (action.kind === "submit_artifact") {
      return {
        ...action,
        artifact_version_id: artifactVersionId,
        submit_path: `/api/v1/workpages/workflow-runs/${workflowRunId}/schedule-v0/artifacts/${artifactVersionId}/submit`,
        action_ref: {
          action_id: String(action.action_id),
          workpage_kind: "schedule-v0",
          workflow_run_id: workflowRunId,
          artifact_version_id: artifactVersionId,
          subject: null
        }
      };
    }
    return action;
  });
  const history = payload.workpage.sections.find(
    (section: Record<string, unknown>) => section.kind === "history_stub"
  ) as { entries: Array<{ label: string; value: string }> };
  history.entries = [
    { label: "Current artifact version", value: artifactVersionId },
    { label: "Supersedes", value: "Initial Stage04 draft" },
    { label: "Latest draft in chain", value: artifactVersionId }
  ];
  customize?.(payload);
  return payload;
}

describe("LogisticsScheduleArtifactWorkpagePage", () => {
  it(
    "opens the latest draft from the run-backed landing, auto-previews heatmap edits, saves a superseding version, and downloads JSON",
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
      expect(artifactTitleBar).not.toBeNull();
      expect(artifactTitleBar).toHaveClass("workpage-page__hero-title-bar--sticky");
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Save draft" })
      ).toBeInTheDocument();
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Download draft JSON" })
      ).toBeInTheDocument();
      expect(artifactHeroActions).not.toBeNull();
      expect(
        within(artifactHeroActions as HTMLElement).getByRole("link", { name: "Back to query landing" })
      ).toBeInTheDocument();
      expect(within(artifactPage).getByRole("heading", { name: "Accepted history" })).toBeInTheDocument();
      expect(within(artifactPage).getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();
      expect(within(artifactPage).getByRole("heading", { name: "Live preview" })).toBeInTheDocument();
      expect(within(artifactPage).getByText("No accepted schedule history is available for this surface yet.")).toBeInTheDocument();

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

      await waitFor(() => {
        expect(mutationLog()).toContain("workpage-schedule-artifact-preview:av-schedule-artifact-001");
      });
      expect(await screen.findByText("Preview applied")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Save draft" }));

      await waitFor(() => {
        expect(window.location.pathname).toBe(
          "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
        );
      });

      expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
      const historyPanel = screen.getByTestId("schedule-draft-history-rail");
      expect(within(historyPanel as HTMLElement).getByText("Current draft")).toBeInTheDocument();
      expect(within(historyPanel as HTMLElement).getAllByText("Previous draft").length).toBeGreaterThan(0);

      await user.click(screen.getByRole("button", { name: "Download draft JSON" }));
      await waitFor(() => {
        expect(mutationLog()).toContain("artifact-download-bin:av-schedule-artifact-002");
      });
    },
    40000
  );

  it("reopens the previous draft from the draft rail and shows the stale-version guidance", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    await user.click(await screen.findByRole("link", { name: "Open editable draft" }));
    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save draft" }));

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
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/submit",
        ({ params }) =>
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
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-artifact-latest",
        () =>
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

    await user.click(screen.getByRole("button", { name: "Save draft" }));

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
  }, 20000);

  it("uses accepted-series navigation without traversing the draft rail", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-accepted-002",
        () =>
        HttpResponse.json(
          buildScheduleArtifactPayload("av-schedule-accepted-002", "wr-weekly-001", (payload) => {
            payload.actions = [];
            payload.artifact_context.artifact_kind = "planning.published_weekly_schedule.workbook";
            payload.artifact_state = {
              ...payload.artifact_state,
              artifact_kind: "planning.published_weekly_schedule.workbook",
              state_kind: "accepted",
              editable: false,
              current_artifact_version_id: "av-schedule-accepted-002",
              accepted_artifact_version_id: "av-schedule-accepted-002"
            };
            payload.accepted_series = {
              series_key: "weekly_schedule_planning.v1:dvc4:pitt-meadows",
              current_artifact_version_id: "av-schedule-accepted-002",
              previous_artifact_version_id: "av-schedule-accepted-001",
              next_artifact_version_id: null,
              entries: [
                {
                  artifact_version_id: "av-schedule-accepted-001",
                  workflow_run_id: "wr-weekly-000",
                  partition_key: "PW-2026-W12",
                  logical_date: "2026-03-15",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-000/workpages/schedule-v0/artifacts/av-schedule-accepted-001"
                },
                {
                  artifact_version_id: "av-schedule-accepted-002",
                  workflow_run_id: "wr-weekly-001",
                  partition_key: "PW-2026-W13",
                  logical_date: "2026-03-22",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-accepted-002"
                }
              ]
            };
            payload.draft_lineage = {
              current_artifact_version_id: "av-schedule-draft-011",
              latest_artifact_version_id: "av-schedule-draft-011",
              previous_artifact_version_id: "av-schedule-draft-010",
              recent_versions: [
                {
                  artifact_version_id: "av-schedule-draft-011",
                  supersedes_artifact_version_id: "av-schedule-draft-010"
                },
                {
                  artifact_version_id: "av-schedule-draft-010",
                  supersedes_artifact_version_id: null
                }
              ]
            };
            payload.artifact_history = {
              current_artifact_version_id: "av-schedule-draft-011",
              latest_artifact_version_id: "av-schedule-draft-011",
              previous_artifact_version_id: "av-schedule-draft-010",
              next_artifact_version_id: null,
              entries: [
                {
                  artifact_version_id: "av-schedule-draft-011",
                  workflow_run_id: "wr-weekly-001",
                  artifact_kind: "planning.draft_weekly_schedule.workbook",
                  created_at: "2026-03-22T18:00:00Z",
                  lineage_note: "Published from latest draft.",
                  supersedes_artifact_version_id: "av-schedule-draft-010",
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-draft-011"
                },
                {
                  artifact_version_id: "av-schedule-draft-010",
                  workflow_run_id: "wr-weekly-001",
                  artifact_kind: "planning.draft_weekly_schedule.workbook",
                  created_at: "2026-03-21T18:00:00Z",
                  lineage_note: "Initial Stage04 draft weekly schedule artifact.",
                  supersedes_artifact_version_id: null,
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-draft-010"
                }
              ]
            };
          })
        )
      ),
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-accepted-001",
        () =>
        HttpResponse.json(
          buildScheduleArtifactPayload("av-schedule-accepted-001", "wr-weekly-000", (payload) => {
            payload.actions = [];
            payload.artifact_context.artifact_kind = "planning.published_weekly_schedule.workbook";
            payload.artifact_state = {
              ...payload.artifact_state,
              artifact_kind: "planning.published_weekly_schedule.workbook",
              state_kind: "accepted",
              editable: false,
              current_artifact_version_id: "av-schedule-accepted-001",
              accepted_artifact_version_id: "av-schedule-accepted-001"
            };
            payload.accepted_series = {
              series_key: "weekly_schedule_planning.v1:dvc4:pitt-meadows",
              current_artifact_version_id: "av-schedule-accepted-001",
              previous_artifact_version_id: null,
              next_artifact_version_id: "av-schedule-accepted-002",
              entries: [
                {
                  artifact_version_id: "av-schedule-accepted-001",
                  workflow_run_id: "wr-weekly-000",
                  partition_key: "PW-2026-W12",
                  logical_date: "2026-03-15",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-000/workpages/schedule-v0/artifacts/av-schedule-accepted-001"
                },
                {
                  artifact_version_id: "av-schedule-accepted-002",
                  workflow_run_id: "wr-weekly-001",
                  partition_key: "PW-2026-W13",
                  logical_date: "2026-03-22",
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-accepted-002"
                }
              ]
            };
          })
        )
      )
    );

    window.history.pushState(
      {},
      "",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-accepted-002"
    );
    render(<App />);

    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Accepted history" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Draft lineage" })).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Previous accepted" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-000/workpages/schedule-v0/artifacts/av-schedule-accepted-001"
      );
    });
  });

  it(
    "keeps the last successful preview visible when a later preview fails",
    async () => {
      const user = userEvent.setup();
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
    const sourceName = personNameFromLabel(sourceCell.getAttribute("aria-label") ?? "");
    const targetName = personNameFromLabel(targetCell.getAttribute("aria-label") ?? "");

    await user.click(sourceCell);
    await user.click(targetCell);

    await waitFor(() => {
      expect(mutationLog()).toContain("workpage-schedule-artifact-preview:av-schedule-artifact-001");
    });
    expect(await screen.findByText("Preview applied")).toBeInTheDocument();

    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/preview",
        () =>
          HttpResponse.json(
            {
              status: "error",
              error: {
                code: "preview_unavailable",
                message: "preview calculation failed"
              }
            },
            { status: 422 }
          )
      )
    );

    const secondSourceCell = heatmapButton(
      heatmap,
      (label) => label.includes(`${targetName} on 2026-03-22: assigned route`)
    );
    const secondTargetCell = heatmapButton(
      heatmap,
      (label) => label.includes(`${sourceName} on 2026-03-22: no planned work`)
    );

    await user.click(secondSourceCell);
    await user.click(secondTargetCell);

    expect(await screen.findByText(/preview_unavailable: preview calculation failed/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Selected day" })).toBeInTheDocument();
    },
    20000
  );

  it("drops mismatched workspace subject context when saving schedule drafts directly", async () => {
    const user = userEvent.setup();
    const submitBodies: Array<Record<string, unknown>> = [];
    server.use(
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-artifact-001",
        () =>
        HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-001"))
      ),
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/submit",
        async ({ params, request }) => {
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
        }
      ),
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/av-schedule-artifact-010",
        () =>
        HttpResponse.json(buildScheduleArtifactPayload("av-schedule-artifact-010"))
      )
    );

    window.history.pushState(
      {
        workpageActionRef: {
          action_id: "workpage.schedule-v0.open_latest_draft",
          workpage_kind: "schedule-v0",
          workflow_run_id: "wr-other-run",
          artifact_version_id: "av-schedule-artifact-001",
          subject: {
            subject_kind: "human_task",
            subject_id: "ht-stage04-001"
          }
        }
      },
      "",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
    render(<App />);

    await screen.findByTestId("schedule-artifact-workpage-page");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-010"
      );
    });

    expect(submitBodies).toHaveLength(1);
    expect(submitBodies[0]).toMatchObject({
      action_ref: {
        action_id: "workpage.schedule-v0.save_draft",
        workpage_kind: "schedule-v0",
        workflow_run_id: "wr-weekly-001",
        artifact_version_id: "av-schedule-artifact-001",
        subject: null
      }
    });
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
