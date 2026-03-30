import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { WorkspaceTaskBoard } from "@/components/WorkspaceTaskBoard";
import { humanTasksRepository } from "@/lib/repositories";
import type {
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract
} from "@/lib/types/contracts";
import type { DrawerPayload } from "@/lib/types/ui";
import {
  buildWorkflowRunDetail,
  buildWorkflowRunWorkspace,
  createContractState
} from "@/test/api/contractState";

function renderBoard(
  workspace: WorkflowRunWorkspaceContract,
  detail: WorkflowRunDetailContract,
  onOpenDetails: (payload: DrawerPayload) => void = () => undefined
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
          onOpenDetails={onOpenDetails}
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

function buildDispatchReviewSurface(): {
  workspace: WorkflowRunWorkspaceContract;
  detail: WorkflowRunDetailContract;
} {
  const state = createContractState();
  state.humanTasks = state.humanTasks.map((task) =>
    task.human_task_id === "ht-claimed-002"
      ? {
          ...task,
          stage_id: "Stage04",
          task_kind: "final_packet_review",
          owner_role: "dispatch_supervisor",
          candidate_roles: ["dispatch_supervisor"]
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
          workpage_actions: [
            {
              action_id: "workpage.eod-v0.open_latest_draft",
              workpage_kind: "eod-v0",
              label: "Open EOD draft",
              presentation: "open_route",
              state: "available",
              route: "/runs/wr-test-001/workpages/eod-v0/artifacts/av-review-draft-001",
              create_path: null,
              subject_context: {
                subject_kind: "human_task",
                subject_id: "ht-claimed-002",
                workflow_run_id: "wr-test-001"
              },
              link_policy: {
                create_relation_kind: "draft",
                submit_relation_kind: "response"
              },
              disabled_reason: null
            }
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

function buildDispatchIntakeSurface(): {
  workspace: WorkflowRunWorkspaceContract;
  detail: WorkflowRunDetailContract;
} {
  const state = createContractState();
  state.humanTasks = state.humanTasks.map((task) =>
    task.human_task_id === "ht-claimed-002"
      ? {
          ...task,
          stage_id: "Stage01",
          task_kind: "eos_input_intake",
          owner_role: "dispatch_supervisor",
          candidate_roles: ["dispatch_supervisor"]
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
              dataset_key: "reporting.eos_raw.workbook",
              artifact_kind: "reporting.eos_raw.workbook",
              artifact_role: "official_input",
              required: true,
              required_count: 1,
              current_count: 0,
              status: "missing"
            }
          ],
          required_reviews: [],
          missing_required_inputs: ["reporting.eos_raw.workbook"],
          blocking_reason_codes: ["required_upload_missing:reporting.eos_raw.workbook"]
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

  it("opens task details from primary card click and keyboard activation without menu bleed-through", async () => {
    const user = userEvent.setup();
    const onOpenDetails = vi.fn();
    const { workspace, detail } = buildWeeklyIntakeSurface();
    renderBoard(workspace, detail, onOpenDetails);

    const card = (await screen.findByRole("heading", { name: "Weekly Intake" })).closest("article");
    expect(card).not.toBeNull();

    await user.click(card as HTMLElement);
    expect(onOpenDetails).toHaveBeenCalledTimes(1);

    (card as HTMLElement).focus();
    fireEvent.keyDown(card as HTMLElement, { key: "Enter" });
    expect(onOpenDetails).toHaveBeenCalledTimes(2);

    await user.click(
      within(card as HTMLElement).getByLabelText("Actions for Weekly Intake")
    );
    expect(onOpenDetails).toHaveBeenCalledTimes(2);
  });

  it("renders dispatch daily intake copy with required-input upload wording", async () => {
    const { workspace, detail } = buildDispatchIntakeSurface();
    renderBoard(workspace, detail);

    const card = (await screen.findByRole("heading", { name: "Daily EOS Intake" })).closest("article");
    expect(card).not.toBeNull();
    expect(
      within(card as HTMLElement).getByText(/Required input: reporting\.eos_raw\.workbook/i)
    ).toBeInTheDocument();
    expect(
      within(card as HTMLElement).getByRole("button", { name: "Upload Input" })
    ).toBeInTheDocument();
  });

  it("renders dispatch review copy and keeps the EOD draft action available", async () => {
    const { workspace, detail } = buildDispatchReviewSurface();
    renderBoard(workspace, detail);

    const card = (await screen.findByRole("heading", { name: "Review EOD Draft" })).closest("article");
    expect(card).not.toBeNull();

    await userEvent.setup().click(
      within(card as HTMLElement).getByLabelText("Actions for Review EOD Draft")
    );
    expect(
      within(card as HTMLElement).getByRole("button", { name: "Open EOD draft" })
    ).toBeInTheDocument();
  });
});
