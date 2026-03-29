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
    const onUpload = vi.fn();
    const onDownload = vi.fn();

    const view = render(
      <TaskCardWide
        task={task}
        onDetails={() => undefined}
        onClaim={onClaim}
        onComplete={onComplete}
        onNeedInfo={onNeedInfo}
        onUpload={onUpload}
        onDownload={onDownload}
      />
    );

    await user.click(screen.getByRole("button", { name: "Claim" }));
    await user.click(screen.getByRole("button", { name: "Complete" }));
    await user.click(screen.getByRole("button", { name: "Need Info" }));
    await user.click(screen.getByRole("button", { name: "Upload" }));
    await user.click(screen.getByRole("button", { name: "Download" }));
    const fileInput = view.container.querySelector("input[type='file']");
    expect(fileInput).not.toBeNull();
    const file = new File(["stub"], "attachment.txt", { type: "text/plain" });
    await user.upload(fileInput as HTMLInputElement, file);

    expect(onClaim).toHaveBeenCalledTimes(1);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onNeedInfo).toHaveBeenCalledTimes(1);
    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(onDownload).toHaveBeenCalledTimes(1);
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

    expect(screen.getByRole("heading", { name: "Stage04 · Weekly Intake" })).toBeInTheDocument();
  });
});
