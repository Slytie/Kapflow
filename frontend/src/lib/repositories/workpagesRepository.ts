import { createIdempotencyKey } from "@/lib/api/idempotency";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import type {
  ArtifactVersionRow,
  WorkpageContract,
  WorkpageDraftResponse,
  WorkpageActionSubjectContext,
  WorkpageSubmittedResponse
} from "@/lib/types/contracts";

function subjectLinkPayload(subjectContext?: WorkpageActionSubjectContext): {
  subject_kind: "human_task" | "approval";
  subject_id: string;
} | undefined {
  if (!subjectContext) {
    return undefined;
  }
  return {
    subject_kind: subjectContext.subject_kind,
    subject_id: subjectContext.subject_id
  };
}

export const workpagesRepository = {
  async schedule(): Promise<WorkpageContract> {
    return onetruthApi.getDemoWorkpage("schedule-v0");
  },

  async scheduleForRun(workflowRunId: string): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunScheduleWorkpage(workflowRunId);
  },

  async eod(): Promise<WorkpageContract> {
    return onetruthApi.getDemoWorkpage("eod-v0");
  },

  async eodForRun(workflowRunId: string): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunEodWorkpage(workflowRunId);
  },

  async eodArtifact(artifactVersionId: string): Promise<WorkpageContract> {
    return onetruthApi.getArtifactWorkpage(artifactVersionId);
  },

  async scheduleArtifact(artifactVersionId: string): Promise<WorkpageContract> {
    return onetruthApi.getArtifactWorkpage(artifactVersionId);
  },

  async createEodDraft(): Promise<WorkpageDraftResponse> {
    return onetruthApi.createDemoEodDraft({
      idempotency_key: createIdempotencyKey("workpage-eod-draft-create", "eod-v0")
    });
  },

  async createEodDraftForRun(
    workflowRunId: string,
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageDraftResponse> {
    return onetruthApi.createWorkflowRunEodDraft(workflowRunId, {
      idempotency_key: createIdempotencyKey("workpage-eod-draft-create", workflowRunId),
      subject_link: subjectLinkPayload(subjectContext)
    });
  },

  async launchWorkspaceDraft(
    createPath: string,
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageDraftResponse> {
    return onetruthApi.createWorkpageDraftAtPath(createPath, {
      idempotency_key: createIdempotencyKey(
        "workspace-workpage-draft-create",
        `${createPath}:${subjectContext?.subject_kind ?? "none"}:${subjectContext?.subject_id ?? "none"}`
      ),
      subject_link: subjectLinkPayload(subjectContext)
    });
  },

  async listEodDraftHistory(workflowRunId: string): Promise<ArtifactVersionRow[]> {
    const artifacts = await onetruthApi.listWorkflowRunArtifacts(workflowRunId);
    return artifacts
      .filter((artifact) => {
        if (artifact.artifact_kind !== "reporting.upd_draft.workbook") {
          return false;
        }
        const demoWorkpageId = artifact.metadata_json?.demo_workpage_id;
        return typeof demoWorkpageId !== "string" || demoWorkpageId === "eod-v0";
      })
      .sort((left, right) => {
        const createdAtCompare = right.created_at.localeCompare(left.created_at);
        if (createdAtCompare !== 0) {
          return createdAtCompare;
        }
        return right.artifact_version_id.localeCompare(left.artifact_version_id);
      })
      .slice(0, 5);
  },

  async listScheduleDraftHistory(workflowRunId: string): Promise<ArtifactVersionRow[]> {
    const artifacts = await onetruthApi.listWorkflowRunArtifacts(workflowRunId);
    return artifacts
      .filter((artifact) => artifact.artifact_kind === "planning.draft_weekly_schedule.workbook")
      .sort((left, right) => {
        const createdAtCompare = right.created_at.localeCompare(left.created_at);
        if (createdAtCompare !== 0) {
          return createdAtCompare;
        }
        return right.artifact_version_id.localeCompare(left.artifact_version_id);
      })
      .slice(0, 5);
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
    },
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpage(artifactVersionId, {
      form_values: payload.formValues,
      checklist_values: payload.checklistValues,
      subject_link: subjectLinkPayload(subjectContext),
      idempotency_key: createIdempotencyKey("workpage-eod-artifact-submit", artifactVersionId)
    });
  },

  async submitScheduleArtifact(
    artifactVersionId: string,
    payload: {
      rows: Array<Record<string, unknown>>;
      reserveRows: Array<Record<string, unknown>>;
    },
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpage(artifactVersionId, {
      rows: payload.rows,
      reserve_rows: payload.reserveRows,
      subject_link: subjectLinkPayload(subjectContext),
      idempotency_key: createIdempotencyKey("workpage-schedule-artifact-submit", artifactVersionId)
    });
  },

  async downloadEodArtifactWorkbook(artifactVersionId: string): Promise<void> {
    const downloaded = await onetruthApi.downloadArtifact(artifactVersionId);
    downloadBinaryToFile(downloaded, `${artifactVersionId}.xlsx`);
  },

  async downloadScheduleArtifactJson(artifactVersionId: string): Promise<void> {
    const downloaded = await onetruthApi.downloadArtifact(artifactVersionId);
    downloadBinaryToFile(downloaded, `${artifactVersionId}.json`);
  }
};
