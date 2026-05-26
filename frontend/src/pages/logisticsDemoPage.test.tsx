import { HttpResponse, http } from "msw";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { App } from "@/app/App";
import { getApiRequestContextHeaders, setApiRequestContextHeaders } from "@/lib/api/config";
import { workpagesRepository } from "@/lib/repositories/workpagesRepository";
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
  it("loads the weekly module from query params and auto-loads its single-run drill-down", async () => {
    setFrontendOperatorContext();
    window.history.pushState(
      {},
      "",
      "/demo/logistics?planning_week_id=PW-2026-W10&module=weekly_schedule_planning"
    );
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).queryByRole("heading", { name: "Family Node Detail" })).not.toBeInTheDocument();
    expect(
      within(detailPanel).queryByText(
        /The shell nav drives workflow switching\. This page keeps the selected module context, run drill-down, and launcher surface together\./i
      )
    ).not.toBeInTheDocument();
    const launcher = await within(detailPanel).findByTestId(
      "logistics-module-launcher-weekly_schedule_planning"
    );
    expect(within(detailPanel).getByRole("heading", { level: 4, name: "Weekly Schedule Planning" })).toBeInTheDocument();
    expect(within(launcher).getByRole("heading", { level: 2, name: "Weekly Schedule Planning" })).toBeInTheDocument();
    expect(
      within(launcher).getByText(/launches the canonical weekly schedule workpage/i)
    ).toBeInTheDocument();
    expect(within(launcher).getByRole("link", { name: "Open schedule workpage" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/schedule-v0"
    );
    expect(within(launcher).getByRole("link", { name: "Open full workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workspace"
    );
    expect(within(launcher).getByRole("link", { name: "Open run detail (secondary)" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001"
    );
    expect(within(detailPanel).queryByRole("button", { name: "Submit draft" })).not.toBeInTheDocument();
    expect(
      within(detailPanel).queryByRole("button", { name: "Download draft JSON" })
    ).not.toBeInTheDocument();
    expect(within(detailPanel).queryByRole("link", { name: "Open full workpage" })).not.toBeInTheDocument();
    expect(within(detailPanel).queryByLabelText("Weekly draft versions timeline")).not.toBeInTheDocument();
    expect(await within(page).findByTestId("logistics-demo-drilldown-graph")).toBeInTheDocument();
    expect(window.location.search).toContain("module=weekly_schedule_planning");
    expect(window.location.search).toContain("workflow_run_id=wr-weekly-001");
  });

  it("keeps the full editorial board collapsed by default while the shell task strip stays visible", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const boardPanel = within(page).getByTestId("logistics-task-board-panel");
    expect(boardPanel).toHaveAttribute("data-expanded", "false");
    expect(within(boardPanel).getByText(/The compact task strip stays pinned in the shell/i)).toBeInTheDocument();
    expect(screen.getByTestId("logistics-task-strip")).toBeInTheDocument();
    expect(within(page).queryByLabelText("To Do")).not.toBeInTheDocument();

    await user.click(within(boardPanel).getByRole("button", { name: "Show task board" }));

    expect(boardPanel).toHaveAttribute("data-expanded", "true");
    expect(within(page).getByLabelText("To Do")).toBeInTheDocument();
    expect(within(page).getByLabelText("In Progress")).toBeInTheDocument();
    expect(within(page).getByLabelText("Waiting Review")).toBeInTheDocument();
  });

  it("shows every active task in the shell task strip with urgent nonzero counts", async () => {
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await screen.findByTestId("logistics-demo-page");
    const strip = await screen.findByTestId("logistics-task-strip");
    const todoCard = within(strip).getByTestId("logistics-task-strip-card-todo");
    const todoCount = within(todoCard).getByTestId("logistics-task-strip-count-todo");
    const weeklyTask = within(todoCard).getByTestId(
      "logistics-task-strip-task-todo-ht-weekly-001"
    );
    const reportingTask = within(todoCard).getByTestId(
      "logistics-task-strip-task-todo-ht-reporting-001"
    );

    expect(todoCount).toHaveTextContent("2");
    expect(todoCount).toHaveClass("has-items");
    expect(weeklyTask).toHaveTextContent("Weekly Scheduling Plan Inputs");
    expect(reportingTask).toHaveTextContent("End of Day Dispatch Report");
    expect(weeklyTask).toHaveClass("is-urgent");
    expect(reportingTask).toHaveClass("is-urgent");
    expect(within(todoCard).queryByText("+1")).not.toBeInTheDocument();
  });

  it("keeps node metadata behind the info dialog instead of in the main detail panel", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).getByRole("heading", { level: 4, name: "Dispatch Reporting" })).toBeInTheDocument();
    expect(within(detailPanel).queryByText("View family node artifacts")).not.toBeInTheDocument();
    expect(within(detailPanel).queryByText("Workflow Run Drill-Down")).not.toBeInTheDocument();
    expect(within(detailPanel).queryByRole("button", { name: "Create editable draft" })).not.toBeInTheDocument();

    await user.click(within(detailPanel).getByRole("button", { name: /Open info for Dispatch Reporting/i }));

    const infoDialog = await screen.findByRole("dialog", { name: "Dispatch Reporting info" });
    expect(within(infoDialog).getByText("dispatch_reporting.v1")).toBeInTheDocument();
    expect(within(infoDialog).getByText("manual_or_event")).toBeInTheDocument();
    expect(within(infoDialog).getByText("active")).toBeInTheDocument();
    expect(within(infoDialog).getByText("workflow_run")).toBeInTheDocument();
  });

  it("renders dispatch reporting as a launcher-only surface from the demo shell", async () => {
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    const launcher = await within(detailPanel).findByTestId(
      "logistics-module-launcher-dispatch_reporting"
    );
    expect(
      within(launcher).getByText(/launches the canonical end-of-day workpage/i)
    ).toBeInTheDocument();
    expect(within(launcher).getByRole("link", { name: "Open EOD workpage" })).toHaveAttribute(
      "href",
      "/runs/wr-report-001/workpages/eod-v0"
    );
    expect(within(launcher).getByRole("link", { name: "Open full workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-report-001/workspace"
    );
    expect(within(launcher).getByRole("link", { name: "Open run detail (secondary)" })).toHaveAttribute(
      "href",
      "/runs/wr-report-001"
    );
    expect(within(detailPanel).queryByRole("button", { name: "Create editable draft" })).not.toBeInTheDocument();
    expect(within(detailPanel).queryByRole("button", { name: "Submit draft" })).not.toBeInTheDocument();
    expect(within(detailPanel).queryByRole("button", { name: "Download workbook" })).not.toBeInTheDocument();
    expect(within(detailPanel).queryByLabelText("Reporting draft versions timeline")).not.toBeInTheDocument();
  });

  it("defaults the weekly module to the review-ready run when a current walkthrough companion exists", async () => {
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
                  activation_key: "logistics-demo:weekly:current:PW-2026-W10",
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
                  activation_key: "logistics-demo:weekly:review-ready:PW-2026-W11",
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

    window.history.pushState(
      {},
      "",
      "/demo/logistics?planning_week_id=PW-2026-W10&module=weekly_schedule_planning&workflow_run_id=wr-weekly-001"
    );
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(
      within(detailPanel).getByRole("heading", {
        level: 4,
        name: "Weekly Schedule Planning"
      })
    ).toBeInTheDocument();
    const launcher = await within(detailPanel).findByTestId(
      "logistics-module-launcher-weekly_schedule_planning"
    );
    expect(
      within(launcher).getByRole("link", { name: "Open schedule workpage" })
    ).toHaveAttribute("href", "/runs/wr-weekly-002/workpages/schedule-v0");
    await waitFor(() =>
      expect(window.location.search).toContain("workflow_run_id=wr-weekly-002")
    );

    await user.click(within(detailPanel).getByRole("button", { name: /Open info for Weekly Schedule Planning/i }));
    const infoDialog = await screen.findByRole("dialog", { name: "Weekly Schedule Planning info" });
    expect(within(infoDialog).getByText("2 linked runs, choose one")).toBeInTheDocument();
    expect(
      within(infoDialog).getByText(/Weekly workpages switch to the review-ready run/i)
    ).toBeInTheDocument();
    expect(within(infoDialog).getByRole("button", { name: /Current walkthrough · wr-weekly-001/i })).toBeInTheDocument();
    expect(within(infoDialog).getByRole("button", { name: /Review-ready weekly · wr-weekly-002/i })).toBeInTheDocument();

    await user.click(within(infoDialog).getByRole("button", { name: /Current walkthrough · wr-weekly-001/i }));

    expect(
      within(launcher).getByRole("link", { name: "Open schedule workpage" })
    ).toHaveAttribute("href", "/runs/wr-weekly-002/workpages/schedule-v0");
    expect(window.location.search).toContain("workflow_run_id=wr-weekly-002");
  });

  it("keeps dispatch reporting on the current run when reporting companions exist", async () => {
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
                  drilldown_kind: "run_group",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-report-001",
                      workflow_id: "dispatch_reporting.v1",
                      partition_key: "SD-2026-03-06"
                    },
                    {
                      workflow_run_id: "wr-report-002",
                      workflow_id: "dispatch_reporting.v1",
                      partition_key: "SD-2026-03-06"
                    }
                  ],
                  artifact_refs: [],
                  selection_summary: "2 linked runs, choose one"
                }
              ],
              edges: []
            },
            linked_workflow_runs: {
              weekly_schedule_planning: [],
              live_dispatch: [],
              dispatch_reporting: [
                {
                  workflow_run_id: "wr-report-001",
                  workflow_id: "dispatch_reporting.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "SD-2026-03-06",
                  logical_date: "SD-2026-03-06",
                  activation_key: "logistics-demo:reporting:current:SD-2026-03-06",
                  state: "OPEN",
                  active_issueCount: 1,
                  active_issue_count: 1,
                  created_at: "2026-03-09T00:00:00Z",
                  updated_at: "2026-03-09T00:00:00Z"
                },
                {
                  workflow_run_id: "wr-report-002",
                  workflow_id: "dispatch_reporting.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "SD-2026-03-06",
                  logical_date: "SD-2026-03-06",
                  activation_key: "logistics-demo:reporting:review-ready:SD-2026-03-06",
                  state: "READY",
                  active_issueCount: 0,
                  active_issue_count: 0,
                  created_at: "2026-03-10T00:00:00Z",
                  updated_at: "2026-03-10T00:00:00Z"
                }
              ],
              summary: {
                weekly_schedule_planning_count: 0,
                live_dispatch_count: 0,
                dispatch_reporting_count: 2
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

    window.history.pushState(
      {},
      "",
      "/demo/logistics?planning_week_id=PW-2026-W10&module=dispatch_reporting"
    );
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    const launcher = await within(detailPanel).findByTestId(
      "logistics-module-launcher-dispatch_reporting"
    );
    expect(
      within(launcher).getByRole("link", { name: "Open EOD workpage" })
    ).toHaveAttribute("href", "/runs/wr-report-001/workpages/eod-v0");
    await waitFor(() =>
      expect(window.location.search).toContain("workflow_run_id=wr-report-001")
    );
  });

  it("does not fetch weekly workpages while the dispatch reporting demo shell is open", async () => {
    const scheduleSpy = vi.spyOn(workpagesRepository, "scheduleForRun");
    const routeDemandSpy = vi.spyOn(workpagesRepository, "routeDemandForRun");
    const driverPreferencesSpy = vi.spyOn(workpagesRepository, "driverPreferencesForRun");
    setFrontendOperatorContext();
    window.history.pushState(
      {},
      "",
      "/demo/logistics?planning_week_id=PW-2026-W10&service_date_id=SD-2026-03-06&module=dispatch_reporting&workflow_run_id=wr-report-001"
    );

    try {
      render(<App />);

      const page = await screen.findByTestId("logistics-demo-page");
      const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
      expect(
        await within(detailPanel).findByTestId("logistics-module-launcher-dispatch_reporting")
      ).toBeInTheDocument();
      expect(scheduleSpy).not.toHaveBeenCalled();
      expect(routeDemandSpy).not.toHaveBeenCalled();
      expect(driverPreferencesSpy).not.toHaveBeenCalled();
    } finally {
      scheduleSpy.mockRestore();
      routeDemandSpy.mockRestore();
      driverPreferencesSpy.mockRestore();
    }
  });

  it(
    "keeps family-node artifacts behind the selected-module info dialog",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState(
        {},
        "",
        "/demo/logistics?planning_week_id=PW-2026-W10&module=weekly_schedule_planning"
      );
      render(<App />);

      const page = await screen.findByTestId("logistics-demo-page");
      const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
      expect(within(detailPanel).queryByRole("button", { name: "View family node artifacts" })).not.toBeInTheDocument();

      await user.click(within(detailPanel).getByRole("button", { name: /Open info for Weekly Schedule Planning/i }));
      const infoDialog = await screen.findByRole("dialog", { name: "Weekly Schedule Planning info" });
      await user.click(within(infoDialog).getByRole("button", { name: "View family node artifacts" }));

      expect(await screen.findByRole("heading", { name: "Downloadable Artifacts (1)" })).toBeInTheDocument();
      expect(screen.getByText("weekly_schedule.xlsx")).toBeInTheDocument();
      expect(screen.getByText("Official output")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Download" }));

      await waitFor(() => {
        expect(mutationLog()).toContain("artifact-download-bin:av-weekly-001");
      });
    },
    10000
  );

  it("omits the family-node artifact drawer link when the selected module has no artifacts", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");

    await user.click(within(detailPanel).getByRole("button", { name: /Open info for Dispatch Reporting/i }));

    const infoDialog = await screen.findByRole("dialog", { name: "Dispatch Reporting info" });
    expect(within(infoDialog).getByText("No family-node artifacts linked.")).toBeInTheDocument();
  });

  it(
    "launches the canonical weekly schedule workpage from the demo-shell launcher",
    async () => {
      const user = userEvent.setup();
      setFrontendOperatorContext();
      window.history.pushState(
        {},
        "",
        "/demo/logistics?planning_week_id=PW-2026-W10&module=weekly_schedule_planning"
      );
      render(<App />);

      const page = await screen.findByTestId("logistics-demo-page");
      const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
      await waitFor(() => {
        expect(
          within(detailPanel).getByRole("link", { name: "Open schedule workpage" })
        ).toHaveAttribute("href", "/runs/wr-weekly-001/workpages/schedule-v0");
      });

      await user.click(within(detailPanel).getByRole("link", { name: "Open schedule workpage" }));

      expect(await screen.findByTestId("schedule-workpage-page")).toBeInTheDocument();
      expect(window.location.pathname).toBe("/runs/wr-weekly-001/workpages/schedule-v0");
    },
    10000
  );

  it("opens a task modal from the shell task strip without leaving the logistics demo route", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await screen.findByTestId("logistics-demo-page");
    await user.click(
      await screen.findByTestId("logistics-task-strip-task-todo-ht-weekly-001")
    );

    expect(window.location.pathname).toBe("/demo/logistics");
    const taskModal = await screen.findByRole("dialog", {
      name: "Stage04 · Weekly Scheduling Plan Inputs"
    });
    expect(taskModal).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Claim" })).toBeInTheDocument();
    expect(within(taskModal).getByRole("link", { name: "Open Workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workspace"
    );
    expect(within(taskModal).getByRole("link", { name: "Open run detail (secondary)" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001"
    );
  });

  it("opens the exact task selected from the multi-task shell strip", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await screen.findByTestId("logistics-demo-page");
    await user.click(
      await screen.findByTestId("logistics-task-strip-task-todo-ht-reporting-001")
    );

    expect(window.location.pathname).toBe("/demo/logistics");
    const taskModal = await screen.findByRole("dialog", {
      name: "Stage01 · End of Day Dispatch Report"
    });
    expect(taskModal).toBeInTheDocument();
    expect(within(taskModal).getByRole("link", { name: "Open Workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-report-001/workspace"
    );
  });

  it("runs task actions from the expanded board and refreshes the lane contents", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    await user.click(within(page).getByRole("button", { name: "Show task board" }));

    const openTasksLane = within(page).getByLabelText("To Do");
    await user.click(
      within(openTasksLane).getByRole("button", { name: /Weekly Scheduling Plan Inputs/i })
    );

    await user.click(await screen.findByRole("button", { name: "Claim" }));

    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-weekly-001");
    });
    await waitFor(() => {
      expect(
        within(within(page).getByLabelText("To Do")).queryByText(/Weekly Scheduling Plan Inputs/i)
      ).not.toBeInTheDocument();
      expect(
        within(within(page).getByLabelText("In Progress")).getByText(/Weekly Scheduling Plan Inputs/i)
      ).toBeInTheDocument();
    });
    expect(await screen.findByRole("button", { name: "Complete Task" })).toBeInTheDocument();
  });
});
