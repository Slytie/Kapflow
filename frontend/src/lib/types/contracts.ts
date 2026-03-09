export type HumanTaskState = "OPEN" | "CLAIMED" | "COMPLETED";
export type ApprovalState = "PENDING" | "RESPONDED";

export interface HumanTaskRow {
  human_task_id: string;
  workflow_run_id: string;
  task_run_id: string;
  task_kind: string;
  state: HumanTaskState;
  candidate_roles: string[];
  owner_role: string | null;
  assignee_actor_id: string | null;
  assignee_actor_type: string | null;
  due_at: string | null;
  escalation_at: string | null;
  lease_version: number;
  claimed_at: string | null;
  claimed_until: string | null;
  linked_approval_id: string | null;
  reopen_count: number;
  generation: number;
  created_at: string;
  updated_at: string;
  task_run_state: string;
  stage_id: string;
  blocked_on_kind: string | null;
  blocked_on_ref: string | null;
  spawned_from_flag_id: string | null;
  available_actions?: string[];
  missing_required_inputs?: string[];
  blocking_reason_codes?: string[];
  can_complete?: boolean;
  can_confirm_review?: boolean;
}

export interface ApprovalRow {
  approval_id: string;
  workflow_run_id: string;
  task_run_id: string;
  approval_kind: string;
  scope_kind: string;
  scope_ref: string;
  state: ApprovalState;
  requested_by_task_run_id: string | null;
  candidate_roles: string[];
  required_role: string;
  requested_at: string;
  responded_at: string | null;
  response_kind: string | null;
  response_reason: string | null;
  decided_by_actor_id: string | null;
  decided_by_actor_type: string | null;
  generation: number;
  created_at: string;
  updated_at: string;
}

export interface FlagRow {
  flag_id: string;
  workflow_run_id: string;
  tenant_id: string;
  domain_id: string;
  workflow_id: string;
  partition_key: string;
  kind: string;
  severity: string;
  state: string;
  summary: string;
  details_json: Record<string, unknown>;
  assigned_group: string | null;
  created_at: string;
  closed_at: string | null;
  created_by_actor_id: string;
  created_by_actor_type: string;
  source_event_id: string | null;
  dedupe_key: string;
  updated_at: string;
}

export interface WorkflowRunRow {
  workflow_run_id: string;
  workflow_id: string;
  workflow_version: string;
  tenant_id: string;
  domain_id: string;
  partition_key: string;
  logical_date: string;
  activation_key: string;
  state: string;
  active_issue_count: number;
  created_at: string;
  updated_at: string;
}

export interface PointerRow {
  workflow_run_id: string;
  pointer_key: string;
  scope_kind: string;
  scope_ref: string;
  artifact_kind: string;
  artifact_version_id: string;
  promotion_reason: string;
  promoted_by_task_run_id: string | null;
  approved_by_approval_id: string | null;
  generation: number;
  updated_at: string;
}

export interface ArtifactVersionRow {
  artifact_version_id: string;
  workflow_run_id: string;
  task_run_id: string | null;
  artifact_kind: string;
  artifact_role: string;
  media_type: string;
  storage_uri: string;
  content_digest: string;
  byte_size: number;
  metadata_json: Record<string, unknown>;
  parent_artifact_version_id: string | null;
  supersedes_artifact_version_id: string | null;
  lineage_note: string | null;
  created_at: string;
  links?: ArtifactLinkRow[];
}

export interface ArtifactLinkRow {
  artifact_version_id: string;
  workflow_run_id: string;
  subject_kind: "workflow_run" | "task_run" | "human_task" | "approval" | "flag";
  subject_id: string;
  relation_kind: string;
  created_at: string;
  created_by_actor_id: string | null;
  created_by_actor_type: string | null;
}

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  sequence_no: number;
  occurred_at: string;
  recorded_at: string;
  tenant_id: string;
  domain_id: string;
  payload: Record<string, unknown>;
  actor: { id: string; type: string };
  links: Array<{ id: string; rel: string; type: string }>;
}

export interface BoardCard {
  card_id: string;
  card_type: "human_task" | "approval";
  lane: string;
  title: string;
  workflow_run_id: string;
  workflow_id: string;
  task_run_id?: string;
  human_task_id?: string;
  stage_id?: string;
  task_kind?: string;
  state?: string;
  owner_role?: string;
  assignee_actor_id?: string | null;
  assignee_actor_type?: string | null;
  due_at?: string | null;
  claimed_at?: string | null;
  claimed_until?: string | null;
  blocked_on_kind?: string | null;
  blocked_on_ref?: string | null;
  spawned_from_flag_id?: string | null;
  linked_approval_count?: number;
  linked_approval_states?: string[];
  approval_id?: string;
  approval_kind?: string;
  scope_kind?: string;
  scope_ref?: string;
  required_role?: string;
  candidate_roles?: string[];
  requested_at?: string;
  responded_at?: string | null;
  response_kind?: string | null;
}

export interface BoardLane {
  lane: string;
  label: string;
  position: number;
  card_count: number;
}

export interface BoardContract {
  board_id: string;
  lanes: BoardLane[];
  cards: BoardCard[];
  summary: {
    workflow_run_count: number;
    human_task_count: number;
    approval_count: number;
    pointer_count: number;
    card_count: number;
  };
  page: { limit: number; offset: number };
  filters: Record<string, string | null>;
  workflow_runs: WorkflowRunRow[];
  pointers: PointerRow[];
}

export interface WorkflowRunDetailContract {
  workflow_run: WorkflowRunRow;
  human_tasks: HumanTaskRow[];
  approvals: ApprovalRow[];
  artifact_versions: ArtifactVersionRow[];
  pointers: PointerRow[];
  flags: FlagRow[];
  summary: {
    human_task_count: number;
    approval_count: number;
    artifact_version_count: number;
    pointer_count: number;
    flag_count: number;
    active_issue_count: number;
  };
}

export type WorkflowWorkspaceNodeStatus =
  | "not_started"
  | "ready"
  | "in_progress"
  | "blocked"
  | "awaiting_approval"
  | "completed"
  | "warning";

export interface WorkflowWorkspaceGraphNode {
  node_id: string;
  stage_id: string;
  label: string;
  status: WorkflowWorkspaceNodeStatus;
  row: number;
  column: number;
  is_blocking: boolean;
  responsibility_summary?: string | null;
  responsibility_detail?: string | null;
}

export interface WorkflowWorkspaceGraphEdge {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;
  edge_kind: "linear" | "branch" | "loopback";
  label: string | null;
}

export interface WorkflowWorkspaceFreshness {
  status: "fresh" | "stale" | "unknown";
  as_of: string | null;
  note: string | null;
}

export interface WorkflowWorkspaceRequiredUpload {
  dataset_key: string;
  template_id: string | null;
  artifact_kind: string;
  required_count: number;
  current_count: number;
  status: string;
}

export interface WorkflowWorkspaceRequiredReview {
  dataset_key: string;
  artifact_kind: string;
  required_count: number;
  reviewed_artifact_version_id: string | null;
  review_confirmation_artifact_version_id: string | null;
  status: string;
}

interface WorkflowWorkspaceWorkItemBase {
  work_id: string;
  graph_node_id: string | null;
  available_actions: string[];
  missing_required_inputs: string[];
  required_uploads: WorkflowWorkspaceRequiredUpload[];
  required_reviews: WorkflowWorkspaceRequiredReview[];
  blocking_reason_codes: string[];
  blocking_reason: string | null;
}

export interface WorkflowWorkspaceTaskWorkItem extends WorkflowWorkspaceWorkItemBase {
  item_kind: "human_task";
  human_task: HumanTaskRow;
}

export interface WorkflowWorkspaceApprovalWorkItem extends WorkflowWorkspaceWorkItemBase {
  item_kind: "approval";
  approval: ApprovalRow;
}

export interface WorkflowWorkspaceFlagWorkItem extends WorkflowWorkspaceWorkItemBase {
  item_kind: "flag";
  flag: FlagRow;
}

export type WorkflowWorkspaceWorkItem =
  | WorkflowWorkspaceTaskWorkItem
  | WorkflowWorkspaceApprovalWorkItem
  | WorkflowWorkspaceFlagWorkItem;

export interface WorkflowRunWorkspaceContract {
  workflow_run: WorkflowRunRow;
  graph: {
    nodes: WorkflowWorkspaceGraphNode[];
    edges: WorkflowWorkspaceGraphEdge[];
  };
  user_work: WorkflowWorkspaceWorkItem[];
  blocking_work: WorkflowWorkspaceWorkItem[];
  latest_event_sequence: number | null;
  freshness: WorkflowWorkspaceFreshness;
}

export type LogisticsStoryFamilyNodeKind = "module";
export type LogisticsStoryModuleDrilldownKind = "none" | "workflow_run" | "run_group";

export interface LogisticsStoryModuleDrilldownRef {
  workflow_run_id: string;
  workflow_id: string;
  partition_key: string;
}

export interface LogisticsStoryModuleArtifactRef {
  artifact_version_id: string;
  label: string;
  source_label: string;
}

export interface LogisticsStoryFamilyModule {
  module_id: string;
  workflow_id: string;
  partition_kind: string;
  activation_policy: string;
  status: string;
  node_kind: LogisticsStoryFamilyNodeKind;
  drilldown_kind: LogisticsStoryModuleDrilldownKind;
  drilldown_refs: LogisticsStoryModuleDrilldownRef[];
  artifact_refs: LogisticsStoryModuleArtifactRef[];
  selection_summary: string;
}

export interface LogisticsStoryFamilyEdge {
  edge_id: string;
  source_module_id: string;
  target_module_id: string;
  source_stage_id: string;
  source_dataset_key: string;
  target_stage_id: string;
  target_dataset_key: string;
  partition_transform_id: string;
  handoff_mode: string;
  writer_mode: string;
  status: string;
}

export interface LogisticsStoryFamilyGraph {
  family_id: string;
  family_version: number;
  modules: LogisticsStoryFamilyModule[];
  edges: LogisticsStoryFamilyEdge[];
}

export interface LogisticsStoryLinkedWorkflowRuns {
  weekly_schedule_planning: WorkflowRunRow[];
  live_dispatch: WorkflowRunRow[];
  dispatch_reporting: WorkflowRunRow[];
  summary: {
    weekly_schedule_planning_count: number;
    live_dispatch_count: number;
    dispatch_reporting_count: number;
  };
}

export interface LogisticsStoryHandoffExecution {
  edge_execution_id: string;
  edge_id: string;
  source_workflow_run_id: string;
  source_stage_id: string;
  source_artifact_version_id: string | null;
  target_workflow_id: string;
  target_workflow_run_id: string | null;
  target_stage_id: string;
  target_partition_key: string;
  status: string;
  created_at: string;
  updated_at: string;
  activated_at: string | null;
  source_workflow_run: WorkflowRunRow | null;
  target_workflow_run: WorkflowRunRow | null;
  coherence: Record<string, unknown>;
}

export interface LogisticsStoryHandoffEdgeSummary {
  edge_id: string;
  execution_count: number;
  status_counts: Record<string, number>;
  coherence_failed_count: number;
  executions: LogisticsStoryHandoffExecution[];
}

export interface LogisticsStoryBoardLane {
  lane: string;
  label: string;
  position: number;
  item_count: number;
}

export interface LogisticsStoryBoardWorkItem {
  item_id: string;
  item_type: "human_task" | "approval" | "flag";
  lane: string;
  title: string;
  workflow_run_id: string;
  workflow_id: string;
  subject_id: string;
  stage_id?: string;
  task_kind?: string;
  state: string;
  owner_role?: string | null;
  approval_kind?: string;
  scope_kind?: string;
  scope_ref?: string;
  required_role?: string | null;
  kind?: string;
  severity?: string;
  available_actions: string[];
  blocking_reason_codes: string[];
  missing_required_inputs: string[];
  linked_artifact_count: number;
}

export interface LogisticsStoryBoard {
  lanes: LogisticsStoryBoardLane[];
  work_items: LogisticsStoryBoardWorkItem[];
  page: {
    limit: number;
    offset: number;
  };
  summary: {
    work_item_count: number;
    human_task_count: number;
    approval_count: number;
    flag_count: number;
    primary_actionable_count: number;
    workflow_item_counts: Record<string, number>;
  };
}

export interface LogisticsStoryOfficialOutputs {
  pointers: PointerRow[];
  pointer_outputs: Array<{
    pointer: PointerRow;
    artifact_version: ArtifactVersionRow | null;
  }>;
  official_output_artifacts: ArtifactVersionRow[];
  coherence: Record<string, unknown>;
  summary: {
    pointer_count: number;
    pointer_output_count: number;
    official_output_artifact_count: number;
    artifact_kind_counts: Record<string, number>;
  };
}

export interface LogisticsThreeWorkflowStoryContract {
  story_id: string;
  family: {
    family_id: string;
    family_version: number;
    contract_version: number;
  };
  partitions: {
    planning_week_id: string;
    service_date_ids: string[];
  };
  family_graph: LogisticsStoryFamilyGraph;
  linked_workflow_runs: LogisticsStoryLinkedWorkflowRuns;
  handoff_activity: {
    edges: LogisticsStoryHandoffEdgeSummary[];
    summary: {
      edge_execution_count: number;
      coherence_failed_count: number;
    };
  };
  board: LogisticsStoryBoard;
  official_outputs: LogisticsStoryOfficialOutputs;
  freshness: {
    latest_event_sequence: number | null;
    latest_event_recorded_at: string | null;
    max_workflow_run_updated_at: string | null;
    generated_at: string;
  };
  coherence: {
    official_outputs: Record<string, unknown>;
    handoff_edges: Array<{
      edge_id: string;
      coherence_failed_count: number;
    }>;
  };
}

export interface TemplateRegistryMetadata {
  id: string;
  workflow_id: string;
  version: number;
}

export interface TemplateRecord {
  template_id: string;
  workflow_id: string;
  stage_id: string;
  dataset_key: string;
  artifact_kind: string;
  variant: string;
  media_type: string;
  file_path: string;
  file_name: string;
  description: string;
}

interface Envelope<T> {
  status: "ok";
  command: string;
  page?: { limit: number; offset: number };
  board?: BoardContract;
  human_tasks?: HumanTaskRow[];
  approvals?: ApprovalRow[];
  pointers?: PointerRow[];
  workflow_runs?: WorkflowRunRow[];
  events?: TimelineEvent[];
  flags?: FlagRow[];
  artifact_versions?: ArtifactVersionRow[];
  workflow_run?: WorkflowRunDetailContract;
  payload?: T;
}

export interface ContractSnapshot {
  snapshot_version: string;
  source: {
    scenario_file: string;
    workflow_run_id: string;
    workflow_id: string;
  };
  contracts: {
    board: Envelope<BoardContract> & { board: BoardContract };
    human_tasks: Envelope<HumanTaskRow[]> & { human_tasks: HumanTaskRow[] };
    approvals: Envelope<ApprovalRow[]> & { approvals: ApprovalRow[] };
    pointers: Envelope<PointerRow[]> & { pointers: PointerRow[] };
    workflow_runs: Envelope<WorkflowRunRow[]> & { workflow_runs: WorkflowRunRow[] };
    timeline_events: Envelope<TimelineEvent[]> & { events: TimelineEvent[] };
    flags: Envelope<FlagRow[]> & { flags: FlagRow[] };
    artifact_versions: Envelope<ArtifactVersionRow[]> & { artifact_versions: ArtifactVersionRow[] };
    workflow_run_detail: {
      status: "ok";
      command: string;
      workflow_run: WorkflowRunRow;
      human_tasks: HumanTaskRow[];
      approvals: ApprovalRow[];
      artifact_versions: ArtifactVersionRow[];
      pointers: PointerRow[];
      flags: FlagRow[];
      summary: WorkflowRunDetailContract["summary"];
    };
  };
}
