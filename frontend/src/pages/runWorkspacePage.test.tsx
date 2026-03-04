import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";

import { App } from "@/app/App";
import { RunWorkspacePage } from "@/pages/RunWorkspacePage";
import { mutationLog } from "@/test/api/handlers";
import { server } from "@/test/api/server";
import { renderRoute } from "@/test/renderRoute";

describe("RunWorkspacePage", () => {
  it("renders graph nodes and edges", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(await screen.findByTestId("workflow-graph")).toBeInTheDocument();
    expect(screen.getAllByTestId(/workflow-graph-node-/).length).toBeGreaterThan(0);
    expect(screen.getAllByTestId(/workflow-graph-edge-/).length).toBeGreaterThan(0);
  });

  it("renders node status labels from workspace projection", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(await screen.findByTestId("workflow-graph")).toBeInTheDocument();
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("In Progress").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Blocked").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Awaiting Approval").length).toBeGreaterThan(0);
  });

  it("highlights blocking graph nodes", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const blockingNode = await screen.findByTestId("workflow-graph-node-stage06_info_loop");
    expect(blockingNode).toHaveClass("is-blocking");
  });

  it("renders freshness line with latest event sequence", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const freshness = await screen.findByTestId("workspace-freshness-line");
    expect(freshness).toHaveTextContent("Freshness");
    expect(freshness).toHaveTextContent("event #");
  });

  it("renders user actionable work below the graph", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(await screen.findByTestId("workspace-action-panel")).toBeInTheDocument();
    expect(screen.getByText(/Stage06 · review_packet/i)).toBeInTheDocument();
  });

  it("disables complete when required inputs are missing", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const taskHeading = await screen.findByText(/Stage06 · review_packet/i);
    const taskCard = taskHeading.closest("article");
    expect(taskCard).not.toBeNull();
    expect(within(taskCard as HTMLElement).getByRole("button", { name: "Complete" })).toBeDisabled();
    expect(within(taskCard as HTMLElement).getByText(/Missing required inputs/i)).toBeInTheDocument();
  });

  it("marks task completable after upload response unblocks missing inputs", async () => {
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const initialCard = (await screen.findByText(/Stage06 · review_packet/i)).closest("article");
    expect(initialCard).not.toBeNull();

    const fileInput = (initialCard as HTMLElement).querySelector("input[type='file']");
    expect(fileInput).not.toBeNull();
    const file = new File(["evidence"], "review-evidence.txt", { type: "text/plain" });
    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [file] } });

    await waitFor(() => {
      expect(mutationLog()).toContain("upload:human_task:ht-claimed-002");
    });

    await waitFor(() => {
      const card = screen.getByText(/Stage06 · review_packet/i).closest("article");
      expect(card).not.toBeNull();
      expect(within(card as HTMLElement).getByRole("button", { name: "Complete" })).toBeEnabled();
    }, { timeout: 2500 });
  });

  it("renders approval work and execute respond actions", async () => {
    const user = userEvent.setup();
    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    const approvalCard = (await screen.findByText(/business_decision · Required: operations_manager/i)).closest("article");
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

    const flagCard = (await screen.findByText(/Courier C-104 did not report/i)).closest("article");
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
      )
    );

    renderRoute(<RunWorkspacePage />, {
      route: "/runs/wr-test-001/workspace",
      path: "/runs/:workflowRunId/workspace"
    });

    expect(await screen.findByText(/Workspace projection is empty/i)).toBeInTheDocument();
  });
});
