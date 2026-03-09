import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { DetailDrawer } from "@/components/DetailDrawer";
import { TaskCardWide } from "@/components/TaskCardWide";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { humanTasksRepository } from "@/lib/repositories";
import type { DrawerPayload } from "@/lib/types/ui";
import type { HumanTaskRow } from "@/lib/types/contracts";

const task: HumanTaskRow = {
  human_task_id: "ht-2",
  workflow_run_id: "wr-2",
  task_run_id: "tr-2",
  task_kind: "review_packet",
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
  created_at: "2026-03-03T00:00:00Z",
  updated_at: "2026-03-03T00:00:00Z",
  task_run_state: "READY",
  stage_id: "Stage06",
  blocked_on_kind: null,
  blocked_on_ref: null,
  spawned_from_flag_id: null
};

function Harness(): JSX.Element {
  const [payload, setPayload] = useState<DrawerPayload | null>(null);

  return (
    <>
      <TaskCardWide
        task={task}
        onDetails={() =>
          setPayload({
            title: "Task details",
            description: "This description is only visible in the drawer.",
            fields: [{ label: "State", value: "OPEN" }],
            artifacts: [
              {
                artifact_version_id: "av-1",
                artifact_kind: "schedule.draft_schedule.workbook",
                artifact_role: "evidence",
                media_type:
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                created_at: "2026-03-04T12:00:00Z",
                file_name: "stage05.xlsx",
                source_label: "Step output"
              }
            ]
          })
        }
      />
      <DetailDrawer payload={payload} onClose={() => setPayload(null)} />
    </>
  );
}

function renderWithQueryClient(element: JSX.Element) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false }
    }
  });
  return {
    queryClient,
    ...render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>)
  };
}

describe("Detail drawer flow", () => {
  it("keeps card compact and shows description in drawer", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<Harness />);

    expect(screen.queryByText("This description is only visible in the drawer.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Details" }));

    expect(screen.getByText("This description is only visible in the drawer.")).toBeInTheDocument();
    expect(await screen.findByText("Task Artifacts (1)")).toBeInTheDocument();
    expect(screen.getByText("stage05.xlsx")).toBeInTheDocument();
    const artifactsSection = screen.getByLabelText("Task artifacts");
    expect(within(artifactsSection).getByRole("button", { name: "Download" })).toBeInTheDocument();
    expect(screen.getByTestId("task-card-wide")).toBeInTheDocument();
  });

  it("executes task actions from drawer and refreshes relevant query views", async () => {
    const user = userEvent.setup();
    const claimSpy = vi.spyOn(humanTasksRepository, "claim").mockResolvedValue();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["claim"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    const { queryClient } = renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage06 review_packet",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage06",
            task_kind: "review_packet",
            state: "OPEN",
            assignee_actor_id: null,
            assignee_actor_type: null,
            owner_role: "dispatch_supervisor",
            available_actions: ["claim"],
            blocking_reason_codes: [],
            missing_required_inputs: []
          }
        }}
        onClose={() => undefined}
      />
    );
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    expect(await screen.findByRole("heading", { name: "Stage06 review_packet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Claim" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Claim" }));

    await waitFor(() => {
      expect(claimSpy).toHaveBeenCalledWith("ht-2");
    });
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["logistics-demo-story"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["board-view"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["my-work"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["run-detail", "wr-2"] });
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["run-workspace", "wr-2"] });
    });

    claimSpy.mockRestore();
    getSpy.mockRestore();
  });

  it("renders only available task actions and calls Stage06 review when offered", async () => {
    const user = userEvent.setup();
    const runStage06Spy = vi.spyOn(humanTasksRepository, "runStage06AgentReview").mockResolvedValue();
    const getSpy = vi.spyOn(humanTasksRepository, "get").mockResolvedValue({
      ...task,
      available_actions: ["run_stage06_agent_review", "upload_attachment"],
      missing_required_inputs: [],
      blocking_reason_codes: []
    });
    vi.spyOn(onetruthApi, "listArtifactsForSubject").mockResolvedValue([]);
    renderWithQueryClient(
      <DetailDrawer
        payload={{
          title: "Stage06 review_packet",
          subtitle: "ht-2",
          fields: [],
          task: {
            human_task_id: "ht-2",
            workflow_run_id: "wr-2",
            task_run_id: "tr-2",
            stage_id: "Stage06",
            task_kind: "review_packet",
            state: "OPEN",
            assignee_actor_id: null,
            assignee_actor_type: null,
            owner_role: "dispatch_supervisor",
            available_actions: ["run_stage06_agent_review", "upload_attachment"],
            blocking_reason_codes: [],
            missing_required_inputs: []
          }
        }}
        onClose={() => undefined}
      />
    );

    expect(await screen.findByRole("button", { name: "Run Stage06 Review" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload attachment" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Run Stage06 Review" }));
    await waitFor(() => {
      expect(runStage06Spy).toHaveBeenCalledWith("ht-2");
    });

    runStage06Spy.mockRestore();
    getSpy.mockRestore();
  });
});
