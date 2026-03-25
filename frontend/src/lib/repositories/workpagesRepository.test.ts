import { workpagesRepository } from "@/lib/repositories";

describe("workpagesRepository", () => {
  it("returns isolated query and artifact-backed EOD contracts plus create/submit responses", async () => {
    const queryLanding = await workpagesRepository.eod();
    const draft = await workpagesRepository.createEodDraft();
    const artifact = await workpagesRepository.eodArtifact(draft.artifact_version_id);
    const submitted = await workpagesRepository.submitEodArtifact(draft.artifact_version_id, {
      formValues: {
        working_devices: "36 online",
        dispatcher_comment: "Drafted from the frontend repository test."
      },
      checklistValues: []
    });

    queryLanding.workpage.summary.service_date = "mutated";

    const queryLandingAgain = await workpagesRepository.eod();
    expect(queryLandingAgain.workpage.summary.service_date).toBe("2026-03-16");
    expect(queryLandingAgain.artifact_context).toBeNull();

    expect(draft.artifact_version_id).toBe("av-eod-artifact-001");
    expect(draft.route).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-001");

    expect(artifact.source.mode).toBe("artifact_projection");
    expect(artifact.artifact_context?.artifact_version_id).toBe("av-eod-artifact-001");
    expect(artifact.freshness.source_version).toBe("av-eod-artifact-001");

    expect(submitted.artifact_version_id).toBe("av-eod-artifact-002");
    expect(submitted.supersedes_artifact_version_id).toBe("av-eod-artifact-001");
    expect(submitted.route).toBe("/demo/logistics/workpages/eod-v0/artifacts/av-eod-artifact-002");
  });
});
