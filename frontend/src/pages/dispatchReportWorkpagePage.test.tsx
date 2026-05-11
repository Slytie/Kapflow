import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
  }) as {
    workpage: {
      sections: Array<{ kind?: string; entries?: Array<{ label: string; value: string }> }>;
    };
  } & Record<string, unknown>;
  const history = payload.workpage.sections.find((section) => section.kind === "history_stub") as {
    entries: Array<{ label: string; value: string }>;
  };
  history.entries = [
    { label: "Current artifact version", value: artifactVersionId },
    { label: "Supersedes", value: "Initial draft" },
    { label: "Latest draft in chain", value: artifactVersionId }
  ];
  return payload;
}

describe("DispatchReportWorkpagePage", () => {
  it(
    "renders the canonical landing as a read-only preview and creates an editable draft route",
    async () => {
      const user = userEvent.setup();
      window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
      render(<App />);

      const page = await screen.findByTestId("dispatch-report-workpage-page");
      expect(within(page).getByRole("heading", { name: "End-of-day report" })).toBeInTheDocument();
      const landingSummarySection = within(page).getByTestId("workpage-summary-section");
      expect(within(landingSummarySection).getByRole("heading", { name: "Daily summary" })).toBeInTheDocument();
      expect(
        within(landingSummarySection).getByTestId("workpage-summary-card-packages_dispatched")
      ).toHaveClass("workpage-summary-card");
      expect(screen.getByRole("button", { name: "Create editable draft" })).toBeInTheDocument();
      expect(screen.getByRole("textbox", { name: /Working devices \/ rabbits/i })).toBeDisabled();
      expect(screen.getByRole("textbox", { name: /Dispatcher comment/i })).toBeDisabled();
      expect(within(page).queryByRole("heading", { name: "Source grounding" })).not.toBeInTheDocument();
      expect(within(page).queryByRole("heading", { name: "Formula-integrity warning" })).not.toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: /Open info for End-of-day report/i }));
      const landingInfoDialog = await screen.findByRole("dialog", { name: "Dispatch reporting context" });
      expect(within(landingInfoDialog).getByRole("heading", { name: "Source grounding" })).toBeInTheDocument();
      expect(within(landingInfoDialog).getByRole("heading", { name: "Import status" })).toBeInTheDocument();
      expect(
        within(landingInfoDialog).getAllByText(
          /Workflow-run-backed dispatch-reporting landing with latest-draft resolution over a canonical reporting run/i
        )
      ).not.toHaveLength(0);
      await user.click(screen.getByRole("button", { name: /Close Dispatch reporting context/i }));

      await user.click(screen.getByRole("button", { name: "Create editable draft" }));

      const artifactPage = await screen.findByTestId("dispatch-report-artifact-workpage-page");
      const artifactTitleBar = artifactPage.querySelector(".workpage-page__hero-title-bar");
      const artifactHeroActions = artifactPage.querySelector(".workpage-page__hero-actions");
      const draftHistoryRail = within(artifactPage).getByTestId("dispatch-report-draft-history-rail");
      expect(artifactTitleBar).not.toBeNull();
      expect(artifactTitleBar).toHaveClass("workpage-page__hero-title-bar--sticky");
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Submit draft" })
      ).toBeInTheDocument();
      expect(
        within(artifactTitleBar as HTMLElement).getByRole("button", { name: "Download workbook" })
      ).toBeInTheDocument();
      expect(artifactHeroActions).not.toBeNull();
      expect(
        within(artifactHeroActions as HTMLElement).getByRole("link", { name: "Back to query landing" })
      ).toBeInTheDocument();
      expect(
        within(artifactHeroActions as HTMLElement).queryByRole("button", { name: "Download workbook" })
      ).not.toBeInTheDocument();
      expect(draftHistoryRail.closest("aside")).toHaveClass("workpage-page__artifact-rail");
      expect(within(draftHistoryRail).getByRole("heading", { name: "Recent draft versions" })).toBeInTheDocument();
      expect(within(artifactPage).queryByRole("heading", { name: "Artifact lineage" })).not.toBeInTheDocument();
      expect(within(artifactPage).queryByRole("heading", { name: "Draft actions" })).not.toBeInTheDocument();
      expect(artifactPage).toBeInTheDocument();
      const artifactSummarySection = within(artifactPage).getByTestId("workpage-summary-section");
      expect(within(artifactSummarySection).getByRole("heading", { name: "Daily summary" })).toBeInTheDocument();
      expect(
        within(artifactSummarySection).getByTestId("workpage-summary-card-delivered_pct")
      ).toHaveClass("workpage-summary-card");
      expect(window.location.pathname).toBe(
        "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
      );
      expect(within(artifactPage).queryByRole("heading", { name: "Source grounding" })).not.toBeInTheDocument();
      expect(within(artifactPage).queryByRole("heading", { name: "Artifact-backed projection note" })).not.toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: /Open info for End-of-day report/i }));
      const draftInfoDialog = await screen.findByRole("dialog", { name: "EOD draft context" });
      expect(within(draftInfoDialog).getByText("artifact_projection")).toBeInTheDocument();
      expect(within(draftInfoDialog).getByRole("heading", { name: "Artifact-backed projection note" })).toBeInTheDocument();
      expect(within(draftInfoDialog).getAllByText("reporting.upd_draft.workbook")).not.toHaveLength(0);
    },
    15000
  );

  it("keeps artifact-backed local edits across refresh when the same artifact version is re-fetched", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
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

    await user.click(screen.getByRole("button", { name: /Open info for End-of-day report/i }));
    const infoDialog = await screen.findByRole("dialog", { name: "EOD draft context" });
    await user.click(within(infoDialog).getByRole("button", { name: "Refresh" }));
    await user.click(screen.getByRole("button", { name: /Close EOD draft context/i }));

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
    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
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
        "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-002"
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
    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Create editable draft" }));
    await screen.findByTestId("dispatch-report-artifact-workpage-page");
    await user.click(screen.getByRole("button", { name: "Submit draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-002"
      );
    });

    const historyPanel = await screen.findByTestId("dispatch-report-draft-history-rail");
    expect(within(historyPanel as HTMLElement).getByText("Current draft")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Previous draft")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Current")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Latest")).toBeInTheDocument();
    expect(within(historyPanel as HTMLElement).getByText("Superseded")).toBeInTheDocument();

    await user.click(within(historyPanel as HTMLElement).getByRole("link", { name: /Previous draft/i }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
      );
    });
    expect(await screen.findByRole("heading", { name: "Latest draft available" })).toBeInTheDocument();
  });

  it("shows conflict reopen UX and preserves local edits until the operator navigates", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId/submit",
        ({ params }) =>
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
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/av-eod-artifact-latest",
        () =>
        HttpResponse.json(buildArtifactPayload("av-eod-artifact-latest"))
      )
    );

    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
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

  it("renders the canonical artifact-backed route directly under the logistics shell", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/av-direct-001", () =>
        HttpResponse.json(buildArtifactPayload("av-direct-001"))
      )
    );

    window.history.pushState(
      {},
      "",
      "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-direct-001"
    );
    render(<App />);

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(screen.queryByText("Secondary detail routes")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open secondary detail routes" }));
    const shellInfoDialog = await screen.findByRole("dialog", { name: "Secondary detail routes" });
    expect(within(shellInfoDialog).getByRole("link", { name: "Run Details" })).toHaveAttribute(
      "href",
      "/runs"
    );
    expect(window.location.pathname).toBe(
      "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-direct-001"
    );
  });

  it("completes the dispatch closeout flow inside the upload route activity modal", async () => {
    const user = userEvent.setup();
    const intakeEnsureBodies: Array<Record<string, unknown>> = [];
    const intakeUploadBodies: Array<Record<string, unknown>> = [];
    let intakeClaimed = false;
    let intakeWorkbookUploaded = false;
    let intakeCompleted = false;
    let reviewClaimed = false;
    let reviewIsConfirmed = false;
    let reviewCompleted = false;
    let approvalRequested = false;
    let approvalResponded = false;
    let approvalResponseKind: string | null = null;
    let currentDraftArtifactId: string | null = null;
    let draftSequence = 0;
    let submittedDraftCount = 0;

    function nextDraftArtifactId(): string {
      draftSequence += 1;
      return `av-closeout-draft-${String(draftSequence).padStart(3, "0")}`;
    }

    function runPayload(): Record<string, any> {
      const payload = structuredClone(eodRunWorkpageStateSnapshot.workpage_state) as Record<
        string,
        any
      >;
      payload.run_context.workflow_run_id = "wr-reporting-001";
      payload.run_context.activation_key = "snapshot:wr-reporting-001:dispatch-reporting";
      payload.source.source_refs = currentDraftArtifactId
        ? [
            "/api/v1/artifacts/av-reporting-eos-001",
            "/api/v1/artifacts/av-reporting-actuals-001",
            `/api/v1/artifacts/${currentDraftArtifactId}`
          ]
        : ["/api/v1/artifacts/av-reporting-eos-001"];
      payload.freshness.source_version = currentDraftArtifactId ?? "run:wr-reporting-001";
      payload.draft_resolution.state = currentDraftArtifactId ? "latest_draft_available" : "no_draft";
      payload.draft_resolution.latest_artifact_version_id = currentDraftArtifactId;
      payload.draft_resolution.artifact_route = currentDraftArtifactId
        ? `/runs/wr-reporting-001/workpages/eod-v0/artifacts/${currentDraftArtifactId}`
        : null;
      payload.draft_resolution.open_action_ref = currentDraftArtifactId
        ? {
            action_id: "workpage.eod-v0.open_latest_draft",
            workpage_kind: "eod-v0",
            workflow_run_id: "wr-reporting-001",
            artifact_version_id: currentDraftArtifactId,
            subject: null
          }
        : null;
      return payload;
    }

    function intakeTaskRow() {
      return {
        human_task_id: "ht-stage01-closeout",
        workflow_run_id: "wr-reporting-001",
        task_run_id: "tr-stage01-closeout",
        task_kind: "eos_input_intake",
        state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "CLAIMED" : "OPEN",
        candidate_roles: ["dispatch_supervisor"],
        owner_role: "dispatch_supervisor",
        assignee_actor_id:
          intakeClaimed || intakeCompleted ? "human:frontend-operator" : null,
        assignee_actor_type: intakeClaimed || intakeCompleted ? "human" : null,
        due_at: null,
        escalation_at: null,
        lease_version: intakeClaimed || intakeCompleted ? 1 : 0,
        claimed_at: intakeClaimed || intakeCompleted ? "2026-03-25T08:30:00Z" : null,
        claimed_until: null,
        linked_approval_id: null,
        reopen_count: 0,
        generation: 0,
        created_at: "2026-03-25T08:00:00Z",
        updated_at: "2026-03-25T08:30:00Z",
        task_run_state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "IN_PROGRESS" : "READY",
        stage_id: "Stage01",
        blocked_on_kind: null,
        blocked_on_ref: null,
        spawned_from_flag_id: null,
        can_confirm_review: false,
        missing_required_inputs: intakeWorkbookUploaded ? [] : ["reporting.eos_raw.workbook"],
        required_uploads: [
          {
            dataset_key: "reporting.eos_raw.workbook",
            template_id: null,
            artifact_kind: "reporting.eos_raw.workbook",
            artifact_role: "official_input",
            required: true,
            required_count: 1,
            current_count: intakeWorkbookUploaded ? 1 : 0,
            status: intakeWorkbookUploaded ? "satisfied" : "missing"
          }
        ],
        required_reviews: []
      };
    }

    function reviewTaskRow() {
      return {
        human_task_id: "ht-stage04-closeout",
        workflow_run_id: "wr-reporting-001",
        task_run_id: "tr-stage04-closeout",
        task_kind: "final_packet_review",
        state: reviewCompleted ? "COMPLETED" : reviewClaimed ? "CLAIMED" : "OPEN",
        candidate_roles: ["dispatch_supervisor"],
        owner_role: "dispatch_supervisor",
        assignee_actor_id:
          reviewClaimed || reviewCompleted ? "human:frontend-operator" : null,
        assignee_actor_type: reviewClaimed || reviewCompleted ? "human" : null,
        due_at: null,
        escalation_at: null,
        lease_version: reviewClaimed || reviewCompleted ? 1 : 0,
        claimed_at: reviewClaimed || reviewCompleted ? "2026-03-25T09:00:00Z" : null,
        claimed_until: null,
        linked_approval_id: approvalRequested && !approvalResponded ? "ap-stage04-closeout" : null,
        reopen_count: 0,
        generation: 0,
        created_at: "2026-03-25T08:45:00Z",
        updated_at: "2026-03-25T09:05:00Z",
        task_run_state: reviewCompleted ? "COMPLETED" : reviewClaimed ? "IN_PROGRESS" : "READY",
        stage_id: "Stage04",
        blocked_on_kind: null,
        blocked_on_ref: null,
        spawned_from_flag_id: null,
        can_confirm_review: !reviewCompleted && !reviewIsConfirmed,
        missing_required_inputs: [],
        required_uploads: [],
        required_reviews: [
          {
            dataset_key: "reporting.upd_draft.workbook",
            artifact_kind: "reporting.upd_draft.workbook",
            required_count: 1,
            reviewed_artifact_version_id: reviewIsConfirmed ? currentDraftArtifactId : null,
            review_confirmation_artifact_version_id: reviewIsConfirmed
              ? "av-review-confirmation-001"
              : null,
            status: reviewIsConfirmed ? "confirmed" : "pending"
          }
        ]
      };
    }

    function pendingApprovalRow() {
      return {
        approval_id: "ap-stage04-closeout",
        workflow_run_id: "wr-reporting-001",
        task_run_id: "tr-stage04-closeout",
        approval_kind: "confirm_dispatch_reporting_packet",
        scope_kind: "stage",
        scope_ref: "Stage04",
        state: approvalResponded ? "RESPONDED" : "PENDING",
        requested_by_task_run_id: "tr-stage04-closeout",
        candidate_roles: ["operations_manager"],
        required_role: "operations_manager",
        requested_at: "2026-03-25T09:10:00Z",
        responded_at: approvalResponded ? "2026-03-25T09:12:00Z" : null,
        response_kind: approvalResponseKind,
        response_reason: null,
        decided_by_actor_id: approvalResponded ? "human:frontend-operator" : null,
        decided_by_actor_type: approvalResponded ? "human" : null,
        generation: approvalResponded ? 1 : 0,
        created_at: "2026-03-25T09:10:00Z",
        updated_at: "2026-03-25T09:12:00Z"
      };
    }

    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0", () =>
        HttpResponse.json(runPayload())
      ),
      http.post("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/intake-task", async ({ request }) => {
        intakeEnsureBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({
          status: "ok",
          command: "api.workpages.eod_intake.ensure",
          intake_task: {
            workflow_run_id: "wr-reporting-001",
            task_run_id: "tr-stage01-closeout",
            human_task_id: "ht-stage01-closeout",
            stage_id: "Stage01",
            task_kind: "eos_input_intake",
            task_run_state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "IN_PROGRESS" : "READY",
            human_task_state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "CLAIMED" : "OPEN",
            activation_key: "workpage:dispatch-reporting:SD-2026-03-24:stage01:eos_input_intake",
            generation: 0,
            created: false,
            service_date: "2026-03-24",
            target_workflow_run_id: "wr-reporting-001",
            target_route: "/runs/wr-reporting-001/workpages/eod-v0",
            created_workflow_run: false
          }
        });
      }),
      http.get("*/api/v1/human-tasks", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.list",
          human_tasks: [
            intakeTaskRow(),
            ...(intakeCompleted ? [reviewTaskRow()] : [])
          ]
        })
      ),
      http.get("*/api/v1/human-tasks/:humanTaskId", ({ params }) =>
        HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.get",
          human_task:
            String(params.humanTaskId) === "ht-stage04-closeout" ? reviewTaskRow() : intakeTaskRow()
        })
      ),
      http.post("*/api/v1/human-tasks/:humanTaskId/claim", ({ params }) => {
        if (String(params.humanTaskId) === "ht-stage01-closeout") {
          intakeClaimed = true;
        }
        if (String(params.humanTaskId) === "ht-stage04-closeout") {
          reviewClaimed = true;
        }
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.claim",
          result: { ok: true }
        });
      }),
      http.post("*/api/v1/human-tasks/:humanTaskId/artifacts/upload", async ({ params, request }) => {
        if (String(params.humanTaskId) === "ht-stage01-closeout") {
          intakeWorkbookUploaded = true;
          intakeUploadBodies.push((await request.json()) as Record<string, unknown>);
        }
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.artifacts.upload",
          artifact_version: {
            artifact_version_id: "av-upload-closeout",
            workflow_run_id: "wr-reporting-001",
            task_run_id: "tr-stage01-closeout",
            artifact_kind: "reporting.eos_raw.workbook",
            artifact_role: "official_input",
            media_type: "application/octet-stream",
            storage_uri: "memory://upload",
            content_digest: "sha256:test",
            byte_size: 12,
            metadata_json: { file_name: "uploaded.bin" },
            parent_artifact_version_id: null,
            supersedes_artifact_version_id: null,
            lineage_note: null,
            created_at: "2026-03-25T08:31:00Z"
          }
        });
      }),
      http.post("*/api/v1/human-tasks/:humanTaskId/complete", ({ params }) => {
        if (String(params.humanTaskId) === "ht-stage01-closeout") {
          intakeCompleted = true;
          currentDraftArtifactId = nextDraftArtifactId();
        }
        if (String(params.humanTaskId) === "ht-stage04-closeout") {
          reviewCompleted = true;
          approvalRequested = true;
        }
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.complete",
          result: { ok: true }
        });
      }),
      http.post("*/api/v1/human-tasks/:humanTaskId/confirm-review", () => {
        reviewIsConfirmed = true;
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.confirm_review",
          result: { artifact_version: "av-review-confirmation-001", idempotent_replay: false }
        });
      }),
      http.get("*/api/v1/approvals", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.approvals.list",
          approvals: approvalRequested && !approvalResponded ? [pendingApprovalRow()] : []
        })
      ),
      http.post("*/api/v1/approvals/:approvalId/respond", async ({ request }) => {
        const body = (await request.json()) as { response_kind?: string };
        approvalResponded = true;
        approvalResponseKind = body.response_kind ?? "approve";
        return HttpResponse.json({
          status: "ok",
          command: "api.approvals.respond",
          approval: pendingApprovalRow()
        });
      }),
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId",
        ({ params }) =>
          HttpResponse.json(
            buildArtifactPayload(String(params.artifactVersionId), "wr-reporting-001")
          )
      ),
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId/submit",
        ({ params }) => {
          submittedDraftCount += 1;
          currentDraftArtifactId = nextDraftArtifactId();
          return HttpResponse.json({
            status: "ok",
            command: "api.workpages.artifact.submit",
            submitted: {
              workflow_run_id: "wr-reporting-001",
              artifact_version_id: currentDraftArtifactId,
              supersedes_artifact_version_id: String(params.artifactVersionId),
              route: `/runs/wr-reporting-001/workpages/eod-v0/artifacts/${currentDraftArtifactId}`
            }
          });
        }
      )
    );

    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
    render(<App />);

    await screen.findByTestId("dispatch-report-workpage-page");
    await user.click(screen.getByRole("button", { name: "Upload route activity" }));

    const dialog = await screen.findByRole("dialog", { name: "Upload route activity" });
    await user.upload(
      within(dialog).getByLabelText("Route-activity workbook"),
      new File(["route-activity"], "2026-03-24.xlsx", {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      })
    );
    expect(within(dialog).getByLabelText("Service date")).toHaveValue("2026-03-24");
    await user.click(within(dialog).getByRole("button", { name: "Import route activity" }));

    expect(
      await within(dialog).findByTestId("dispatch-report-quick-edit-editor")
    ).toBeInTheDocument();
    expect(within(dialog).getByTestId("dispatch-closeout-latest-draft")).toHaveTextContent(
      "av-closeout-draft-001"
    );
    expect(within(dialog).queryByLabelText("Manager review file")).not.toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Submit draft" }));
    await waitFor(() => {
      expect(submittedDraftCount).toBe(1);
    });

    await user.click(within(dialog).getByRole("button", { name: "Confirm latest draft review" }));
    await user.click(within(dialog).getByRole("button", { name: "Complete review task" }));

    await waitFor(() => {
      expect(
        within(dialog).getByRole("button", { name: "Approve final packet" })
      ).toBeEnabled();
    });
    await user.click(within(dialog).getByRole("button", { name: "Approve final packet" }));

    expect(await within(dialog).findByRole("heading", { name: "Closeout updated" })).toBeInTheDocument();
    expect(within(dialog).getByText(/planning handoff has been requested/i)).toBeInTheDocument();
    expect(approvalResponseKind).toBe("approve");
    expect(window.location.pathname).toBe("/runs/wr-reporting-001/workpages/eod-v0");
    expect(intakeEnsureBodies[0]?.service_date).toBe("2026-03-24");
    expect(
      (intakeUploadBodies[0]?.metadata_json as Record<string, unknown> | undefined)?.service_date
    ).toBe("2026-03-24");
  });

  it("switches the closeout flow onto the selected reporting date run after import", async () => {
    const user = userEvent.setup();
    const intakeEnsureBodies: Array<Record<string, unknown>> = [];
    const intakeUploadBodies: Array<Record<string, unknown>> = [];
    let intakeClaimed = false;
    let intakeWorkbookUploaded = false;
    let intakeCompleted = false;
    let targetDraftArtifactId: string | null = null;

    function runPayload(input: {
      workflowRunId: string;
      logicalDate: string;
      draftArtifactVersionId?: string | null;
    }): Record<string, any> {
      const payload = structuredClone(eodRunWorkpageStateSnapshot.workpage_state) as Record<
        string,
        any
      >;
      payload.run_context.workflow_run_id = input.workflowRunId;
      payload.run_context.logical_date = input.logicalDate;
      payload.run_context.partition_key = `SD-${input.logicalDate}`;
      payload.run_context.activation_key = `snapshot:${input.workflowRunId}:dispatch-reporting`;
      payload.source.source_refs = input.draftArtifactVersionId
        ? [
            "/api/v1/artifacts/av-reporting-eos-001",
            "/api/v1/artifacts/av-reporting-actuals-001",
            `/api/v1/artifacts/${input.draftArtifactVersionId}`
          ]
        : ["/api/v1/artifacts/av-reporting-eos-001"];
      payload.freshness.source_version =
        input.draftArtifactVersionId ?? `run:${input.workflowRunId}`;
      payload.draft_resolution.state = input.draftArtifactVersionId
        ? "latest_draft_available"
        : "no_draft";
      payload.draft_resolution.latest_artifact_version_id = input.draftArtifactVersionId ?? null;
      payload.draft_resolution.artifact_route = input.draftArtifactVersionId
        ? `/runs/${input.workflowRunId}/workpages/eod-v0/artifacts/${input.draftArtifactVersionId}`
        : null;
      payload.draft_resolution.open_action_ref = input.draftArtifactVersionId
        ? {
            action_id: "workpage.eod-v0.open_latest_draft",
            workpage_kind: "eod-v0",
            workflow_run_id: input.workflowRunId,
            artifact_version_id: input.draftArtifactVersionId,
            subject: null
          }
        : null;
      return payload;
    }

    function intakeTaskRow(workflowRunId: string) {
      return {
        human_task_id: "ht-stage01-closeout-target",
        workflow_run_id: workflowRunId,
        task_run_id: "tr-stage01-closeout-target",
        task_kind: "eos_input_intake",
        state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "CLAIMED" : "OPEN",
        candidate_roles: ["dispatch_supervisor"],
        owner_role: "dispatch_supervisor",
        assignee_actor_id:
          intakeClaimed || intakeCompleted ? "human:frontend-operator" : null,
        assignee_actor_type: intakeClaimed || intakeCompleted ? "human" : null,
        due_at: null,
        escalation_at: null,
        lease_version: intakeClaimed || intakeCompleted ? 1 : 0,
        claimed_at: intakeClaimed || intakeCompleted ? "2026-03-25T08:30:00Z" : null,
        claimed_until: null,
        linked_approval_id: null,
        reopen_count: 0,
        generation: 0,
        created_at: "2026-03-25T08:00:00Z",
        updated_at: "2026-03-25T08:30:00Z",
        task_run_state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "IN_PROGRESS" : "READY",
        stage_id: "Stage01",
        blocked_on_kind: null,
        blocked_on_ref: null,
        spawned_from_flag_id: null,
        can_confirm_review: false,
        missing_required_inputs: intakeWorkbookUploaded ? [] : ["reporting.eos_raw.workbook"],
        required_uploads: [
          {
            dataset_key: "reporting.eos_raw.workbook",
            template_id: null,
            artifact_kind: "reporting.eos_raw.workbook",
            artifact_role: "official_input",
            required: true,
            required_count: 1,
            current_count: intakeWorkbookUploaded ? 1 : 0,
            status: intakeWorkbookUploaded ? "satisfied" : "missing"
          }
        ],
        required_reviews: []
      };
    }

    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0", ({ params }) =>
        HttpResponse.json(
          String(params.workflowRunId) === "wr-reporting-002"
            ? runPayload({
                workflowRunId: "wr-reporting-002",
                logicalDate: "2026-03-25",
                draftArtifactVersionId: targetDraftArtifactId
              })
            : runPayload({
                workflowRunId: "wr-reporting-001",
                logicalDate: "2026-03-24"
              })
        )
      ),
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/intake-task",
        async ({ request }) => {
          intakeEnsureBodies.push((await request.json()) as Record<string, unknown>);
          return HttpResponse.json({
            status: "ok",
            command: "api.workpages.eod_intake.ensure",
            intake_task: {
              workflow_run_id: "wr-reporting-002",
              task_run_id: "tr-stage01-closeout-target",
              human_task_id: "ht-stage01-closeout-target",
              stage_id: "Stage01",
              task_kind: "eos_input_intake",
              task_run_state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "IN_PROGRESS" : "READY",
              human_task_state: intakeCompleted ? "COMPLETED" : intakeClaimed ? "CLAIMED" : "OPEN",
              activation_key: "workpage:dispatch-reporting:SD-2026-03-25:stage01:eos_input_intake",
              generation: 0,
              created: true,
              service_date: "2026-03-25",
              target_workflow_run_id: "wr-reporting-002",
              target_route: "/runs/wr-reporting-002/workpages/eod-v0",
              created_workflow_run: true
            }
          });
        }
      ),
      http.get("*/api/v1/human-tasks", ({ request }) => {
        const url = new URL(request.url);
        const requestedRunId = url.searchParams.get("workflow_run_id");
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.list",
          human_tasks:
            requestedRunId === "wr-reporting-002"
              ? [intakeTaskRow("wr-reporting-002")]
              : []
        });
      }),
      http.get("*/api/v1/human-tasks/:humanTaskId", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.get",
          human_task: intakeTaskRow("wr-reporting-002")
        })
      ),
      http.post("*/api/v1/human-tasks/:humanTaskId/claim", () => {
        intakeClaimed = true;
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.claim",
          result: { ok: true }
        });
      }),
      http.post("*/api/v1/human-tasks/:humanTaskId/artifacts/upload", async ({ request }) => {
        intakeWorkbookUploaded = true;
        intakeUploadBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.artifacts.upload",
          artifact_version: {
            artifact_version_id: "av-upload-closeout-target",
            workflow_run_id: "wr-reporting-002",
            task_run_id: "tr-stage01-closeout-target",
            artifact_kind: "reporting.eos_raw.workbook",
            artifact_role: "official_input",
            media_type: "application/octet-stream",
            storage_uri: "memory://upload",
            content_digest: "sha256:test",
            byte_size: 12,
            metadata_json: { file_name: "uploaded.bin" },
            parent_artifact_version_id: null,
            supersedes_artifact_version_id: null,
            lineage_note: null,
            created_at: "2026-03-25T08:31:00Z"
          }
        });
      }),
      http.post("*/api/v1/human-tasks/:humanTaskId/complete", () => {
        intakeCompleted = true;
        targetDraftArtifactId = "av-closeout-draft-025";
        return HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.complete",
          result: { ok: true }
        });
      }),
      http.get("*/api/v1/approvals", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.approvals.list",
          approvals: []
        })
      ),
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId",
        ({ params }) =>
          HttpResponse.json(
            buildArtifactPayload(String(params.artifactVersionId), String(params.workflowRunId))
          )
      )
    );

    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
    render(<App />);

    await screen.findByTestId("dispatch-report-workpage-page");
    await user.click(screen.getByRole("button", { name: "Upload route activity" }));

    const dialog = await screen.findByRole("dialog", { name: "Upload route activity" });
    await user.upload(
      within(dialog).getByLabelText("Route-activity workbook"),
      new File(["route-activity"], "2026-03-24.xlsx", {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      })
    );
    expect(within(dialog).getByLabelText("Service date")).toHaveValue("2026-03-24");

    const serviceDateInput = within(dialog).getByLabelText("Service date");
    fireEvent.change(serviceDateInput, { target: { value: "2026-03-25" } });
    expect(serviceDateInput).toHaveValue("2026-03-25");

    expect(
      within(dialog).getByText(
        "The selected service date will be used instead of the workbook file name date."
      )
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Import will continue on the reporting run for/i)
    ).toHaveTextContent("2026-03-25");

    await user.click(within(dialog).getByRole("button", { name: "Import route activity" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/runs/wr-reporting-002/workpages/eod-v0");
    });
    const targetRunDialog = await screen.findByRole("dialog", { name: "Upload route activity" });
    expect(
      await within(targetRunDialog).findByTestId("dispatch-report-quick-edit-editor")
    ).toBeInTheDocument();
    expect(
      within(targetRunDialog).getByTestId("dispatch-closeout-latest-draft")
    ).toHaveTextContent("av-closeout-draft-025");
    expect(intakeEnsureBodies[0]?.service_date).toBe("2026-03-25");
    expect(
      (intakeUploadBodies[0]?.metadata_json as Record<string, unknown> | undefined)?.service_date
    ).toBe("2026-03-25");
  });

  it("submits canonical artifact drafts with carried workspace subject context and refresh invalidation", async () => {
    const user = userEvent.setup();
    const submitBodies: Array<Record<string, unknown>> = [];
    const invalidateSpy = vi.spyOn(QueryClient.prototype, "invalidateQueries");
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/av-eod-artifact-001", () =>
        HttpResponse.json(buildArtifactPayload("av-eod-artifact-001"))
      ),
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId/submit",
        async ({ params, request }) => {
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
        }
      ),
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/av-eod-artifact-010", () =>
        HttpResponse.json(buildArtifactPayload("av-eod-artifact-010"))
      )
    );

    window.history.pushState(
      {
        usr: {
          workpageActionRef: {
            action_id: "workpage.eod-v0.open_latest_draft",
            workpage_kind: "eod-v0",
            workflow_run_id: "wr-eod-artifact-001",
            artifact_version_id: "av-eod-artifact-001",
            subject: {
              subject_kind: "approval",
              subject_id: "ap-stage04-001"
            }
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
      action_ref: {
        action_id: "workpage.eod-v0.submit_draft",
        workpage_kind: "eod-v0",
        workflow_run_id: "wr-eod-artifact-001",
        artifact_version_id: "av-eod-artifact-001",
        subject: {
          subject_kind: "approval",
          subject_id: "ap-stage04-001"
        }
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
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/av-run-latest-001", () =>
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
