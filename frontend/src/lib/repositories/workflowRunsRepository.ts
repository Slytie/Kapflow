import { onetruthApi } from "@/lib/api/onetruthApi";
import type {
  WorkflowRunDetailContract,
  WorkflowRunRow,
  WorkflowRunWorkspaceContract
} from "@/lib/types/contracts";
import {
  downloadLatestAttachmentForSubject,
  listAttachmentsForSubject,
  uploadAttachmentForSubject
} from "@/lib/repositories/artifactAttachments";

export interface WorkflowRunQuery {
  state?: string;
}

export const workflowRunsRepository = {
  async list(query: WorkflowRunQuery = {}): Promise<WorkflowRunRow[]> {
    return onetruthApi.listWorkflowRuns({
      workflow_id: "schedule_planning.v1",
      state: query.state && query.state !== "all" ? query.state : undefined,
      limit: 300,
      offset: 0
    });
  },

  async detail(workflowRunId?: string): Promise<WorkflowRunDetailContract> {
    const resolvedWorkflowRunId =
      workflowRunId ??
      (
        await onetruthApi.listWorkflowRuns({
          workflow_id: "schedule_planning.v1",
          limit: 1,
          offset: 0
        })
      )[0]?.workflow_run_id;
    if (!resolvedWorkflowRunId) {
      throw new Error("No workflow runs available for detail lookup");
    }
    return onetruthApi.getWorkflowRunDetail(resolvedWorkflowRunId);
  },

  async workspace(workflowRunId: string): Promise<WorkflowRunWorkspaceContract> {
    return onetruthApi.getWorkflowRunWorkspace(workflowRunId);
  },

  async prepareLiveDispatchDay(
    workflowRunId: string,
    payload: {
      published_artifact_version_id: string;
      service_date_id: string;
      idempotency_key: string;
    }
  ) {
    return onetruthApi.prepareLiveDispatchDay(workflowRunId, payload);
  },

  async uploadAttachment(workflowRunId: string, file: File): Promise<void> {
    await uploadAttachmentForSubject({
      subjectKind: "workflow_run",
      subjectId: workflowRunId,
      file,
      artifactKind: "attachment.workflow_run",
      artifactRole: "evidence"
    });
  },

  async downloadLatestAttachment(workflowRunId: string): Promise<void> {
    await downloadLatestAttachmentForSubject("workflow_run", workflowRunId);
  },

  async listAttachments(workflowRunId: string) {
    return listAttachmentsForSubject("workflow_run", workflowRunId);
  }
};
