import { render, screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";

import { App } from "@/app/App";
import { server } from "@/test/api/server";

const projectA = {
  project_id: "cp-page-001",
  tenant_id: "tenant-a",
  domain_id: "domain-x",
  project_key: "CAPEX-001",
  name: "Packaging line upgrade",
  state: "active",
  metadata_json: {},
  created_by_actor_id: "human:admin",
  created_by_actor_type: "human",
  created_at: "2026-06-04T08:00:00Z",
  updated_at: "2026-06-04T08:00:00Z",
  caller_role: "project_admin"
};

const projectB = {
  ...projectA,
  project_id: "cp-page-002",
  project_key: "CAPEX-002",
  name: "Dock modernization",
  caller_role: "project_viewer"
};

function run(workflowRunId: string) {
  return {
    workflow_run_id: workflowRunId,
    project_id: "cp-page-001",
    workflow_id: "capex.intake.v1",
    workflow_version: "v1",
    tenant_id: "tenant-a",
    domain_id: "domain-x",
    partition_key: "CAPEX-001",
    logical_date: "2026-06-04",
    activation_key: workflowRunId,
    state: "OPEN",
    active_issue_count: 0,
    created_at: "2026-06-04T08:00:00Z",
    updated_at: "2026-06-04T08:00:00Z"
  };
}

function registerCapexHandlers(): void {
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
          actor_roles: ["operations_manager"],
          boundary_profile: "ci_test",
          request_context_mode: "trusted_headers",
          actor_switching_allowed: true
        }
      })
    ),
    http.get("*/api/v1/capex/projects", () =>
      HttpResponse.json({
        status: "ok",
        command: "api.capex.projects.list",
        projects: [projectA, projectB],
        page: { limit: 5, offset: 0 }
      })
    ),
    http.get("*/api/v1/capex/projects/:projectId/dashboard", ({ params }) => {
      const selectedProject = params.projectId === "cp-page-002" ? projectB : projectA;
      return HttpResponse.json({
        status: "ok",
        command: "api.capex.projects.dashboard",
        project_id: selectedProject.project_id,
        dashboard: {
          schema_version: "capex_project_dashboard.v1",
          project: selectedProject,
          caller_role: selectedProject.caller_role,
          counts: {
            workflow_run_count: 1,
            open_human_task_count: 1,
            pending_approval_count: 1,
            active_flag_count: 1,
            artifact_version_count: 2,
            pointer_count: 1,
            timeline_event_count: 3
          },
          workflow_runs: [run("wr-capex-page-001")],
          human_tasks: [
            {
              human_task_id: "ht-capex-page-001",
              workflow_run_id: "wr-capex-page-001",
              project_id: selectedProject.project_id,
              task_run_id: "tr-capex-page-001",
              task_kind: "project_review",
              state: "OPEN",
              candidate_roles: ["operations_manager"],
              owner_role: "operations_manager",
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
              created_at: "2026-06-04T08:00:00Z",
              updated_at: "2026-06-04T08:00:00Z",
              task_run_state: "READY",
              stage_id: "Stage01",
              blocked_on_kind: null,
              blocked_on_ref: null,
              spawned_from_flag_id: null
            }
          ],
          approvals: [
            {
              approval_id: "ap-capex-page-001",
              workflow_run_id: "wr-capex-page-001",
              project_id: selectedProject.project_id,
              task_run_id: "tr-capex-page-001",
              approval_kind: "project_review",
              scope_kind: "task_run",
              scope_ref: "Stage01",
              state: "PENDING",
              requested_by_task_run_id: "tr-capex-page-001",
              candidate_roles: ["operations_manager"],
              required_role: "operations_manager",
              requested_at: "2026-06-04T08:00:00Z",
              responded_at: null,
              response_kind: null,
              response_reason: null,
              decided_by_actor_id: null,
              decided_by_actor_type: null,
              generation: 0,
              created_at: "2026-06-04T08:00:00Z",
              updated_at: "2026-06-04T08:00:00Z"
            }
          ],
          flags: [
            {
              flag_id: "fl-capex-page-001",
              workflow_run_id: "wr-capex-page-001",
              project_id: selectedProject.project_id,
              tenant_id: "tenant-a",
              domain_id: "domain-x",
              workflow_id: "capex.intake.v1",
              partition_key: "CAPEX-001",
              kind: "project_gap",
              severity: "high",
              state: "open",
              summary: "Funding package incomplete",
              details_json: {},
              assigned_group: "operations_manager",
              created_at: "2026-06-04T08:00:00Z",
              closed_at: null,
              created_by_actor_id: "human:admin",
              created_by_actor_type: "human",
              source_event_id: null,
              dedupe_key: "capex-page",
              updated_at: "2026-06-04T08:00:00Z"
            }
          ],
          artifact_versions: [],
          pointers: [],
          timeline_events: [],
          page: { limit: 8, offset: 0 }
        }
      });
    })
  );
}

describe("CapexProjectDashboardPage", () => {
  it("renders assigned project selector, caller role, counts, and queue links", async () => {
    registerCapexHandlers();
    window.history.pushState({}, "", "/capex/projects");
    render(<App />);

    const page = await screen.findByTestId("capex-projects-page");
    expect(window.location.pathname).toBe("/capex/projects/cp-page-001");
    expect(within(page).getByRole("heading", { name: "Packaging line upgrade" })).toBeInTheDocument();
    expect(within(page).getAllByText("admin").length).toBeGreaterThan(0);
    expect(within(page).getByText("Open tasks")).toBeInTheDocument();
    expect(within(page).getByText("project review")).toBeInTheDocument();
    expect(within(page).getByText("Funding package incomplete")).toBeInTheDocument();
    expect(within(page).getByRole("link", { name: "Workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-capex-page-001/workspace"
    );
    expect(within(page).getByRole("link", { name: /Dock modernization/ })).toHaveAttribute(
      "href",
      "/capex/projects/cp-page-002"
    );
  });
});
