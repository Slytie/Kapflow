import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { App } from "@/app/App";
import { RunWorkspacePage } from "@/pages/RunWorkspacePage";
import { mutationLog } from "@/test/api/handlers";
import { server } from "@/test/api/server";
import { renderRoute } from "@/test/renderRoute";

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
    expect(within(drawer).getByText("Stage official output")).toBeInTheDocument();
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

    expect(within(taskCard as HTMLElement).getByRole("button", { name: "Complete" })).toBeDisabled();
    expect(within(taskCard as HTMLElement).getByText(/Missing required inputs/i)).toBeInTheDocument();
  });

  it("shows template download for required upload rows", async () => {
    const user = userEvent.setup();
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const taskCard = (await screen.findByRole("heading", { name: "Review Packet" })).closest("article");
    expect(taskCard).not.toBeNull();
    const downloadTemplate = within(taskCard as HTMLElement).getByRole("button", {
      name: "Download Template"
    });
    expect(downloadTemplate).toBeEnabled();

    await user.click(downloadTemplate);
    await waitFor(() => {
      expect(mutationLog()).toContain(
        "template-download:schedule.stage06.supervisor_review.doc.empty.v1"
      );
    });
  });

  it("upload changes requirement state after workspace refetch", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const initialCard = (await screen.findByRole("heading", { name: "Review Packet" })).closest(
      "article"
    );
    expect(initialCard).not.toBeNull();

    expect(
      within(initialCard as HTMLElement).getByText(/schedule\.supervisor_review\.doc \(missing\)/i)
    ).toBeInTheDocument();

    const requiredUploadRow = within(initialCard as HTMLElement)
      .getByText(/Required upload: schedule\.supervisor_review\.doc/i)
      .closest(".workspace-board-card__requirement");
    expect(requiredUploadRow).not.toBeNull();
    const fileInput = (requiredUploadRow as HTMLElement).querySelector("input[type='file']");
    expect(fileInput).not.toBeNull();
    const file = new File(["evidence"], "review-evidence.txt", { type: "text/plain" });
    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [file] } });

    await waitFor(() => {
      expect(mutationLog()).toContain("upload:human_task:ht-claimed-002");
    });

    await waitFor(() => {
      const card = screen.getByRole("heading", { name: "Review Packet" }).closest("article");
      expect(card).not.toBeNull();
      expect(
        within(card as HTMLElement).getByText(/schedule\.supervisor_review\.doc \(satisfied\)/i)
      ).toBeInTheDocument();
      expect(within(card as HTMLElement).getByRole("button", { name: "Complete" })).toBeDisabled();
    }, { timeout: 2500 });
  });

  it("shows required review actions including confirm-review", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const taskCard = (await screen.findByRole("heading", { name: "Review Packet" })).closest("article");
    expect(taskCard).not.toBeNull();
    expect(
      within(taskCard as HTMLElement).getAllByRole("button", { name: "Open Draft" }).length
    ).toBeGreaterThan(0);
    expect(
      within(taskCard as HTMLElement).getAllByRole("button", { name: "Confirm Reviewed" }).length
    ).toBeGreaterThan(0);
  });

  it("confirm-review unblocks completion after workspace refetch", async () => {
    const user = userEvent.setup();
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const initialCard = (await screen.findByRole("heading", { name: "Review Packet" })).closest(
      "article"
    );
    expect(initialCard).not.toBeNull();

    const requiredUploadRow = within(initialCard as HTMLElement)
      .getByText(/Required upload: schedule\.supervisor_review\.doc/i)
      .closest(".workspace-board-card__requirement");
    expect(requiredUploadRow).not.toBeNull();
    const uploadInput = (requiredUploadRow as HTMLElement).querySelector("input[type='file']");
    expect(uploadInput).not.toBeNull();
    fireEvent.change(uploadInput as HTMLInputElement, {
      target: { files: [new File(["evidence"], "review-response.txt", { type: "text/plain" })] }
    });

    await waitFor(() => {
      expect(mutationLog()).toContain("upload:human_task:ht-claimed-002");
    });

    const confirmButtons = within(initialCard as HTMLElement).getAllByRole("button", {
      name: "Confirm Reviewed"
    });
    await user.click(confirmButtons[0]);

    await waitFor(() => {
      expect(mutationLog()).toContain("confirm-review:ht-claimed-002");
    });

    await waitFor(() => {
      const card = screen.getByRole("heading", { name: "Review Packet" }).closest("article");
      expect(card).not.toBeNull();
      expect(within(card as HTMLElement).getByRole("button", { name: "Complete" })).toBeEnabled();
    });
  });

  it("renders approval work and execute respond actions", async () => {
    const user = userEvent.setup();
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const approvalCard = (
      await screen.findByRole("heading", { name: "Stage07 Approval" })
    ).closest("article");
    expect(approvalCard).not.toBeNull();
    await user.click(within(approvalCard as HTMLElement).getByRole("button", { name: "Approve" }));

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

    const flagCard = (
      await screen.findByRole("heading", { name: /Courier C-104 did not report/i })
    ).closest("article");
    expect(flagCard).not.toBeNull();

    const uploadButton = within(flagCard as HTMLElement).getByRole("button", { name: "Upload" });
    const downloadButton = within(flagCard as HTMLElement).getByRole("button", { name: "Download" });
    expect(uploadButton).toBeEnabled();
    expect(downloadButton).toBeEnabled();

    await user.click(downloadButton);
  });

  it("loads through app route /runs/:workflowRunId/workspace", async () => {
    window.history.pushState({}, "", "/runs/wr-test-001/workspace");
    render(<App />);

    expect(await screen.findByTestId("run-workspace-page")).toBeInTheDocument();
  });

  it("opens workspace by default from app root route", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);

    expect(await screen.findByTestId("run-workspace-page")).toBeInTheDocument();
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
