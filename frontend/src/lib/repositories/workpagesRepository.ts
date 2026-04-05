import { createIdempotencyKey } from "@/lib/api/idempotency";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import type {
  ArtifactVersionRow,
  WorkpageContract,
  WorkpageCreateResponse,
  WorkpageActionSubjectContext,
  WorkpagePreviewResponse,
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

  async routeDemandForRun(workflowRunId: string): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunRouteDemandWorkpage(workflowRunId);
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

  async routeDemandArtifact(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunRouteDemandArtifactWorkpage(
      workflowRunId,
      artifactVersionId
    );
  },

  async createEodDraft(): Promise<WorkpageCreateResponse> {
    return onetruthApi.createDemoEodDraft({
      idempotency_key: createIdempotencyKey("workpage-eod-draft-create", "eod-v0")
    });
  },

  async createEodDraftForRun(
    workflowRunId: string,
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageCreateResponse> {
    return onetruthApi.createWorkflowRunEodDraft(workflowRunId, {
      idempotency_key: createIdempotencyKey("workpage-eod-draft-create", workflowRunId),
      subject_link: subjectLinkPayload(subjectContext)
    });
  },

  async createWorkpage(
    createPath: string,
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageCreateResponse> {
    return onetruthApi.createWorkpageAtPath(createPath, {
      idempotency_key: createIdempotencyKey(
        "workspace-workpage-create",
        `${createPath}:${subjectContext?.subject_kind ?? "none"}:${subjectContext?.subject_id ?? "none"}`
      ),
      subject_link: subjectLinkPayload(subjectContext)
    });
  },

  async driverPreferencesForRun(workflowRunId: string): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunDriverPreferencesWorkpage(workflowRunId);
  },

  async driverPreferencesArtifact(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunDriverPreferencesArtifactWorkpage(
      workflowRunId,
      artifactVersionId
    );
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

  async listRouteDemandHistory(workflowRunId: string): Promise<ArtifactVersionRow[]> {
    const artifacts = await onetruthApi.listWorkflowRunArtifacts(workflowRunId);
    return artifacts
      .filter((artifact) => artifact.artifact_kind === "planning.route_slot_requirements.workbook")
      .sort((left, right) => {
        const createdAtCompare = right.created_at.localeCompare(left.created_at);
        if (createdAtCompare !== 0) {
          return createdAtCompare;
        }
        return right.artifact_version_id.localeCompare(left.artifact_version_id);
      })
      .slice(0, 5);
  },

  async listDriverPreferencesHistory(workflowRunId: string): Promise<ArtifactVersionRow[]> {
    const artifacts = await onetruthApi.listWorkflowRunArtifacts(workflowRunId);
    return artifacts
      .filter((artifact) => artifact.artifact_kind === "planning.driver_shift_preferences.workbook")
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

  async submitScheduleArtifactAtPath(
    submitPath: string,
    artifactVersionId: string,
    payload: {
      rows: Array<Record<string, unknown>>;
      reserveRows: Array<Record<string, unknown>>;
    },
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpageAtPath(submitPath, {
      rows: payload.rows,
      reserve_rows: payload.reserveRows,
      subject_link: subjectLinkPayload(subjectContext),
      idempotency_key: createIdempotencyKey("workpage-schedule-artifact-submit", artifactVersionId)
    });
  },

  async previewScheduleArtifact(
    previewPath: string,
    payload: {
      rows: Array<Record<string, unknown>>;
      reserveRows: Array<Record<string, unknown>>;
    }
  ): Promise<WorkpagePreviewResponse> {
    return onetruthApi.previewArtifactWorkpageAtPath(previewPath, {
      rows: payload.rows,
      reserve_rows: payload.reserveRows
    });
  },

  async submitRouteDemandArtifactAtPath(
    submitPath: string,
    artifactVersionId: string,
    payload: {
      dailyDemandRows: Array<{
        service_date: string;
        planned_route_count: number;
      }>;
    },
    subjectContext?: WorkpageActionSubjectContext
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpageAtPath(submitPath, {
      daily_demand_rows: payload.dailyDemandRows,
      subject_link: subjectLinkPayload(subjectContext),
      idempotency_key: createIdempotencyKey("workpage-route-demand-artifact-submit", artifactVersionId)
    });
  },

  async submitDriverPreferencesArtifactAtPath(
    submitPath: string,
    artifactVersionId: string,
    payload: {
      driverRows: Array<{
        driver_id: string;
        preferences_by_weekday: Record<string, string | null>;
      }>;
    }
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpageAtPath(submitPath, {
      driver_rows: payload.driverRows,
      idempotency_key: createIdempotencyKey(
        "workpage-driver-preferences-artifact-submit",
        artifactVersionId
      )
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
