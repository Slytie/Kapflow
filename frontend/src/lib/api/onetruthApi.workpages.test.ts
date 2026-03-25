import { HttpResponse, http } from "msw";

import scheduleWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_state.json";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { server } from "@/test/api/server";

describe("onetruthApi workpage parsing", () => {
  it("parses the backend demo workpage wrapper contract without stripping metadata", async () => {
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
    expect(contract.workpage.workpage_id).toBe("schedule-v0");
    expect(contract.workpage.sections.map((section) => section.kind)).toEqual([
      "summary_cards",
      "table",
      "table",
      "table",
      "note_panel",
      "form",
      "history_stub"
    ]);
  });
});
