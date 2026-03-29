import { render, screen } from "@testing-library/react";

import { ApprovalCard } from "@/components/ApprovalCard";

describe("ApprovalCard", () => {
  it("shows the dispatch finalize-and-feedback hint for Stage04 approvals", () => {
    render(
      <ApprovalCard
        approval={{
          approval_id: "ap-dispatch-stage04",
          workflow_run_id: "wr-test-001",
          task_run_id: "tr-test-001",
          approval_kind: "business_decision",
          scope_kind: "stage",
          scope_ref: "Stage04",
          state: "PENDING",
          requested_by_task_run_id: "tr-test-001",
          candidate_roles: ["operations_manager"],
          required_role: "operations_manager",
          response_kind: null,
          response_reason: null,
          decided_by_actor_id: null,
          decided_by_actor_type: null,
          requested_at: "2026-03-29T00:00:00Z",
          responded_at: null,
          generation: 0,
          created_at: "2026-03-29T00:00:00Z",
          updated_at: "2026-03-29T00:00:00Z"
        }}
        onDetails={() => undefined}
      />
    );

    expect(
      screen.getByText(/Approving finalizes the daily packet and sends planning feedback automatically\./i)
    ).toBeInTheDocument();
  });
});
