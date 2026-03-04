import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { DetailDrawer } from "@/components/DetailDrawer";
import { TaskCardWide } from "@/components/TaskCardWide";
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
            fields: [{ label: "State", value: "OPEN" }]
          })
        }
      />
      <DetailDrawer payload={payload} onClose={() => setPayload(null)} />
    </>
  );
}

describe("Detail drawer flow", () => {
  it("keeps card compact and shows description in drawer", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    expect(screen.queryByText("This description is only visible in the drawer.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Details" }));

    expect(screen.getByText("This description is only visible in the drawer.")).toBeInTheDocument();
    expect(screen.getByTestId("task-card-wide")).toBeInTheDocument();
  });
});
