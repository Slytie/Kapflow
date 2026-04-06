import { createIdempotencyKey } from "@/lib/api/idempotency";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import type {
  ArtifactVersionRow,
  WorkpageContract,
  WorkpageCreateResponse,
  WorkpagePreviewResponse,
  WorkpageSubmittedResponse
} from "@/lib/types/contracts";
import type { WorkpageActionRef } from "@/lib/types/workpages";

export const workpagesRepository = {
  async scheduleForRun(workflowRunId: string): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunScheduleWorkpage(workflowRunId);
  },

  async routeDemandForRun(workflowRunId: string): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunRouteDemandWorkpage(workflowRunId);
  },

  async eodForRun(workflowRunId: string): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunEodWorkpage(workflowRunId);
  },

  async eodArtifact(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunEodArtifactWorkpage(workflowRunId, artifactVersionId);
  },

  async scheduleArtifact(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    return onetruthApi.getWorkflowRunScheduleArtifactWorkpage(workflowRunId, artifactVersionId);
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

  async createEodDraftForRun(
    workflowRunId: string,
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageCreateResponse> {
    return onetruthApi.createWorkflowRunEodDraft(workflowRunId, {
      idempotency_key: createIdempotencyKey("workpage-eod-draft-create", workflowRunId),
      action_ref: actionRef
    });
  },

  async createWorkpage(
    createPath: string,
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageCreateResponse> {
    return onetruthApi.createWorkpageAtPath(createPath, {
      idempotency_key: createIdempotencyKey(
        "workspace-workpage-create",
        `${createPath}:${actionRef?.subject?.subject_kind ?? "none"}:${actionRef?.subject?.subject_id ?? "none"}`
      ),
      action_ref: actionRef
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
      .filter((artifact) => artifact.artifact_kind === "reporting.upd_draft.workbook")
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
    workflowRunId: string,
    artifactVersionId: string,
    payload: {
      formValues: Record<string, unknown>;
      checklistValues: Array<{
        item_id: string;
        selected: boolean;
        note: string;
      }>;
    },
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitWorkflowRunEodArtifactWorkpage(workflowRunId, artifactVersionId, {
      form_values: payload.formValues,
      checklist_values: payload.checklistValues,
      action_ref: actionRef,
      idempotency_key: createIdempotencyKey("workpage-eod-artifact-submit", artifactVersionId)
    });
  },

  async submitScheduleArtifact(
    workflowRunId: string,
    artifactVersionId: string,
    payload: {
      rows: Array<Record<string, unknown>>;
      reserveRows: Array<Record<string, unknown>>;
    },
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitWorkflowRunScheduleArtifactWorkpage(workflowRunId, artifactVersionId, {
      rows: payload.rows,
      reserve_rows: payload.reserveRows,
      action_ref: actionRef,
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
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpageAtPath(submitPath, {
      rows: payload.rows,
      reserve_rows: payload.reserveRows,
      action_ref: actionRef,
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
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpageAtPath(submitPath, {
      daily_demand_rows: payload.dailyDemandRows,
      action_ref: actionRef,
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
    },
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.submitArtifactWorkpageAtPath(submitPath, {
      driver_rows: payload.driverRows,
      action_ref: actionRef,
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
