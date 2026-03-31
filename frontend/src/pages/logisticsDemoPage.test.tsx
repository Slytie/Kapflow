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
        /The shell nav drives workflow switching\. This page keeps the selected module context, run drill-down, and inline work surface together\./i
      )
    ).not.toBeInTheDocument();
    expect(within(detailPanel).getByRole("heading", { name: "Weekly Schedule Planning" })).toBeInTheDocument();

    const inlineSchedule = await within(detailPanel).findByTestId("logistics-inline-schedule-artifact");
    const inlineScheduleSummary = within(inlineSchedule).getByTestId("workpage-summary-section");
    expect(
      within(inlineScheduleSummary).getByRole("heading", { name: "Draft workbook summary" })
    ).toBeInTheDocument();
    expect(
      within(inlineScheduleSummary).getByTestId("workpage-summary-card-route_assignment_count")
    ).toHaveClass("workpage-summary-card");
    expect(within(inlineScheduleSummary).getByText("158")).toBeInTheDocument();
    const inlineTitleBar = inlineSchedule.querySelector(".workpage-page__hero-title-bar");
    const inlineHeroActions = inlineSchedule.querySelector(".workpage-page__hero-actions");
    expect(inlineTitleBar).not.toBeNull();
    expect(inlineTitleBar).toHaveClass("workpage-page__hero-title-bar--sticky");
    expect(inlineHeroActions).not.toBeNull();
    expect(
      within(inlineTitleBar as HTMLElement).getByRole("button", { name: "Submit draft" })
    ).toBeInTheDocument();
    expect(
      within(inlineTitleBar as HTMLElement).getByRole("button", { name: "Download draft JSON" })
    ).toBeInTheDocument();
    expect(
      within(inlineHeroActions as HTMLElement).getByRole("link", { name: "Open full workpage" })
    ).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-001"
    );
    expect(
      within(inlineHeroActions as HTMLElement).queryByRole("button", { name: "Download draft JSON" })
    ).not.toBeInTheDocument();
    expect(within(detailPanel).getByLabelText("Weekly draft versions timeline")).toBeInTheDocument();
    expect(within(inlineSchedule).queryByRole("heading", { name: "Draft actions" })).not.toBeInTheDocument();
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

  it("keeps node metadata behind the info dialog instead of in the main detail panel", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).getByRole("heading", { name: "Dispatch Reporting" })).toBeInTheDocument();
    expect(within(detailPanel).queryByText("dispatch_reporting.v1")).not.toBeInTheDocument();
    expect(within(detailPanel).queryByText("View family node artifacts")).not.toBeInTheDocument();
    expect(within(detailPanel).queryByText("Workflow Run Drill-Down")).not.toBeInTheDocument();

    await user.click(within(detailPanel).getByRole("button", { name: /Open info for Dispatch Reporting/i }));

    const infoDialog = await screen.findByRole("dialog", { name: "Dispatch Reporting info" });
    expect(within(infoDialog).getByText("dispatch_reporting.v1")).toBeInTheDocument();
    expect(within(infoDialog).getByText("manual_or_event")).toBeInTheDocument();
    expect(within(infoDialog).getByText("active")).toBeInTheDocument();
    expect(within(infoDialog).getByText("workflow_run")).toBeInTheDocument();
  });

  it("keeps inline EOD source grounding behind the workpage title info button", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    const inlineEod = await within(detailPanel).findByTestId(/logistics-inline-eod-(landing|artifact)/);
    const expectedDialogTitle =
      inlineEod.getAttribute("data-testid") === "logistics-inline-eod-artifact"
        ? "EOD draft context"
        : "Dispatch reporting context";
    const inlineEodSummary = within(inlineEod).getByTestId("workpage-summary-section");
    expect(within(inlineEodSummary).getByRole("heading", { name: "Daily summary" })).toBeInTheDocument();
    expect(
      within(inlineEodSummary).getByTestId("workpage-summary-card-packages_dispatched")
    ).toHaveClass("workpage-summary-card");

    expect(within(inlineEod).queryByRole("heading", { name: "Source grounding" })).not.toBeInTheDocument();
    expect(within(inlineEod).queryByRole("heading", { name: "Formula-integrity warning" })).not.toBeInTheDocument();
    expect(within(inlineEod).queryByRole("heading", { name: "Artifact-backed projection note" })).not.toBeInTheDocument();
    if (inlineEod.getAttribute("data-testid") === "logistics-inline-eod-artifact") {
      expect(within(detailPanel).getByLabelText("Reporting draft versions timeline")).toBeInTheDocument();
    }

    await user.click(within(inlineEod).getByRole("button", { name: /Open info for End-of-day report/i }));

    const infoDialog = await screen.findByRole("dialog", { name: expectedDialogTitle });
    expect(within(infoDialog).getByRole("heading", { name: "Source grounding" })).toBeInTheDocument();
    expect(
      within(infoDialog).queryByRole("heading", {
        name: /Formula-integrity warning|Artifact-backed projection note/i
      })
    ).toBeInTheDocument();
    expect(
      within(infoDialog).getAllByText(
        expectedDialogTitle === "EOD draft context"
          ? /Artifact-backed projection of the immutable EOD draft workbook/i
          : /Run-backed dispatch reporting landing surface for the selected module run/i
      )
    ).not.toHaveLength(0);
    await user.click(screen.getByRole("button", { name: new RegExp(`Close ${expectedDialogTitle}`, "i") }));
  });

  it("requires explicit run selection when the selected module has multiple linked runs", async () => {
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

    window.history.pushState(
      {},
      "",
      "/demo/logistics?planning_week_id=PW-2026-W10&module=weekly_schedule_planning"
    );
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const detailPanel = within(page).getByTestId("logistics-module-detail-panel");
    expect(within(detailPanel).getByRole("heading", { name: "Weekly Schedule Planning" })).toBeInTheDocument();
    expect(
      within(detailPanel).getByText("Pick a linked run in the summary above to load the inline work surface here.")
    ).toBeInTheDocument();
    expect(within(page).queryByTestId("logistics-demo-drilldown-graph")).not.toBeInTheDocument();

    await user.click(within(detailPanel).getByRole("button", { name: /Open info for Weekly Schedule Planning/i }));
    const infoDialog = await screen.findByRole("dialog", { name: "Weekly Schedule Planning info" });
    expect(within(infoDialog).getByText("2 linked runs, choose one")).toBeInTheDocument();
    expect(within(infoDialog).getByText(/Choose the linked workflow run/i)).toBeInTheDocument();

    await user.click(within(infoDialog).getByRole("button", { name: /wr-weekly-002/i }));

    const inlineSchedule = await within(detailPanel).findByTestId("logistics-inline-schedule-landing");
    expect(
      within(inlineSchedule).getByRole("link", { name: "Open full workpage" })
    ).toHaveAttribute("href", "/runs/wr-weekly-002/workpages/schedule-v0");
    expect(window.location.search).toContain("workflow_run_id=wr-weekly-002");
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
    "switches weekly draft versions inline without leaving the logistics demo route",
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
      const inlineSchedule = await within(detailPanel).findByTestId("logistics-inline-schedule-artifact");
      expect(within(inlineSchedule).getByText("Artifact av-schedule-artifact-001")).toBeInTheDocument();

      await user.click(within(inlineSchedule).getByRole("button", { name: "Submit draft" }));

      await waitFor(() => {
        expect(mutationLog()).toContain(
          "workpage-schedule-artifact-submit:av-schedule-artifact-001:av-schedule-artifact-002"
        );
      });

      const refreshedInlineSchedule = await within(detailPanel).findByTestId(
        "logistics-inline-schedule-artifact"
      );
      expect(within(refreshedInlineSchedule).getByText("Artifact av-schedule-artifact-002")).toBeInTheDocument();

      const timeline = within(detailPanel).getByLabelText("Weekly draft versions timeline");
      expect(within(timeline).getByText("Current draft")).toBeInTheDocument();
      expect(within(timeline).getByText("Previous draft")).toBeInTheDocument();
      await user.click(within(timeline).getByRole("button", { name: /Previous draft/i }));

      await waitFor(() => {
        expect(within(detailPanel).getByText("Artifact av-schedule-artifact-001")).toBeInTheDocument();
      });
      expect(window.location.pathname).toBe("/demo/logistics");
    },
    10000
  );

  it("opens a task modal from the shell task strip without leaving the logistics demo route", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    await screen.findByTestId("logistics-demo-page");
    await user.click(screen.getByTestId("logistics-task-strip-card-todo"));

    expect(window.location.pathname).toBe("/demo/logistics");
    const taskModal = await screen.findByRole("dialog", { name: "Stage04 weekly_input_intake" });
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

  it("runs task actions from the expanded board and refreshes the lane contents", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    await user.click(within(page).getByRole("button", { name: "Show task board" }));

    const openTasksLane = within(page).getByLabelText("To Do");
    await user.click(
      within(openTasksLane).getByRole("button", { name: /Stage04 weekly_input_intake/i })
    );

    await user.click(await screen.findByRole("button", { name: "Claim" }));

    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-weekly-001");
    });
    await waitFor(() => {
      expect(
        within(within(page).getByLabelText("To Do")).queryByText(/Stage04 weekly_input_intake/i)
      ).not.toBeInTheDocument();
      expect(
        within(within(page).getByLabelText("In Progress")).getByText(/Stage04 weekly_input_intake/i)
      ).toBeInTheDocument();
    });
    expect(await screen.findByRole("button", { name: "Complete Task" })).toBeInTheDocument();
  });
});
