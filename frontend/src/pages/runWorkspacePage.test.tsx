import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import { App } from "@/app/App";
import type {
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceApprovalWorkItem,
  WorkflowWorkspaceTaskWorkItem,
  WorkflowWorkspaceWorkpageAction
} from "@/lib/types/contracts";
import { RunWorkspacePage } from "@/pages/RunWorkspacePage";
import { mutationLog } from "@/test/api/handlers";
import {
  buildWorkflowRunWorkspace,
  createContractState
} from "@/test/api/contractState";
import { server } from "@/test/api/server";
import { renderRoute } from "@/test/renderRoute";
import { buildEodArtifactWorkpageState } from "@/test/workpages/eodArtifactFixture";

function buildWorkspaceWithTaskWorkpageAction(
  action: WorkflowWorkspaceWorkpageAction
): WorkflowRunWorkspaceContract {
  const workspace = buildWorkflowRunWorkspace(createContractState(), "wr-test-001");
  const applyAction = (item: WorkflowRunWorkspaceContract["user_work"][number]) =>
    item.item_kind === "human_task" && item.human_task.human_task_id === "ht-claimed-002"
      ? ({
          ...item,
          workpage_actions: [action]
        } satisfies WorkflowWorkspaceTaskWorkItem)
      : item;
  return {
    ...workspace,
    user_work: workspace.user_work.map(applyAction),
    blocking_work: workspace.blocking_work.map(applyAction)
  };
}

function buildWorkspaceWithApprovalWorkpageAction(
  action: WorkflowWorkspaceWorkpageAction
): WorkflowRunWorkspaceContract {
  const workspace = buildWorkflowRunWorkspace(createContractState(), "wr-test-001");
  const applyAction = (item: WorkflowRunWorkspaceContract["user_work"][number]) =>
    item.item_kind === "approval" && item.approval.approval_id === "ap-pending-001"
      ? ({
          ...item,
          workpage_actions: [action]
        } satisfies WorkflowWorkspaceApprovalWorkItem)
      : item;
  return {
    ...workspace,
    user_work: workspace.user_work.map(applyAction),
    blocking_work: workspace.blocking_work.map(applyAction)
  };
}

async function findWorkspaceCard(title: string): Promise<HTMLElement> {
  const card = (await screen.findByRole("heading", { name: title })).closest("article");
  expect(card).not.toBeNull();
  return card as HTMLElement;
}

async function openWorkspaceCardMenu(
  _user: ReturnType<typeof userEvent.setup>,
  title: string
): Promise<HTMLElement> {
  return findWorkspaceCard(title);
}

async function openTaskModalFromWorkspaceCard(
  user: ReturnType<typeof userEvent.setup>,
  title: string
): Promise<{ card: HTMLElement; modal: HTMLElement }> {
  const card = await findWorkspaceCard(title);
  await user.click(within(card).getByRole("button", { name: "Details" }));
  const modal = await screen.findByRole("dialog");
  return { card, modal };
}

function renderWorkspaceApp(): void {
  window.history.pushState({}, "", "/runs/wr-test-001/workspace");
  render(<App />);
}

describe("RunWorkspacePage", () => {
  it("renders graph block and swimlanes on the same page", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const workspacePage = await screen.findByTestId("run-workspace-page");
    expect(within(workspacePage).getByTestId("workflow-graph")).toBeInTheDocument();
    expect(within(workspacePage).getByTestId("workspace-swimlanes")).toBeInTheDocument();
  });

  it("removes non-design headings", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(await screen.findByTestId("workflow-graph")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Run Workspace" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Live Workflow Graph" })).not.toBeInTheDocument();
  });

  it("renders graph node status classes from the workspace projection", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const completedNode = await screen.findByTestId("workflow-graph-node-stage03");
    const activeNode = await screen.findByTestId("workflow-graph-node-stage06");
    const blockingNode = await screen.findByTestId("workflow-graph-node-stage06_info_loop");

    expect(completedNode).toHaveClass("workflow-graph-pill--completed");
    expect(activeNode).toHaveClass("workflow-graph-pill--active");
    expect(blockingNode).toHaveClass("workflow-graph-pill--warning");
    expect(blockingNode).toHaveClass("is-blocking");
  });

  it("shows who claimed or can claim the latest task on graph nodes", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const claimedNode = await screen.findByTestId("workflow-graph-node-stage06");
    const claimableNode = await screen.findByTestId("workflow-graph-node-stage06_info_loop");

    expect(within(claimedNode).getByText(/Claimed by Frontend Operator/i)).toBeInTheDocument();
    expect(within(claimableNode).getByText(/Can claim: Dispatch Supervisor/i)).toBeInTheDocument();
  });

  it("opens the information sidebar when a workflow graph task is clicked", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/runs/wr-test-001/workspace");
    render(<App />);

    const node = await screen.findByTestId("workflow-graph-node-stage06");
    await user.click(node);

    expect(await screen.findByRole("heading", { name: "Stage06 Supervisor Review" })).toBeInTheDocument();
    expect(
      screen.getByText("Graph node status is projected by the server workspace endpoint.")
    ).toBeInTheDocument();
  });

  it("shows historical stage artifacts for previously completed work from graph nodes", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/runs/wr-test-001/workspace");
    render(<App />);

    const node = await screen.findByTestId("workflow-graph-node-stage07");
    await user.click(node);

    const drawer = await screen.findByLabelText("Details drawer");
    expect(within(drawer).getByText(/Task Artifacts/i)).toBeInTheDocument();
    expect(within(drawer).getByText("schedule.replan_delta.workbook")).toBeInTheDocument();
  });

  it("includes stage official outputs from pointers when opening graph node details", async () => {
    const user = userEvent.setup();
    window.history.pushState({}, "", "/runs/wr-test-001/workspace");
    render(<App />);

    const node = await screen.findByTestId("workflow-graph-node-stage06");
    await user.click(node);

    const drawer = await screen.findByLabelText("Details drawer");
    expect(within(drawer).getByText(/Task Artifacts/i)).toBeInTheDocument();
    expect(within(drawer).getByText(/Stage official output/i)).toBeInTheDocument();
  });

  it("renders swimlane headers and expected counts", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(await screen.findByRole("heading", { name: "To Do" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "In Progress" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Review" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Done" })).toBeInTheDocument();

    expect(screen.getByTestId("workspace-lane-count-todo")).toHaveTextContent("1");
    expect(screen.getByTestId("workspace-lane-count-in_progress")).toHaveTextContent("1");
    expect(screen.getByTestId("workspace-lane-count-review")).toHaveTextContent("2");
    expect(screen.getByTestId("workspace-lane-count-done")).toHaveTextContent("2");
  });

  it("disables complete when required inputs are missing", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const taskHeading = await screen.findByRole("heading", { name: "Review Packet" });
    const taskCard = taskHeading.closest("article");
    expect(taskCard).not.toBeNull();

    expect(
      within(taskCard as HTMLElement)
        .getAllByRole("button", { name: "Complete" })
        .every((button) => (button as HTMLButtonElement).disabled)
    ).toBe(true);
    expect(within(taskCard as HTMLElement).getByText(/Missing required inputs/i)).toBeInTheDocument();
  });

  it("shows template download for required upload rows", async () => {
    const user = userEvent.setup();
    renderWorkspaceApp();

    const { modal } = await openTaskModalFromWorkspaceCard(user, "Review Packet");
    const requirementRow = within(modal)
      .getByText("Supervisor Review Packet")
      .closest(".task-modal__document-row");
    expect(requirementRow).not.toBeNull();
    const downloadTemplate = within(requirementRow as HTMLElement).getByRole("button", {
      name: "Download template"
    });
    expect(downloadTemplate).toBeEnabled();

    await user.click(downloadTemplate);
    await waitFor(() => {
      expect(mutationLog()).toContain(
        "template-download-bin:schedule.stage06.supervisor_review.doc.empty.v1"
      );
    });
  });

  it("upload changes requirement state after workspace refetch", async () => {
    const user = userEvent.setup();
    renderWorkspaceApp();

    const { modal } = await openTaskModalFromWorkspaceCard(user, "Review Packet");
    const requiredUploadRow = within(modal)
      .getByText("Supervisor Review Packet")
      .closest(".task-modal__document-row");
    expect(requiredUploadRow).not.toBeNull();
    expect(within(requiredUploadRow as HTMLElement).getByText("Missing")).toBeInTheDocument();
    expect(
      within(requiredUploadRow as HTMLElement).getByRole("button", { name: "Add File" })
    ).toBeInTheDocument();
    const fileInput = (requiredUploadRow as HTMLElement).querySelector("input[type='file']");
    expect(fileInput).not.toBeNull();
    const file = new File(["evidence"], "review-evidence.txt", { type: "text/plain" });
    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [file] } });

    await waitFor(() => {
      expect(mutationLog()).toContain("upload:human_task:ht-claimed-002");
    });

    await waitFor(() => {
      expect(within(modal).getByText("Satisfied")).toBeInTheDocument();
      expect(within(modal).getByRole("button", { name: "Replace" })).toBeInTheDocument();
      expect(within(modal).getByRole("button", { name: "Submit for Review" })).toBeEnabled();
    });

    await waitFor(() => {
      const card = screen.getByRole("heading", { name: "Review Packet" }).closest("article");
      expect(card).not.toBeNull();
      expect(within(card as HTMLElement).getByText("2 missing inputs")).toBeInTheDocument();
    }, { timeout: 2500 });
  });

  it("shows required review rows in the task modal and keeps confirm-review as the primary action", async () => {
    const user = userEvent.setup();
    renderWorkspaceApp();

    const { modal } = await openTaskModalFromWorkspaceCard(user, "Review Packet");
    expect(within(modal).getByRole("heading", { name: "Required Documents" })).toBeInTheDocument();
    expect(within(modal).getAllByRole("button", { name: "View" }).length).toBeGreaterThan(0);
    expect(
      within(modal).getAllByText("Review Required").length
    ).toBeGreaterThan(0);
    expect(within(modal).getByRole("button", { name: "Submit for Review" })).toBeEnabled();
  });

  it("renders unavailable projected workpage actions without replacing existing review actions", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.workspace",
          workspace: buildWorkspaceWithTaskWorkpageAction({
            action_id: "workpage.schedule-v0.open_latest_draft",
            workpage_kind: "schedule-v0",
            label: "Open schedule draft",
            presentation: "open_route",
            state: "unavailable",
            route: null,
            create_path: null,
            subject_context: {
              subject_kind: "human_task",
              subject_id: "ht-claimed-002",
              workflow_run_id: "wr-test-001"
            },
            link_policy: {
              create_relation_kind: null,
              submit_relation_kind: "response"
            },
            disabled_reason: "schedule_draft_unavailable"
          })
        })
      ),
      http.get("*/api/v1/workpages/artifacts/av-schedule-artifact-001", () =>
        HttpResponse.json(structuredClone(scheduleArtifactStateSnapshot.workpage_state))
      )
    );

    renderWorkspaceApp();

    const taskCard = await openWorkspaceCardMenu(user, "Review Packet");
    expect(
      within(taskCard).getByRole("button", { name: "Open schedule draft" })
    ).toBeDisabled();
    expect(within(taskCard).getByText("Schedule draft unavailable for this run yet")).toBeInTheDocument();

    const { modal } = await openTaskModalFromWorkspaceCard(user, "Review Packet");
    expect(within(modal).queryByRole("link", { name: "Open schedule draft" })).not.toBeInTheDocument();
    expect(within(modal).getByRole("button", { name: "Submit for Review" })).toBeEnabled();
  });

  it("navigates directly to projected open-route workpages from workspace task cards", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.workspace",
          workspace: buildWorkspaceWithTaskWorkpageAction({
            action_id: "workpage.schedule-v0.open_latest_draft",
            workpage_kind: "schedule-v0",
            label: "Open schedule draft",
            presentation: "open_route",
            state: "available",
            route: "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001",
            create_path: null,
            subject_context: {
              subject_kind: "human_task",
              subject_id: "ht-claimed-002",
              workflow_run_id: "wr-test-001"
            },
            link_policy: {
              create_relation_kind: null,
              submit_relation_kind: "response"
            },
            disabled_reason: null
          })
        })
      ),
      http.get("*/api/v1/workpages/artifacts/av-schedule-artifact-001", () =>
        HttpResponse.json(scheduleArtifactStateSnapshot.workpage_state)
      )
    );

    window.history.pushState({}, "", "/runs/wr-test-001/workspace");
    render(<App />);

    const taskCard = await openWorkspaceCardMenu(user, "Review Packet");
    await user.click(within(taskCard).getByRole("button", { name: "Open schedule draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
      );
    });
    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
  });

  it("creates projected workspace drafts through backend-provided create paths", async () => {
    const user = userEvent.setup();
    const requestBodies: Array<Record<string, unknown>> = [];
    server.use(
      http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.workspace",
          workspace: buildWorkspaceWithApprovalWorkpageAction({
            action_id: "workpage.eod-v0.create_draft",
            workpage_kind: "eod-v0",
            label: "Create EOD draft",
            presentation: "create_draft_then_open",
            state: "available",
            route: null,
            create_path: "/api/v1/workpages/workflow-runs/wr-eod-artifact-001/eod-v0/drafts",
            subject_context: {
              subject_kind: "approval",
              subject_id: "ap-pending-001",
              workflow_run_id: "wr-test-001"
            },
            link_policy: {
              create_relation_kind: "draft",
              submit_relation_kind: "response"
            },
            disabled_reason: null
          })
        })
      ),
      http.get("*/api/v1/workpages/artifacts/av-eod-artifact-001", () =>
        HttpResponse.json(
          buildEodArtifactWorkpageState({
            artifactVersionId: "av-eod-artifact-001",
            workflowRunId: "wr-eod-artifact-001"
          })
        )
      ),
      http.post("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/drafts", async ({ params, request }) => {
        requestBodies.push((await request.json()) as Record<string, unknown>);
        return HttpResponse.json({
          status: "ok",
          command: "api.workpages.eod_drafts.create",
          draft: {
            workflow_run_id: String(params.workflowRunId),
            artifact_version_id: "av-eod-artifact-001",
            route: `/runs/${String(params.workflowRunId)}/workpages/eod-v0/artifacts/av-eod-artifact-001`
          }
        });
      })
    );

    window.history.pushState({}, "", "/runs/wr-test-001/workspace");
    render(<App />);

    const approvalCard = await openWorkspaceCardMenu(user, "Stage07 Approval");
    await user.click(within(approvalCard).getByRole("button", { name: "Create EOD draft" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe(
        "/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
      );
    });
    expect(requestBodies).toHaveLength(1);
    expect(requestBodies[0]).toMatchObject({
      subject_link: {
        subject_kind: "approval",
        subject_id: "ap-pending-001"
      }
    });
  });

  it("confirm-review unblocks completion after workspace refetch", async () => {
    const user = userEvent.setup();
    renderWorkspaceApp();

    const { card, modal } = await openTaskModalFromWorkspaceCard(user, "Review Packet");
    const requiredUploadRow = within(modal)
      .getByText("Supervisor Review Packet")
      .closest(".task-modal__document-row");
    expect(requiredUploadRow).not.toBeNull();
    const uploadInput = (requiredUploadRow as HTMLElement).querySelector("input[type='file']");
    expect(uploadInput).not.toBeNull();
    fireEvent.change(uploadInput as HTMLInputElement, {
      target: { files: [new File(["evidence"], "review-response.txt", { type: "text/plain" })] }
    });

    await waitFor(() => {
      expect(mutationLog()).toContain("upload:human_task:ht-claimed-002");
    });

    await user.click(within(modal).getByRole("button", { name: "Submit for Review" }));

    await waitFor(() => {
      expect(mutationLog()).toContain("confirm-review:ht-claimed-002");
    });

    await waitFor(() => {
      expect(
        within(card)
          .getAllByRole("button", { name: "Complete" })
          .some((button) => !(button as HTMLButtonElement).disabled)
      ).toBe(true);
    });
    expect(within(modal).getByRole("button", { name: "Complete Task" })).toBeEnabled();
  });

  it("renders approval work and execute respond actions", async () => {
    const user = userEvent.setup();
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const approvalCard = await openWorkspaceCardMenu(user, "Stage07 Approval");
    await user.click(within(approvalCard).getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(mutationLog()).toContain("respond:ap-pending-001:approve");
    });
  });

  it("renders flag item with upload and download affordances", async () => {
    const user = userEvent.setup();
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const flagCard = await openWorkspaceCardMenu(user, "Courier C-104 did not report for shift");

    const uploadButton = within(flagCard).getByRole("button", { name: "Upload" });
    const downloadButton = within(flagCard).getByRole("button", { name: "Download" });
    expect(uploadButton).toBeEnabled();
    expect(downloadButton).toBeEnabled();

    await user.click(downloadButton);
  });

  it("loads through app route /runs/:workflowRunId/workspace", async () => {
    window.history.pushState({}, "", "/runs/wr-test-001/workspace");
    render(<App />);

    expect(await screen.findByTestId("run-workspace-page")).toBeInTheDocument();
  });

  it("opens logistics demo by default from app root route", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);

    expect(await screen.findByTestId("logistics-demo-page")).toBeInTheDocument();
  });

  it("shows loading, error, and empty states", async () => {
    server.use(
      http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", async () => {
        await new Promise((resolve) => setTimeout(resolve, 40));
        return HttpResponse.json(
          {
            status: "error",
            error: {
              code: "projection_unavailable",
              message: "workspace projection unavailable",
              details: {}
            }
          },
          { status: 503 }
        );
      })
    );

    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(screen.getByText(/Loading run workspace/i)).toBeInTheDocument();
    expect(await screen.findByText(/Run workspace failed to load/i)).toBeInTheDocument();
  });

  it("shows empty state when workspace projection has no graph or work rows", async () => {
    server.use(
      http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.workspace",
          workspace: {
            workflow_run: {
              workflow_run_id: "wr-test-001",
              workflow_id: "schedule_planning.v1",
              workflow_version: "v1",
              tenant_id: "tenant-a",
              domain_id: "domain-x",
              partition_key: "SD-2026-03-07",
              logical_date: "2026-03-07",
              activation_key: "stage06",
              state: "OPEN",
              active_issue_count: 0,
              created_at: "2026-03-04T10:00:00Z",
              updated_at: "2026-03-04T10:00:00Z"
            },
            graph: { nodes: [], edges: [] },
            user_work: [],
            blocking_work: [],
            latest_event_sequence: null,
            freshness: {
              status: "fresh",
              as_of: "2026-03-04T10:00:00Z",
              note: "none"
            }
          }
        })
      ),
      http.get("*/api/v1/workflow-runs/:workflowRunId", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.get",
          workflow_run: {
            workflow_run_id: "wr-test-001",
            workflow_id: "schedule_planning.v1",
            workflow_version: "v1",
            tenant_id: "tenant-a",
            domain_id: "domain-x",
            partition_key: "SD-2026-03-07",
            logical_date: "2026-03-07",
            activation_key: "stage06",
            state: "OPEN",
            active_issue_count: 0,
            created_at: "2026-03-04T10:00:00Z",
            updated_at: "2026-03-04T10:00:00Z"
          },
          human_tasks: [],
          approvals: [],
          artifact_versions: [],
          pointers: [],
          flags: [],
          summary: {
            human_task_count: 0,
            approval_count: 0,
            artifact_version_count: 0,
            pointer_count: 0,
            flag_count: 0,
            active_issue_count: 0
          }
        })
      )
    );

    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(await screen.findByText(/Workspace projection is empty/i)).toBeInTheDocument();
  });

  it("keeps graph and swimlanes rendered on the same workspace page", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const page = await screen.findByTestId("run-workspace-page");
    expect(within(page).getByTestId("workflow-graph")).toBeInTheDocument();
    expect(within(page).getByTestId("workspace-swimlanes")).toBeInTheDocument();
  });
});
