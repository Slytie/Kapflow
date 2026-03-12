import { createIdempotencyKey } from "@/lib/api/idempotency";
import { onetruthApi } from "@/lib/api/onetruthApi";
import type {
  HumanTaskSubgraph,
  HumanTaskRow,
  WorkflowWorkspaceRequiredUpload
} from "@/lib/types/contracts";
import {
  downloadBase64ToFile,
  downloadLatestAttachmentForSubject,
  listAttachmentsForSubject,
  uploadAttachmentForSubject
} from "@/lib/repositories/artifactAttachments";

export interface HumanTaskQuery {
  workflowRunId?: string;
  state?: string;
  assignee?: string;
  query?: string;
}

function matchesQuery(task: HumanTaskRow, query: string): boolean {
  const normalized = query.toLowerCase();
  return (
    task.task_kind.toLowerCase().includes(normalized) ||
    task.stage_id.toLowerCase().includes(normalized) ||
    (task.owner_role ?? "").toLowerCase().includes(normalized)
  );
}

export const humanTasksRepository = {
  async list(query: HumanTaskQuery): Promise<HumanTaskRow[]> {
    const rows = await onetruthApi.listHumanTasks({
      workflow_run_id:
        query.workflowRunId && query.workflowRunId !== "all" ? query.workflowRunId : undefined,
      state: query.state && query.state !== "all" ? query.state : undefined,
      assignee_actor_id:
        query.assignee && query.assignee !== "all" ? query.assignee : undefined,
      limit: 300,
      offset: 0
    });

    return rows.filter((row) => {
      if (query.query && !matchesQuery(row, query.query)) {
        return false;
      }
      return true;
    });
  },

  async get(humanTaskId: string): Promise<HumanTaskRow> {
    return onetruthApi.getHumanTask(humanTaskId);
  },

  async getSubgraph(humanTaskId: string): Promise<HumanTaskSubgraph> {
    return onetruthApi.getHumanTaskSubgraph(humanTaskId);
  },

  async claim(humanTaskId: string, leaseSeconds = 300): Promise<void> {
    await onetruthApi.claimHumanTask(humanTaskId, {
      lease_seconds: leaseSeconds,
      idempotency_key: createIdempotencyKey("claim", humanTaskId)
    });
  },

  async complete(humanTaskId: string, outcome = "complete"): Promise<void> {
    await onetruthApi.completeHumanTask(humanTaskId, {
      outcome,
      idempotency_key: createIdempotencyKey("complete", humanTaskId)
    });
  },

  async runStage06AgentReview(humanTaskId: string): Promise<void> {
    await onetruthApi.runStage06AgentReview(humanTaskId, {
      idempotency_key: createIdempotencyKey("stage06-agent-review", humanTaskId)
    });
  },

  async confirmReview(humanTaskId: string, reviewedArtifactVersionIds: string[]): Promise<void> {
    const reviewedIds = [...new Set(reviewedArtifactVersionIds.filter(Boolean))].sort();
    if (reviewedIds.length === 0) {
      return;
    }
    await onetruthApi.confirmHumanTaskReview(humanTaskId, {
      reviewed_artifact_version_ids: reviewedIds,
      idempotency_key: createIdempotencyKey("confirm-review", `${humanTaskId}:${reviewedIds.join(",")}`)
    });
  },

  async openDraftArtifact(artifactVersionId: string): Promise<void> {
    const downloaded = await onetruthApi.downloadArtifact(artifactVersionId);
    const metadataName = downloaded.artifact_version.metadata_json?.file_name;
    const fileName =
      typeof metadataName === "string" && metadataName.length > 0
        ? metadataName
        : `${downloaded.artifact_version.artifact_version_id}`;
    downloadBase64ToFile(
      downloaded.content_base64,
      fileName,
      downloaded.artifact_version.media_type
    );
  },

  async uploadRequiredResponse(
    humanTaskId: string,
    requirement: WorkflowWorkspaceRequiredUpload,
    file: File
  ): Promise<void> {
    await uploadAttachmentForSubject({
      subjectKind: "human_task",
      subjectId: humanTaskId,
      file,
      artifactKind: requirement.artifact_kind || requirement.dataset_key,
      artifactRole: "evidence"
    });
  },

  async uploadAttachment(humanTaskId: string, file: File): Promise<void> {
    await uploadAttachmentForSubject({
      subjectKind: "human_task",
      subjectId: humanTaskId,
      file,
      artifactKind: "attachment.human_task",
      artifactRole: "evidence"
    });
  },

  async downloadLatestAttachment(humanTaskId: string): Promise<void> {
    await downloadLatestAttachmentForSubject("human_task", humanTaskId);
  },

  async listAttachments(humanTaskId: string) {
    return listAttachmentsForSubject("human_task", humanTaskId);
  }
};
