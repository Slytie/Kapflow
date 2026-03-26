import { HttpResponse, http } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { mutationLog } from "@/test/api/handlers";
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

describe("LogisticsDemoPage", () => {
  it("selects a family node and auto-loads a single-run workflow drill-down graph", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    expect(within(page).getByTestId("workflow-graph")).toBeInTheDocument();

    const weeklyNode = within(page).getByTestId("workflow-graph-node-weekly_schedule_planning");
    await user.click(weeklyNode);

    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).getByRole("heading", { name: "Weekly Schedule Planning" })).toBeInTheDocument();
    expect(within(detailPanel).getByText(/Single linked run selected automatically/i)).toBeInTheDocument();
    expect(
      within(detailPanel).getByRole("link", { name: "Open full workspace" })
    ).toHaveAttribute("href", "/runs/wr-weekly-001/workspace");
    expect(
      within(detailPanel).getByRole("link", { name: "Open run detail (secondary)" })
    ).toHaveAttribute("href", "/runs/wr-weekly-001");
    expect(
      within(detailPanel).getByRole("link", { name: "Open schedule workpage" })
    ).toHaveAttribute("href", "/runs/wr-weekly-001/workpages/schedule-v0");

    expect(await within(page).findByTestId("logistics-demo-drilldown-graph")).toBeInTheDocument();
  });

  it("keeps family graph keyboard-operable for node selection", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const reportingNode = within(page).getByTestId("workflow-graph-node-dispatch_reporting");
    reportingNode.focus();
    await user.keyboard("{Enter}");

    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).getByRole("heading", { name: "Dispatch Reporting" })).toBeInTheDocument();
    expect(
      within(detailPanel).getByRole("link", { name: "Open EOD workpage" })
    ).toHaveAttribute("href", "/runs/wr-report-001/workpages/eod-v0");
  });

  it("shows canonical header entrypoints and keeps demo workpages as compatibility aliases", async () => {
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const canonicalHeader = within(page).getByText("Canonical run-backed workpages").closest("div") as HTMLElement;
    const aliasHeader = within(page).getByText("Compatibility alias workpages").closest("div") as HTMLElement;

    expect(canonicalHeader).toBeInTheDocument();
    expect(within(canonicalHeader).getByRole("link", { name: "Open weekly review workpage" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/schedule-v0"
    );
    expect(within(canonicalHeader).getByRole("link", { name: "Open EOD workpage" })).toHaveAttribute(
      "href",
      "/runs/wr-report-001/workpages/eod-v0"
    );
    expect(aliasHeader).toBeInTheDocument();
    expect(within(aliasHeader).getByRole("link", { name: "Open demo schedule alias" })).toHaveAttribute(
      "href",
      "/demo/logistics/workpages/schedule-v0"
    );
    expect(within(aliasHeader).getByRole("link", { name: "Open demo EOD alias" })).toHaveAttribute(
      "href",
      "/demo/logistics/workpages/eod-v0"
    );
    expect(within(page).queryByRole("button", { name: "Create editable EOD draft" })).not.toBeInTheDocument();
  });

  it("does not expose a workpage CTA for live-dispatch drilldowns", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const liveDispatchNode = within(page).getByTestId("workflow-graph-node-live_dispatch");
    await user.click(liveDispatchNode);

    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).getByRole("heading", { name: "Live Dispatch" })).toBeInTheDocument();
    expect(within(detailPanel).queryByRole("link", { name: "Open schedule workpage" })).not.toBeInTheDocument();
    expect(within(detailPanel).queryByRole("link", { name: "Open EOD workpage" })).not.toBeInTheDocument();
  });

  it("requires explicit run selection when a workpage family links to multiple runs", async () => {
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
                }
              ],
              edges: []
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

    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    expect(within(page).queryByRole("link", { name: "Open weekly review workpage" })).not.toBeInTheDocument();
    expect(
      within(page).getByText(
        "Weekly review workpage: choose a linked weekly-planning run from the family-node drill-down below."
      )
    ).toBeInTheDocument();

    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).getByText(/Choose a workflow run to open drill-down/i)).toBeInTheDocument();
    expect(within(page).queryByTestId("logistics-demo-drilldown-graph")).not.toBeInTheDocument();

    await user.click(within(detailPanel).getByRole("button", { name: /wr-weekly-002/i }));
    expect(
      within(detailPanel).getByRole("link", { name: "Open schedule workpage" })
    ).toHaveAttribute("href", "/runs/wr-weekly-002/workpages/schedule-v0");
  });

  it("renders family-node artifact download affordances", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    await user.click(within(page).getByTestId("workflow-graph-node-weekly_schedule_planning"));

    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    const downloadButton = within(detailPanel).getByRole("button", {
      name: "Download weekly_schedule.xlsx"
    });
    expect(downloadButton).toBeInTheDocument();
    await user.click(downloadButton);
    await waitFor(() => {
      expect(mutationLog()).toContain("artifact-download-bin:av-weekly-001");
    });
  });

  it("opens a task drawer from the unified board without leaving the logistics demo route", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    expect(within(page).getByRole("heading", { name: "Unified Action Board" })).toBeInTheDocument();
    expect(within(page).getByLabelText("Open Exceptions")).toBeInTheDocument();
    expect(within(page).getByLabelText("Open Tasks")).toBeInTheDocument();
    expect(within(page).getByText("weekly_seed_to_live_dispatch")).toBeInTheDocument();

    const openTasksLane = within(page).getByLabelText("Open Tasks");
    await user.click(
      within(openTasksLane).getByRole("button", { name: /Stage03 planning_feedback_review/i })
    );

    expect(window.location.pathname).toBe("/demo/logistics");
    expect(await screen.findByLabelText("Task context")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Claim" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete" })).not.toBeInTheDocument();
    const drawerLinks = await screen.findByLabelText("Drawer links");
    expect(within(drawerLinks).getByRole("link", { name: "Open run workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workspace"
    );
    expect(within(drawerLinks).getByRole("link", { name: "Open run detail (secondary)" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001"
    );
  });

  it("runs task actions from the drawer and refreshes story lanes after success", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const openTasksLane = within(page).getByLabelText("Open Tasks");
    await user.click(
      within(openTasksLane).getByRole("button", { name: /Stage03 planning_feedback_review/i })
    );

    await user.click(await screen.findByRole("button", { name: "Claim" }));

    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-weekly-001");
    });
    await waitFor(() => {
      expect(within(within(page).getByLabelText("Open Tasks")).queryByText(/Stage03 planning_feedback_review/i)).not.toBeInTheDocument();
      expect(within(within(page).getByLabelText("Claimed Tasks")).getByText(/Stage03 planning_feedback_review/i)).toBeInTheDocument();
    });
    expect(await screen.findByRole("button", { name: "Complete" })).toBeInTheDocument();
  });

  it("shows artifact download affordance in the drawer for linked task artifacts", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const claimedLane = within(page).getByLabelText("Claimed Tasks");
    await user.click(
      within(claimedLane).getByRole("button", { name: /Stage01 dispatch_seed_intake/i })
    );

    expect(await screen.findByRole("heading", { name: /Task Artifacts/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
  });

  it("keeps logistics as primary nav and demotes legacy schedule links to secondary detail routes", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    expect(screen.getByRole("link", { name: "Logistics Demo" })).toHaveAttribute(
      "href",
      "/demo/logistics"
    );
    expect(screen.getByRole("link", { name: "Run Details" })).toHaveAttribute("href", "/runs");
    expect(screen.queryByRole("heading", { name: "Linked Workflow Runs" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Schedule Board (Legacy)" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Runs (Legacy Views)" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Timeline (Legacy View)" })).not.toBeInTheDocument();
    expect(within(page).getByRole("heading", { name: "Family Node Detail" })).toBeInTheDocument();
  });
});
