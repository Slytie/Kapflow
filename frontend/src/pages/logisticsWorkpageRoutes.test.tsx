import { HttpResponse, http } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { server } from "@/test/api/server";

function setFrontendOperatorContext(): void {
  const currentContext = getApiRequestContextHeaders();
  setApiRequestContextHeaders({
    ...currentContext,
    actorId: "human:frontend-operator",
    actorType: "human",
    actorRoles: "dispatch_supervisor,schedule_planner,fleet_coordinator,operations_manager"
  });
}

describe("logistics workpage routes", () => {
  it("navigates from the shell graph to the canonical weekly schedule workpage", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const nav = await screen.findByTestId("logistics-family-nav");
    expect(within(nav).getByTestId("logistics-family-nav-edge-reporting_actuals_to_future_planning")).toBeInTheDocument();
    expect(nav.querySelector("svg")).toBeNull();

    await user.click(screen.getByTestId("logistics-family-nav-node-weekly_schedule_planning"));

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
  });

  it("navigates from the shell graph to the canonical end-of-day workpage", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await screen.findByTestId("logistics-family-nav");
    await user.click(screen.getByTestId("logistics-family-nav-node-dispatch_reporting"));

    expect(await screen.findByTestId("dispatch-report-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/runs/wr-report-001/workpages/eod-v0");
  });

  it("navigates from the shell graph to the live-dispatch workspace", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();

    server.use(
      http.get("*/api/v1/stories/logistics-three-workflow", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.stories.logistics_three_workflow",
          story: {
            story_id: "logistics_three_workflow_demo.v1",
            family: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              contract_version: 1
            },
            partitions: {
              planning_week_id: "PW-2026-W10",
              service_date_ids: ["SD-2026-03-06"]
            },
            family_graph: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              modules: [
                {
                  module_id: "dispatch_reporting",
                  workflow_id: "dispatch_reporting.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [],
                  artifact_refs: [],
                  selection_summary: ""
                },
                {
                  module_id: "weekly_schedule_planning",
                  workflow_id: "weekly_schedule_planning.v1",
                  partition_kind: "PlanningWeekID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [],
                  artifact_refs: [],
                  selection_summary: ""
                },
                {
                  module_id: "live_dispatch",
                  workflow_id: "live_dispatch.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "event_driven",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-live-001",
                      workflow_id: "live_dispatch.v1",
                      partition_key: "SD-2026-03-06"
                    }
                  ],
                  artifact_refs: [],
                  selection_summary: "1 linked run, 0 downloadable artifacts"
                }
              ],
              edges: [
                {
                  edge_id: "reporting_actuals_to_future_planning",
                  source_module_id: "dispatch_reporting",
                  target_module_id: "weekly_schedule_planning",
                  handoff_mode: "artifact_handoff"
                },
                {
                  edge_id: "weekly_seed_to_live_dispatch",
                  source_module_id: "weekly_schedule_planning",
                  target_module_id: "live_dispatch",
                  handoff_mode: "artifact_handoff"
                }
              ]
            },
            linked_workflow_runs: {
              weekly_schedule_planning: [],
              live_dispatch: [
                {
                  workflow_run_id: "wr-live-001",
                  workflow_id: "live_dispatch.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "SD-2026-03-06",
                  logical_date: "2026-03-06",
                  activation_key: "live_dispatch.v1:SD-2026-03-06",
                  state: "OPEN",
                  active_issue_count: 1,
                  created_at: "2026-03-09T00:00:00Z",
                  updated_at: "2026-03-09T00:00:00Z"
                }
              ],
              dispatch_reporting: [],
              summary: {
                weekly_schedule_planning_count: 0,
                live_dispatch_count: 1,
                dispatch_reporting_count: 0
              }
            },
            handoff_activity: {
              edges: [],
              summary: {
                edge_execution_count: 0,
                coherence_failed_count: 0
              }
            },
            board: {
              lanes: [],
              work_items: [],
              page: { limit: 100, offset: 0 },
              summary: {
                work_item_count: 0,
                human_task_count: 0,
                approval_count: 0,
                flag_count: 0,
                primary_actionable_count: 0,
                workflow_item_counts: {}
              }
            },
            official_outputs: {
              pointers: [],
              pointer_outputs: [],
              official_output_artifacts: [],
              coherence: {},
              summary: {
                pointer_count: 0,
                pointer_output_count: 0,
                official_output_artifact_count: 0,
                artifact_kind_counts: {}
              }
            },
            freshness: {
              latest_event_sequence: null,
              latest_event_recorded_at: "2026-03-09T00:00:00Z",
              max_workflow_run_updated_at: "2026-03-09T00:00:00Z",
              generated_at: "2026-03-09T00:00:00Z"
            },
            coherence: {
              official_outputs: {},
              handoff_edges: []
            }
          }
        })
      )
    );

    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await screen.findByTestId("logistics-family-nav");
    await user.click(screen.getByTestId("logistics-family-nav-node-live_dispatch"));

    expect(await screen.findByText("Loading run workspace")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/runs/wr-live-001/workspace");
  });

  it("keeps utility destinations in the hamburger menu instead of the primary shell rail", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await screen.findByRole("button", { name: "Open utility menu" });
    expect(screen.queryByRole("link", { name: "My Work" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Approvals" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open utility menu" }));

    expect(screen.getByRole("menuitem", { name: "My Work" })).toHaveAttribute("href", "/my-work");
    expect(screen.getByRole("menuitem", { name: "Approvals" })).toHaveAttribute("href", "/approvals");
    expect(screen.getByRole("menuitem", { name: "Exceptions" })).toHaveAttribute("href", "/exceptions");
    expect(screen.getByRole("menuitem", { name: "Official Outputs" })).toHaveAttribute(
      "href",
      "/official-outputs"
    );
  });

  it("shows a neutral graph on non-logistics routes and lets node clicks enter the logistics flow", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/my-work");
    render(<App />);

    expect(await screen.findByText("My Work Queue")).toBeInTheDocument();
    expect(screen.getByTestId("logistics-family-nav-node-dispatch_reporting")).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.getByTestId("logistics-family-nav-node-weekly_schedule_planning")).toHaveAttribute(
      "aria-pressed",
      "false"
    );
    expect(screen.getByTestId("logistics-family-nav-node-live_dispatch")).toHaveAttribute(
      "aria-pressed",
      "false"
    );

    await user.click(screen.getByTestId("logistics-family-nav-node-weekly_schedule_planning"));

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
  });

  it("marks the active workflow in the shell graph for run-backed workpage routes", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-weekly-001/workpages/schedule-v0");
    render(<App />);

    expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
    expect(screen.getByTestId("logistics-family-nav-node-weekly_schedule_planning")).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.getByTestId("logistics-family-nav-node-dispatch_reporting")).toHaveAttribute(
      "aria-pressed",
      "false"
    );

    await user.click(await screen.findByRole("link", { name: "Open editable draft" }));

    expect(await screen.findByTestId("schedule-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
    expect(screen.getByTestId("logistics-family-nav-node-weekly_schedule_planning")).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("creates an editable EOD draft from the canonical run-backed landing under the shared shell", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/runs/wr-reporting-001/workpages/eod-v0");
    render(<App />);

    expect(await screen.findByTestId("dispatch-report-workpage-page")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Create editable draft" }));

    expect(await screen.findByTestId("dispatch-report-artifact-workpage-page")).toBeInTheDocument();
    expect(window.location.pathname).toBe(
      "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
    );
    expect(screen.getByTestId("logistics-family-nav-node-dispatch_reporting")).toHaveAttribute(
      "aria-pressed",
      "true"
    );
  });

  it("routes multi-run modules back to the logistics home with the module selected", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();

    server.use(
      http.get("*/api/v1/stories/logistics-three-workflow", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.stories.logistics_three_workflow",
          story: {
            story_id: "logistics_three_workflow_demo.v1",
            family: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              contract_version: 1
            },
            partitions: {
              planning_week_id: "PW-2026-W10",
              service_date_ids: ["SD-2026-03-06"]
            },
            family_graph: {
              family_id: "logistics_ops_family.v1",
              family_version: 1,
              modules: [
                {
                  module_id: "weekly_schedule_planning",
                  workflow_id: "weekly_schedule_planning.v1",
                  partition_kind: "PlanningWeekID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "run_group",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-weekly-001",
                      workflow_id: "weekly_schedule_planning.v1",
                      partition_key: "PW-2026-W10"
                    },
                    {
                      workflow_run_id: "wr-weekly-002",
                      workflow_id: "weekly_schedule_planning.v1",
                      partition_key: "PW-2026-W11"
                    }
                  ],
                  artifact_refs: [],
                  selection_summary: "2 linked runs, choose one"
                },
                {
                  module_id: "dispatch_reporting",
                  workflow_id: "dispatch_reporting.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [],
                  artifact_refs: [],
                  selection_summary: ""
                },
                {
                  module_id: "live_dispatch",
                  workflow_id: "live_dispatch.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "manual_or_event",
                  status: "ready",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [],
                  artifact_refs: [],
                  selection_summary: ""
                }
              ],
              edges: [
                {
                  edge_id: "reporting_actuals_to_future_planning",
                  source_module_id: "dispatch_reporting",
                  target_module_id: "weekly_schedule_planning",
                  handoff_mode: "artifact_handoff"
                },
                {
                  edge_id: "weekly_seed_to_live_dispatch",
                  source_module_id: "weekly_schedule_planning",
                  target_module_id: "live_dispatch",
                  handoff_mode: "artifact_handoff"
                }
              ]
            },
            linked_workflow_runs: {
              weekly_schedule_planning: [
                {
                  workflow_run_id: "wr-weekly-001",
                  workflow_id: "weekly_schedule_planning.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "PW-2026-W10",
                  logical_date: "PW-2026-W10",
                  activation_key: "weekly_schedule_planning.v1:PW-2026-W10",
                  state: "OPEN",
                  active_issue_count: 1,
                  created_at: "2026-03-09T00:00:00Z",
                  updated_at: "2026-03-09T00:00:00Z"
                },
                {
                  workflow_run_id: "wr-weekly-002",
                  workflow_id: "weekly_schedule_planning.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "PW-2026-W11",
                  logical_date: "PW-2026-W11",
                  activation_key: "weekly_schedule_planning.v1:PW-2026-W11",
                  state: "READY",
                  active_issue_count: 0,
                  created_at: "2026-03-10T00:00:00Z",
                  updated_at: "2026-03-10T00:00:00Z"
                }
              ],
              live_dispatch: [],
              dispatch_reporting: [],
              summary: {
                weekly_schedule_planning_count: 2,
                live_dispatch_count: 0,
                dispatch_reporting_count: 0
              }
            },
            handoff_activity: {
              edges: [],
              summary: {
                edge_execution_count: 0,
                coherence_failed_count: 0
              }
            },
            board: {
              lanes: [],
              work_items: [],
              page: { limit: 100, offset: 0 },
              summary: {
                work_item_count: 0,
                human_task_count: 0,
                approval_count: 0,
                flag_count: 0,
                primary_actionable_count: 0,
                workflow_item_counts: {}
              }
            },
            official_outputs: {
              pointers: [],
              pointer_outputs: [],
              official_output_artifacts: [],
              coherence: {},
              summary: {
                pointer_count: 0,
                pointer_output_count: 0,
                official_output_artifact_count: 0,
                artifact_kind_counts: {}
              }
            },
            freshness: {
              latest_event_sequence: null,
              latest_event_recorded_at: "2026-03-09T00:00:00Z",
              max_workflow_run_updated_at: "2026-03-09T00:00:00Z",
              generated_at: "2026-03-09T00:00:00Z"
            },
            coherence: {
              official_outputs: {},
              handoff_edges: []
            }
          }
        })
      )
    );

    window.history.pushState({}, "", "/my-work");
    render(<App />);

    expect(await screen.findByText("My Work Queue")).toBeInTheDocument();
    await user.click(screen.getByTestId("logistics-family-nav-node-weekly_schedule_planning"));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/demo/logistics");
    });
    expect(window.location.search).toContain("module=weekly_schedule_planning");

    const detailPanel = await screen.findByTestId("logistics-module-detail-panel");
    await user.click(within(detailPanel).getByRole("button", { name: /Open info for Weekly Schedule Planning/i }));
    const infoDialog = await screen.findByRole("dialog", { name: "Weekly Schedule Planning info" });
    expect(within(infoDialog).getByText(/Choose the linked workflow run/i)).toBeInTheDocument();
  });
});
