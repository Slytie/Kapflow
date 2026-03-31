import { humanTasksRepository } from "@/lib/repositories";
import * as artifactAttachments from "@/lib/repositories/artifactAttachments";

describe("humanTasksRepository", () => {
  it("passes required-upload artifact_role through to subject upload calls", async () => {
    const uploadSpy = vi
      .spyOn(artifactAttachments, "uploadAttachmentForSubject")
      .mockResolvedValue({
        artifact_version_id: "av-uploaded-001",
        workflow_run_id: "wr-test-001",
        task_run_id: null,
        artifact_kind: "planning.route_slot_requirements.workbook",
        artifact_role: "official_input",
        media_type: "application/json",
        storage_uri: "memory://av-uploaded-001",
        content_digest: "sha256:test",
        byte_size: 7,
        metadata_json: {},
        parent_artifact_version_id: null,
        supersedes_artifact_version_id: null,
        lineage_note: null,
        created_at: "2026-03-31T12:00:00Z"
      });

    const file = new File(["fixture"], "route-slots.json", { type: "application/json" });
    await humanTasksRepository.uploadRequiredResponse(
      "ht-weekly-intake-001",
      {
        dataset_key: "planning.route_slot_requirements.workbook",
        template_id: null,
        artifact_kind: "planning.route_slot_requirements.workbook",
        artifact_role: "official_input",
        required_count: 1,
        current_count: 0,
        status: "missing"
      },
      file
    );

    expect(uploadSpy).toHaveBeenCalledWith({
      subjectKind: "human_task",
      subjectId: "ht-weekly-intake-001",
      file,
      artifactKind: "planning.route_slot_requirements.workbook",
      artifactRole: "official_input"
    });

    uploadSpy.mockRestore();
  });
});
