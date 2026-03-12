import type {
  ApprovalRow,
  FlagRow,
  HumanTaskExpansionKind,
  HumanTaskSubgraphRef,
  HumanTaskRow,
  PointerRow,
  TimelineEvent,
  WorkflowRunDetailContract,
  WorkflowRunRow
} from "@/lib/types/contracts";

export type ShellFilterKey = "workflowRunId" | "state" | "assignee" | "severity" | "query";

export interface ShellFilters {
  workflowRunId: string;
  state: string;
  assignee: string;
  severity: string;
  query: string;
}

export interface DrawerField {
  label: string;
  value: string;
}

export interface DrawerArtifact {
  artifact_version_id: string;
  artifact_kind: string;
  artifact_role: string | null;
  media_type: string;
  created_at: string;
  file_name: string | null;
  source_label: string;
}

export interface DrawerArtifactSource {
  workflow_run_id: string;
  subject_kind: "workflow_run" | "task_run" | "human_task" | "approval" | "flag";
  subject_id: string;
  source_label: string;
}

export interface DrawerTaskContext {
  human_task_id: string;
  workflow_run_id: string;
  task_run_id: string;
  stage_id: string;
  task_kind: string;
  state: string;
  assignee_actor_id: string | null;
  assignee_actor_type: string | null;
  owner_role: string | null;
  candidate_roles?: string[];
  linked_approval_id?: string | null;
  blocked_on_kind?: string | null;
  blocked_on_ref?: string | null;
  available_actions: string[];
  blocking_reason_codes: string[];
  missing_required_inputs: string[];
  is_composite?: boolean;
  expansion_kind?: HumanTaskExpansionKind;
  subgraph_ref?: HumanTaskSubgraphRef | null;
}

export interface DrawerLink {
  label: string;
  to: string;
}

export interface DrawerPayload {
  title: string;
  subtitle?: string;
  description?: string;
  fields: DrawerField[];
  links?: DrawerLink[];
  artifacts?: DrawerArtifact[];
  artifact_sources?: DrawerArtifactSource[];
  task?: DrawerTaskContext;
}

export type BoardLaneId =
  | "unclaimed"
  | "claimed"
  | "awaiting_approval"
  | "needs_information"
  | "exception_work";

export interface BoardLaneView {
  id: BoardLaneId;
  title: string;
  items: BoardItem[];
}

export type BoardItem =
  | { kind: "task"; task: HumanTaskRow }
  | { kind: "approval"; approval: ApprovalRow }
  | { kind: "flag"; flag: FlagRow };

export interface BoardViewModel {
  lanes: BoardLaneView[];
  workflowRuns: WorkflowRunRow[];
}

export interface TimelineRowModel {
  eventId: string;
  sequenceNo: number;
  eventType: string;
  occurredAt: string;
  actorId: string;
  subject: string;
  details: string;
  raw: TimelineEvent;
}

export interface WorkflowRunDetailView {
  detail: WorkflowRunDetailContract;
  timeline: TimelineRowModel[];
}

export interface PointerViewModel {
  pointer: PointerRow;
  workflowRun?: WorkflowRunRow;
}
