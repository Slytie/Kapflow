import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { WorkspaceTaskBoard } from "@/components/WorkspaceTaskBoard";
import { humanTasksRepository } from "@/lib/repositories";
import type {
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract
} from "@/lib/types/contracts";
import {
  buildWorkflowRunDetail,
  buildWorkflowRunWorkspace,
  createContractState
} from "@/test/api/contractState";

function renderBoard(
  workspace: WorkflowRunWorkspaceContract,
  detail: WorkflowRunDetailContract
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <WorkspaceTaskBoard
          workflowRunId={detail.workflow_run.workflow_run_id}
          workspace={workspace}
          detail={detail}
          onRefresh={() => undefined}
          onOpenDetails={() => undefined}
        />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

function buildWeeklyBuildSurface(): {
  workspace: WorkflowRunWorkspaceContract;
  detail: WorkflowRunDetailContract;
} {
  const state = createContractState();
  state.humanTasks = state.humanTasks.map((task) =>
    task.human_task_id === "ht-claimed-002"
      ? {
          ...task,
          stage_id: "Stage04",
          task_kind: "work_item",
          owner_role: "schedule_planner",
          candidate_roles: ["schedule_planner"]
        }
      : task
  );
  const detail = buildWorkflowRunDetail(state, "wr-test-001");
  const baseWorkspace = buildWorkflowRunWorkspace(state, "wr-test-001");
  const patchTaskItem = (
    item: WorkflowRunWorkspaceContract["user_work"][number]
  ): typeof item =>
    item.item_kind === "human_task" && item.human_task.human_task_id === "ht-claimed-002"
      ? {
          ...item,
          available_actions: ["run_weekly_stage04_openai_agent", "upload_attachment"],
          required_uploads: [],
          required_reviews: [],
          missing_required_inputs: [],
          blocking_reason_codes: []
        }
      : item;
  return {
    detail,
    workspace: {
      ...baseWorkspace,
      user_work: baseWorkspace.user_work.map(patchTaskItem),
      blocking_work: baseWorkspace.blocking_work.map(patchTaskItem)
    }
  };
}

function buildWeeklyIntakeSurface(): {
  workspace: WorkflowRunWorkspaceContract;
  detail: WorkflowRunDetailContract;
} {
  const state = createContractState();
  state.humanTasks = state.humanTasks.map((task) =>
    task.human_task_id === "ht-claimed-002"
      ? {
          ...task,
          stage_id: "Stage04",
          task_kind: "weekly_input_intake",
          owner_role: "schedule_planner",
          candidate_roles: ["schedule_planner"]
        }
      : task
  );
  const detail = buildWorkflowRunDetail(state, "wr-test-001");
  const baseWorkspace = buildWorkflowRunWorkspace(state, "wr-test-001");
  const patchTaskItem = (
    item: WorkflowRunWorkspaceContract["user_work"][number]
  ): typeof item =>
    item.item_kind === "human_task" && item.human_task.human_task_id === "ht-claimed-002"
      ? {
          ...item,
          available_actions: ["upload_attachment"],
          required_uploads: [
            {
              dataset_key: "planning.route_slot_requirements.workbook",
              artifact_kind: "planning.route_slot_requirements.workbook",
              artifact_role: "official_input",
              required: true,
              required_count: 1,
              current_count: 0,
              status: "missing"
            }
          ],
          required_reviews: [],
          missing_required_inputs: ["planning.route_slot_requirements.workbook"],
          blocking_reason_codes: [
            "required_upload_missing:planning.route_slot_requirements.workbook"
          ]
        }
      : item;
  return {
    detail,
    workspace: {
      ...baseWorkspace,
      user_work: baseWorkspace.user_work.map(patchTaskItem),
      blocking_work: baseWorkspace.blocking_work.map(patchTaskItem)
    }
  };
}

describe("WorkspaceTaskBoard weekly surfaces", () => {
  it("renders the weekly Stage04 build action and invokes the repository method", async () => {
    const user = userEvent.setup();
    const runSpy = vi
      .spyOn(humanTasksRepository, "runWeeklyStage04OpenAIAgent")
      .mockResolvedValue();
    const { workspace, detail } = buildWeeklyBuildSurface();
    renderBoard(workspace, detail);

    const card = (await screen.findByRole("heading", { name: "Build Weekly Draft" })).closest("article");
    expect(card).not.toBeNull();

    await user.click(
      within(card as HTMLElement).getByLabelText("Actions for Build Weekly Draft")
    );
    await user.click(
      within(card as HTMLElement).getByRole("button", { name: "Run Stage04 Build" })
    );

    await waitFor(() => {
      expect(runSpy).toHaveBeenCalledWith("ht-claimed-002");
    });

    runSpy.mockRestore();
  });

  it("labels weekly intake requirements as required inputs with upload-input copy", async () => {
    const { workspace, detail } = buildWeeklyIntakeSurface();
    renderBoard(workspace, detail);

    const card = (await screen.findByRole("heading", { name: "Weekly Intake" })).closest("article");
    expect(card).not.toBeNull();
    expect(
      within(card as HTMLElement).getByText(
        /Required input: planning\.route_slot_requirements\.workbook/i
      )
    ).toBeInTheDocument();
    expect(
      within(card as HTMLElement).getByRole("button", { name: "Upload Input" })
    ).toBeInTheDocument();
  });
});
