import { onetruthApi } from "@/lib/api/onetruthApi";
import type { FlagRow } from "@/lib/types/contracts";
import {
  downloadLatestAttachmentForSubject,
  listAttachmentsForSubject,
  uploadAttachmentForSubject
} from "@/lib/repositories/artifactAttachments";

export interface FlagQuery {
  workflowRunId?: string;
  state?: string;
  severity?: string;
}

export const flagsRepository = {
  async list(query: FlagQuery): Promise<FlagRow[]> {
    const normalizedState =
      query.state && query.state !== "all" ? query.state.toLowerCase() : undefined;

    return onetruthApi.listFlags({
      workflow_run_id:
        query.workflowRunId && query.workflowRunId !== "all" ? query.workflowRunId : undefined,
      state: normalizedState,
      severity: query.severity && query.severity !== "all" ? query.severity : undefined,
      limit: 300,
      offset: 0
    });
  },

  async uploadAttachment(flagId: string, file: File): Promise<void> {
    await uploadAttachmentForSubject({
      subjectKind: "flag",
      subjectId: flagId,
      file,
      artifactKind: "attachment.flag",
      artifactRole: "evidence"
    });
  },

  async downloadLatestAttachment(flagId: string): Promise<void> {
    await downloadLatestAttachmentForSubject("flag", flagId);
  },

  async listAttachments(flagId: string) {
    return listAttachmentsForSubject("flag", flagId);
  }
};
