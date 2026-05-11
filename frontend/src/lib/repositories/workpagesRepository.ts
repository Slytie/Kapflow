import { createIdempotencyKey } from "@/lib/api/idempotency";
import { onetruthApi } from "@/lib/api/onetruthApi";
import { downloadBinaryToFile } from "@/lib/repositories/artifactAttachments";
import type {
  WorkpageContract,
  WorkpageCreateResponse,
  WorkpageEodIntakeTask,
  WorkpagePreviewResponse,
  WorkpageScheduleRouteDemandCoverageApplyResponse,
  WorkpageScheduleRouteDemandCoverageRecommendationsResponse,
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

  async ensureEodIntakeTaskForRun(
    workflowRunId: string,
    options?: { serviceDate?: string }
  ): Promise<WorkpageEodIntakeTask> {
    return onetruthApi.ensureWorkflowRunEodIntakeTask(workflowRunId, {
      idempotency_key: createIdempotencyKey(
        "workpage-eod-intake-ensure",
        `${workflowRunId}:${options?.serviceDate ?? "current"}`
      ),
      service_date: options?.serviceDate
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

  async addDriverAvailabilityException(
    workflowRunId: string,
    payload: {
      driverId: string;
      startDate: string;
      endDate: string;
      reasonCode: string;
      reasonNote: string;
    },
    actionRef?: WorkpageActionRef
  ): Promise<Record<string, unknown>> {
    return onetruthApi.addWorkflowRunDriverAvailabilityException(workflowRunId, {
      driver_id: payload.driverId,
      start_date: payload.startDate,
      end_date: payload.endDate,
      reason_code: payload.reasonCode,
      reason_note: payload.reasonNote,
      action_ref: actionRef,
      idempotency_key: driverAvailabilityExceptionIdempotencyKey(
        workflowRunId,
        payload
      )
    });
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

  async markScheduleSickNoShowAtPath(
    sickNoShowPath: string,
    artifactVersionId: string,
    payload: {
      driverId: string;
      serviceDate: string;
      reasonNote: string;
      rows: Array<Record<string, unknown>>;
      reserveRows: Array<Record<string, unknown>>;
    },
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageSubmittedResponse> {
    return onetruthApi.markScheduleSickNoShowAtPath(sickNoShowPath, {
      driver_id: payload.driverId,
      service_date: payload.serviceDate,
      reason_note: payload.reasonNote,
      rows: payload.rows,
      reserve_rows: payload.reserveRows,
      action_ref: actionRef,
      idempotency_key: createIdempotencyKey(
        "workpage-schedule-sick-no-show",
        `${artifactVersionId}:${payload.driverId}:${payload.serviceDate}:${payload.reasonNote}`
      )
    });
  },

  async getScheduleRouteDemandCoverageCandidatesAtPath(
    coverageCandidatesPath: string,
    payload: {
      routeDemandArtifactVersionId: string;
      serviceDates?: string[];
      rows: Array<Record<string, unknown>>;
      reserveRows: Array<Record<string, unknown>>;
      maxCandidates?: number;
    }
  ): Promise<WorkpageScheduleRouteDemandCoverageRecommendationsResponse> {
    return onetruthApi.getScheduleRouteDemandCoverageCandidatesAtPath(
      coverageCandidatesPath,
      {
        route_demand_artifact_version_id: payload.routeDemandArtifactVersionId,
        service_dates: payload.serviceDates,
        rows: payload.rows,
        reserve_rows: payload.reserveRows,
        max_candidates: payload.maxCandidates
      }
    );
  },

  async applyScheduleRouteDemandCoverageAtPath(
    coverageApplyPath: string,
    artifactVersionId: string,
    payload: {
      routeDemandArtifactVersionId: string;
      serviceDates?: string[];
      rows: Array<Record<string, unknown>>;
      reserveRows: Array<Record<string, unknown>>;
      selections: Array<Record<string, unknown>>;
      maxCandidates?: number;
    }
  ): Promise<WorkpageScheduleRouteDemandCoverageApplyResponse> {
    return onetruthApi.applyScheduleRouteDemandCoverageAtPath(coverageApplyPath, {
      route_demand_artifact_version_id: payload.routeDemandArtifactVersionId,
      service_dates: payload.serviceDates,
      rows: payload.rows,
      reserve_rows: payload.reserveRows,
      selections: payload.selections,
      max_candidates: payload.maxCandidates,
      idempotency_key: createIdempotencyKey(
        "workpage-schedule-route-demand-coverage",
        `${artifactVersionId}:${payload.routeDemandArtifactVersionId}`
      )
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

  async createRouteDemandNextWeekAtPath(
    createPath: string,
    workflowRunId: string,
    actionRef?: WorkpageActionRef
  ): Promise<WorkpageCreateResponse> {
    return onetruthApi.createWorkpageAtPath(createPath, {
      idempotency_key: createIdempotencyKey("workpage-route-demand-next-week-create", workflowRunId),
      action_ref: actionRef
    });
  },

  async saveAndRunRouteDemandArtifactAtPath(
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
      idempotency_key: createIdempotencyKey("workpage-route-demand-save-and-run", artifactVersionId)
    });
  },

  async submitDriverPreferencesArtifactAtPath(
    submitPath: string,
    artifactVersionId: string,
    payload: {
      driverRows: Array<{
        driver_id: string;
        driver_quality: "high" | "medium" | "low";
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

function driverAvailabilityExceptionIdempotencyKey(
  workflowRunId: string,
  payload: {
    driverId: string;
    startDate: string;
    endDate: string;
    reasonCode: string;
    reasonNote: string;
  }
): string {
  const normalizedReasonNote = payload.reasonNote.trim().replace(/\s+/g, " ");
  return [
    "frontend",
    "workpage-driver-availability-exception-add",
    workflowRunId,
    payload.driverId,
    payload.startDate,
    payload.endDate,
    payload.reasonCode,
    encodeURIComponent(normalizedReasonNote)
  ].join(":");
}
