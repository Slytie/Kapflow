import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";

import { MyWorkPage } from "@/pages/MyWorkPage";
import { renderRoute } from "@/test/renderRoute";
import { server } from "@/test/api/server";

describe("MyWorkPage", () => {
  it("filters rows by URL state filter", async () => {
    renderRoute(<MyWorkPage />, {
      route: "/my-work?run=wr-test-001&state=OPEN",
      path: "/my-work"
    });

    expect(await screen.findByText(/information_request/i)).toBeInTheDocument();
    expect(screen.queryByText(/exception_triage/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete" })).not.toBeInTheDocument();
  });

  it("hides tasks that the current actor cannot claim or complete", async () => {
    server.use(
      http.get("*/api/v1/human-tasks", () =>
        HttpResponse.json({
          status: "ok",
          command: "api.human_tasks.list",
          human_tasks: [
            {
              human_task_id: "ht-blocked-001",
              workflow_run_id: "wr-test-001",
              task_run_id: "tr-blocked-001",
              task_kind: "review_packet",
              state: "CLAIMED",
              candidate_roles: ["dispatch_supervisor"],
              owner_role: "dispatch_supervisor",
              assignee_actor_id: "human:someone-else",
              assignee_actor_type: "human",
              due_at: null,
              escalation_at: null,
              lease_version: 1,
              claimed_at: "2026-03-04T08:00:00Z",
              claimed_until: null,
              linked_approval_id: null,
              reopen_count: 0,
              generation: 0,
              created_at: "2026-03-04T07:59:00Z",
              updated_at: "2026-03-04T08:00:00Z",
              task_run_state: "IN_PROGRESS",
              stage_id: "Stage06",
              blocked_on_kind: null,
              blocked_on_ref: null,
              spawned_from_flag_id: null,
              available_actions: [],
              missing_required_inputs: [],
              blocking_reason_codes: ["claimed_by_other_actor"]
            }
          ],
          page: { limit: 100, offset: 0 }
        })
      )
    );

    renderRoute(<MyWorkPage />, {
      route: "/my-work?run=wr-test-001",
      path: "/my-work"
    });

    expect(
      await screen.findByText(/No actionable tasks for current user/i)
    ).toBeInTheDocument();
    expect(screen.queryByTestId("queue-row")).not.toBeInTheDocument();
  });
});
