import { workpagesRepository } from "@/lib/repositories";
import { mutationLog } from "@/test/api/handlers";

describe("workpagesRepository", () => {
  it("returns run-backed and artifact-backed EOD contracts plus canonical create/submit responses", async () => {
    const queryLanding = await workpagesRepository.eodForRun("wr-reporting-001");
    const draft = await workpagesRepository.createEodDraftForRun("wr-reporting-001");
    const artifact = await workpagesRepository.eodArtifact(
      draft.workflow_run_id,
      draft.artifact_version_id
    );
    const submitted = await workpagesRepository.submitEodArtifact(
      draft.workflow_run_id,
      draft.artifact_version_id,
      {
        formValues: {
          working_devices: "36 online",
          dispatcher_comment: "Drafted from the frontend repository test."
        },
        checklistValues: []
      }
    );
    const submittedArtifact = await workpagesRepository.eodArtifact(
      submitted.workflow_run_id,
      submitted.artifact_version_id
    );

    expect(draft.artifact_version_id).toBe("av-eod-artifact-001");
    expect(draft.route).toBe("/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001");

    expect(queryLanding.source.mode).toBe("run_projection");
    expect(queryLanding.run_context?.workflow_run_id).toBe("wr-reporting-001");
    expect(queryLanding.artifact_context).toBeNull();
    expect(artifact.source.mode).toBe("artifact_projection");
    expect(artifact.artifact_context?.artifact_version_id).toBe("av-eod-artifact-001");
    expect(artifact.freshness.source_version).toBe("av-eod-artifact-001");
    expect(artifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-eod-artifact-001"
    ]);

    expect(submitted.artifact_version_id).toBe("av-eod-artifact-002");
    expect(submitted.supersedes_artifact_version_id).toBe("av-eod-artifact-001");
    expect(submitted.route).toBe(
      "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-002"
    );
    expect(submittedArtifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-eod-artifact-002",
      "av-eod-artifact-001"
    ]);
    expect(submittedArtifact.artifact_history?.entries[0]?.lineage_note).toMatch(
      /Submitted artifact-backed EOD draft version/i
    );
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
    expect(eodLandingBeforeCreate.draft_resolution).toMatchObject({
      state: "no_draft",
      latest_artifact_version_id: null,
      artifact_route: null
    });
    expect(eodLandingBeforeCreate.draft_resolution?.create_action_ref).toMatchObject({
      action_id: "workpage.eod-v0.create_draft",
      workpage_kind: "eod-v0",
      workflow_run_id: "wr-reporting-001",
      artifact_version_id: null
    });

    expect(draft.workflow_run_id).toBe("wr-reporting-001");
    expect(draft.artifact_version_id).toBe("av-eod-artifact-001");
    expect(draft.route).toBe("/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001");

    expect(eodLandingAfterCreate.draft_resolution).toMatchObject({
      state: "latest_draft_available",
      latest_artifact_version_id: "av-eod-artifact-001",
      artifact_route: "/runs/wr-reporting-001/workpages/eod-v0/artifacts/av-eod-artifact-001"
    });
    expect(eodLandingAfterCreate.draft_resolution?.open_action_ref).toMatchObject({
      action_id: "workpage.eod-v0.open_latest_draft",
      workpage_kind: "eod-v0",
      workflow_run_id: "wr-reporting-001",
      artifact_version_id: "av-eod-artifact-001"
    });
    expect(eodLandingAfterCreate.artifact_context).toBeNull();
  });

  it("returns schedule artifact history, fetches the artifact contract, submits a new version, and downloads JSON", async () => {
    const scheduleLanding = await workpagesRepository.scheduleForRun("wr-weekly-001");
    const artifact = await workpagesRepository.scheduleArtifact(
      "wr-weekly-001",
      "av-schedule-artifact-001"
    );
    const previewAction = artifact.actions.find(
      (action): action is typeof artifact.actions[number] & { preview_path: string } =>
        action.kind === "preview_recalc" && typeof action.preview_path === "string"
    );
    const saveAction = artifact.actions.find(
      (action): action is typeof artifact.actions[number] & { submit_path: string } =>
        action.kind === "submit_artifact" && typeof action.submit_path === "string"
    );
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
    const preview = await workpagesRepository.previewScheduleArtifact(previewAction?.preview_path ?? "", {
      rows: assignmentRows,
      reserveRows
    });
    const submitted = await workpagesRepository.submitScheduleArtifactAtPath(
      saveAction?.submit_path ?? "",
      "av-schedule-artifact-001",
      {
        rows: assignmentRows,
        reserveRows
      }
    );
    const submittedArtifact = await workpagesRepository.scheduleArtifact(
      "wr-weekly-001",
      submitted.artifact_version_id
    );
    await workpagesRepository.downloadScheduleArtifactJson("av-schedule-artifact-002");

    expect(scheduleLanding.source.mode).toBe("run_projection");
    expect(artifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-schedule-artifact-001"
    ]);
    expect(artifact.source.mode).toBe("artifact_projection");
    expect(artifact.artifact_context?.artifact_kind).toBe("planning.draft_weekly_schedule.workbook");
    expect(preview.preview.artifact_version_id).toBe("av-schedule-artifact-001");
    expect(preview.preview.dirty).toBe(true);
    expect(artifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-schedule-artifact-001"
    ]);
    expect(submitted.artifact_version_id).toBe("av-schedule-artifact-002");
    expect(submitted.supersedes_artifact_version_id).toBe("av-schedule-artifact-001");
    expect(submitted.route).toBe(
      "/runs/wr-weekly-001/workpages/schedule-v0/artifacts/av-schedule-artifact-002"
    );
    expect(submittedArtifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-schedule-artifact-002",
      "av-schedule-artifact-001"
    ]);
    expect(mutationLog()).toContain("workpage-schedule-artifact-preview:av-schedule-artifact-001");
    expect(mutationLog()).toContain("artifact-download-bin:av-schedule-artifact-002");
  });

  it("returns route-demand contracts and saves a new immutable route-demand version", async () => {
    const routeDemandLanding = await workpagesRepository.routeDemandForRun("wr-weekly-001");
    const artifact = await workpagesRepository.routeDemandArtifact(
      "wr-weekly-001",
      "av-route-demand-artifact-001"
    );
    const saveAction = artifact.actions.find((action) => action.kind === "save");
    const firstDay = artifact.route_demand_calculations?.day_cards[0];
    const dayCards = artifact.route_demand_calculations?.day_cards ?? [];
    const futureDay = dayCards[dayCards.length - 1];
    const submitted = await workpagesRepository.submitRouteDemandArtifactAtPath(
      saveAction?.submit_path ?? "",
      "av-route-demand-artifact-001",
      {
        dailyDemandRows: [
          ...dayCards.map((card) => ({
            service_date: card.service_date,
            planned_route_count:
              card.service_date === futureDay?.service_date
                ? card.planned_route_count + 2
                : card.planned_route_count
          }))
        ]
      }
    );
    const submittedArtifact = await workpagesRepository.routeDemandArtifact(
      "wr-weekly-001",
      submitted.artifact_version_id
    );

    expect(routeDemandLanding.source.mode).toBe("run_projection");
    expect(routeDemandLanding.workpage.workpage_id).toBe("route-demand-v0");
    expect(routeDemandLanding.route_demand_calculations?.day_cards).toHaveLength(14);
    expect(routeDemandLanding.route_demand_calculations?.day_cards[13]?.service_date).toBe(
      "2026-04-04"
    );
    expect(routeDemandLanding.actions.map((action) => action.kind)).toEqual(["open_latest"]);
    expect(artifact.source.mode).toBe("artifact_projection");
    expect(artifact.route_demand_calculations?.day_cards[0]?.service_date).toBe(
      firstDay?.service_date
    );
    expect(futureDay?.service_date).toBe("2026-04-04");
    expect(artifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-route-demand-artifact-001"
    ]);
    expect(submitted.artifact_version_id).toBe("av-route-demand-artifact-002");
    expect(submitted.supersedes_artifact_version_id).toBe("av-route-demand-artifact-001");
    expect(submitted.route).toBe(
      "/runs/wr-weekly-001/workpages/route-demand-v0/artifacts/av-route-demand-artifact-002"
    );
    expect(submittedArtifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-route-demand-artifact-002",
      "av-route-demand-artifact-001"
    ]);
    expect(
      submittedArtifact.route_demand_calculations?.day_cards.find(
        (card) => card.service_date === futureDay?.service_date
      )?.planned_route_count
    ).toBe((futureDay?.planned_route_count ?? 0) + 2);
    expect(mutationLog()).toContain(
      "workpage-route-demand-artifact-submit:av-route-demand-artifact-001:av-route-demand-artifact-002"
    );
  });

  it("creates, reads, lists, and saves immutable driver-preferences snapshots", async () => {
    const landingBeforeCreate = await workpagesRepository.driverPreferencesForRun("wr-weekly-001");
    const created = await workpagesRepository.createWorkpage(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0/snapshots"
    );
    const artifact = await workpagesRepository.driverPreferencesArtifact(
      "wr-weekly-001",
      created.artifact_version_id
    );
    const saveAction = artifact.actions.find((action) => action.kind === "save");
    const firstDriver = artifact.preference_grid?.drivers[0];
    const submitted = await workpagesRepository.submitDriverPreferencesArtifactAtPath(
      saveAction?.submit_path ?? "",
      created.artifact_version_id,
      {
        driverRows: (artifact.preference_grid?.drivers ?? []).map((row, index) => ({
          driver_id: row.driver_id,
          preferences_by_weekday:
            index === 0
              ? { ...row.preferences_by_weekday, mon: "open_to_work" }
              : row.preferences_by_weekday
        }))
      }
    );
    const submittedArtifact = await workpagesRepository.driverPreferencesArtifact(
      "wr-weekly-001",
      submitted.artifact_version_id
    );

    expect(landingBeforeCreate.actions.map((action) => action.kind)).toEqual([
      "create_snapshot",
      "add_availability_exception"
    ]);
    expect(created.route).toBe(
      "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-001"
    );
    expect(artifact.preference_grid?.drivers[0]?.driver_id).toBe(firstDriver?.driver_id);
    expect(artifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-driver-preferences-artifact-001"
    ]);
    expect(submitted.artifact_version_id).toBe("av-driver-preferences-artifact-002");
    expect(submitted.supersedes_artifact_version_id).toBe("av-driver-preferences-artifact-001");
    expect(submitted.route).toBe(
      "/runs/wr-weekly-001/workpages/driver-preferences-v0/artifacts/av-driver-preferences-artifact-002"
    );
    expect(submittedArtifact.artifact_history?.entries.map((entry) => entry.artifact_version_id)).toEqual([
      "av-driver-preferences-artifact-002",
      "av-driver-preferences-artifact-001"
    ]);
    expect(mutationLog()).toContain(
      "workpage-driver-preferences-artifact-submit:av-driver-preferences-artifact-001:av-driver-preferences-artifact-002"
    );
  });
});
