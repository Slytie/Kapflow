import { createIdempotencyKey } from "@/lib/api/idempotency";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import type {
  WorkpageContract,
  WorkpageDraftResponse,
  WorkpageSubmittedResponse
} from "@/lib/types/contracts";

export const workpagesRepository = {
  async schedule(): Promise<WorkpageContract> {
    return onetruthApi.getDemoWorkpage("schedule-v0");
  },

  async eod(): Promise<WorkpageContract> {
    return onetruthApi.getDemoWorkpage("eod-v0");
  },

  async eodArtifact(artifactVersionId: string): Promise<WorkpageContract> {
    return onetruthApi.getArtifactWorkpage(artifactVersionId);
  },

  async createEodDraft(): Promise<WorkpageDraftResponse> {
    return onetruthApi.createDemoEodDraft({
      idempotency_key: createIdempotencyKey("workpage-eod-draft-create", "eod-v0")
    });
  },

  async submitEodArtifact(
    artifactVersionId: string,
    payload: {
      formValues: Record<string, unknown>;
      checklistValues: Array<{
        item_id: string;
        selected: boolean;
        note: string;
      }>;
    }
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpage(artifactVersionId, {
      form_values: payload.formValues,
      checklist_values: payload.checklistValues,
      idempotency_key: createIdempotencyKey("workpage-eod-artifact-submit", artifactVersionId)
    });
  },

  async downloadEodArtifactWorkbook(artifactVersionId: string): Promise<void> {
    const downloaded = await onetruthApi.downloadArtifact(artifactVersionId);
    downloadBinaryToFile(downloaded, `${artifactVersionId}.xlsx`);
  }
};
