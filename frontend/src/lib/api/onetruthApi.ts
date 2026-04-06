import { requestBinary, requestJson } from "@/lib/api/httpClient";
import { apiConfig } from "@/lib/api/config";
import type {
  ApprovalRow,
  BoardContract,
  FlagRow,
  HumanTaskRow,
  HumanTaskSubgraph,
  HumanTaskSubgraphArtifactRef,
  HumanTaskSubgraphEdge,
  HumanTaskSubgraphNode,
  LogisticsStoryFamilyEdge,
  LogisticsStoryFamilyModule,
  LogisticsThreeWorkflowStoryContract,
  PointerRow,
  TemplateRecord,
  TemplateRegistryMetadata,
  TimelineEvent,
  WorkpageCreateResponse,
  WorkpageContract,
  WorkpagePreviewResponse,
  WorkpageSubmittedResponse,
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceWorkpageAction,
  WorkflowWorkspaceFreshness,
  WorkflowWorkspaceGraphEdge,
  WorkflowWorkspaceGraphNode,
  WorkflowWorkspaceRequiredReview,
  WorkflowWorkspaceRequiredUpload,
  WorkflowWorkspaceWorkItem,
  WorkflowRunRow,
  ViewerSession
} from "@/lib/types/contracts";
import type {
  WorkpageScheduleAcceptedSeries,
  WorkpageAction,
  WorkpageArtifactHistory,
  WorkpageDriverPreferencesAction,
  WorkpageDriverPreferencesGrid,
  WorkpageDriverPreferencesScheduleImpact,
  WorkpageScheduleAction,
  WorkpageScheduleArtifactState,
  WorkpageScheduleCalculations,
  WorkpageScheduleCheck,
  WorkpageScheduleDependency,
  WorkpageScheduleDraftLineage,
  WorkpageRouteDemandAction,
  WorkpageRouteDemandCalculations,
  WorkpageRouteDemandDayCard,
  WorkpageRouteDemandRefreshTask,
  WorkpageRouteDemandScheduleImpact
} from "@/lib/types/workpages";

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

interface HumanTaskDetailEnvelope extends ListEnvelope {
  human_task: HumanTaskRow;
}

interface HumanTaskSubgraphEnvelope extends ListEnvelope {
  human_task_id: string;
  is_composite: boolean;
  expansion_kind: "task_subgraph";
  subgraph: Record<string, unknown>;
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

interface PrepareLiveDispatchEnvelope extends ListEnvelope {
  workflow_run_id: string;
  result: {
    edge_execution: Record<string, unknown>;
    target_workflow_run: WorkflowRunRow;
    live_seed_artifact: WorkflowRunDetailContract["artifact_versions"][number];
    seed_intake_task: Record<string, unknown>;
  };
}

interface WorkpageEnvelope extends ListEnvelope {
  workpage?: Record<string, unknown>;
  source?: Record<string, unknown>;
  freshness?: Record<string, unknown>;
  artifact_context?: Record<string, unknown> | null;
  run_context?: Record<string, unknown> | null;
  draft_resolution?: Record<string, unknown> | null;
  artifact_state?: Record<string, unknown> | null;
  calculations?: Record<string, unknown> | null;
  artifact_history?: Record<string, unknown> | null;
  draft_lineage?: Record<string, unknown> | null;
  accepted_series?: Record<string, unknown> | null;
  schedule_impact?: Record<string, unknown> | null;
  preference_grid?: Record<string, unknown> | null;
  dependencies?: Array<Record<string, unknown>> | null;
  actions?: Array<Record<string, unknown>> | null;
}

interface WorkpageCreateEnvelope extends ListEnvelope {
  draft?: Record<string, unknown>;
  created?: Record<string, unknown>;
}

interface WorkpageSubmitEnvelope extends ListEnvelope {
  submitted?: Record<string, unknown>;
}

interface WorkpagePreviewEnvelope extends ListEnvelope {
  preview?: Record<string, unknown>;
}

interface PointersEnvelope extends ListEnvelope {
  pointers: PointerRow[];
}

interface BoardEnvelope extends ListEnvelope {
  board: BoardContract;
}

interface LogisticsStoryEnvelope extends ListEnvelope {
  story: LogisticsThreeWorkflowStoryContract;
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

interface ClaimCompleteResultEnvelope extends ListEnvelope {
  result: Record<string, unknown>;
}

interface ApprovalRespondEnvelope extends ListEnvelope {
  approval: ApprovalRow;
}

interface ConfirmReviewResultEnvelope extends ListEnvelope {
  result: Record<string, unknown>;
}

interface TemplateListEnvelope extends ListEnvelope {
  registry: TemplateRegistryMetadata;
  templates: TemplateRecord[];
}

interface ViewerSessionEnvelope extends ListEnvelope {
  viewer_session: Record<string, unknown>;
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

const LOGISTICS_MODULE_NODE_KINDS = new Set(["module"]);
const LOGISTICS_MODULE_DRILLDOWN_KINDS = new Set(["none", "workflow_run", "run_group"]);
const HUMAN_TASK_SUBGRAPH_NODE_KINDS = new Set(["step", "gate"]);

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

function requiredObject(value: unknown, field: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Invalid API response: expected object at '${field}'.`);
  }
  return value as Record<string, unknown>;
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

function normalizeHumanTaskSubgraphNode(
  node: Record<string, unknown>,
  index: number
): HumanTaskSubgraphNode {
  const rawStatus = asString(node.status, "not_started");
  const status = GRAPH_STATUSES.has(rawStatus) ? rawStatus : "not_started";
  const rawNodeKind = asString(node.node_kind, "step");
  const nodeKind: HumanTaskSubgraphNode["node_kind"] = HUMAN_TASK_SUBGRAPH_NODE_KINDS.has(
    rawNodeKind
  )
    ? (rawNodeKind as HumanTaskSubgraphNode["node_kind"])
    : "step";
  return {
    node_id: asString(node.node_id, `subgraph_node_${index}`),
    label: asString(node.label, `Step ${index + 1}`),
    node_kind: nodeKind,
    status: status as HumanTaskSubgraphNode["status"],
    row: asNumber(node.row, 0),
    column: asNumber(node.column, index),
    is_blocking: Boolean(node.is_blocking)
  };
}

function normalizeHumanTaskSubgraphEdge(
  edge: Record<string, unknown>,
  index: number
): HumanTaskSubgraphEdge {
  const kind = asString(edge.edge_kind, "linear");
  return {
    edge_id: asString(edge.edge_id, `subgraph_edge_${index}`),
    from_node_id: asString(edge.from_node_id),
    to_node_id: asString(edge.to_node_id),
    edge_kind: kind === "branch" ? "branch" : kind === "loopback" ? "loopback" : "linear",
    label: asStringOrNull(edge.label)
  };
}

function normalizeHumanTaskSubgraphArtifactRef(
  artifactRef: Record<string, unknown>
): HumanTaskSubgraphArtifactRef {
  return {
    artifact_version_id: asString(artifactRef.artifact_version_id),
    label: asString(artifactRef.label, asString(artifactRef.artifact_version_id, "artifact")),
    source_label: asString(artifactRef.source_label, "Artifact")
  };
}

function normalizeHumanTaskSubgraph(
  humanTaskId: string,
  subgraph: Record<string, unknown>
): HumanTaskSubgraph {
  const freshnessRecord = asRecord(subgraph.freshness);
  return {
    graph_id: asString(subgraph.graph_id, `task_subgraph:${humanTaskId}`),
    template_id: asString(subgraph.template_id),
    title: asString(subgraph.title, "Task process"),
    nodes: asArray<Record<string, unknown>>(subgraph.nodes).map(
      normalizeHumanTaskSubgraphNode
    ),
    edges: asArray<Record<string, unknown>>(subgraph.edges).map(
      normalizeHumanTaskSubgraphEdge
    ),
    freshness: {
      status: ["fresh", "stale", "unknown"].includes(asString(freshnessRecord.status))
        ? (asString(freshnessRecord.status) as WorkflowWorkspaceFreshness["status"])
        : "unknown",
      as_of: asStringOrNull(freshnessRecord.as_of),
      note: asStringOrNull(freshnessRecord.note)
    },
    artifact_refs: asArray<Record<string, unknown>>(subgraph.artifact_refs).map(
      normalizeHumanTaskSubgraphArtifactRef
    )
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
  const blockingReasonCodes = asArray<string>(item.blocking_reason_codes);
  if (blockingReasonCodes.length > 0) {
    return blockingReasonCodes[0];
  }
  const requirements = asArray<Record<string, unknown>>(item.blocking_requirements);
  if (requirements.length === 0) {
    return null;
  }
  const requirement = asString(requirements[0].requirement);
  return requirement || "blocked";
}

function normalizeRequiredUploads(value: unknown): WorkflowWorkspaceRequiredUpload[] {
  return asArray<Record<string, unknown>>(value).map((item) => ({
    dataset_key: asString(item.dataset_key),
    template_id: asStringOrNull(item.template_id),
    artifact_kind: asString(item.artifact_kind),
    artifact_role: asStringOrNull(item.artifact_role),
    required: typeof item.required === "boolean" ? item.required : true,
    required_count: asNumber(item.required_count, 1),
    current_count: asNumber(item.current_count, 0),
    status: asString(item.status, "missing")
  }));
}

function normalizeRequiredReviews(value: unknown): WorkflowWorkspaceRequiredReview[] {
  return asArray<Record<string, unknown>>(value).map((item) => ({
    dataset_key: asString(item.dataset_key),
    artifact_kind: asString(item.artifact_kind),
    required_count: asNumber(item.required_count, 1),
    reviewed_artifact_version_id: asStringOrNull(item.reviewed_artifact_version_id),
    review_confirmation_artifact_version_id: asStringOrNull(item.review_confirmation_artifact_version_id),
    status: asString(item.status, "pending_confirmation")
  }));
}

function normalizeWorkpageActions(value: unknown): WorkflowWorkspaceWorkpageAction[] {
  return asArray<Record<string, unknown>>(value).map((action) => {
    const subjectContext = asRecord(action.subject_context);
    const linkPolicy = asRecord(action.link_policy);
    const presentation: WorkflowWorkspaceWorkpageAction["presentation"] =
      asString(action.presentation, "open_route") === "create_then_open"
        ? "create_then_open"
        : "open_route";
    const rawState = asString(action.state, "unavailable");
    const state: WorkflowWorkspaceWorkpageAction["state"] =
      rawState === "available" ? "available" : "unavailable";
    return {
      action_id: asString(action.action_id),
      workpage_kind: asString(action.workpage_kind),
      label: asString(action.label),
      presentation,
      state,
      route: asStringOrNull(action.route),
      create_path: asStringOrNull(action.create_path),
      subject_context: {
        subject_kind: asString(subjectContext.subject_kind) === "approval" ? "approval" : "human_task",
        subject_id: asString(subjectContext.subject_id),
        workflow_run_id: asString(subjectContext.workflow_run_id)
      },
      link_policy: {
        create_relation_kind: asStringOrNull(linkPolicy.create_relation_kind),
        submit_relation_kind: asStringOrNull(linkPolicy.submit_relation_kind)
      },
      disabled_reason: asStringOrNull(action.disabled_reason)
    };
  });
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
    workpage_actions: normalizeWorkpageActions(item.workpage_actions),
    missing_required_inputs: asArray<string>(item.missing_required_inputs),
    required_uploads: normalizeRequiredUploads(item.required_uploads),
    required_reviews: normalizeRequiredReviews(item.required_reviews),
    blocking_reason_codes: asArray<string>(item.blocking_reason_codes),
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
    workpage_actions: normalizeWorkpageActions(item.workpage_actions),
    missing_required_inputs: asArray<string>(item.missing_required_inputs),
    required_uploads: [],
    required_reviews: [],
    blocking_reason_codes: asArray<string>(item.blocking_reason_codes),
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
    workpage_actions: normalizeWorkpageActions(item.workpage_actions),
    missing_required_inputs: asArray<string>(item.missing_required_inputs),
    required_uploads: [],
    required_reviews: [],
    blocking_reason_codes: asArray<string>(item.blocking_reason_codes),
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

function defaultModuleSelectionSummary(runCount: number, artifactCount: number): string {
  const runWord = runCount === 1 ? "run" : "runs";
  const artifactWord = artifactCount === 1 ? "artifact" : "artifacts";
  return `${runCount} linked ${runWord}, ${artifactCount} downloadable ${artifactWord}`;
}

function normalizeLogisticsStoryModule(
  moduleValue: Record<string, unknown>,
  index: number
): LogisticsStoryFamilyModule {
  const drilldownRefs = asArray<Record<string, unknown>>(moduleValue.drilldown_refs)
    .map((ref) => ({
      workflow_run_id: asString(ref.workflow_run_id),
      workflow_id: asString(ref.workflow_id),
      partition_key: asString(ref.partition_key)
    }))
    .filter((ref) => ref.workflow_run_id.length > 0);
  const artifactRefs = asArray<Record<string, unknown>>(moduleValue.artifact_refs)
    .map((ref) => ({
      artifact_version_id: asString(ref.artifact_version_id),
      label: asString(ref.label, asString(ref.artifact_version_id, "artifact")),
      source_label: asString(ref.source_label, "Artifact")
    }))
    .filter((ref) => ref.artifact_version_id.length > 0);

  const rawNodeKind = asString(moduleValue.node_kind, "module");
  const nodeKind: LogisticsStoryFamilyModule["node_kind"] = LOGISTICS_MODULE_NODE_KINDS.has(rawNodeKind)
    ? "module"
    : "module";

  const rawDrilldownKind = asString(moduleValue.drilldown_kind);
  let drilldownKind: LogisticsStoryFamilyModule["drilldown_kind"];
  if (LOGISTICS_MODULE_DRILLDOWN_KINDS.has(rawDrilldownKind)) {
    drilldownKind = rawDrilldownKind as LogisticsStoryFamilyModule["drilldown_kind"];
  } else if (drilldownRefs.length === 0) {
    drilldownKind = "none";
  } else if (drilldownRefs.length === 1) {
    drilldownKind = "workflow_run";
  } else {
    drilldownKind = "run_group";
  }

  const selectionSummary = asString(
    moduleValue.selection_summary,
    defaultModuleSelectionSummary(drilldownRefs.length, artifactRefs.length)
  );

  return {
    module_id: asString(moduleValue.module_id, `module_${index}`),
    workflow_id: asString(moduleValue.workflow_id),
    partition_kind: asString(moduleValue.partition_kind),
    activation_policy: asString(moduleValue.activation_policy),
    status: asString(moduleValue.status),
    node_kind: nodeKind,
    drilldown_kind: drilldownKind,
    drilldown_refs: drilldownRefs,
    artifact_refs: artifactRefs,
    selection_summary: selectionSummary
  };
}

function normalizeLogisticsStoryEdge(edgeValue: Record<string, unknown>): LogisticsStoryFamilyEdge {
  return {
    edge_id: asString(edgeValue.edge_id),
    source_module_id: asString(edgeValue.source_module_id),
    target_module_id: asString(edgeValue.target_module_id),
    source_stage_id: asString(edgeValue.source_stage_id),
    source_dataset_key: asString(edgeValue.source_dataset_key),
    target_stage_id: asString(edgeValue.target_stage_id),
    target_dataset_key: asString(edgeValue.target_dataset_key),
    partition_transform_id: asString(edgeValue.partition_transform_id),
    handoff_mode: asString(edgeValue.handoff_mode),
    writer_mode: asString(edgeValue.writer_mode),
    status: asString(edgeValue.status)
  };
}

function normalizeLogisticsStoryContract(story: unknown): LogisticsThreeWorkflowStoryContract {
  const storyRecord = asRecord(story);
  const familyGraphRecord = asRecord(storyRecord.family_graph);
  const modules = asArray<Record<string, unknown>>(familyGraphRecord.modules).map(
    normalizeLogisticsStoryModule
  );
  const edges = asArray<Record<string, unknown>>(familyGraphRecord.edges).map(
    normalizeLogisticsStoryEdge
  );
  return {
    ...(storyRecord as unknown as LogisticsThreeWorkflowStoryContract),
    family_graph: {
      ...(familyGraphRecord as unknown as LogisticsThreeWorkflowStoryContract["family_graph"]),
      family_id: asString(familyGraphRecord.family_id),
      family_version: asNumber(familyGraphRecord.family_version, 1),
      modules,
      edges
    }
  };
}

function normalizeViewerSession(session: unknown): ViewerSession {
  const record = asRecord(session);
  const boundaryProfile = asString(record.boundary_profile, "shared_env");
  const requestContextMode = asString(record.request_context_mode, "server_derived");
  return {
    tenant_id: asString(record.tenant_id),
    domain_id: asString(record.domain_id),
    actor_id: asString(record.actor_id),
    actor_type: asString(record.actor_type),
    actor_roles: asArray(record.actor_roles)
      .map((role) => asString(role))
      .filter(Boolean),
    boundary_profile:
      boundaryProfile === "local_dev" || boundaryProfile === "ci_test"
        ? boundaryProfile
        : "shared_env",
    request_context_mode:
      requestContextMode === "trusted_headers" ? "trusted_headers" : "server_derived",
    actor_switching_allowed: Boolean(record.actor_switching_allowed)
  };
}

function normalizeWorkpageContract(payload: WorkpageEnvelope): WorkpageContract {
  const workpage = requiredObject(payload.workpage, "workpage");
  const source = requiredObject(payload.source, "source");
  const freshness = requiredObject(payload.freshness, "freshness");
  const artifactContext =
    payload.artifact_context === null || payload.artifact_context === undefined
      ? null
      : requiredObject(payload.artifact_context, "artifact_context");
  const runContext =
    payload.run_context === null || payload.run_context === undefined
      ? null
      : requiredObject(payload.run_context, "run_context");
  const draftResolution =
    payload.draft_resolution === null || payload.draft_resolution === undefined
      ? null
      : requiredObject(payload.draft_resolution, "draft_resolution");
  const artifactState =
    payload.artifact_state === null || payload.artifact_state === undefined
      ? null
      : requiredObject(payload.artifact_state, "artifact_state");
  const calculations =
    payload.calculations === null || payload.calculations === undefined
      ? null
      : requiredObject(payload.calculations, "calculations");
  const artifactHistory =
    payload.artifact_history === null || payload.artifact_history === undefined
      ? null
      : requiredObject(payload.artifact_history, "artifact_history");
  const draftLineage =
    payload.draft_lineage === null || payload.draft_lineage === undefined
      ? null
      : requiredObject(payload.draft_lineage, "draft_lineage");
  const acceptedSeries =
    payload.accepted_series === null || payload.accepted_series === undefined
      ? null
      : requiredObject(payload.accepted_series, "accepted_series");
  const scheduleImpact =
    payload.schedule_impact === null || payload.schedule_impact === undefined
      ? null
      : requiredObject(payload.schedule_impact, "schedule_impact");
  const preferenceGrid =
    payload.preference_grid === null || payload.preference_grid === undefined
      ? null
      : requiredObject(payload.preference_grid, "preference_grid");

  if (!Array.isArray(workpage.sections)) {
    throw new Error("Invalid API response: expected array at 'workpage.sections'.");
  }
  if (
    !workpage.source_examples ||
    typeof workpage.source_examples !== "object" ||
    Array.isArray(workpage.source_examples)
  ) {
    throw new Error("Invalid API response: expected object at 'workpage.source_examples'.");
  }
  if (
    !workpage.validation ||
    typeof workpage.validation !== "object" ||
    Array.isArray(workpage.validation)
  ) {
    throw new Error("Invalid API response: expected object at 'workpage.validation'.");
  }

  return {
    workpage: workpage as unknown as WorkpageContract["workpage"],
    source: {
      mode: asString(source.mode),
      primary_dataset_key:
        source.primary_dataset_key === null ? null : asString(source.primary_dataset_key),
      source_dataset_keys: requiredArray(source.source_dataset_keys, "source.source_dataset_keys")
        .map((datasetKey) => asString(datasetKey))
        .filter(Boolean),
      source_artifact_version_id: asStringOrNull(source.source_artifact_version_id),
      source_refs: requiredArray(source.source_refs, "source.source_refs")
        .map((ref) => asString(ref))
        .filter(Boolean)
    },
    freshness: {
      generated_at: asString(freshness.generated_at),
      source_kind: asString(freshness.source_kind),
      source_version: asString(freshness.source_version)
    },
    artifact_context: artifactContext
      ? {
          artifact_version_id: asString(artifactContext.artifact_version_id),
          workflow_run_id: asString(artifactContext.workflow_run_id),
          artifact_kind: asString(artifactContext.artifact_kind),
          supersedes_artifact_version_id: asStringOrNull(
            artifactContext.supersedes_artifact_version_id
          ),
          superseded_by_artifact_version_id: asStringOrNull(
            artifactContext.superseded_by_artifact_version_id
          ),
          latest_in_chain_artifact_version_id: asString(
            artifactContext.latest_in_chain_artifact_version_id
          ),
          download_path: asString(artifactContext.download_path)
        }
      : null,
    run_context: runContext
      ? {
          workflow_run_id: asString(runContext.workflow_run_id),
          workflow_id: asString(runContext.workflow_id),
          workflow_version: asString(runContext.workflow_version),
          partition_key: asString(runContext.partition_key),
          logical_date: asString(runContext.logical_date),
          activation_key: asString(runContext.activation_key),
          state: asString(runContext.state)
        }
      : null,
    draft_resolution: draftResolution
      ? {
          state:
            asString(draftResolution.state) === "latest_draft_available"
              ? "latest_draft_available"
              : "no_draft",
          latest_artifact_version_id: asStringOrNull(draftResolution.latest_artifact_version_id),
          artifact_route: asStringOrNull(draftResolution.artifact_route)
        }
      : null,
    artifact_state: normalizeScheduleArtifactState(artifactState),
    dependencies: normalizeScheduleDependencies(payload.dependencies),
    calculations: normalizeScheduleCalculations(calculations),
    route_demand_calculations: normalizeRouteDemandCalculations(calculations),
    preference_grid: normalizeDriverPreferencesGrid(preferenceGrid),
    schedule_impact: normalizeScheduleImpact(scheduleImpact, asString(workpage.workpage_id)),
    artifact_history: normalizeArtifactHistory(artifactHistory),
    draft_lineage: normalizeScheduleDraftLineage(draftLineage),
    accepted_series: normalizeScheduleAcceptedSeries(acceptedSeries),
    actions: normalizeWorkpageActionsForContract(payload.actions)
  };
}

function normalizeWorkpageCreateResponse(payload: WorkpageCreateEnvelope): WorkpageCreateResponse {
  const created = requiredObject(payload.created ?? payload.draft, "created");
  return {
    workflow_run_id: asString(created.workflow_run_id),
    artifact_version_id: asString(created.artifact_version_id),
    route: asString(created.route)
  };
}

function normalizeWorkpageSubmittedResponse(
  payload: WorkpageSubmitEnvelope
): WorkpageSubmittedResponse {
  const submitted = requiredObject(payload.submitted, "submitted");
  return {
    workflow_run_id: asString(submitted.workflow_run_id),
    artifact_version_id: asString(submitted.artifact_version_id),
    supersedes_artifact_version_id: asString(submitted.supersedes_artifact_version_id),
    route: asString(submitted.route)
  };
}

function normalizeScheduleArtifactState(
  value: Record<string, unknown> | null
): WorkpageScheduleArtifactState | null {
  if (!value) {
    return null;
  }
  return {
    state_kind: asString(value.state_kind),
    artifact_kind: asString(value.artifact_kind),
    editable: Boolean(value.editable),
    current_artifact_version_id: asStringOrNull(value.current_artifact_version_id),
    latest_artifact_version_id: asStringOrNull(value.latest_artifact_version_id),
    accepted_artifact_version_id: asStringOrNull(value.accepted_artifact_version_id)
  };
}

function normalizeScheduleDependency(
  value: Record<string, unknown>
): WorkpageScheduleDependency {
  return {
    dependency_key: asString(value.dependency_key),
    artifact_kind: asString(value.artifact_kind),
    artifact_version_id: asStringOrNull(value.artifact_version_id),
    impact_class: asString(value.impact_class),
    state: asString(value.state, "resolved") as WorkpageScheduleDependency["state"],
    source_ref: asStringOrNull(value.source_ref)
  };
}

function normalizeScheduleDependencies(
  value: unknown
): WorkpageScheduleDependency[] {
  return asArray<Record<string, unknown>>(value).map(normalizeScheduleDependency);
}

function normalizeScheduleCheck(value: Record<string, unknown>): WorkpageScheduleCheck {
  return {
    check_id: asString(value.check_id),
    label: asString(value.label),
    state: asString(value.state),
    blocking: Boolean(value.blocking),
    affected_service_dates: asArray(value.affected_service_dates)
      .map((item) => asString(item))
      .filter(Boolean),
    affected_driver_ids: asArray(value.affected_driver_ids)
      .map((item) => asString(item))
      .filter(Boolean)
  };
}

function normalizeScheduleCalculations(
  value: Record<string, unknown> | null
): WorkpageScheduleCalculations | null {
  if (!value) {
    return null;
  }
  const topBar = asRecord(value.top_bar);
  const selectedDay = asRecord(value.selected_day);
  return {
    top_bar: {
      days: asArray<Record<string, unknown>>(topBar.days).map((day) => ({
        service_date: asString(day.service_date),
        weekday_label: asString(day.weekday_label),
        routes_required: asNumber(day.routes_required),
        routes_scheduled:
          day.routes_scheduled === undefined ? undefined : asNumber(day.routes_scheduled),
        on_call_target: asNumber(day.on_call_target),
        on_call_drivers:
          day.on_call_drivers === undefined ? undefined : asNumber(day.on_call_drivers),
        total_staff: day.total_staff === undefined ? undefined : asNumber(day.total_staff),
        excess_capacity:
          day.excess_capacity === undefined ? undefined : asNumber(day.excess_capacity),
        excess_capacity_target:
          day.excess_capacity_target === undefined
            ? undefined
            : asNumber(day.excess_capacity_target),
        available_driver_count:
          day.available_driver_count === undefined
            ? undefined
            : asNumber(day.available_driver_count),
        capacity_state:
          day.capacity_state === undefined ? undefined : asString(day.capacity_state)
      }))
    },
    selected_day: {
      service_date: asString(selectedDay.service_date),
      routes_required: asNumber(selectedDay.routes_required),
      routes_scheduled:
        selectedDay.routes_scheduled === undefined
          ? undefined
          : asNumber(selectedDay.routes_scheduled),
      on_call_target:
        selectedDay.on_call_target === undefined
          ? undefined
          : asNumber(selectedDay.on_call_target),
      on_call_drivers:
        selectedDay.on_call_drivers === undefined
          ? undefined
          : asNumber(selectedDay.on_call_drivers),
      available_driver_count:
        selectedDay.available_driver_count === undefined
          ? undefined
          : asNumber(selectedDay.available_driver_count),
      available_driver_ids: asArray(selectedDay.available_driver_ids)
        .map((item) => asString(item))
        .filter(Boolean),
      available_preference_buckets: {
        open_to_work: asArray(asRecord(selectedDay.available_preference_buckets).open_to_work)
          .map((item) => asString(item))
          .filter(Boolean),
        prefer_not_to_work: asArray(
          asRecord(selectedDay.available_preference_buckets).prefer_not_to_work
        )
          .map((item) => asString(item))
          .filter(Boolean),
        definitely_can_not_work: asArray(
          asRecord(selectedDay.available_preference_buckets).definitely_can_not_work
        )
          .map((item) => asString(item))
          .filter(Boolean),
        unset: asArray(asRecord(selectedDay.available_preference_buckets).unset)
          .map((item) => asString(item))
          .filter(Boolean)
      },
      drivers_available:
        selectedDay.drivers_available === undefined
          ? undefined
          : asNumber(selectedDay.drivers_available),
      projected_on_call_needed:
        selectedDay.projected_on_call_needed === undefined
          ? undefined
          : asNumber(selectedDay.projected_on_call_needed),
      open_questions:
        selectedDay.open_questions === undefined
          ? undefined
          : asString(selectedDay.open_questions)
    },
    driver_metrics: asArray<Record<string, unknown>>(value.driver_metrics).map((item) => ({
      driver_id: asString(item.driver_id),
      driver_name: asString(item.driver_name),
      scheduled_hours: asNumber(item.scheduled_hours),
      scheduled_routes: asNumber(item.scheduled_routes),
      on_call_shifts: asNumber(item.on_call_shifts),
      preference_state: asString(item.preference_state),
      availability_state: asString(item.availability_state),
      compliance_state: asString(item.compliance_state),
      issues: asArray(item.issues).map((issue) => asString(issue)).filter(Boolean)
    })),
    checks: asArray<Record<string, unknown>>(value.checks).map(normalizeScheduleCheck)
  };
}

function normalizeScheduleDraftLineage(
  value: Record<string, unknown> | null
): WorkpageScheduleDraftLineage | null {
  if (!value) {
    return null;
  }
  return {
    current_artifact_version_id: asStringOrNull(value.current_artifact_version_id),
    latest_artifact_version_id: asStringOrNull(value.latest_artifact_version_id),
    previous_artifact_version_id: asStringOrNull(value.previous_artifact_version_id),
    recent_versions: asArray<Record<string, unknown>>(value.recent_versions).map((item) => ({
      artifact_version_id: asString(item.artifact_version_id),
      supersedes_artifact_version_id: asStringOrNull(item.supersedes_artifact_version_id)
    }))
  };
}

function normalizeArtifactHistory(
  value: Record<string, unknown> | null
): WorkpageArtifactHistory | null {
  if (!value) {
    return null;
  }
  return {
    current_artifact_version_id: asStringOrNull(value.current_artifact_version_id),
    latest_artifact_version_id: asStringOrNull(value.latest_artifact_version_id),
    previous_artifact_version_id: asStringOrNull(value.previous_artifact_version_id),
    next_artifact_version_id: asStringOrNull(value.next_artifact_version_id),
    entries: asArray<Record<string, unknown>>(value.entries).map((item) => ({
      artifact_version_id: asString(item.artifact_version_id),
      workflow_run_id: asString(item.workflow_run_id),
      artifact_kind: asString(item.artifact_kind),
      created_at: asString(item.created_at),
      lineage_note: asStringOrNull(item.lineage_note),
      supersedes_artifact_version_id: asStringOrNull(item.supersedes_artifact_version_id),
      route: asString(item.route)
    }))
  };
}

function normalizeScheduleAcceptedSeries(
  value: Record<string, unknown> | null
): WorkpageScheduleAcceptedSeries | null {
  if (!value) {
    return null;
  }
  return {
    series_key: asStringOrNull(value.series_key),
    current_artifact_version_id: asStringOrNull(value.current_artifact_version_id),
    previous_artifact_version_id: asStringOrNull(value.previous_artifact_version_id),
    next_artifact_version_id: asStringOrNull(value.next_artifact_version_id),
    entries: asArray<Record<string, unknown>>(value.entries).map((item) => ({
      artifact_version_id: asString(item.artifact_version_id),
      workflow_run_id: asString(item.workflow_run_id),
      partition_key: asString(item.partition_key),
      logical_date: asString(item.logical_date),
      artifact_kind: asString(item.artifact_kind),
      route: asString(item.route)
    }))
  };
}

function normalizeScheduleActions(value: unknown): WorkpageScheduleAction[] {
  return asArray<Record<string, unknown>>(value).map((action) => ({
    action_id: asString(action.action_id),
    kind: asString(action.kind) as WorkpageScheduleAction["kind"],
    label: asString(action.label),
    state: asString(action.state, "unavailable") as WorkpageScheduleAction["state"],
    workpage_kind: asString(action.workpage_kind),
    artifact_version_id: asStringOrNull(action.artifact_version_id),
    route: asStringOrNull(action.route),
    preview_path: asStringOrNull(action.preview_path),
    submit_path: asStringOrNull(action.submit_path),
    disabled_reason: asStringOrNull(action.disabled_reason)
  }));
}

function normalizeRouteDemandDayCard(
  value: Record<string, unknown>
): WorkpageRouteDemandDayCard {
  const delta =
    value.delta_from_previous_version &&
    typeof value.delta_from_previous_version === "object" &&
    !Array.isArray(value.delta_from_previous_version)
      ? (value.delta_from_previous_version as Record<string, unknown>)
      : null;
  return {
    service_date: asString(value.service_date),
    weekday_label: asString(value.weekday_label),
    planned_route_count: asNumber(value.planned_route_count),
    standard_slot_count: asNumber(value.standard_slot_count),
    standard_early_slot_count: asNumber(value.standard_early_slot_count),
    standard_late_slot_count: asNumber(value.standard_late_slot_count),
    rescue_slot_count: asNumber(value.rescue_slot_count),
    overflow_slot_count: asNumber(value.overflow_slot_count),
    on_call_target: asNumber(value.on_call_target),
    excess_capacity_target: asNumber(value.excess_capacity_target),
    delta_from_previous_version: delta
      ? {
          planned_route_count_delta: asNumber(delta.planned_route_count_delta)
        }
      : null
  };
}

function normalizeRouteDemandCalculations(
  value: Record<string, unknown> | null
): WorkpageRouteDemandCalculations | null {
  if (!value) {
    return null;
  }
  if (!Array.isArray(value.day_cards)) {
    return null;
  }
  return {
    day_cards: asArray<Record<string, unknown>>(value.day_cards).map(
      normalizeRouteDemandDayCard
    )
  };
}

function normalizeRouteDemandRefreshTask(
  value: Record<string, unknown> | null
): WorkpageRouteDemandRefreshTask | null {
  if (!value) {
    return null;
  }
  return {
    human_task_id: asString(value.human_task_id),
    task_run_id: asString(value.task_run_id),
    state: asString(value.state),
    owner_role: asStringOrNull(value.owner_role),
    activation_key: asString(value.activation_key),
    blocked_on_kind: asStringOrNull(value.blocked_on_kind),
    blocked_on_ref: asStringOrNull(value.blocked_on_ref)
  };
}

function normalizeRouteDemandScheduleImpact(
  value: Record<string, unknown> | null
): WorkpageRouteDemandScheduleImpact | null {
  if (!value) {
    return null;
  }
  return {
    latest_schedule_draft_artifact_version_id: asStringOrNull(
      value.latest_schedule_draft_artifact_version_id
    ),
    latest_route_demand_artifact_version_id: asStringOrNull(
      value.latest_route_demand_artifact_version_id
    ),
    dependency_state: asString(value.dependency_state),
    schedule_state: asString(value.schedule_state),
    refresh_task: normalizeRouteDemandRefreshTask(
      value.refresh_task &&
        typeof value.refresh_task === "object" &&
        !Array.isArray(value.refresh_task)
        ? (value.refresh_task as Record<string, unknown>)
        : null
    )
  };
}

function normalizeDriverPreferencesGrid(
  value: Record<string, unknown> | null
): WorkpageDriverPreferencesGrid | null {
  if (!value) {
    return null;
  }
  return {
    weekdays: asArray(value.weekdays)
      .map((item) => asString(item))
      .filter(Boolean) as WorkpageDriverPreferencesGrid["weekdays"],
    drivers: asArray<Record<string, unknown>>(value.drivers).map((item) => {
      const preferences = asRecord(item.preferences_by_weekday);
      return {
        driver_id: asString(item.driver_id),
        driver_name: asString(item.driver_name),
        employment_type: asString(item.employment_type),
        on_call_eligible: Boolean(item.on_call_eligible),
        preferences_by_weekday: {
          sun: asStringOrNull(preferences.sun),
          mon: asStringOrNull(preferences.mon),
          tue: asStringOrNull(preferences.tue),
          wed: asStringOrNull(preferences.wed),
          thu: asStringOrNull(preferences.thu),
          fri: asStringOrNull(preferences.fri),
          sat: asStringOrNull(preferences.sat)
        }
      };
    })
  };
}

function normalizeDriverPreferencesScheduleImpact(
  value: Record<string, unknown> | null
): WorkpageDriverPreferencesScheduleImpact | null {
  if (!value) {
    return null;
  }
  return {
    latest_schedule_draft_artifact_version_id: asStringOrNull(
      value.latest_schedule_draft_artifact_version_id
    ),
    latest_driver_preferences_artifact_version_id: asStringOrNull(
      value.latest_driver_preferences_artifact_version_id
    ),
    dependency_state: asString(value.dependency_state),
    schedule_state: asString(value.schedule_state)
  };
}

function normalizeScheduleImpact(
  value: Record<string, unknown> | null,
  workpageId: string
): WorkpageContract["schedule_impact"] {
  if (!value) {
    return null;
  }
  if (workpageId === "driver-preferences-v0") {
    return normalizeDriverPreferencesScheduleImpact(value);
  }
  return normalizeRouteDemandScheduleImpact(value);
}

function normalizeDriverPreferencesAction(
  action: Record<string, unknown>
): WorkpageDriverPreferencesAction {
  return {
    action_id: asString(action.action_id),
    kind: asString(action.kind) as WorkpageDriverPreferencesAction["kind"],
    label: asString(action.label),
    state: asString(action.state, "unavailable") as WorkpageDriverPreferencesAction["state"],
    workpage_kind: asString(action.workpage_kind),
    artifact_version_id: asStringOrNull(action.artifact_version_id),
    route: asStringOrNull(action.route),
    create_path: asStringOrNull(action.create_path),
    submit_path: asStringOrNull(action.submit_path),
    disabled_reason: asStringOrNull(action.disabled_reason)
  };
}

function normalizeWorkpageActionsForContract(value: unknown): WorkpageAction[] {
  return asArray<Record<string, unknown>>(value).map((action) => {
    const workpageKind = asString(action.workpage_kind);
    const kind = asString(action.kind);
    if (workpageKind === "driver-preferences-v0") {
      return normalizeDriverPreferencesAction(action);
    }
    if (kind === "open_latest" || kind === "save") {
      const routeDemandAction: WorkpageRouteDemandAction = {
        action_id: asString(action.action_id),
        kind: kind as WorkpageRouteDemandAction["kind"],
        label: asString(action.label),
        state: asString(action.state, "unavailable") as WorkpageRouteDemandAction["state"],
        workpage_kind: asString(action.workpage_kind),
        artifact_version_id: asStringOrNull(action.artifact_version_id),
        route: asStringOrNull(action.route),
        submit_path: asStringOrNull(action.submit_path),
        disabled_reason: asStringOrNull(action.disabled_reason)
      };
      return routeDemandAction;
    }
    return normalizeScheduleActions([action])[0] as WorkpageAction;
  });
}

function normalizeWorkpagePreviewResponse(
  payload: WorkpagePreviewEnvelope
): WorkpagePreviewResponse {
  const preview = requiredObject(payload.preview, "preview");
  const calculations = normalizeScheduleCalculations(asRecord(preview.calculations));
  if (!calculations) {
    throw new Error("Invalid API response: expected object at 'preview.calculations'.");
  }
  return {
    preview: {
      workflow_run_id: asString(preview.workflow_run_id),
      artifact_version_id: asString(preview.artifact_version_id),
      dirty: Boolean(preview.dirty),
      dependency_state: asString(preview.dependency_state),
      dependencies: normalizeScheduleDependencies(preview.dependencies),
      calculations
    }
  };
}

interface WorkpageSubjectLinkPayload {
  subject_kind: "human_task" | "approval";
  subject_id: string;
}

function normalizeApiPath(path: string): string {
  if (!path) {
    return path;
  }
  if (path.startsWith("http://") || path.startsWith("https://")) {
    const url = new URL(path);
    path = `${url.pathname}${url.search}${url.hash}`;
  }
  if (path.startsWith(apiConfig.baseUrl)) {
    const suffix = path.slice(apiConfig.baseUrl.length);
    return suffix.startsWith("/") ? suffix : `/${suffix}`;
  }
  if (path.startsWith("/api/v1/")) {
    return path.slice("/api/v1".length);
  }
  return path;
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
  body: Blob;
  fileName: string | null;
  mediaType: string;
  contentLength: number | null;
  requestId: string | null;
}

export const onetruthApi = {
  async getViewerSession(): Promise<ViewerSession> {
    const payload = await requestJson<ViewerSessionEnvelope>("/viewer");
    return normalizeViewerSession(payload.viewer_session);
  },

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

  async getHumanTask(humanTaskId: string): Promise<HumanTaskRow> {
    const payload = await requestJson<HumanTaskDetailEnvelope>(`/human-tasks/${humanTaskId}`);
    return payload.human_task;
  },

  async getHumanTaskSubgraph(humanTaskId: string): Promise<HumanTaskSubgraph> {
    const payload = await requestJson<HumanTaskSubgraphEnvelope>(
      `/human-tasks/${humanTaskId}/subgraph`
    );
    if (!payload.is_composite || payload.expansion_kind !== "task_subgraph") {
      throw new Error("Invalid API response: task subgraph is unavailable.");
    }
    return normalizeHumanTaskSubgraph(humanTaskId, asRecord(payload.subgraph));
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

  async confirmHumanTaskReview(
    humanTaskId: string,
    payload: {
      reviewed_artifact_version_ids: string[];
      idempotency_key: string;
    }
  ): Promise<Record<string, unknown>> {
    const result = await requestJson<ConfirmReviewResultEnvelope>(
      `/human-tasks/${humanTaskId}/confirm-review`,
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

  async runWeeklyStage04OpenAIAgent(
    humanTaskId: string,
    payload: { idempotency_key: string }
  ): Promise<Record<string, unknown>> {
    const result = await requestJson<ClaimCompleteResultEnvelope>(
      `/human-tasks/${humanTaskId}/weekly-stage04-openai-agent`,
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

  async prepareLiveDispatchDay(
    workflowRunId: string,
    payload: {
      published_artifact_version_id: string;
      service_date_id: string;
      idempotency_key: string;
    }
  ): Promise<PrepareLiveDispatchEnvelope["result"]> {
    const result = await requestJson<PrepareLiveDispatchEnvelope>(
      `/workflow-runs/${workflowRunId}/prepare-live-dispatch-day`,
      {
        method: "POST",
        body: payload
      }
    );
    return requiredObject(result.result, "result") as PrepareLiveDispatchEnvelope["result"];
  },

  async getWorkflowRunScheduleWorkpage(workflowRunId: string): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/schedule-v0`
    );
    return normalizeWorkpageContract(payload);
  },

  async getWorkflowRunRouteDemandWorkpage(workflowRunId: string): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/route-demand-v0`
    );
    return normalizeWorkpageContract(payload);
  },

  async getWorkflowRunDriverPreferencesWorkpage(workflowRunId: string): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/driver-preferences-v0`
    );
    return normalizeWorkpageContract(payload);
  },

  async getWorkflowRunEodWorkpage(workflowRunId: string): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/eod-v0`
    );
    return normalizeWorkpageContract(payload);
  },

  async createWorkflowRunEodDraft(
    workflowRunId: string,
    payload: { idempotency_key: string; subject_link?: WorkpageSubjectLinkPayload }
  ): Promise<WorkpageCreateResponse> {
    const result = await requestJson<WorkpageCreateEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/eod-v0/drafts`,
      {
        method: "POST",
        body: payload
      }
    );
    return normalizeWorkpageCreateResponse(result);
  },

  async getWorkflowRunScheduleArtifactWorkpage(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/schedule-v0/artifacts/${encodeURIComponent(artifactVersionId)}`
    );
    return normalizeWorkpageContract(payload);
  },

  async getWorkflowRunEodArtifactWorkpage(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/eod-v0/artifacts/${encodeURIComponent(artifactVersionId)}`
    );
    return normalizeWorkpageContract(payload);
  },

  async getWorkflowRunRouteDemandArtifactWorkpage(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/route-demand-v0/artifacts/${encodeURIComponent(artifactVersionId)}`
    );
    return normalizeWorkpageContract(payload);
  },

  async getWorkflowRunDriverPreferencesArtifactWorkpage(
    workflowRunId: string,
    artifactVersionId: string
  ): Promise<WorkpageContract> {
    const payload = await requestJson<WorkpageEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/driver-preferences-v0/artifacts/${encodeURIComponent(artifactVersionId)}`
    );
    return normalizeWorkpageContract(payload);
  },

  async createWorkpageAtPath(
    createPath: string,
    payload: { idempotency_key: string; subject_link?: WorkpageSubjectLinkPayload }
  ): Promise<WorkpageCreateResponse> {
    const result = await requestJson<WorkpageCreateEnvelope>(normalizeApiPath(createPath), {
      method: "POST",
      body: payload
    });
    return normalizeWorkpageCreateResponse(result);
  },

  async submitWorkflowRunScheduleArtifactWorkpage(
    workflowRunId: string,
    artifactVersionId: string,
    payload: {
      rows?: Array<Record<string, unknown>>;
      reserve_rows?: Array<Record<string, unknown>>;
      subject_link?: WorkpageSubjectLinkPayload;
      idempotency_key: string;
    }
  ): Promise<WorkpageSubmittedResponse> {
    const result = await requestJson<WorkpageSubmitEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/schedule-v0/artifacts/${encodeURIComponent(artifactVersionId)}/submit`,
      {
        method: "POST",
        body: payload
      }
    );
    return normalizeWorkpageSubmittedResponse(result);
  },

  async submitWorkflowRunEodArtifactWorkpage(
    workflowRunId: string,
    artifactVersionId: string,
    payload: {
      form_values?: Record<string, unknown>;
      checklist_values?: Array<Record<string, unknown>>;
      subject_link?: WorkpageSubjectLinkPayload;
      idempotency_key: string;
    }
  ): Promise<WorkpageSubmittedResponse> {
    const result = await requestJson<WorkpageSubmitEnvelope>(
      `/workpages/workflow-runs/${encodeURIComponent(workflowRunId)}/eod-v0/artifacts/${encodeURIComponent(artifactVersionId)}/submit`,
      {
        method: "POST",
        body: payload
      }
    );
    return normalizeWorkpageSubmittedResponse(result);
  },

  async submitArtifactWorkpageAtPath(
    submitPath: string,
    payload: {
      form_values?: Record<string, unknown>;
      checklist_values?: Array<Record<string, unknown>>;
      rows?: Array<Record<string, unknown>>;
      reserve_rows?: Array<Record<string, unknown>>;
      daily_demand_rows?: Array<Record<string, unknown>>;
      driver_rows?: Array<Record<string, unknown>>;
      subject_link?: WorkpageSubjectLinkPayload;
      idempotency_key: string;
    }
  ): Promise<WorkpageSubmittedResponse> {
    const result = await requestJson<WorkpageSubmitEnvelope>(normalizeApiPath(submitPath), {
      method: "POST",
      body: payload
    });
    return normalizeWorkpageSubmittedResponse(result);
  },

  async previewArtifactWorkpageAtPath(
    previewPath: string,
    payload: {
      rows: Array<Record<string, unknown>>;
      reserve_rows: Array<Record<string, unknown>>;
    }
  ): Promise<WorkpagePreviewResponse> {
    const result = await requestJson<WorkpagePreviewEnvelope>(normalizeApiPath(previewPath), {
      method: "POST",
      body: payload
    });
    return normalizeWorkpagePreviewResponse(result);
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

  async getLogisticsThreeWorkflowStory(query: {
    planning_week_id: string;
    service_date_id?: string;
  }): Promise<LogisticsThreeWorkflowStoryContract> {
    const payload = await requestJson<LogisticsStoryEnvelope>("/stories/logistics-three-workflow", {
      query
    });
    if (!payload.story || typeof payload.story !== "object") {
      throw new Error("Invalid API response: missing story payload");
    }
    return normalizeLogisticsStoryContract(payload.story);
  },

  async listTemplates(query: {
    workflow_id?: string;
    stage_id?: string;
    dataset_key?: string;
    variant?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ registry: TemplateRegistryMetadata; templates: TemplateRecord[] }> {
    const payload = await requestJson<TemplateListEnvelope>("/templates", { query });
    return {
      registry: payload.registry,
      templates: requiredArray<TemplateRecord>(payload.templates, "templates")
    };
  },

  async downloadTemplate(templateId: string): Promise<{
    body: Blob;
    fileName: string | null;
    mediaType: string;
    contentLength: number | null;
    requestId: string | null;
  }> {
    return requestBinary(`/templates/${templateId}/download.bin`);
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

  async listArtifactsForSubject(query: {
    workflow_run_id: string;
    subject_kind: "workflow_run" | "task_run" | "human_task" | "approval" | "flag";
    subject_id: string;
  }): Promise<WorkflowRunDetailContract["artifact_versions"]> {
    const payload = await requestJson<ArtifactVersionListEnvelope>("/artifacts", { query });
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
    return requestBinary(`/artifacts/${artifactVersionId}/download.bin`);
  }
};
