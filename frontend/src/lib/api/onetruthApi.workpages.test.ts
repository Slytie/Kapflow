import { HttpResponse, http } from "msw";

import artifactCreateRunSnapshot from "@fixtures/workpage_eod_v0_run_artifact_create_response.json";
import driverPreferencesArtifactCreateSnapshot from "@fixtures/workpage_driver_preferences_v0_artifact_create_response.json";
import driverPreferencesArtifactStateSnapshot from "@fixtures/workpage_driver_preferences_v0_artifact_state.json";
import driverPreferencesArtifactSubmitSnapshot from "@fixtures/workpage_driver_preferences_v0_artifact_submit_response.json";
import driverPreferencesRunWorkpageStateSnapshot from "@fixtures/workpage_driver_preferences_v0_run_state.json";
import eodRunWorkpageStateSnapshot from "@fixtures/workpage_eod_v0_run_state.json";
import routeDemandArtifactStateSnapshot from "@fixtures/workpage_route_demand_v0_artifact_state.json";
import routeDemandArtifactSubmitSnapshot from "@fixtures/workpage_route_demand_v0_artifact_submit_response.json";
import routeDemandRunWorkpageStateSnapshot from "@fixtures/workpage_route_demand_v0_run_state.json";
import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import scheduleArtifactSubmitSnapshot from "@fixtures/workpage_schedule_v0_artifact_submit_response.json";
import scheduleRunWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_run_state.json";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { server } from "@/test/api/server";
import {
  buildEodArtifactSubmitResponse,
  buildEodArtifactWorkpageState
} from "@/test/workpages/eodArtifactFixture";

describe("onetruthApi workpage parsing", () => {
  it("parses the canonical artifact-backed EOD workpage wrapper including artifact context", async () => {
    server.use(
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId",
        () =>
        HttpResponse.json(
          buildEodArtifactWorkpageState({
            artifactVersionId: "<artifact_version_id:1>",
            workflowRunId: "<workflow_run_id:2>"
          })
        )
      )
    );

    const contract = await onetruthApi.getWorkflowRunEodArtifactWorkpage(
      "wr-reporting-001",
      "av-eod-artifact-001"
    );

    expect(contract.source.mode).toBe("artifact_projection");
    expect(contract.freshness.source_kind).toBe("artifact_version");
    expect(contract.artifact_context).toMatchObject({
      artifact_version_id: "<artifact_version_id:1>",
      workflow_run_id: "<workflow_run_id:2>",
      artifact_kind: "reporting.upd_draft.workbook",
      latest_in_chain_artifact_version_id: "<artifact_version_id:1>"
    });
    expect(contract.actions).toMatchObject([
      {
        action_id: "workpage.eod-v0.submit_draft",
        kind: "submit_artifact",
        workpage_kind: "eod-v0",
        artifact_version_id: "<artifact_version_id:1>"
      }
    ]);
    expect(contract.run_context).toBeNull();
    expect(contract.draft_resolution).toBeNull();
  });

  it("parses the workflow-run-backed schedule workpage wrapper including run context", async () => {
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0", () =>
        HttpResponse.json(scheduleRunWorkpageStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getWorkflowRunScheduleWorkpage("wr-weekly-001");

    expect(contract.source.mode).toBe("run_projection");
    expect(contract.run_context).toMatchObject({
      workflow_run_id: "<workflow_run_id:1>",
      workflow_id: "weekly_schedule_planning.v1"
    });
    expect(contract.draft_resolution).toBeNull();
    expect(contract.artifact_context).toBeNull();
  });

  it("parses the schedule artifact-backed workpage wrapper including artifact context", async () => {
    server.use(
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId",
        () =>
        HttpResponse.json(scheduleArtifactStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getWorkflowRunScheduleArtifactWorkpage(
      "wr-weekly-001",
      "av-schedule-artifact-001"
    );

    expect(contract.source.mode).toBe("artifact_projection");
    expect(contract.freshness.source_kind).toBe("artifact_version");
    expect(contract.artifact_context).toMatchObject({
      artifact_kind: "planning.draft_weekly_schedule.workbook",
      artifact_version_id: "<artifact_version_id:2>",
      workflow_run_id: "<workflow_run_id:1>",
      latest_in_chain_artifact_version_id: "<artifact_version_id:2>"
    });
    expect(contract.artifact_state).toMatchObject({
      state_kind: "draft",
      editable: true,
      current_artifact_version_id: "<artifact_version_id:2>"
    });
    expect(contract.dependencies[0]).toMatchObject({
      dependency_key: "route_slot_requirements",
      state: "aligned"
    });
    expect(contract.calculations?.selected_day).toMatchObject({
      service_date: "2026-03-24"
    });
    expect(contract.draft_lineage).toMatchObject({
      current_artifact_version_id: "<artifact_version_id:2>"
    });
    expect(contract.accepted_series).toMatchObject({
      series_key: "weekly_schedule_planning.v1:dvc4:pitt-meadows"
    });
    expect(contract.actions.map((action) => action.kind)).toEqual([
      "preview_recalc",
      "submit_artifact",
      "open_latest",
      "create_snapshot"
    ]);
    expect(contract.run_context).toBeNull();
    expect(contract.draft_resolution).toBeNull();
  });

  it("parses the workflow-run-backed route-demand workpage wrapper including schedule impact", async () => {
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0", () =>
        HttpResponse.json(routeDemandRunWorkpageStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getWorkflowRunRouteDemandWorkpage("wr-weekly-001");

    expect(contract.workpage.workpage_id).toBe("route-demand-v0");
    expect(contract.route_demand_calculations?.day_cards[0]?.service_date).toBe("2026-03-22");
    expect(contract.schedule_impact).toMatchObject({
      dependency_state: "aligned"
    });
    expect(contract.actions.map((action) => action.kind)).toEqual(["open_latest"]);
  });

  it("parses the workflow-run-backed driver-preferences workpage wrapper including create action", async () => {
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0", () =>
        HttpResponse.json(driverPreferencesRunWorkpageStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getWorkflowRunDriverPreferencesWorkpage("wr-weekly-001");

    expect(contract.workpage.workpage_id).toBe("driver-preferences-v0");
    expect(contract.preference_grid?.weekdays).toEqual([
      "sun",
      "mon",
      "tue",
      "wed",
      "thu",
      "fri",
      "sat"
    ]);
    expect(contract.schedule_impact).toMatchObject({
      schedule_state: "no_snapshot"
    });
    expect(contract.actions.map((action) => action.kind)).toEqual(["create_snapshot"]);
  });

  it("parses the artifact-backed driver-preferences workpage wrapper including canonical save action", async () => {
    server.use(
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/artifacts/:artifactVersionId",
        () => HttpResponse.json(driverPreferencesArtifactStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getWorkflowRunDriverPreferencesArtifactWorkpage(
      "wr-weekly-001",
      "av-driver-preferences-artifact-001"
    );

    expect(contract.source.mode).toBe("artifact_projection");
    expect(contract.artifact_context?.artifact_kind).toBe(
      "planning.driver_shift_preferences.workbook"
    );
    expect(contract.preference_grid?.drivers.length).toBeGreaterThan(0);
    expect(contract.actions.map((action) => action.kind)).toEqual(["save"]);
  });

  it("parses the artifact-backed route-demand workpage wrapper including canonical save action", async () => {
    server.use(
      http.get(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/artifacts/:artifactVersionId",
        () => HttpResponse.json(routeDemandArtifactStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getWorkflowRunRouteDemandArtifactWorkpage(
      "wr-weekly-001",
      "av-route-demand-artifact-001"
    );

    expect(contract.source.mode).toBe("artifact_projection");
    expect(contract.artifact_context?.artifact_kind).toBe(
      "planning.route_slot_requirements.workbook"
    );
    expect(contract.route_demand_calculations?.day_cards.length).toBeGreaterThan(0);
    expect(contract.schedule_impact?.latest_schedule_draft_artifact_version_id).toBeTruthy();
    expect(contract.actions.map((action) => action.kind)).toEqual(["save"]);
  });

  it("parses the workflow-run-backed EOD landing wrapper including draft resolution", async () => {
    server.use(
      http.get("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0", () =>
        HttpResponse.json(eodRunWorkpageStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getWorkflowRunEodWorkpage("wr-reporting-001");

    expect(contract.source.mode).toBe("run_projection");
    expect(contract.run_context).toMatchObject({
      workflow_run_id: "<workflow_run_id:1>",
      workflow_id: "dispatch_reporting.v1"
    });
    expect(contract.draft_resolution).toMatchObject({
      state: "latest_draft_available",
      artifact_route:
        "/runs/<workflow_run_id:1>/workpages/eod-v0/artifacts/<artifact_version_id:2>",
      open_action_ref: {
        action_id: "workpage.eod-v0.open_latest_draft",
        workpage_kind: "eod-v0",
        workflow_run_id: "<workflow_run_id:1>",
        artifact_version_id: "<artifact_version_id:2>",
        subject: null
      }
    });
  });

  it("parses the workflow-run-backed draft-create envelope", async () => {
    server.use(
      http.post("*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/drafts", () =>
        HttpResponse.json(artifactCreateRunSnapshot.create_response)
      )
    );

    const draft = await onetruthApi.createWorkflowRunEodDraft("wr-reporting-001", {
      idempotency_key: "frontend:test:create-run-draft"
    });

    expect(draft).toEqual(artifactCreateRunSnapshot.create_response.draft);
  });

  it("parses the generic workpage create envelope", async () => {
    server.use(
      http.post("*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/snapshots", () =>
        HttpResponse.json(driverPreferencesArtifactCreateSnapshot.create_response)
      )
    );

    const created = await onetruthApi.createWorkpageAtPath(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0/snapshots",
      {
        idempotency_key: "frontend:test:create-driver-preferences"
      }
    );

    expect(created).toEqual(driverPreferencesArtifactCreateSnapshot.create_response.created);
  });

  it("parses the canonical EOD artifact-submit envelope", async () => {
    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/eod-v0/artifacts/:artifactVersionId/submit",
        () =>
        HttpResponse.json(
          buildEodArtifactSubmitResponse({
            artifactVersionId: "<artifact_version_id:1>",
            workflowRunId: "<workflow_run_id:2>",
            supersedesArtifactVersionId: "<supersedes_artifact_version_id:3>"
          })
        )
      )
    );

    const submitted = await onetruthApi.submitWorkflowRunEodArtifactWorkpage(
      "wr-reporting-001",
      "av-eod-artifact-001",
      {
        form_values: { working_devices: "36" },
        checklist_values: [],
        idempotency_key: "frontend:test:submit-draft"
      }
    );

    expect(submitted).toEqual({
      artifact_version_id: "<artifact_version_id:1>",
      route: "/runs/<workflow_run_id:2>/workpages/eod-v0/artifacts/<artifact_version_id:1>",
      supersedes_artifact_version_id: "<supersedes_artifact_version_id:3>",
      workflow_run_id: "<workflow_run_id:2>"
    });
  });

  it("parses the canonical schedule artifact-submit envelope", async () => {
    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/submit",
        () =>
        HttpResponse.json(scheduleArtifactSubmitSnapshot.submit_response)
      )
    );

    const submitted = await onetruthApi.submitWorkflowRunScheduleArtifactWorkpage(
      "wr-weekly-001",
      "av-schedule-artifact-001",
      {
        rows: [],
        reserve_rows: [],
        idempotency_key: "frontend:test:submit-schedule-draft"
      }
    );

    expect(submitted).toEqual(scheduleArtifactSubmitSnapshot.submit_response.submitted);
  });

  it("parses the canonical schedule artifact-submit and preview envelopes", async () => {
    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/submit",
        () => HttpResponse.json(scheduleArtifactSubmitSnapshot.submit_response)
      ),
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/schedule-v0/artifacts/:artifactVersionId/preview",
        () =>
          HttpResponse.json({
            status: "ok",
            command: "api.workpages.artifact.preview",
            preview: {
              workflow_run_id: "<workflow_run_id:1>",
              artifact_version_id: "<artifact_version_id:2>",
              dirty: true,
              dependency_state: "aligned",
              dependencies: scheduleArtifactStateSnapshot.workpage_state.dependencies,
              calculations: scheduleArtifactStateSnapshot.workpage_state.calculations
            }
          })
      )
    );

    const submitted = await onetruthApi.submitArtifactWorkpageAtPath(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/schedule-v0/artifacts/av-schedule-artifact-001/submit",
      {
        rows: [],
        reserve_rows: [],
        idempotency_key: "frontend:test:submit-schedule-draft-canonical"
      }
    );
    const preview = await onetruthApi.previewArtifactWorkpageAtPath(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/schedule-v0/artifacts/av-schedule-artifact-001/preview",
      {
        rows: [],
        reserve_rows: []
      }
    );

    expect(submitted).toEqual(scheduleArtifactSubmitSnapshot.submit_response.submitted);
    expect(preview.preview).toMatchObject({
      workflow_run_id: "<workflow_run_id:1>",
      artifact_version_id: "<artifact_version_id:2>",
      dirty: true,
      dependency_state: "aligned"
    });
    expect(preview.preview.calculations.selected_day.service_date).toBe("2026-03-24");
  });

  it("parses the canonical route-demand artifact-submit envelope", async () => {
    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/route-demand-v0/artifacts/:artifactVersionId/submit",
        () => HttpResponse.json(routeDemandArtifactSubmitSnapshot.submit_response)
      )
    );

    const submitted = await onetruthApi.submitArtifactWorkpageAtPath(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/route-demand-v0/artifacts/av-route-demand-artifact-001/submit",
      {
        daily_demand_rows: [
          {
            service_date: "2026-03-22",
            planned_route_count: 24
          }
        ],
        idempotency_key: "frontend:test:submit-route-demand-canonical"
      }
    );

    expect(submitted).toEqual(routeDemandArtifactSubmitSnapshot.submit_response.submitted);
  });

  it("parses the canonical driver-preferences artifact-submit envelope", async () => {
    server.use(
      http.post(
        "*/api/v1/workpages/workflow-runs/:workflowRunId/driver-preferences-v0/artifacts/:artifactVersionId/submit",
        () => HttpResponse.json(driverPreferencesArtifactSubmitSnapshot.submit_response)
      )
    );

    const submitted = await onetruthApi.submitArtifactWorkpageAtPath(
      "/api/v1/workpages/workflow-runs/wr-weekly-001/driver-preferences-v0/artifacts/av-driver-preferences-artifact-001/submit",
      {
        driver_rows: [
          {
            driver_id: "DRV-001",
            preferences_by_weekday: {
              sun: null,
              mon: "open_to_work",
              tue: null,
              wed: null,
              thu: null,
              fri: null,
              sat: null
            }
          }
        ],
        idempotency_key: "frontend:test:submit-driver-preferences-canonical"
      }
    );

    expect(submitted).toEqual(driverPreferencesArtifactSubmitSnapshot.submit_response.submitted);
  });
});
