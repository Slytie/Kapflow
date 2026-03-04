import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AttachmentActions } from "@/components/AttachmentActions";
import { QueueRow } from "@/components/QueueRow";
import { TaskCardWide } from "@/components/TaskCardWide";
import type { HumanTaskRow } from "@/lib/types/contracts";

const task: HumanTaskRow = {
  human_task_id: "ht-3",
  workflow_run_id: "wr-3",
  task_run_id: "tr-3",
  task_kind: "information_request",
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

describe("AttachmentActions", () => {
  it("renders upload/download in card and row views", () => {
    render(
      <>
        <TaskCardWide task={task} onDetails={() => undefined} />
        <QueueRow
          title="Stage06 information_request"
          subtitle="dispatch_supervisor"
          status="OPEN"
          onDetails={() => undefined}
        />
      </>
    );

    const uploadButtons = screen.getAllByRole("button", { name: "Upload" });
    const downloadButtons = screen.getAllByRole("button", { name: "Download" });

    expect(uploadButtons.length).toBeGreaterThanOrEqual(2);
    expect(downloadButtons.length).toBeGreaterThanOrEqual(2);
  });

  it("calls upload and download callbacks from inline controls", async () => {
    const user = userEvent.setup();
    const onUpload = vi.fn();
    const onDownload = vi.fn();
    const { container } = render(
      <AttachmentActions onUpload={onUpload} onDownload={onDownload} />
    );

    const input = container.querySelector('input[type="file"]');
    if (!(input instanceof HTMLInputElement)) {
      throw new Error("file input not found");
    }
    const file = new File(["fixture-content"], "fixture.txt", { type: "text/plain" });
    await user.upload(input, file);
    expect(onUpload).toHaveBeenCalledTimes(1);
    expect(onUpload).toHaveBeenCalledWith(file);

    await user.click(screen.getByRole("button", { name: "Download" }));
    expect(onDownload).toHaveBeenCalledTimes(1);
  });
});
