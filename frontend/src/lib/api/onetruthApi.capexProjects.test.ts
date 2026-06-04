import { HttpResponse, http } from "msw";

import { onetruthApi } from "@/lib/api/onetruthApi";
import { server } from "@/test/api/server";

const project = {
  project_id: "cp-ui-001",
  tenant_id: "tenant-a",
  domain_id: "domain-x",
  project_key: "CAPEX-UI-001",
  name: "Packaging line upgrade",
  state: "active",
  metadata_json: { site: "plant-12" },
  created_by_actor_id: "human:admin",
  created_by_actor_type: "human",
  created_at: "2026-06-04T08:00:00Z",
  updated_at: "2026-06-04T08:00:00Z",
  caller_role: "project_admin"
};

const run = {
  workflow_run_id: "wr-capex-ui-001",
  project_id: "cp-ui-001",
  workflow_id: "capex.intake.v1",
  workflow_version: "v1",
  tenant_id: "tenant-a",
  domain_id: "domain-x",
  partition_key: "CAPEX-UI-001",
  logical_date: "2026-06-04",
  activation_key: "capex-ui",
  state: "OPEN",
  active_issue_count: 0,
  created_at: "2026-06-04T08:00:00Z",
  updated_at: "2026-06-04T08:00:00Z"
};

describe("onetruthApi CAPEX projects", () => {
  it("loads assigned projects, dashboard projection, and project workflow runs", async () => {
    const seenUrls: string[] = [];
    server.use(
      http.get("*/api/v1/capex/projects", ({ request }) => {
        seenUrls.push(new URL(request.url).pathname + new URL(request.url).search);
        return HttpResponse.json({
          status: "ok",
          command: "api.capex.projects.list",
          projects: [project],
          page: { limit: 5, offset: 0 }
        });
      }),
      http.get("*/api/v1/capex/projects/:projectId/dashboard", ({ params, request }) => {
        seenUrls.push(new URL(request.url).pathname + new URL(request.url).search);
        return HttpResponse.json({
          status: "ok",
          command: "api.capex.projects.dashboard",
          project_id: params.projectId,
          dashboard: {
            schema_version: "capex_project_dashboard.v1",
            project,
            caller_role: "project_admin",
            counts: {
              workflow_run_count: 1,
              open_human_task_count: 2,
              pending_approval_count: 1,
              active_flag_count: 0,
              artifact_version_count: 3,
              pointer_count: 1,
              timeline_event_count: 4
            },
            workflow_runs: [run],
            human_tasks: [],
            approvals: [],
            flags: [],
            artifact_versions: [],
            pointers: [],
            timeline_events: [],
            page: { limit: 8, offset: 0 }
          }
        });
      }),
      http.get("*/api/v1/capex/projects/:projectId/workflow-runs", ({ request }) => {
        seenUrls.push(new URL(request.url).pathname + new URL(request.url).search);
        return HttpResponse.json({
          status: "ok",
          command: "api.capex.projects.workflow_runs.list",
          workflow_runs: [run],
          page: { limit: 50, offset: 0 }
        });
      })
    );

    await expect(onetruthApi.listCapexProjects({ limit: 5, offset: 0 })).resolves.toEqual([
      project
    ]);
    await expect(onetruthApi.getCapexProjectDashboard("cp-ui-001", { limit: 8 })).resolves.toMatchObject({
      project: { project_id: "cp-ui-001" },
      caller_role: "project_admin",
      counts: { workflow_run_count: 1 }
    });
    await expect(onetruthApi.listCapexProjectWorkflowRuns("cp-ui-001", { limit: 50 })).resolves.toEqual([
      run
    ]);

    expect(seenUrls).toEqual([
      "/api/v1/capex/projects?limit=5&offset=0",
      "/api/v1/capex/projects/cp-ui-001/dashboard?limit=8",
      "/api/v1/capex/projects/cp-ui-001/workflow-runs?limit=50"
    ]);
  });
});
