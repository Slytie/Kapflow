import { HttpResponse, http } from "msw";

import { onetruthApi } from "@/lib/api/onetruthApi";
import { server } from "@/test/api/server";

describe("onetruthApi logistics story parsing", () => {
  it("normalizes family-module drilldown metadata with backward-compatible defaults", async () => {
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
                  module_id: "live_dispatch",
                  workflow_id: "live_dispatch.v1",
                  partition_kind: "ServiceDateID",
                  activation_policy: "event_driven",
                  status: "active",
                  drilldown_refs: [
                    {
                      workflow_run_id: "wr-live-001",
                      workflow_id: "live_dispatch.v1",
                      partition_key: "SD-2026-03-06"
                    },
                    {
                      workflow_run_id: "wr-live-002",
                      workflow_id: "live_dispatch.v1",
                      partition_key: "SD-2026-03-06"
                    }
                  ],
                  artifact_refs: [{ artifact_version_id: "av-live-001" }]
                }
              ],
              edges: []
            },
            linked_workflow_runs: {
              weekly_schedule_planning: [],
              live_dispatch: [],
              dispatch_reporting: [],
              summary: {
                weekly_schedule_planning_count: 0,
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
              latest_event_recorded_at: null,
              max_workflow_run_updated_at: null,
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

    const story = await onetruthApi.getLogisticsThreeWorkflowStory({
      planning_week_id: "PW-2026-W10"
    });

    expect(story.family_graph.modules).toHaveLength(1);
    expect(story.family_graph.modules[0]).toMatchObject({
      node_kind: "module",
      drilldown_kind: "run_group",
      drilldown_refs: [
        {
          workflow_run_id: "wr-live-001",
          workflow_id: "live_dispatch.v1",
          partition_key: "SD-2026-03-06"
        },
        {
          workflow_run_id: "wr-live-002",
          workflow_id: "live_dispatch.v1",
          partition_key: "SD-2026-03-06"
        }
      ],
      artifact_refs: [
        {
          artifact_version_id: "av-live-001",
          label: "av-live-001",
          source_label: "Artifact"
        }
      ],
      selection_summary: "2 linked runs, 1 downloadable artifact"
    });
  });
});
