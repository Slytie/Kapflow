import { HttpResponse, http } from "msw";

import artifactCreateSnapshot from "@fixtures/workpage_eod_v0_artifact_create_response.json";
import artifactCreateRunSnapshot from "@fixtures/workpage_eod_v0_run_artifact_create_response.json";
import eodRunWorkpageStateSnapshot from "@fixtures/workpage_eod_v0_run_state.json";
import scheduleArtifactStateSnapshot from "@fixtures/workpage_schedule_v0_artifact_state.json";
import scheduleArtifactSubmitSnapshot from "@fixtures/workpage_schedule_v0_artifact_submit_response.json";
import scheduleRunWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_run_state.json";
import scheduleWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_state.json";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { server } from "@/test/api/server";
import {
  buildEodArtifactSubmitResponse,
  buildEodArtifactWorkpageState
} from "@/test/workpages/eodArtifactFixture";

describe("onetruthApi workpage parsing", () => {
  it("parses the backend demo workpage wrapper without stripping metadata", async () => {
    server.use(
      http.get("*/api/v1/workpages/demo/schedule-v0", () =>
        HttpResponse.json(scheduleWorkpageStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getDemoWorkpage("schedule-v0");

    expect(contract.source).toMatchObject({
      mode: "demo",
      primary_dataset_key: null,
      source_dataset_keys: [
        "planning.route_slot_requirements.workbook",
        "planning.approved_availability.workbook",
        "planning.driver_capabilities.workbook",
        "planning.actual_hours_snapshot.workbook",
        "planning.input_bundle.doc"
      ]
    });
    expect(contract.freshness.source_version).toBe("weekly_stage04_actual_ops_lab_v3");
    expect(contract.artifact_context).toBeNull();
    expect(contract.workpage.workpage_id).toBe("schedule-v0");
  });

  it("parses the artifact-backed workpage wrapper including artifact context", async () => {
    server.use(
      http.get("*/api/v1/workpages/artifacts/:artifactVersionId", () =>
        HttpResponse.json(
          buildEodArtifactWorkpageState({
            artifactVersionId: "<artifact_version_id:1>",
            workflowRunId: "<workflow_run_id:2>"
          })
        )
      )
    );

    const contract = await onetruthApi.getArtifactWorkpage("av-eod-artifact-001");

    expect(contract.source.mode).toBe("artifact_projection");
    expect(contract.freshness.source_kind).toBe("artifact_version");
    expect(contract.artifact_context).toMatchObject({
      artifact_version_id: "<artifact_version_id:1>",
      workflow_run_id: "<workflow_run_id:2>",
      artifact_kind: "reporting.upd_draft.workbook",
      latest_in_chain_artifact_version_id: "<artifact_version_id:1>"
    });
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
      http.get("*/api/v1/workpages/artifacts/:artifactVersionId", () =>
        HttpResponse.json(scheduleArtifactStateSnapshot.workpage_state)
      )
    );

    const contract = await onetruthApi.getArtifactWorkpage("av-schedule-artifact-001");

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
      "submit_artifact"
    ]);
    expect(contract.run_context).toBeNull();
    expect(contract.draft_resolution).toBeNull();
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
        "/runs/<workflow_run_id:1>/workpages/eod-v0/artifacts/<artifact_version_id:2>"
    });
  });

  it("parses the draft-create envelope", async () => {
    server.use(
      http.post("*/api/v1/workpages/demo/eod-v0/drafts", () =>
        HttpResponse.json(artifactCreateSnapshot.create_response)
      )
    );

    const draft = await onetruthApi.createDemoEodDraft({
      idempotency_key: "frontend:test:create-draft"
    });

    expect(draft).toEqual(artifactCreateSnapshot.create_response.draft);
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

  it("parses the artifact-submit envelope", async () => {
    server.use(
      http.post("*/api/v1/workpages/artifacts/:artifactVersionId/submit", () =>
        HttpResponse.json(
          buildEodArtifactSubmitResponse({
            artifactVersionId: "<artifact_version_id:1>",
            workflowRunId: "<workflow_run_id:2>",
            supersedesArtifactVersionId: "<supersedes_artifact_version_id:3>"
          })
        )
      )
    );

    const submitted = await onetruthApi.submitArtifactWorkpage("av-eod-artifact-001", {
      form_values: { working_devices: "36" },
      checklist_values: [],
      idempotency_key: "frontend:test:submit-draft"
    });

    expect(submitted).toEqual({
      artifact_version_id: "<artifact_version_id:1>",
      route: "/runs/<workflow_run_id:2>/workpages/eod-v0/artifacts/<artifact_version_id:1>",
      supersedes_artifact_version_id: "<supersedes_artifact_version_id:3>",
      workflow_run_id: "<workflow_run_id:2>"
    });
  });

  it("parses the schedule artifact-submit envelope", async () => {
    server.use(
      http.post("*/api/v1/workpages/artifacts/:artifactVersionId/submit", () =>
        HttpResponse.json(scheduleArtifactSubmitSnapshot.submit_response)
      )
    );

    const submitted = await onetruthApi.submitArtifactWorkpage("av-schedule-artifact-001", {
      rows: [],
      reserve_rows: [],
      idempotency_key: "frontend:test:submit-schedule-draft"
    });

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
});
