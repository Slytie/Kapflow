import { requestJson } from "@/lib/api/httpClient";
import type {
  ApprovalRow,
  BoardContract,
  FlagRow,
  HumanTaskRow,
  PointerRow,
  TimelineEvent,
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceFreshness,
  WorkflowWorkspaceGraphEdge,
  WorkflowWorkspaceGraphNode,
  WorkflowWorkspaceWorkItem,
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

interface WorkflowRunWorkspaceEnvelope extends ListEnvelope {
  workspace?: WorkflowRunWorkspaceContract;
  workflow_run?: WorkflowRunRow;
  graph?: {
    nodes?: Array<Record<string, unknown>>;
    edges?: Array<Record<string, unknown>>;
    latest_event_sequence?: number | null;
  };
  user_work?: Array<Record<string, unknown>>;
  blocking_work?: Array<Record<string, unknown>>;
  freshness?: Record<string, unknown>;
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

const GRAPH_LAYOUT: Record<string, { row: number; column: number }> = {
  stage03_inputs_ready: { row: 0, column: 0 },
  stage04_capacity_ready: { row: 0, column: 1 },
  stage05_draft_triage: { row: 0, column: 2 },
  stage06_review: { row: 0, column: 3 },
  stage06_publish_approval: { row: 0, column: 4 },
  stage06_base_published: { row: 0, column: 5 },
  stage07_exception_control: { row: 0, column: 6 },
  stage07_replan_approval: { row: 0, column: 7 },
  stage07_delta_published: { row: 0, column: 8 }
};

const GRAPH_STATUSES = new Set([
  "not_started",
  "ready",
  "in_progress",
  "blocked",
  "awaiting_approval",
  "completed",
  "warning"
]);

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asStringOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function requiredArray<T = unknown>(value: unknown, field: string): T[] {
  if (!Array.isArray(value)) {
    throw new Error(`Invalid API response: expected array at '${field}'.`);
  }
  return value as T[];
}

function normalizeGraphNode(node: Record<string, unknown>, index: number): WorkflowWorkspaceGraphNode {
  const nodeId = asString(node.node_id, `node_${index}`);
  const layout = GRAPH_LAYOUT[nodeId] ?? { row: 0, column: index };
  const rawStatus = asString(node.status, "not_started");
  const status = GRAPH_STATUSES.has(rawStatus) ? rawStatus : "not_started";
  const blockingSubjects = asArray(node.blocking_subject_ids);
  return {
    node_id: nodeId,
    stage_id: nodeId.replace(/^stage(\d{2}).*$/, "Stage$1"),
    label: asString(node.label, nodeId),
    status: status as WorkflowWorkspaceGraphNode["status"],
    row: layout.row,
    column: layout.column,
    is_blocking:
      blockingSubjects.length > 0 ||
      status === "blocked" ||
      status === "awaiting_approval" ||
      status === "warning"
  };
}

function normalizeGraphEdge(edge: Record<string, unknown>, index: number): WorkflowWorkspaceGraphEdge {
  const fromNodeId = asString(edge.from);
  const toNodeId = asString(edge.to);
  const kind = asString(edge.kind, "mainline");
  return {
    edge_id: `e-${fromNodeId}-${toNodeId}-${index}`,
    from_node_id: fromNodeId,
    to_node_id: toNodeId,
    edge_kind: kind === "branch" ? "branch" : kind === "loopback" ? "loopback" : "linear",
    label: asStringOrNull(edge.label)
  };
}

function graphNodeIdForStage(stageId: string | null, nodes: WorkflowWorkspaceGraphNode[]): string | null {
  if (!stageId) {
    return null;
  }
  const match = nodes.find((node) => node.stage_id === stageId);
  return match ? match.node_id : null;
}

function firstBlockingReason(item: Record<string, unknown>): string | null {
  const requirements = asArray<Record<string, unknown>>(item.blocking_requirements);
  if (requirements.length === 0) {
    return null;
  }
  const requirement = asString(requirements[0].requirement);
  return requirement || "blocked";
}

function normalizeWorkspaceTaskItem(
  item: Record<string, unknown>,
  workflowRun: WorkflowRunRow,
  graphNodes: WorkflowWorkspaceGraphNode[]
): WorkflowWorkspaceWorkItem {
  const metadata = asRecord(item.metadata);
  const stageId = asString(metadata.stage_id);
  const task: HumanTaskRow = {
    human_task_id: asString(item.subject_id),
    workflow_run_id: asString(metadata.workflow_run_id, workflowRun.workflow_run_id),
    task_run_id: asString(metadata.task_run_id),
    task_kind: asString(metadata.task_kind, "unknown_task"),
    state: asString(item.canonical_state, "OPEN") as HumanTaskRow["state"],
    candidate_roles: asArray<string>(metadata.candidate_roles),
    owner_role: asStringOrNull(metadata.owner_role),
    assignee_actor_id: asStringOrNull(metadata.assignee_actor_id),
    assignee_actor_type: asStringOrNull(metadata.assignee_actor_type),
    due_at: asStringOrNull(metadata.due_at),
    escalation_at: null,
    lease_version: 0,
    claimed_at: null,
    claimed_until: null,
    linked_approval_id: null,
    reopen_count: 0,
    generation: 0,
    created_at: asString(metadata.updated_at, workflowRun.created_at),
    updated_at: asString(metadata.updated_at, workflowRun.updated_at),
    task_run_state: asString(item.canonical_state, "OPEN"),
    stage_id: stageId || "Stage00",
    blocked_on_kind: asStringOrNull(metadata.blocked_on_kind),
    blocked_on_ref: asStringOrNull(metadata.blocked_on_ref),
    spawned_from_flag_id: asStringOrNull(metadata.spawned_from_flag_id)
  };
  return {
    work_id: asString(item.id, `human_task:${task.human_task_id}`),
    item_kind: "human_task",
    human_task: task,
    graph_node_id: graphNodeIdForStage(task.stage_id, graphNodes),
    available_actions: asArray<string>(item.available_actions),
    missing_required_inputs: asArray<string>(item.missing_required_inputs),
    blocking_reason: firstBlockingReason(item)
  };
}

function normalizeWorkspaceApprovalItem(
  item: Record<string, unknown>,
  workflowRun: WorkflowRunRow,
  graphNodes: WorkflowWorkspaceGraphNode[]
): WorkflowWorkspaceWorkItem {
  const metadata = asRecord(item.metadata);
  const stageId = asString(metadata.scope_ref);
  const approval: ApprovalRow = {
    approval_id: asString(item.subject_id),
    workflow_run_id: asString(metadata.workflow_run_id, workflowRun.workflow_run_id),
    task_run_id: asString(metadata.task_run_id),
    approval_kind: asString(metadata.approval_kind, "business_decision"),
    scope_kind: asString(metadata.scope_kind, "stage"),
    scope_ref: stageId || "unknown",
    state: asString(item.canonical_state, "PENDING") as ApprovalRow["state"],
    requested_by_task_run_id: null,
    candidate_roles: asArray<string>(metadata.candidate_roles),
    required_role: asString(metadata.required_role, "unknown"),
    requested_at: asString(metadata.requested_at, workflowRun.created_at),
    responded_at: asStringOrNull(metadata.responded_at),
    response_kind: asStringOrNull(metadata.response_kind),
    response_reason: null,
    decided_by_actor_id: null,
    decided_by_actor_type: null,
    generation: 0,
    created_at: asString(metadata.requested_at, workflowRun.created_at),
    updated_at: asString(metadata.updated_at, workflowRun.updated_at)
  };
  return {
    work_id: asString(item.id, `approval:${approval.approval_id}`),
    item_kind: "approval",
    approval,
    graph_node_id: graphNodeIdForStage(approval.scope_ref, graphNodes),
    available_actions: asArray<string>(item.available_actions),
    missing_required_inputs: asArray<string>(item.missing_required_inputs),
    blocking_reason: firstBlockingReason(item)
  };
}

function normalizeWorkspaceFlagItem(
  item: Record<string, unknown>,
  workflowRun: WorkflowRunRow,
  graphNodes: WorkflowWorkspaceGraphNode[]
): WorkflowWorkspaceWorkItem {
  const metadata = asRecord(item.metadata);
  const flag: FlagRow = {
    flag_id: asString(item.subject_id),
    workflow_run_id: asString(metadata.workflow_run_id, workflowRun.workflow_run_id),
    tenant_id: workflowRun.tenant_id,
    domain_id: workflowRun.domain_id,
    workflow_id: workflowRun.workflow_id,
    partition_key: workflowRun.partition_key,
    kind: asString(metadata.kind, "exception"),
    severity: asString(metadata.severity, "medium"),
    state: asString(item.canonical_state, "open"),
    summary: asString(metadata.summary, "Flag"),
    details_json: asRecord(metadata.details_json),
    assigned_group: asStringOrNull(metadata.assigned_group),
    created_at: asString(metadata.created_at, workflowRun.created_at),
    closed_at: asStringOrNull(metadata.closed_at),
    created_by_actor_id: "unknown",
    created_by_actor_type: "unknown",
    source_event_id: null,
    dedupe_key: "",
    updated_at: asString(metadata.updated_at, workflowRun.updated_at)
  };
  return {
    work_id: asString(item.id, `flag:${flag.flag_id}`),
    item_kind: "flag",
    flag,
    graph_node_id: graphNodeIdForStage("Stage07", graphNodes),
    available_actions: asArray<string>(item.available_actions),
    missing_required_inputs: asArray<string>(item.missing_required_inputs),
    blocking_reason: firstBlockingReason(item)
  };
}

function normalizeWorkspaceContract(payload: WorkflowRunWorkspaceEnvelope): WorkflowRunWorkspaceContract {
  if (payload.workspace) {
    return payload.workspace;
  }

  const workflowRun = payload.workflow_run;
  if (!workflowRun) {
    throw new Error("Invalid API response: missing workflow workspace payload.");
  }
  const graph = asRecord(payload.graph);
  const graphNodes = requiredArray<Record<string, unknown>>(graph.nodes, "graph.nodes").map(
    normalizeGraphNode
  );
  const graphEdges = requiredArray<Record<string, unknown>>(graph.edges, "graph.edges").map(
    normalizeGraphEdge
  );

  const userWork = requiredArray<Record<string, unknown>>(payload.user_work, "user_work").map((item) => {
    const subjectKind = asString(item.subject_kind);
    if (subjectKind === "human_task") {
      return normalizeWorkspaceTaskItem(item, workflowRun, graphNodes);
    }
    if (subjectKind === "approval") {
      return normalizeWorkspaceApprovalItem(item, workflowRun, graphNodes);
    }
    return normalizeWorkspaceFlagItem(item, workflowRun, graphNodes);
  });

  const blockingWork = requiredArray<Record<string, unknown>>(payload.blocking_work, "blocking_work").map(
    (item) => {
      const subjectKind = asString(item.subject_kind);
      if (subjectKind === "human_task") {
        return normalizeWorkspaceTaskItem(item, workflowRun, graphNodes);
      }
      if (subjectKind === "approval") {
        return normalizeWorkspaceApprovalItem(item, workflowRun, graphNodes);
      }
      return normalizeWorkspaceFlagItem(item, workflowRun, graphNodes);
    }
  );

  const freshnessPayload = asRecord(payload.freshness);
  const latestEventSequence =
    asNumber(graph.latest_event_sequence, Number.NaN) ||
    asNumber(freshnessPayload.latest_event_sequence, Number.NaN);
  const freshness: WorkflowWorkspaceFreshness = {
    status: freshnessPayload.latest_event_recorded_at ? "fresh" : "unknown",
    as_of:
      asStringOrNull(freshnessPayload.latest_event_recorded_at) ??
      asStringOrNull(freshnessPayload.workflow_run_updated_at),
    note: asStringOrNull(freshnessPayload.generated_at)
  };

  return {
    workflow_run: workflowRun,
    graph: {
      nodes: graphNodes,
      edges: graphEdges
    },
    user_work: userWork,
    blocking_work: blockingWork,
    latest_event_sequence: Number.isFinite(latestEventSequence) ? latestEventSequence : null,
    freshness
  };
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
    return requiredArray<HumanTaskRow>(payload.human_tasks, "human_tasks");
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

  async runStage06AgentReview(
    humanTaskId: string,
    payload: { idempotency_key: string }
  ): Promise<Record<string, unknown>> {
    const result = await requestJson<ClaimCompleteResultEnvelope>(
      `/human-tasks/${humanTaskId}/stage06-agent-review`,
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
    return requiredArray<ApprovalRow>(payload.approvals, "approvals");
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
    return requiredArray<FlagRow>(payload.flags, "flags");
  },

  async listWorkflowRuns(query: {
    workflow_id?: string;
    state?: string;
    limit?: number;
    offset?: number;
  }): Promise<WorkflowRunRow[]> {
    const payload = await requestJson<WorkflowRunsEnvelope>("/workflow-runs", { query });
    return requiredArray<WorkflowRunRow>(payload.workflow_runs, "workflow_runs");
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

  async getWorkflowRunWorkspace(workflowRunId: string): Promise<WorkflowRunWorkspaceContract> {
    const payload = await requestJson<WorkflowRunWorkspaceEnvelope>(
      `/workflow-runs/${workflowRunId}/workspace`
    );
    return normalizeWorkspaceContract(payload);
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
    return requiredArray<PointerRow>(payload.pointers, "pointers");
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
    return requiredArray<TimelineEvent>(payload.events, "events");
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
