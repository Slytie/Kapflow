import type {
  ApprovalRow,
  FlagRow,
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

export interface DrawerPayload {
  title: string;
  subtitle?: string;
  description?: string;
  fields: DrawerField[];
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
