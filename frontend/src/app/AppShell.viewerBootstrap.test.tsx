import { HttpResponse, http } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { server } from "@/test/api/server";

describe("AppShell viewer bootstrap", () => {
  it("uses shared-env viewer bootstrap and omits trusted headers after bootstrap", async () => {
    let workflowRunsHeaders:
      | {
          tenant: string | null;
          domain: string | null;
          actorId: string | null;
          actorType: string | null;
          actorRoles: string | null;
        }
      | null = null;

    server.use(
      http.get("*/api/v1/viewer", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.viewer.bootstrap",
          viewer_session: {
            tenant_id: "tenant-a",
            domain_id: "domain-x",
            actor_id: "service:shared-gateway",
            actor_type: "service",
            actor_roles: ["dispatch_supervisor"],
            boundary_profile: "shared_env",
            request_context_mode: "server_derived",
            actor_switching_allowed: false
          }
        })
      ),
      http.get("*/api/v1/workflow-runs", ({ request }) => {
        workflowRunsHeaders = {
          tenant: request.headers.get("x-onetruth-tenant-id"),
          domain: request.headers.get("x-onetruth-domain-id"),
          actorId: request.headers.get("x-onetruth-actor-id"),
          actorType: request.headers.get("x-onetruth-actor-type"),
          actorRoles: request.headers.get("x-onetruth-actor-roles")
        };
        return HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.list",
          workflow_runs: [],
          page: { limit: 100, offset: 0 }
        });
      })
    );

    window.history.pushState({}, "", "/runs");
    render(<App />);

    const viewerPanel = await screen.findByTestId("viewer-session-panel");
    const viewerSession = within(viewerPanel).getByTestId("viewer-session");
    expect(within(viewerPanel).getByText("Viewer session")).toBeInTheDocument();
    expect(within(viewerSession).getByText("service:shared-gateway")).toBeInTheDocument();
    expect(screen.queryByLabelText("Active user")).not.toBeInTheDocument();
    expect(await screen.findByText(/No runs in scope/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(workflowRunsHeaders).not.toBeNull();
    });
    expect(workflowRunsHeaders).toEqual({
      tenant: null,
      domain: null,
      actorId: null,
      actorType: null,
      actorRoles: null
    });
  });

  it("keeps the shell full width and opens task details as a centered modal", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("*/api/v1/viewer", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.viewer.bootstrap",
          viewer_session: {
            tenant_id: "tenant-a",
            domain_id: "domain-x",
            actor_id: "human:frontend-operator",
            actor_type: "human",
            actor_roles: ["dispatch_supervisor"],
            boundary_profile: "shared_env",
            request_context_mode: "server_derived",
            actor_switching_allowed: false
          }
        })
      ),
      http.get("*/api/v1/human-tasks", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.list",
          human_tasks: [
            {
              human_task_id: "ht-queue-001",
              workflow_run_id: "wr-queue-001",
              task_run_id: "tr-queue-001",
              task_kind: "review_packet",
              state: "OPEN",
              candidate_roles: ["dispatch_supervisor"],
              owner_role: "dispatch_supervisor",
              assignee_actor_id: null,
              assignee_actor_type: null,
              due_at: null,
              escalation_at: null,
              lease_version: 0,
              claimed_at: null,
              claimed_until: null,
              linked_approval_id: null,
              reopen_count: 0,
              generation: 0,
              created_at: "2026-03-31T09:00:00Z",
              updated_at: "2026-03-31T09:00:00Z",
              task_run_state: "READY",
              stage_id: "Stage06",
              blocked_on_kind: null,
              blocked_on_ref: null,
              spawned_from_flag_id: null,
              available_actions: ["claim"],
              missing_required_inputs: [],
              blocking_reason_codes: []
            }
          ],
          page: { limit: 100, offset: 0 }
        })
      )
    );

    window.history.pushState({}, "", "/my-work");
    render(<App />);

    expect(await screen.findByText("My Work Queue")).toBeInTheDocument();
    expect(await screen.findByText("Stage06 · Review Packet")).toBeInTheDocument();

    const shell = document.querySelector(".app-shell");
    const closedDrawer = document.querySelector(".detail-drawer--closed");
    expect(shell).not.toBeNull();
    expect(closedDrawer).toHaveAttribute("aria-hidden", "true");
    expect(getComputedStyle(shell as Element).gridTemplateColumns).not.toContain("380");

    await user.click(screen.getByRole("button", { name: "Details" }));

    const modal = await screen.findByRole("dialog");
    expect(modal).toHaveClass("task-modal");
    expect(within(modal).getByRole("heading", { name: "Stage06 · Review Packet" })).toBeInTheDocument();
    expect(getComputedStyle(shell as Element).gridTemplateColumns).not.toContain("380");
    expect(screen.queryByLabelText("Details drawer")).not.toBeInTheDocument();
  });
});
