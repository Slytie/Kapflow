import type {
  LogisticsStoryBoardWorkItem,
  LogisticsStoryFamilyModule,
  LogisticsStoryModuleArtifactRef,
  LogisticsStoryModuleDrilldownRef,
  LogisticsThreeWorkflowStoryContract,
  WorkflowRunRow,
  WorkflowWorkspaceFreshness,
  WorkflowWorkspaceGraphEdge,
  WorkflowWorkspaceGraphNode
} from "@/lib/types/contracts";
import type { DrawerPayload } from "@/lib/types/ui";
import { taskDisplayHeading, taskDisplayLabel } from "@/lib/workspace/taskLabels";

export const DEFAULT_LOGISTICS_PLANNING_WEEK_ID = "PW-2026-W10";

export const LOGISTICS_MODULE_LAYOUT: Record<
  string,
  { row: number; column: number; label: string }
> = {
  dispatch_reporting: {
    row: 0,
    column: 0,
    label: "Dispatch Reporting"
  },
  weekly_schedule_planning: {
    row: 0,
    column: 1,
    label: "Weekly Schedule Planning"
  },
  live_dispatch: {
    row: 0,
    column: 2,
    label: "Live Dispatch"
  }
};

export interface EditorialBoardLane {
  id: "todo" | "in_progress" | "waiting_review";
  title: string;
  items: LogisticsStoryBoardWorkItem[];
}

export interface LogisticsTaskStripCardModel {
  lane_id: EditorialBoardLane["id"];
  title: string;
  count: number;
  top_item: LogisticsStoryBoardWorkItem | null;
  extra_count: number;
}

export function normalizeStatus(input: string): string {
  return input.trim().toLowerCase();
}

export function graphStatusForModule(
  moduleStatus: string,
  runStates: string[]
): WorkflowWorkspaceGraphNode["status"] {
  const normalizedRunStates = runStates.map(normalizeStatus);
  if (
    normalizedRunStates.some((state) =>
      new Set(["open", "ready", "in_progress", "claimed", "pending", "triage", "blocked"]).has(
        state
      )
    )
  ) {
    return "in_progress";
  }
  if (normalizedRunStates.length > 0) {
    return "completed";
  }

  const normalizedModuleStatus = normalizeStatus(moduleStatus);
  if (["blocked", "error", "failed", "warning"].includes(normalizedModuleStatus)) {
    return "warning";
  }
  if (["active", "ready", "enabled"].includes(normalizedModuleStatus)) {
    return "ready";
  }
  return "not_started";
}

export function moduleDisplayLabel(module: LogisticsStoryFamilyModule | string): string {
  const moduleId = typeof module === "string" ? module : module.module_id;
  return LOGISTICS_MODULE_LAYOUT[moduleId]?.label ?? moduleId;
}

export function workflowIdToModuleId(workflowId: string): string | null {
  if (workflowId === "weekly_schedule_planning.v1") {
    return "weekly_schedule_planning";
  }
  if (workflowId === "dispatch_reporting.v1") {
    return "dispatch_reporting";
  }
  if (workflowId === "live_dispatch.v1") {
    return "live_dispatch";
  }
  return null;
}

export function runRowsForStory(story: LogisticsThreeWorkflowStoryContract): WorkflowRunRow[] {
  return [
    ...story.linked_workflow_runs.dispatch_reporting,
    ...story.linked_workflow_runs.weekly_schedule_planning,
    ...story.linked_workflow_runs.live_dispatch
  ];
}

export function moduleRunRefs(
  module: LogisticsStoryFamilyModule
): LogisticsStoryModuleDrilldownRef[] {
  const deduped = new Map<string, LogisticsStoryModuleDrilldownRef>();
  for (const ref of module.drilldown_refs) {
    if (!deduped.has(ref.workflow_run_id)) {
      deduped.set(ref.workflow_run_id, ref);
    }
  }
  return Array.from(deduped.values());
}

export function logisticsFamilyGraphNodes(
  story: LogisticsThreeWorkflowStoryContract
): WorkflowWorkspaceGraphNode[] {
  const storyRuns = runRowsForStory(story);
  const runById = new Map(storyRuns.map((run) => [run.workflow_run_id, run]));
  return story.family_graph.modules.map((module, index) => {
    const moduleLayout = LOGISTICS_MODULE_LAYOUT[module.module_id] ?? {
      row: 0,
      column: index,
      label: module.module_id
    };
    const refs = moduleRunRefs(module);
    const refRunStates = refs
      .map((ref) => runById.get(ref.workflow_run_id)?.state ?? "")
      .filter((state) => state.length > 0);
    const workflowRunStates =
      refRunStates.length > 0
        ? refRunStates
        : storyRuns
            .filter((run) => run.workflow_id === module.workflow_id)
            .map((run) => run.state);
    const runCount = refs.length > 0 ? refs.length : workflowRunStates.length;

    return {
      node_id: module.module_id,
      stage_id: module.workflow_id,
      label: moduleLayout.label,
      status: graphStatusForModule(module.status, workflowRunStates),
      row: moduleLayout.row,
      column: moduleLayout.column,
      is_blocking: false,
      responsibility_summary:
        runCount > 0
          ? `${runCount} linked run${runCount === 1 ? "" : "s"}`
          : "No linked runs",
      responsibility_detail: module.selection_summary || module.activation_policy
    };
  });
}

export function logisticsFamilyGraphEdges(
  story: LogisticsThreeWorkflowStoryContract
): WorkflowWorkspaceGraphEdge[] {
  return story.family_graph.edges.map((edge) => ({
    edge_id: edge.edge_id,
    from_node_id: edge.source_module_id,
    to_node_id: edge.target_module_id,
    edge_kind: edge.handoff_mode === "notify_only" ? "branch" : "linear",
    label: edge.handoff_mode
  }));
}

export function storyFreshness(
  story: LogisticsThreeWorkflowStoryContract
): WorkflowWorkspaceFreshness {
  return {
    status: story.freshness.latest_event_recorded_at ? "fresh" : "unknown",
    as_of: story.freshness.latest_event_recorded_at ?? story.freshness.generated_at,
    note: `story generated at ${story.freshness.generated_at}`
  };
}

export function stateBadgeClass(state: string): string {
  const normalized = normalizeStatus(state);
  if (["completed", "responded", "closed", "resolved"].includes(normalized)) {
    return "status-badge status-badge--success";
  }
  if (
    ["open", "claimed", "pending", "triage", "blocked", "ready", "in_progress"].includes(
      normalized
    )
  ) {
    return "status-badge status-badge--active";
  }
  return "status-badge status-badge--default";
}

export function boardItemMeta(item: LogisticsStoryBoardWorkItem): string {
  if (item.item_type === "human_task") {
    return item.stage_id ?? "stage";
  }
  if (item.item_type === "approval") {
    return `${item.approval_kind ?? "approval"} · ${item.scope_ref ?? "scope"}`;
  }
  return `${item.kind ?? "flag"} · ${item.severity ?? "severity"}`;
}

export function boardItemActions(item: LogisticsStoryBoardWorkItem): string {
  if (item.available_actions.length === 0) {
    return "none";
  }
  return item.available_actions.join(", ");
}

function isResolvedBoardState(state: string): boolean {
  return ["completed", "responded", "closed", "resolved"].includes(normalizeStatus(state));
}

function isWaitingReviewItem(item: LogisticsStoryBoardWorkItem): boolean {
  if (item.item_type === "approval") {
    return true;
  }
  const taskKind = item.task_kind?.toLowerCase() ?? "";
  if (taskKind.includes("review")) {
    return true;
  }
  return item.available_actions.some(
    (action) => action.toLowerCase() === "confirm_review"
  );
}

function boardItemTaskLabel(item: LogisticsStoryBoardWorkItem): string {
  if (!item.stage_id || !item.task_kind) {
    return item.title;
  }
  return taskDisplayLabel({
    stage_id: item.stage_id,
    task_kind: item.task_kind
  });
}

function boardItemTaskHeading(item: LogisticsStoryBoardWorkItem): string {
  if (!item.stage_id || !item.task_kind) {
    return item.title;
  }
  return taskDisplayHeading({
    stage_id: item.stage_id,
    task_kind: item.task_kind
  });
}

function presentBoardItem(item: LogisticsStoryBoardWorkItem): LogisticsStoryBoardWorkItem {
  if (item.item_type !== "human_task") {
    return item;
  }
  return {
    ...item,
    title: boardItemTaskLabel(item)
  };
}

export function editorialBoard(story: LogisticsThreeWorkflowStoryContract): {
  lanes: EditorialBoardLane[];
  flags: LogisticsStoryBoardWorkItem[];
} {
  const activeItems = story.board.work_items
    .filter((item) => !isResolvedBoardState(item.state))
    .map(presentBoardItem);
  const lanes: EditorialBoardLane[] = [
    { id: "todo", title: "To Do", items: [] },
    { id: "in_progress", title: "In Progress", items: [] },
    { id: "waiting_review", title: "Waiting Review", items: [] }
  ];
  const flags = activeItems.filter((item) => item.item_type === "flag");

  for (const item of activeItems) {
    if (item.item_type === "flag") {
      continue;
    }
    if (isWaitingReviewItem(item)) {
      lanes[2].items.push(item);
      continue;
    }
    if (["claimed", "in_progress"].includes(normalizeStatus(item.state))) {
      lanes[1].items.push(item);
      continue;
    }
    lanes[0].items.push(item);
  }

  return { lanes, flags };
}

export function logisticsTaskStripCards(
  story: LogisticsThreeWorkflowStoryContract
): LogisticsTaskStripCardModel[] {
  return editorialBoard(story).lanes.map((lane) => ({
    lane_id: lane.id,
    title: lane.title,
    count: lane.items.length,
    top_item: lane.items[0] ?? null,
    extra_count: Math.max(0, lane.items.length - 1)
  }));
}

export function boardItemSupportText(item: LogisticsStoryBoardWorkItem): string | null {
  if (item.item_type === "human_task" && item.missing_required_inputs.length > 0) {
    return `Missing inputs: ${item.missing_required_inputs.join(", ")}`;
  }
  if (item.item_type === "flag") {
    return `${item.kind ?? "flag"} · ${item.severity ?? "severity"}`;
  }
  if (item.linked_artifact_count > 0) {
    return `${item.linked_artifact_count} linked artifact${
      item.linked_artifact_count === 1 ? "" : "s"
    }`;
  }
  return null;
}

export function artifactLabel(
  artifactRef: LogisticsStoryModuleArtifactRef
): string {
  return artifactRef.label.trim().length > 0
    ? artifactRef.label
    : artifactRef.artifact_version_id;
}

export function runRefSummary(
  ref: LogisticsStoryModuleDrilldownRef,
  run: WorkflowRunRow | null
): string {
  if (run) {
    return `${run.workflow_run_id} · ${run.state} · ${run.partition_key}`;
  }
  return `${ref.workflow_run_id} · ${ref.partition_key}`;
}

export function buildBoardItemDrawerPayload(
  item: LogisticsStoryBoardWorkItem
): DrawerPayload {
  if (item.item_type === "human_task") {
    return {
      title: boardItemTaskHeading(item),
      subtitle: item.subject_id,
      description:
        "Inspect context and run authoritative task actions from the centered task modal without leaving the logistics shell.",
      fields: [
        { label: "Workflow", value: item.workflow_id },
        { label: "Workflow run", value: item.workflow_run_id },
        { label: "State", value: item.state },
        { label: "Board lane", value: item.lane },
        { label: "Actions", value: boardItemActions(item) }
      ],
      links: [
        { label: "Open Workspace", to: `/runs/${item.workflow_run_id}/workspace` },
        { label: "Open run detail (secondary)", to: `/runs/${item.workflow_run_id}` }
      ],
      task: {
        human_task_id: item.subject_id,
        workflow_run_id: item.workflow_run_id,
        task_run_id: "loading",
        stage_id: item.stage_id ?? "unknown",
        task_kind: item.task_kind ?? "unknown",
        state: item.state,
        assignee_actor_id: null,
        assignee_actor_type: null,
        owner_role: item.owner_role ?? null,
        linked_approval_id: null,
        blocked_on_kind: null,
        blocked_on_ref: null,
        available_actions: item.available_actions,
        blocking_reason_codes: item.blocking_reason_codes,
        missing_required_inputs: item.missing_required_inputs
      },
      artifact_sources: [
        {
          workflow_run_id: item.workflow_run_id,
          subject_kind: "human_task",
          subject_id: item.subject_id,
          source_label: "Task attachment"
        }
      ]
    };
  }

  if (item.item_type === "approval") {
    return {
      title: item.title,
      subtitle: item.subject_id,
      description:
        "Approval context and response evidence remain in the shared detail drawer.",
      fields: [
        { label: "Workflow", value: item.workflow_id },
        { label: "Workflow run", value: item.workflow_run_id },
        { label: "State", value: item.state },
        { label: "Approval kind", value: item.approval_kind ?? "approval" },
        { label: "Scope", value: item.scope_ref ?? item.scope_kind ?? "unknown" },
        { label: "Required role", value: item.required_role ?? "unknown" }
      ]
    };
  }

  return {
    title: item.title,
    subtitle: item.subject_id,
    description:
      "Exceptions stay in the contextual rail, but the full runtime context still opens in the shared drawer.",
    fields: [
      { label: "Workflow", value: item.workflow_id },
      { label: "Workflow run", value: item.workflow_run_id },
      { label: "State", value: item.state },
      { label: "Kind", value: item.kind ?? "flag" },
      { label: "Severity", value: item.severity ?? "unknown" }
    ]
  };
}
