import dispatchCreateSnapshot from "@fixtures/workspace_eod_workpage_action_create_state.json";
import dispatchOpenSnapshot from "@fixtures/workspace_eod_workpage_action_open_state.json";
import scheduleAvailableSnapshot from "@fixtures/workspace_schedule_workpage_action_available_state.json";
import scheduleUnavailableSnapshot from "@fixtures/workspace_schedule_workpage_action_unavailable_state.json";
import { http, HttpResponse } from "msw";

import { onetruthApi } from "@/lib/api/onetruthApi";
import { server } from "@/test/api/server";

function firstWorkpageAction(snapshot: { workspace: Record<string, unknown> }) {
  const workspace = snapshot.workspace as {
    user_work?: Array<Record<string, unknown>>;
    blocking_work?: Array<Record<string, unknown>>;
  };
  const items = [...(workspace.user_work ?? []), ...(workspace.blocking_work ?? [])];
  for (const item of items) {
    const actions = item.workpage_actions;
    if (Array.isArray(actions) && actions.length > 0) {
      return actions[0] as Record<string, unknown>;
    }
  }
  throw new Error("expected at least one workpage action in snapshot");
}

describe("onetruthApi workspace parsing", () => {
  it("normalizes schedule workpage actions including available and unavailable states", async () => {
    server.use(
      http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", ({ params }) => {
        if (String(params.workflowRunId) === "wr-weekly-unavailable") {
          return HttpResponse.json(scheduleUnavailableSnapshot.workspace);
        }
        return HttpResponse.json(scheduleAvailableSnapshot.workspace);
      })
    );

    const available = await onetruthApi.getWorkflowRunWorkspace("wr-weekly-available");
    const unavailable = await onetruthApi.getWorkflowRunWorkspace("wr-weekly-unavailable");

    const availableItem = [...available.user_work, ...available.blocking_work].find(
      (item) => item.item_kind === "human_task" && item.workpage_actions.length > 0
    );
    const unavailableItem = [...unavailable.user_work, ...unavailable.blocking_work].find(
      (item) => item.item_kind === "human_task" && item.workpage_actions.length > 0
    );

    expect(availableItem?.workpage_actions[0]).toMatchObject({
      ...firstWorkpageAction(scheduleAvailableSnapshot),
      presentation: "open_route",
      state: "available"
    });
    expect(unavailableItem?.workpage_actions[0]).toMatchObject({
      ...firstWorkpageAction(scheduleUnavailableSnapshot),
      presentation: "open_route",
      state: "unavailable",
      route: null,
      create_path: null
    });
  });

  it("normalizes dispatch workpage actions for create and open flows", async () => {
    server.use(
      http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", ({ params }) => {
        if (String(params.workflowRunId) === "wr-reporting-open") {
          return HttpResponse.json(dispatchOpenSnapshot.workspace);
        }
        return HttpResponse.json(dispatchCreateSnapshot.workspace);
      })
    );

    const createWorkspace = await onetruthApi.getWorkflowRunWorkspace("wr-reporting-create");
    const openWorkspace = await onetruthApi.getWorkflowRunWorkspace("wr-reporting-open");

    const createItem = [...createWorkspace.user_work, ...createWorkspace.blocking_work].find(
      (item) => item.item_kind === "approval" && item.workpage_actions.length > 0
    );
    const openItem = [...openWorkspace.user_work, ...openWorkspace.blocking_work].find(
      (item) => item.item_kind === "approval" && item.workpage_actions.length > 0
    );

    expect(createItem?.workpage_actions[0]).toMatchObject({
      ...firstWorkpageAction(dispatchCreateSnapshot),
      presentation: "create_draft_then_open",
      route: null
    });
    expect(openItem?.workpage_actions[0]).toMatchObject({
      ...firstWorkpageAction(dispatchOpenSnapshot),
      presentation: "open_route",
      create_path: null
    });
  });
});
