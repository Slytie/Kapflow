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
