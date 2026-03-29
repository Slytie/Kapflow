import { humanTasksRepository } from "@/lib/repositories";
import * as artifactAttachments from "@/lib/repositories/artifactAttachments";

describe("humanTasksRepository", () => {
  it("passes required-upload artifact_role through to subject upload calls", async () => {
    const uploadSpy = vi
      .spyOn(artifactAttachments, "uploadAttachmentForSubject")
      .mockResolvedValue(undefined);

    const file = new File(["fixture"], "route-slots.json", { type: "application/json" });
    await humanTasksRepository.uploadRequiredResponse(
      "ht-weekly-intake-001",
      {
        dataset_key: "planning.route_slot_requirements.workbook",
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
