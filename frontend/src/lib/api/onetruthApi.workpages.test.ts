import { HttpResponse, http } from "msw";

import artifactCreateSnapshot from "@fixtures/workpage_eod_v0_artifact_create_response.json";
import artifactStateSnapshot from "@fixtures/workpage_eod_v0_artifact_state.json";
import artifactSubmitSnapshot from "@fixtures/workpage_eod_v0_artifact_submit_response.json";
import scheduleWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_state.json";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { server } from "@/test/api/server";

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
    expect(contract.freshness.source_version).toBe("weekly_stage04_actual_ops_lab_v2");
    expect(contract.artifact_context).toBeNull();
    expect(contract.workpage.workpage_id).toBe("schedule-v0");
  });

  it("parses the artifact-backed workpage wrapper including artifact context", async () => {
    server.use(
      http.get("*/api/v1/workpages/artifacts/:artifactVersionId", () =>
        HttpResponse.json(artifactStateSnapshot.workpage_state)
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

  it("parses the artifact-submit envelope", async () => {
    server.use(
      http.post("*/api/v1/workpages/artifacts/:artifactVersionId/submit", () =>
        HttpResponse.json(artifactSubmitSnapshot.submit_response)
      )
    );

    const submitted = await onetruthApi.submitArtifactWorkpage("av-eod-artifact-001", {
      form_values: { working_devices: "36" },
      checklist_values: [],
      idempotency_key: "frontend:test:submit-draft"
    });

    expect(submitted).toEqual(artifactSubmitSnapshot.submit_response.submitted);
  });
});
