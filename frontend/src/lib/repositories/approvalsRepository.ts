import { createIdempotencyKey } from "@/lib/api/idempotency";
import { onetruthApi } from "@/lib/api/onetruthApi";
import type { ApprovalRow } from "@/lib/types/contracts";
import {
  downloadLatestAttachmentForSubject,
  listAttachmentsForSubject,
  uploadAttachmentForSubject
} from "@/lib/repositories/artifactAttachments";

export interface ApprovalQuery {
  workflowRunId?: string;
  state?: string;
}

export const approvalsRepository = {
  async list(query: ApprovalQuery): Promise<ApprovalRow[]> {
    return onetruthApi.listApprovals({
      workflow_run_id:
        query.workflowRunId && query.workflowRunId !== "all" ? query.workflowRunId : undefined,
      state: query.state && query.state !== "all" ? query.state : undefined,
      limit: 300,
      offset: 0
    });
  },

  async respond(
    approvalId: string,
    responseKind: "approve" | "reject" | "request_changes",
    responseReason?: string
  ): Promise<ApprovalRow> {
    return onetruthApi.respondApproval(approvalId, {
      response_kind: responseKind,
      response_reason: responseReason,
      idempotency_key: createIdempotencyKey(`approval-${responseKind}`, approvalId)
    });
  },

  async uploadAttachment(approvalId: string, file: File): Promise<void> {
    await uploadAttachmentForSubject({
      subjectKind: "approval",
      subjectId: approvalId,
      file,
      artifactKind: "attachment.approval",
      artifactRole: "evidence"
    });
  },

  async downloadLatestAttachment(approvalId: string): Promise<void> {
    await downloadLatestAttachmentForSubject("approval", approvalId);
  },

  async listAttachments(approvalId: string) {
    return listAttachmentsForSubject("approval", approvalId);
  }
};
