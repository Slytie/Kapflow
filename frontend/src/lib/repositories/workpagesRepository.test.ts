import { workpagesRepository } from "@/lib/repositories";
import { mutationLog } from "@/test/api/handlers";

describe("workpagesRepository", () => {
  it("returns isolated demo query and artifact-backed EOD contracts plus create/submit responses", async () => {
    const queryLanding = await workpagesRepository.eod();
    const draft = await workpagesRepository.createEodDraft();
    const artifact = await workpagesRepository.eodArtifact(draft.artifact_version_id);
    const draftHistory = await workpagesRepository.listEodDraftHistory(draft.workflow_run_id);
    const submitted = await workpagesRepository.submitEodArtifact(draft.artifact_version_id, {
      formValues: {
        working_devices: "36 online",
        dispatcher_comment: "Drafted from the frontend repository test."
      },
      checklistValues: []
    });
    const submittedHistory = await workpagesRepository.listEodDraftHistory(draft.workflow_run_id);

    queryLanding.workpage.summary.service_date = "mutated";

    const queryLandingAgain = await workpagesRepository.eod();
    expect(queryLandingAgain.workpage.summary.service_date).toBe("2026-03-16");
    expect(queryLandingAgain.artifact_context).toBeNull();

    expect(draft.artifact_version_id).toBe("av-eod-artifact-001");
    expect(draft.route).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-001");

    expect(artifact.source.mode).toBe("artifact_projection");
    expect(artifact.artifact_context?.artifact_version_id).toBe("av-eod-artifact-001");
    expect(artifact.freshness.source_version).toBe("av-eod-artifact-001");
    expect(draftHistory.map((row) => row.artifact_version_id)).toEqual(["av-eod-artifact-001"]);

    expect(submitted.artifact_version_id).toBe("av-eod-artifact-002");
    expect(submitted.supersedes_artifact_version_id).toBe("av-eod-artifact-001");
    expect(submitted.route).toBe("/runs/wr-eod-artifact-001/workpages/eod-v0/artifacts/av-eod-artifact-002");
    expect(submittedHistory.map((row) => row.artifact_version_id)).toEqual([
      "av-eod-artifact-002",
      "av-eod-artifact-001"
    ]);
    expect(submittedHistory[0]?.lineage_note).toMatch(/Submitted artifact-backed EOD draft version/i);
  });

  it("returns run-backed schedule/EOD contracts and canonical EOD draft-create routes", async () => {
    const schedule = await workpagesRepository.scheduleForRun("wr-weekly-001");
    const eodLandingBeforeCreate = await workpagesRepository.eodForRun("wr-reporting-001");
    const draft = await workpagesRepository.createEodDraftForRun("wr-reporting-001");
    const eodLandingAfterCreate = await workpagesRepository.eodForRun("wr-reporting-001");

    expect(schedule.source.mode).toBe("run_projection");
    expect(schedule.run_context?.workflow_run_id).toBe("wr-weekly-001");
    expect(schedule.draft_resolution).toBeNull();

    expect(eodLandingBeforeCreate.source.mode).toBe("run_projection");
    expect(eodLandingBeforeCreate.run_context?.workflow_run_id).toBe("wr-reporting-001");
    expect(eodLandingBeforeCreate.draft_resolution).toEqual({
      state: "no_draft",
      latest_artifact_version_id: null,
      artifact_route: null
    });

    expect(draft.workflow_run_id).toBe("wr-reporting-001");
    expect(draft.artifact_version_id).toBe("av-eod-artifact-001");
    expect(draft.route).toBe("/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001");

    expect(eodLandingAfterCreate.draft_resolution).toEqual({
      state: "latest_draft_available",
      latest_artifact_version_id: "av-eod-artifact-001",
      artifact_route: "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
    });
    expect(eodLandingAfterCreate.artifact_context).toBeNull();
  });

  it("returns schedule artifact history, fetches the artifact contract, submits a new version, and downloads JSON", async () => {
    const scheduleLanding = await workpagesRepository.scheduleForRun("wr-weekly-001");
    const initialHistory = await workpagesRepository.listScheduleDraftHistory("wr-weekly-001");
    const artifact = await workpagesRepository.scheduleArtifact("av-schedule-artifact-001");
    const assignmentRows = (artifact.workpage.sections[2] as { rows: Array<Record<string, unknown>> }).rows.map(
      (row) => ({ ...row })
    );
    const reserveRows = (artifact.workpage.sections[3] as { rows: Array<Record<string, unknown>> }).rows.map(
      (row) => ({ ...row })
    );
    assignmentRows[0] = {
      ...assignmentRows[0],
      assigned_driver_id: "DRV-MANUAL-77",
      assignment_status: "manual_override"
    };
    reserveRows[0] = {
      ...reserveRows[0],
      assigned_driver_id: "DRV-MANUAL-88",
      assignment_status: "manual_override"
    };
    const submitted = await workpagesRepository.submitScheduleArtifact("av-schedule-artifact-001", {
      rows: assignmentRows,
      reserveRows
    });
    const submittedHistory = await workpagesRepository.listScheduleDraftHistory("wr-weekly-001");
    await workpagesRepository.downloadScheduleArtifactJson("av-schedule-artifact-002");

    expect(scheduleLanding.source.mode).toBe("run_projection");
    expect(initialHistory.map((row) => row.artifact_version_id)).toEqual(["av-schedule-artifact-001"]);
    expect(artifact.source.mode).toBe("artifact_projection");
    expect(artifact.artifact_context?.artifact_kind).toBe("planning.draft_weekly_schedule.workbook");
    expect(submitted.artifact_version_id).toBe("av-schedule-artifact-002");
    expect(submitted.supersedes_artifact_version_id).toBe("av-schedule-artifact-001");
    expect(submitted.route).toBe(
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
    );
    expect(submittedHistory.map((row) => row.artifact_version_id)).toEqual([
      "av-schedule-artifact-002",
      "av-schedule-artifact-001"
    ]);
    expect(mutationLog()).toContain("artifact-download-bin:av-schedule-artifact-002");
  });
});
