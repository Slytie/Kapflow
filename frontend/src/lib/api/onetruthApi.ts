import { requestJson } from "@/lib/api/httpClient";
import type {
  ApprovalRow,
  BoardContract,
  FlagRow,
  HumanTaskRow,
  PointerRow,
  TimelineEvent,
  WorkflowRunDetailContract,
  WorkflowRunRow
} from "@/lib/types/contracts";

interface PageEnvelope {
  limit: number;
  offset: number;
}

interface ListEnvelope {
  status: "ok";
  command: string;
  page?: PageEnvelope;
}

interface HumanTasksEnvelope extends ListEnvelope {
  human_tasks: HumanTaskRow[];
}

interface ApprovalsEnvelope extends ListEnvelope {
  approvals: ApprovalRow[];
}

interface FlagsEnvelope extends ListEnvelope {
  flags: FlagRow[];
}

interface WorkflowRunsEnvelope extends ListEnvelope {
  workflow_runs: WorkflowRunRow[];
}

interface WorkflowRunDetailEnvelope extends ListEnvelope {
  workflow_run: WorkflowRunRow;
  human_tasks: HumanTaskRow[];
  approvals: ApprovalRow[];
  artifact_versions: WorkflowRunDetailContract["artifact_versions"];
  pointers: PointerRow[];
  flags: FlagRow[];
  summary: WorkflowRunDetailContract["summary"];
}

interface PointersEnvelope extends ListEnvelope {
  pointers: PointerRow[];
}

interface BoardEnvelope extends ListEnvelope {
  board: BoardContract;
}

interface TimelineEnvelope extends ListEnvelope {
  events: TimelineEvent[];
}

interface ArtifactVersionEnvelope extends ListEnvelope {
  artifact_version: WorkflowRunDetailContract["artifact_versions"][number];
}

interface ArtifactVersionListEnvelope extends ListEnvelope {
  artifact_versions: WorkflowRunDetailContract["artifact_versions"];
}

interface ArtifactDownloadEnvelope extends ListEnvelope {
  artifact_version: WorkflowRunDetailContract["artifact_versions"][number];
  content_base64: string;
  byte_size: number;
}

interface ClaimCompleteResultEnvelope extends ListEnvelope {
  result: Record<string, unknown>;
}

interface ApprovalRespondEnvelope extends ListEnvelope {
  approval: ApprovalRow;
}

export interface ArtifactUploadPayload {
  artifact_kind: string;
  artifact_role?: string;
  file_name: string;
  media_type?: string;
  content_base64: string;
  metadata_json?: Record<string, unknown>;
  parent_artifact_version_id?: string | null;
  supersedes_artifact_version_id?: string | null;
  lineage_note?: string | null;
  relation_kind?: string;
  idempotency_key: string;
}

export interface ArtifactDownloadResult {
  artifact_version: WorkflowRunDetailContract["artifact_versions"][number];
  content_base64: string;
  byte_size: number;
}

export const onetruthApi = {
  async listHumanTasks(query: {
    workflow_run_id?: string;
    state?: string;
    stage_id?: string;
    task_kind?: string;
    assignee_actor_id?: string;
    owner_role?: string;
    limit?: number;
    offset?: number;
  }): Promise<HumanTaskRow[]> {
    const payload = await requestJson<HumanTasksEnvelope>("/human-tasks", { query });
    return payload.human_tasks;
  },

  async claimHumanTask(
    humanTaskId: string,
    payload: { lease_seconds: number; idempotency_key: string }
  ): Promise<Record<string, unknown>> {
    const result = await requestJson<ClaimCompleteResultEnvelope>(
      `/human-tasks/${humanTaskId}/claim`,
      {
        method: "POST",
        body: payload
      }
    );
    return result.result;
  },

  async completeHumanTask(
    humanTaskId: string,
    payload: { outcome: string; idempotency_key: string }
  ): Promise<Record<string, unknown>> {
    const result = await requestJson<ClaimCompleteResultEnvelope>(
      `/human-tasks/${humanTaskId}/complete`,
      {
        method: "POST",
        body: payload
      }
    );
    return result.result;
  },

  async listApprovals(query: {
    workflow_run_id?: string;
    state?: string;
    approval_kind?: string;
    required_role?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApprovalRow[]> {
    const payload = await requestJson<ApprovalsEnvelope>("/approvals", { query });
    return payload.approvals;
  },

  async respondApproval(
    approvalId: string,
    payload: { response_kind: string; response_reason?: string; idempotency_key: string }
  ): Promise<ApprovalRow> {
    const result = await requestJson<ApprovalRespondEnvelope>(`/approvals/${approvalId}/respond`, {
      method: "POST",
      body: payload
    });
    return result.approval;
  },

  async listFlags(query: {
    workflow_run_id?: string;
    state?: string;
    severity?: string;
    kind?: string;
    assigned_group?: string;
    limit?: number;
    offset?: number;
  }): Promise<FlagRow[]> {
    const payload = await requestJson<FlagsEnvelope>("/flags", { query });
    return payload.flags;
  },

  async listWorkflowRuns(query: {
    workflow_id?: string;
    state?: string;
    limit?: number;
    offset?: number;
  }): Promise<WorkflowRunRow[]> {
    const payload = await requestJson<WorkflowRunsEnvelope>("/workflow-runs", { query });
    return payload.workflow_runs;
  },

  async getWorkflowRunDetail(workflowRunId: string): Promise<WorkflowRunDetailContract> {
    const payload = await requestJson<WorkflowRunDetailEnvelope>(`/workflow-runs/${workflowRunId}`);
    return {
      workflow_run: payload.workflow_run,
      human_tasks: payload.human_tasks,
      approvals: payload.approvals,
      artifact_versions: payload.artifact_versions,
      pointers: payload.pointers,
      flags: payload.flags,
      summary: payload.summary
    };
  },

  async listPointers(query: {
    workflow_run_id?: string;
    scope_kind?: string;
    scope_ref?: string;
    artifact_kind?: string;
    limit?: number;
    offset?: number;
  }): Promise<PointerRow[]> {
    const payload = await requestJson<PointersEnvelope>("/pointers", { query });
    return payload.pointers;
  },

  async listBoard(query: {
    workflow_id?: string;
    workflow_run_id?: string;
    stage_id?: string;
    task_kind?: string;
    task_state?: string;
    approval_state?: string;
    assignee_actor_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<BoardContract> {
    const payload = await requestJson<BoardEnvelope>("/board/schedule-planning", { query });
    return payload.board;
  },

  async listTimelineEvents(query: {
    workflow_run_id?: string;
    event_type?: string;
    since_sequence_no?: number;
    limit?: number;
    offset?: number;
  }): Promise<TimelineEvent[]> {
    const payload = await requestJson<TimelineEnvelope>("/timeline-events", { query });
    return payload.events;
  },

  async listHumanTaskArtifacts(humanTaskId: string): Promise<WorkflowRunDetailContract["artifact_versions"]> {
    const payload = await requestJson<ArtifactVersionListEnvelope>(`/human-tasks/${humanTaskId}/artifacts`);
    return payload.artifact_versions;
  },

  async uploadHumanTaskArtifact(
    humanTaskId: string,
    payload: ArtifactUploadPayload
  ): Promise<WorkflowRunDetailContract["artifact_versions"][number]> {
    const result = await requestJson<ArtifactVersionEnvelope>(`/human-tasks/${humanTaskId}/artifacts/upload`, {
      method: "POST",
      body: payload
    });
    return result.artifact_version;
  },

  async listApprovalArtifacts(approvalId: string): Promise<WorkflowRunDetailContract["artifact_versions"]> {
    const payload = await requestJson<ArtifactVersionListEnvelope>(`/approvals/${approvalId}/artifacts`);
    return payload.artifact_versions;
  },

  async uploadApprovalArtifact(
    approvalId: string,
    payload: ArtifactUploadPayload
  ): Promise<WorkflowRunDetailContract["artifact_versions"][number]> {
    const result = await requestJson<ArtifactVersionEnvelope>(`/approvals/${approvalId}/artifacts/upload`, {
      method: "POST",
      body: payload
    });
    return result.artifact_version;
  },

  async listFlagArtifacts(flagId: string): Promise<WorkflowRunDetailContract["artifact_versions"]> {
    const payload = await requestJson<ArtifactVersionListEnvelope>(`/flags/${flagId}/artifacts`);
    return payload.artifact_versions;
  },

  async uploadFlagArtifact(
    flagId: string,
    payload: ArtifactUploadPayload
  ): Promise<WorkflowRunDetailContract["artifact_versions"][number]> {
    const result = await requestJson<ArtifactVersionEnvelope>(`/flags/${flagId}/artifacts/upload`, {
      method: "POST",
      body: payload
    });
    return result.artifact_version;
  },

  async listWorkflowRunArtifacts(
    workflowRunId: string
  ): Promise<WorkflowRunDetailContract["artifact_versions"]> {
    const payload = await requestJson<ArtifactVersionListEnvelope>(`/workflow-runs/${workflowRunId}/artifacts`);
    return payload.artifact_versions;
  },

  async uploadWorkflowRunArtifact(
    workflowRunId: string,
    payload: ArtifactUploadPayload
  ): Promise<WorkflowRunDetailContract["artifact_versions"][number]> {
    const result = await requestJson<ArtifactVersionEnvelope>(`/workflow-runs/${workflowRunId}/artifacts/upload`, {
      method: "POST",
      body: payload
    });
    return result.artifact_version;
  },

  async downloadArtifact(artifactVersionId: string): Promise<ArtifactDownloadResult> {
    const payload = await requestJson<ArtifactDownloadEnvelope>(`/artifacts/${artifactVersionId}/download`);
    return {
      artifact_version: payload.artifact_version,
      content_base64: payload.content_base64,
      byte_size: payload.byte_size
    };
  }
};
