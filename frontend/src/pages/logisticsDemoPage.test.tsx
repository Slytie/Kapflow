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

  it("shows workspace-first header entrypoints and keeps workpages contextual", async () => {
    setFrontendOperatorContext();
    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    const weeklyHeader = within(page).getByText("Start Here: Weekly Planning").closest("div") as HTMLElement;
    const liveHeader = within(page).getByText("Step 2: Live Dispatch").closest("div") as HTMLElement;
    const reportingHeader = within(page).getByText("Step 3: Reporting").closest("div") as HTMLElement;
    const contextualHeader = within(page).getByText("Contextual workpages").closest("div") as HTMLElement;

    expect(weeklyHeader).toBeInTheDocument();
    expect(within(weeklyHeader).getByRole("link", { name: "Open weekly workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workspace"
    );
    expect(within(weeklyHeader).getByText(/OPENAI_API_KEY/i)).toBeInTheDocument();
    expect(liveHeader).toBeInTheDocument();
    expect(
      within(liveHeader).getByText(/Publish the current weekly schedule first/i)
    ).toBeInTheDocument();
    expect(reportingHeader).toBeInTheDocument();
    expect(within(reportingHeader).getByRole("link", { name: "Open reporting workspace" })).toHaveAttribute(
      "href",
      "/runs/wr-report-001/workspace"
    );
    expect(contextualHeader).toBeInTheDocument();
    expect(within(contextualHeader).getByRole("link", { name: "Open weekly review workpage" })).toHaveAttribute(
      "href",
      "/runs/wr-weekly-001/workpages/schedule-v0"
    );
    expect(within(contextualHeader).getByRole("link", { name: "Open EOD workpage" })).toHaveAttribute(
      "href",
      "/runs/wr-report-001/workpages/eod-v0"
    );
    expect(within(contextualHeader).getByRole("link", { name: "Open demo schedule alias" })).toHaveAttribute(
      "href",
      "/demo/logistics/workpages/schedule-v0"
    );
    expect(within(contextualHeader).getByRole("link", { name: "Open demo EOD alias" })).toHaveAttribute(
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
    expect(within(page).queryByRole("link", { name: "Open weekly workspace" })).not.toBeInTheDocument();
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
      within(openTasksLane).getByRole("button", { name: /Stage04 weekly_input_intake/i })
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
      within(openTasksLane).getByRole("button", { name: /Stage04 weekly_input_intake/i })
    );

    await user.click(await screen.findByRole("button", { name: "Claim" }));

    await waitFor(() => {
      expect(mutationLog()).toContain("claim:ht-weekly-001");
    });
    await waitFor(() => {
      expect(within(within(page).getByLabelText("Open Tasks")).queryByText(/Stage04 weekly_input_intake/i)).not.toBeInTheDocument();
      expect(within(within(page).getByLabelText("Claimed Tasks")).getByText(/Stage04 weekly_input_intake/i)).toBeInTheDocument();
    });
    expect(await screen.findByRole("button", { name: "Complete" })).toBeInTheDocument();
  });

  it("prepares the live day from the shell and exposes the live task artifact drawer", async () => {
    const user = userEvent.setup();
    setFrontendOperatorContext();
    let prepared = false;

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
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-report-001",
                      workflow_id: "dispatch_reporting.v1",
                      partition_key: "SD-2026-03-06"
                    }
                  ],
                  artifact_refs: [],
                  selection_summary: "1 linked run, 0 downloadable artifacts"
                },
                {
                  module_id: "weekly_schedule_planning",
                  workflow_id: "weekly_schedule_planning.v1",
                  partition_kind: "PlanningWeekID",
                  activation_policy: "manual_or_event",
                  status: "active",
                  node_kind: "module",
                  drilldown_kind: "workflow_run",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-weekly-001",
                      workflow_id: "weekly_schedule_planning.v1",
                      partition_key: "PW-2026-W10"
                    }
                  ],
                  artifact_refs: prepared
                    ? [
                        {
                          artifact_version_id: "av-weekly-001",
                          label: "weekly_schedule.xlsx",
                          source_label: "Official output"
                        }
                      ]
                    : [
                        {
                          artifact_version_id: "av-weekly-001",
                          label: "weekly_schedule.xlsx",
                          source_label: "Official output"
                        }
                      ],
                  selection_summary: "1 linked run, 1 downloadable artifact"
                },
                {
                  module_id: "live_dispatch",
                  workflow_id: "live_dispatch.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "event_driven",
                  status: prepared ? "active" : "ready",
                  node_kind: "module",
                  drilldown_kind: prepared ? "workflow_run" : "none",
                  drilldown_refs: prepared
                    ? [
                        {
                          workflow_run_id: "wr-live-001",
                          workflow_id: "live_dispatch.v1",
                          partition_key: "SD-2026-03-06"
                        }
                      ]
                    : [],
                  artifact_refs: [],
                  selection_summary: prepared
                    ? "1 linked run, 0 downloadable artifacts"
                    : "0 linked runs, prepare service day after weekly publish"
                }
              ],
              edges: [
                {
                  edge_id: "reporting_actuals_to_future_planning",
                  source_module_id: "dispatch_reporting",
                  target_module_id: "weekly_schedule_planning",
                  source_stage_id: "Stage05",
                  source_dataset_key: "reporting.final_packet.workbook",
                  target_stage_id: "Stage03",
                  target_dataset_key: "planning.actual_hours_snapshot.workbook",
                  partition_transform_id: "service_day_to_future_planning_week",
                  handoff_mode: "notify_only",
                  writer_mode: "source_only",
                  status: "active"
                },
                {
                  edge_id: "weekly_seed_to_live_dispatch",
                  source_module_id: "weekly_schedule_planning",
                  target_module_id: "live_dispatch",
                  source_stage_id: "Stage07",
                  source_dataset_key: "planning.daily_dispatch_seed.workbook",
                  target_stage_id: "Stage01",
                  target_dataset_key: "dispatch.base_schedule_seed.workbook",
                  partition_transform_id: "planning_week_to_service_date",
                  handoff_mode: "materialize_seed",
                  writer_mode: "target_materialize",
                  status: "active"
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
                }
              ],
              live_dispatch: prepared
                ? [
                    {
                      workflow_run_id: "wr-live-001",
                      workflow_id: "live_dispatch.v1",
                      workflow_version: "v1",
                      tenant_id: "tenant-a",
                      domain_id: "domain-x",
                      partition_key: "SD-2026-03-06",
                      logical_date: "SD-2026-03-06",
                      activation_key: "live_dispatch.v1:SD-2026-03-06",
                      state: "OPEN",
                      active_issue_count: 0,
                      created_at: "2026-03-09T00:00:00Z",
                      updated_at: "2026-03-09T00:00:00Z"
                    }
                  ]
                : [],
              dispatch_reporting: [
                {
                  workflow_run_id: "wr-report-001",
                  workflow_id: "dispatch_reporting.v1",
                  workflow_version: "v1",
                  tenant_id: "tenant-a",
                  domain_id: "domain-x",
                  partition_key: "SD-2026-03-06",
                  logical_date: "SD-2026-03-06",
                  activation_key: "dispatch_reporting.v1:SD-2026-03-06",
                  state: "OPEN",
                  active_issue_count: 0,
                  created_at: "2026-03-09T00:00:00Z",
                  updated_at: "2026-03-09T00:00:00Z"
                }
              ],
              summary: {
                weekly_schedule_planning_count: 1,
                live_dispatch_count: prepared ? 1 : 0,
                dispatch_reporting_count: 1
              }
            },
            handoff_activity: {
              edges: [],
              summary: {
                edge_execution_count: prepared ? 1 : 0,
                coherence_failed_count: 0
              }
            },
            board: {
              lanes: [
                { lane: "human_tasks.open", label: "Open Tasks", position: 10, item_count: prepared ? 3 : 2 },
                { lane: "human_tasks.claimed", label: "Claimed Tasks", position: 20, item_count: 0 }
              ],
              work_items: [
                {
                  item_id: "human_task:ht-weekly-001",
                  item_type: "human_task",
                  lane: "human_tasks.open",
                  title: "Stage04 weekly_input_intake",
                  workflow_run_id: "wr-weekly-001",
                  workflow_id: "weekly_schedule_planning.v1",
                  subject_id: "ht-weekly-001",
                  stage_id: "Stage04",
                  task_kind: "weekly_input_intake",
                  state: "OPEN",
                  owner_role: "schedule_planner",
                  available_actions: ["claim"],
                  blocking_reason_codes: [],
                  missing_required_inputs: [],
                  linked_artifact_count: 0
                },
                ...(prepared
                  ? [
                      {
                        item_id: "human_task:ht-live-001",
                        item_type: "human_task",
                        lane: "human_tasks.open",
                        title: "Stage01 dispatch_seed_intake",
                        workflow_run_id: "wr-live-001",
                        workflow_id: "live_dispatch.v1",
                        subject_id: "ht-live-001",
                        stage_id: "Stage01",
                        task_kind: "dispatch_seed_intake",
                        state: "OPEN",
                        owner_role: "dispatch_supervisor",
                        available_actions: ["claim", "upload_attachment"],
                        blocking_reason_codes: [],
                        missing_required_inputs: [],
                        linked_artifact_count: 1
                      }
                    ]
                  : []),
                {
                  item_id: "human_task:ht-reporting-001",
                  item_type: "human_task",
                  lane: "human_tasks.open",
                  title: "Stage01 eos_input_intake",
                  workflow_run_id: "wr-report-001",
                  workflow_id: "dispatch_reporting.v1",
                  subject_id: "ht-reporting-001",
                  stage_id: "Stage01",
                  task_kind: "eos_input_intake",
                  state: "OPEN",
                  owner_role: "dispatch_supervisor",
                  available_actions: ["claim"],
                  blocking_reason_codes: [],
                  missing_required_inputs: [],
                  linked_artifact_count: 0
                }
              ],
              page: { limit: 100, offset: 0 },
              summary: {
                work_item_count: prepared ? 3 : 2,
                human_task_count: prepared ? 3 : 2,
                approval_count: 0,
                flag_count: 0,
                primary_actionable_count: prepared ? 3 : 2,
                workflow_item_counts: {
                  "weekly_schedule_planning.v1": 1,
                  ...(prepared ? { "live_dispatch.v1": 1 } : {}),
                  "dispatch_reporting.v1": 1
                }
              }
            },
            official_outputs: {
              pointers: [],
              pointer_outputs: [],
              official_output_artifacts: [
                {
                  artifact_version_id: "av-weekly-001",
                  workflow_run_id: "wr-weekly-001",
                  task_run_id: null,
                  artifact_kind: "planning.published_weekly_schedule.workbook",
                  artifact_role: "official_output",
                  media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                  storage_uri: "memory://story/av-weekly-001.xlsx",
                  content_digest: "sha256:weekly001",
                  byte_size: 1024,
                  metadata_json: { file_name: "weekly_schedule.xlsx" },
                  parent_artifact_version_id: null,
                  supersedes_artifact_version_id: null,
                  lineage_note: null,
                  created_at: "2026-03-09T00:00:00Z"
                }
              ],
              coherence: {},
              summary: {
                pointer_count: 0,
                pointer_output_count: 0,
                official_output_artifact_count: 1,
                artifact_kind_counts: {
                  "planning.published_weekly_schedule.workbook": 1
                }
              }
            },
            freshness: {
              latest_event_sequence: 44,
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
      ),
      http.post("*/api/v1/workflow-runs/:workflowRunId/prepare-live-dispatch-day", () => {
        prepared = true;
        return HttpResponse.json({
          status: "ok",
          command: "api.workflow_runs.prepare_live_dispatch_day",
          workflow_run_id: "wr-weekly-001",
          result: {
            edge_execution: {
              edge_execution_id: "edge-weekly-live-001",
              edge_id: "weekly_seed_to_live_dispatch",
              source_workflow_run_id: "wr-weekly-001",
              target_workflow_run_id: "wr-live-001",
              target_partition_key: "SD-2026-03-06",
              status: "activated"
            },
            target_workflow_run: {
              workflow_run_id: "wr-live-001",
              workflow_id: "live_dispatch.v1",
              workflow_version: "v1",
              tenant_id: "tenant-a",
              domain_id: "domain-x",
              partition_key: "SD-2026-03-06",
              logical_date: "SD-2026-03-06",
              activation_key: "live_dispatch.v1:SD-2026-03-06",
              state: "OPEN",
              active_issue_count: 0,
              created_at: "2026-03-09T00:00:00Z",
              updated_at: "2026-03-09T00:00:00Z"
            },
            live_seed_artifact: {
              artifact_version_id: "av-live-001",
              workflow_run_id: "wr-live-001",
              task_run_id: "tr-live-stage01-001",
              artifact_kind: "dispatch.base_schedule_seed.workbook",
              artifact_role: "official_input",
              media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              storage_uri: "memory://story/av-live-001.xlsx",
              content_digest: "sha256:live001",
              byte_size: 860,
              metadata_json: {},
              parent_artifact_version_id: "av-weekly-001",
              supersedes_artifact_version_id: null,
              lineage_note: null,
              created_at: "2026-03-09T00:00:00Z"
            },
            seed_intake_task: {
              human_task_id: "ht-live-001",
              workflow_run_id: "wr-live-001",
              task_run_id: "tr-live-stage01-001",
              task_kind: "dispatch_seed_intake",
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
              created_at: "2026-03-09T00:00:00Z",
              updated_at: "2026-03-09T00:00:00Z",
              task_run_state: "READY",
              stage_id: "Stage01",
              blocked_on_kind: null,
              blocked_on_ref: null,
              spawned_from_flag_id: null,
              available_actions: ["claim", "upload_attachment"],
              blocking_reason_codes: [],
              missing_required_inputs: [],
              is_composite: true
            }
          }
        });
      })
    );

    window.history.pushState({}, "", "/demo/logistics?planning_week_id=PW-2026-W10");
    render(<App />);

    const page = await screen.findByTestId("logistics-demo-page");
    await user.click(within(page).getByRole("button", { name: "Prepare service day" }));

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Open live dispatch workspace" })).toHaveAttribute(
        "href",
        "/runs/wr-live-001/workspace"
      );
    });

    const openTasksLane = within(page).getByLabelText("Open Tasks");
    await user.click(
      within(openTasksLane).getByRole("button", { name: /Stage01 dispatch_seed_intake/i })
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
