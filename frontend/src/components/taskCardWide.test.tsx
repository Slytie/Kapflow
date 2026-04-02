import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TaskCardWide } from "@/components/TaskCardWide";
import type { HumanTaskRow } from "@/lib/types/contracts";

const task: HumanTaskRow = {
  human_task_id: "ht-1",
  workflow_run_id: "wr-1",
  task_run_id: "tr-1",
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

describe("TaskCardWide", () => {
  it("renders inline actions and triggers callbacks without opening details", async () => {
    const user = userEvent.setup();
    const onClaim = vi.fn();
    const onComplete = vi.fn();
    const onNeedInfo = vi.fn();

    render(
      <TaskCardWide
        task={task}
        onDetails={() => undefined}
        onClaim={onClaim}
        onComplete={onComplete}
        onNeedInfo={onNeedInfo}
        documentCues={[
          { key: "missing", label: "1 missing input", tone: "danger" },
          { key: "artifacts", label: "2 artifacts", tone: "neutral" }
        ]}
      />
    );

    await user.click(screen.getByRole("button", { name: "Claim" }));
    await user.click(screen.getByRole("button", { name: "Complete" }));
    await user.click(screen.getByRole("button", { name: "Need Info" }));
    expect(screen.getByText("1 missing input")).toBeInTheDocument();
    expect(screen.getByText("2 artifacts")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Download" })).not.toBeInTheDocument();

    expect(onClaim).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onNeedInfo).toHaveBeenCalledTimes(1);
  });

  it("maps weekly task kinds to operator-friendly headings", () => {
    render(
      <TaskCardWide
        task={{
          ...task,
          stage_id: "Stage04",
          task_kind: "weekly_input_intake"
        }}
        onDetails={() => undefined}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Stage04 · Weekly Scheduling Plan Inputs" })
    ).toBeInTheDocument();
  });
});
