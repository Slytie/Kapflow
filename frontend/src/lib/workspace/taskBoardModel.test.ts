import { describe, expect, it } from "vitest";

import {
  actionRefTargetsSubject,
  buildWorkspaceBoardCards,
  buildWorkspaceLaneCards,
  humanizeBlockingReason,
  workpageActionStateLabel
} from "@/lib/workspace/taskBoardModel";

describe("taskBoardModel", () => {
  it("builds mixed task, approval, and flag cards into swimlanes", () => {
    const detail = {
      human_tasks: [
        {
          human_task_id: "ht-1",
          stage_id: "Stage04",
          task_kind: "work_item",
          state: "OPEN",
          assignee_actor_id: null,
          owner_role: "schedule_planner",
          candidate_roles: ["schedule_planner"],
          missing_required_inputs: [],
          required_uploads: [],
          required_reviews: [],
          available_actions: []
        }
      ],
      approvals: [
        {
          approval_id: "ap-1",
          approval_kind: "business_decision",
          scope_ref: "Stage06",
          state: "PENDING",
          required_role: "operations_manager",
          candidate_roles: ["operations_manager"],
          response_kind: null
        }
      ],
      flags: [
        {
          flag_id: "fg-1",
          summary: "Route drift",
          state: "open",
          severity: "high",
          created_by_actor_id: "human:ops-manager",
          assigned_group: "dispatch"
        }
      ]
    } as any;

    const cards = buildWorkspaceBoardCards({
      detail,
      taskItemById: new Map([["ht-1", { available_actions: ["claim"], item_kind: "human_task" } as any]]),
      approvalItemById: new Map([["ap-1", { available_actions: ["approve"], item_kind: "approval" } as any]]),
      flagItemById: new Map([["fg-1", { available_actions: [], item_kind: "flag" } as any]])
    });
    const lanes = buildWorkspaceLaneCards(cards);

    expect(cards).toHaveLength(3);
    expect(lanes.todo.map((card) => card.cardId)).toContain("task:ht-1");
    expect(lanes.review.map((card) => card.cardId)).toEqual(
      expect.arrayContaining(["approval:ap-1", "flag:fg-1"])
    );
  });

  it("matches action refs against the carried subject and humanizes blocking state", () => {
    expect(
      actionRefTargetsSubject(
        {
          action_ref: {
            action_id: "open",
            workpage_kind: "schedule-v0",
            workflow_run_id: "wr-1",
            artifact_version_id: "av-1",
            subject: {
              subject_kind: "approval",
              subject_id: "ap-1"
            }
          }
        } as any,
        "approval",
        "ap-1"
      )
    ).toBe(true);
    expect(humanizeBlockingReason("candidate_role_mismatch")).toBe(
      "Your current actor role cannot claim this task"
    );
    expect(
      workpageActionStateLabel({
        label: "Open latest",
        disabled_reason: "schedule_draft_unavailable"
      } as any)
    ).toBe("Schedule draft unavailable for this run yet");
  });
});
