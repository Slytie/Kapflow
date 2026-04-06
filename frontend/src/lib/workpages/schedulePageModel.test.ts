import { describe, expect, it } from "vitest";

import {
  buildAcceptedRail,
  buildDraftRail,
  scheduleLandingRoute,
  workpageBackRoute,
  workpageConflictDetails
} from "@/lib/workpages/schedulePageModel";

describe("schedulePageModel", () => {
  it("builds accepted and draft rails from backend-authored history", () => {
    const contract = {
      accepted_series: {
        current_artifact_version_id: "av-accepted-2",
        previous_artifact_version_id: "av-accepted-1",
        next_artifact_version_id: null,
        entries: [
          {
            artifact_version_id: "av-accepted-1",
            logical_date: "2026-03-24",
            partition_key: "PK-1",
            artifact_kind: "planning.accepted_weekly_schedule.packet",
            route: "/runs/wr-1/workpages/schedule-v0/artifacts/av-accepted-1"
          },
          {
            artifact_version_id: "av-accepted-2",
            logical_date: "2026-03-25",
            partition_key: "PK-2",
            artifact_kind: "planning.accepted_weekly_schedule.packet",
            route: "/runs/wr-2/workpages/schedule-v0/artifacts/av-accepted-2"
          }
        ]
      },
      artifact_history: {
        current_artifact_version_id: "av-draft-2",
        latest_artifact_version_id: "av-draft-2",
        previous_artifact_version_id: "av-draft-1",
        next_artifact_version_id: null,
        entries: [
          {
            artifact_version_id: "av-draft-1",
            created_at: "2026-03-24T00:00:00Z",
            lineage_note: "Initial draft",
            supersedes_artifact_version_id: null,
            route: "/runs/wr-1/workpages/schedule-v0/artifacts/av-draft-1"
          },
          {
            artifact_version_id: "av-draft-2",
            created_at: "2026-03-25T00:00:00Z",
            lineage_note: "Submitted draft",
            supersedes_artifact_version_id: "av-draft-1",
            route: "/runs/wr-1/workpages/schedule-v0/artifacts/av-draft-2"
          }
        ]
      }
    } as any;

    const acceptedRail = buildAcceptedRail(contract);
    const draftRail = buildDraftRail(contract);

    expect(acceptedRail.entries[1]?.isCurrent).toBe(true);
    expect(acceptedRail.previousRoute).toContain("av-accepted-1");
    expect(draftRail.entries[1]?.isLatest).toBe(true);
    expect(draftRail.previousRoute).toContain("av-draft-1");
  });

  it("extracts conflict navigation details and canonical run routes", () => {
    expect(scheduleLandingRoute("wr-1")).toBe("/runs/wr-1/workpages/schedule-v0");
    expect(workpageBackRoute("wr-1")).toEqual({
      href: "/runs/wr-1",
      label: "Back to run detail"
    });
    expect(
      workpageConflictDetails({
        code: "workpage_artifact_conflict",
        details: {
          artifact_version_id: "av-old",
          latest_artifact_version_id: "av-new",
          workflow_run_id: "wr-1",
          route: "/runs/wr-1/workpages/schedule-v0/artifacts/av-new"
        },
        status: 409,
        message: "stale artifact"
      })
    ).toBeNull();
  });
});
