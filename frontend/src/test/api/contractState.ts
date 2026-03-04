import type {
  ApprovalRow,
  ArtifactVersionRow,
  BoardCard,
  BoardContract,
  FlagRow,
  HumanTaskRow,
  PointerRow,
  TimelineEvent,
  WorkflowRunDetailContract,
  WorkflowRunWorkspaceContract,
  WorkflowWorkspaceWorkItem,
  WorkflowRunRow
} from "@/lib/types/contracts";

const WORKFLOW_RUN_ID = "wr-test-001";

export interface ContractState {
  tenantId: string;
  domainId: string;
  workflowRuns: WorkflowRunRow[];
  humanTasks: HumanTaskRow[];
  approvals: ApprovalRow[];
  flags: FlagRow[];
  pointers: PointerRow[];
  artifactVersions: ArtifactVersionRow[];
  timelineEvents: TimelineEvent[];
  audit: {
    mutations: string[];
  };
  uploadedTaskAttachmentIds: Set<string>;
  uploadedApprovalAttachmentIds: Set<string>;
  uploadedFlagAttachmentIds: Set<string>;
  stage06ReviewedTaskIds: Set<string>;
  forceForbidden: boolean;
}

function nowIso(offsetSeconds = 0): string {
  const date = new Date(Date.now() + offsetSeconds * 1000);
  return date.toISOString();
}

function boardLaneForTask(task: HumanTaskRow): string {
  if (task.state === "OPEN") {
    return "human_tasks.open";
  }
  if (task.state === "CLAIMED") {
    return "human_tasks.claimed";
  }
  return "human_tasks.completed";
}

function boardLaneForApproval(approval: ApprovalRow): string {
  return approval.state === "PENDING" ? "approvals.pending" : "approvals.responded";
}

function toBoardTaskCard(task: HumanTaskRow, workflowId: string): BoardCard {
  const relatedApprovals = [] as ApprovalRow[];
  return {
    card_id: `human_task:${task.human_task_id}`,
    card_type: "human_task",
    lane: boardLaneForTask(task),
    title: `${task.stage_id} ${task.task_kind}`,
    workflow_run_id: task.workflow_run_id,
    workflow_id: workflowId,
    task_run_id: task.task_run_id,
    human_task_id: task.human_task_id,
    stage_id: task.stage_id,
    task_kind: task.task_kind,
    state: task.state,
    owner_role: task.owner_role ?? undefined,
    assignee_actor_id: task.assignee_actor_id,
    assignee_actor_type: task.assignee_actor_type,
    due_at: task.due_at,
    claimed_at: task.claimed_at,
    claimed_until: task.claimed_until,
    blocked_on_kind: task.blocked_on_kind,
    blocked_on_ref: task.blocked_on_ref,
    spawned_from_flag_id: task.spawned_from_flag_id,
    linked_approval_count: relatedApprovals.length,
    linked_approval_states: relatedApprovals.map((approval) => approval.state)
  };
}

function toBoardApprovalCard(approval: ApprovalRow, workflowId: string): BoardCard {
  return {
    card_id: `approval:${approval.approval_id}`,
    card_type: "approval",
    lane: boardLaneForApproval(approval),
    title: `${approval.approval_kind} ${approval.scope_ref}`,
    workflow_run_id: approval.workflow_run_id,
    workflow_id: workflowId,
    approval_id: approval.approval_id,
    task_run_id: approval.task_run_id,
    approval_kind: approval.approval_kind,
    scope_kind: approval.scope_kind,
    scope_ref: approval.scope_ref,
    state: approval.state,
    required_role: approval.required_role,
    candidate_roles: approval.candidate_roles,
    requested_at: approval.requested_at,
    responded_at: approval.responded_at,
    response_kind: approval.response_kind
  };
}

export function buildBoardContract(state: ContractState): BoardContract {
  const workflowId = state.workflowRuns[0]?.workflow_id ?? "schedule_planning.v1";
  const cards = [
    ...state.humanTasks.map((task) => toBoardTaskCard(task, workflowId)),
    ...state.approvals.map((approval) => toBoardApprovalCard(approval, workflowId))
  ];

  const laneOrder = [
    "human_tasks.open",
    "human_tasks.claimed",
    "approvals.pending",
    "approvals.responded",
    "human_tasks.completed"
  ];

  const laneLabels: Record<string, string> = {
    "human_tasks.open": "Open Tasks",
    "human_tasks.claimed": "Claimed Tasks",
    "approvals.pending": "Pending Approvals",
    "approvals.responded": "Responded Approvals",
    "human_tasks.completed": "Completed Tasks"
  };

  const lanes = laneOrder.map((lane, index) => ({
    lane,
    label: laneLabels[lane],
    position: (index + 1) * 10,
    card_count: cards.filter((card) => card.lane === lane).length
  }));

  return {
    board_id: "schedule-planning",
    filters: {
      workflow_id: "schedule_planning.v1",
      workflow_run_id: WORKFLOW_RUN_ID,
      stage_id: null,
      task_kind: null,
      task_state: null,
      approval_state: null
    },
    lanes,
    cards,
    page: { limit: 100, offset: 0 },
    workflow_runs: state.workflowRuns,
    pointers: state.pointers,
    summary: {
      workflow_run_count: state.workflowRuns.length,
      human_task_count: state.humanTasks.length,
      approval_count: state.approvals.length,
      pointer_count: state.pointers.length,
      card_count: cards.length
    }
  };
}

export function buildWorkflowRunDetail(state: ContractState, workflowRunId: string): WorkflowRunDetailContract {
  const workflowRun = state.workflowRuns.find((row) => row.workflow_run_id === workflowRunId);
  if (!workflowRun) {
    throw new Error(`workflow run not found: ${workflowRunId}`);
  }

  const humanTasks = state.humanTasks.filter((row) => row.workflow_run_id === workflowRunId);
  const approvals = state.approvals.filter((row) => row.workflow_run_id === workflowRunId);
  const pointers = state.pointers.filter((row) => row.workflow_run_id === workflowRunId);
  const flags = state.flags.filter((row) => row.workflow_run_id === workflowRunId);
  const artifactVersions = state.artifactVersions.filter((row) => row.workflow_run_id === workflowRunId);

  return {
    workflow_run: workflowRun,
    human_tasks: humanTasks,
    approvals,
    artifact_versions: artifactVersions,
    pointers,
    flags,
    summary: {
      human_task_count: humanTasks.length,
      approval_count: approvals.length,
      artifact_version_count: artifactVersions.length,
      pointer_count: pointers.length,
      flag_count: flags.length,
      active_issue_count: workflowRun.active_issue_count
    }
  };
}

function buildWorkspaceTaskItem(
  task: HumanTaskRow,
  options: {
    graphNodeId: string;
    availableActions: string[];
    missingRequiredInputs?: string[];
    blockingReason?: string | null;
  }
): WorkflowWorkspaceWorkItem {
  return {
    work_id: `human_task:${task.human_task_id}`,
    item_kind: "human_task",
    human_task: task,
    graph_node_id: options.graphNodeId,
    available_actions: options.availableActions,
    missing_required_inputs: options.missingRequiredInputs ?? [],
    blocking_reason: options.blockingReason ?? null
  };
}

function buildWorkspaceApprovalItem(
  approval: ApprovalRow,
  options: {
    graphNodeId: string;
    blockingReason?: string | null;
  }
): WorkflowWorkspaceWorkItem {
  return {
    work_id: `approval:${approval.approval_id}`,
    item_kind: "approval",
    approval,
    graph_node_id: options.graphNodeId,
    available_actions:
      approval.state === "PENDING"
        ? [
            "respond_approval",
            "respond_approve",
            "respond_reject",
            "respond_request_changes",
            "upload_attachment",
            "download_attachment"
          ]
        : ["download_attachment"],
    missing_required_inputs: [],
    blocking_reason: options.blockingReason ?? null
  };
}

function buildWorkspaceFlagItem(flag: FlagRow): WorkflowWorkspaceWorkItem {
  return {
    work_id: `flag:${flag.flag_id}`,
    item_kind: "flag",
    flag,
    graph_node_id: "stage07",
    available_actions: ["upload_attachment", "download_attachment"],
    missing_required_inputs: [],
    blocking_reason: null
  };
}

export function buildWorkflowRunWorkspace(
  state: ContractState,
  workflowRunId: string
): WorkflowRunWorkspaceContract {
  const workflowRun = state.workflowRuns.find((row) => row.workflow_run_id === workflowRunId);
  if (!workflowRun) {
    throw new Error(`workflow run not found: ${workflowRunId}`);
  }

  const reviewTask = state.humanTasks.find((task) => task.human_task_id === "ht-claimed-002");
  const infoTask = state.humanTasks.find((task) => task.human_task_id === "ht-open-001");
  const pendingApproval = state.approvals.find(
    (approval) => approval.approval_id === "ap-pending-001" && approval.state === "PENDING"
  );
  const activeFlag = state.flags.find((flag) => flag.flag_id === "flag-001");

  const reviewMissingInputs =
    reviewTask && !state.uploadedTaskAttachmentIds.has(reviewTask.human_task_id)
      ? ["Upload review evidence attachment"]
      : [];

  const reviewStatus =
    reviewTask?.state === "COMPLETED"
      ? "completed"
      : reviewTask?.state === "CLAIMED"
        ? "in_progress"
        : "ready";

  const infoStatus =
    infoTask?.state === "COMPLETED"
      ? "completed"
      : infoTask?.state === "CLAIMED"
        ? "in_progress"
        : "blocked";

  const stage07Status = pendingApproval ? "awaiting_approval" : activeFlag ? "warning" : "ready";

  const graphNodes: WorkflowRunWorkspaceContract["graph"]["nodes"] = [
    {
      node_id: "stage03",
      stage_id: "Stage03",
      label: "Demand Forecast",
      status: "completed",
      row: 0,
      column: 0,
      is_blocking: false
    },
    {
      node_id: "stage04",
      stage_id: "Stage04",
      label: "Capacity Plan",
      status: "completed",
      row: 0,
      column: 1,
      is_blocking: false
    },
    {
      node_id: "stage05",
      stage_id: "Stage05",
      label: "Draft Schedule",
      status: "completed",
      row: 0,
      column: 2,
      is_blocking: false
    },
    {
      node_id: "stage06",
      stage_id: "Stage06",
      label: "Supervisor Review",
      status: reviewStatus,
      row: 0,
      column: 3,
      is_blocking: reviewMissingInputs.length > 0
    },
    {
      node_id: "stage06_info_loop",
      stage_id: "Stage06",
      label: "Information Request Loop",
      status: infoStatus,
      row: 1,
      column: 3,
      is_blocking: infoStatus === "blocked"
    },
    {
      node_id: "stage07",
      stage_id: "Stage07",
      label: "Exception Control",
      status: stage07Status,
      row: 0,
      column: 4,
      is_blocking: Boolean(pendingApproval)
    }
  ];

  const graphEdges: WorkflowRunWorkspaceContract["graph"]["edges"] = [
    {
      edge_id: "e-stage03-stage04",
      from_node_id: "stage03",
      to_node_id: "stage04",
      edge_kind: "linear",
      label: null
    },
    {
      edge_id: "e-stage04-stage05",
      from_node_id: "stage04",
      to_node_id: "stage05",
      edge_kind: "linear",
      label: null
    },
    {
      edge_id: "e-stage05-stage06",
      from_node_id: "stage05",
      to_node_id: "stage06",
      edge_kind: "linear",
      label: null
    },
    {
      edge_id: "e-stage06-branch-info",
      from_node_id: "stage06",
      to_node_id: "stage06_info_loop",
      edge_kind: "branch",
      label: "needs information"
    },
    {
      edge_id: "e-stage06-info-loopback",
      from_node_id: "stage06_info_loop",
      to_node_id: "stage05",
      edge_kind: "loopback",
      label: "rework"
    },
    {
      edge_id: "e-stage06-stage07",
      from_node_id: "stage06",
      to_node_id: "stage07",
      edge_kind: "linear",
      label: null
    }
  ];

  const userWork: WorkflowWorkspaceWorkItem[] = [];
  if (reviewTask && reviewTask.state !== "COMPLETED") {
    userWork.push(
      buildWorkspaceTaskItem(reviewTask, {
        graphNodeId: "stage06",
        availableActions: [
          "complete",
          "upload_attachment",
          "download_attachment",
          "run_stage06_agent_review"
        ],
        missingRequiredInputs: reviewMissingInputs
      })
    );
  }
  if (pendingApproval) {
    userWork.push(
      buildWorkspaceApprovalItem(pendingApproval, {
        graphNodeId: "stage07",
        blockingReason: "Awaiting required approval response"
      })
    );
  }
  if (activeFlag) {
    userWork.push(buildWorkspaceFlagItem(activeFlag));
  }

  const blockingWork: WorkflowWorkspaceWorkItem[] = [];
  if (infoTask && infoTask.state !== "COMPLETED") {
    blockingWork.push(
      buildWorkspaceTaskItem(infoTask, {
        graphNodeId: "stage06_info_loop",
        availableActions: ["claim", "upload_attachment", "download_attachment"],
        missingRequiredInputs: ["Attach requestor clarification document"],
        blockingReason: "Information request must be completed before publish can continue"
      })
    );
  }
  if (pendingApproval) {
    blockingWork.push(
      buildWorkspaceApprovalItem(pendingApproval, {
        graphNodeId: "stage07",
        blockingReason: "Major replan remains blocked until approval response"
      })
    );
  }

  const latestEventSequence =
    state.timelineEvents.length > 0
      ? Math.max(...state.timelineEvents.map((event) => event.sequence_no))
      : null;

  return {
    workflow_run: workflowRun,
    graph: {
      nodes: graphNodes,
      edges: graphEdges
    },
    user_work: userWork,
    blocking_work: blockingWork,
    latest_event_sequence: latestEventSequence,
    freshness: {
      status: "fresh",
      as_of: nowIso(-6),
      note: "Polling-backed workspace projection"
    }
  };
}

export function createContractState(): ContractState {
  return {
    tenantId: "tenant-a",
    domainId: "domain-x",
    workflowRuns: [
      {
        workflow_run_id: WORKFLOW_RUN_ID,
        workflow_id: "schedule_planning.v1",
        workflow_version: "v1",
        tenant_id: "tenant-a",
        domain_id: "domain-x",
        partition_key: "SD-2026-03-07",
        logical_date: "2026-03-07",
        activation_key: "stage06_review_requires_more_information:workflow-run",
        state: "OPEN",
        active_issue_count: 1,
        created_at: nowIso(-600),
        updated_at: nowIso(-60)
      }
    ],
    humanTasks: [
      {
        human_task_id: "ht-open-001",
        workflow_run_id: WORKFLOW_RUN_ID,
        task_run_id: "tr-open-001",
        task_kind: "information_request",
        state: "OPEN",
        candidate_roles: ["dispatch_supervisor"],
        owner_role: "dispatch_supervisor",
        assignee_actor_id: null,
        assignee_actor_type: null,
        due_at: null,
        escalation_at: null,
        lease_version: 0,
        claimed_at: null,
        claimed_until: null,
        linked_approval_id: null,
        reopen_count: 0,
        generation: 0,
        created_at: nowIso(-500),
        updated_at: nowIso(-500),
        task_run_state: "READY",
        stage_id: "Stage06",
        blocked_on_kind: null,
        blocked_on_ref: null,
        spawned_from_flag_id: null
      },
      {
        human_task_id: "ht-claimed-002",
        workflow_run_id: WORKFLOW_RUN_ID,
        task_run_id: "tr-claimed-002",
        task_kind: "review_packet",
        state: "CLAIMED",
        candidate_roles: ["dispatch_supervisor"],
        owner_role: "dispatch_supervisor",
        assignee_actor_id: "human:dispatch-supervisor-1",
        assignee_actor_type: "human",
        due_at: null,
        escalation_at: null,
        lease_version: 1,
        claimed_at: nowIso(-400),
        claimed_until: null,
        linked_approval_id: null,
        reopen_count: 0,
        generation: 0,
        created_at: nowIso(-450),
        updated_at: nowIso(-400),
        task_run_state: "IN_PROGRESS",
        stage_id: "Stage06",
        blocked_on_kind: null,
        blocked_on_ref: null,
        spawned_from_flag_id: null
      },
      {
        human_task_id: "ht-exception-003",
        workflow_run_id: WORKFLOW_RUN_ID,
        task_run_id: "tr-exception-003",
        task_kind: "exception_triage",
        state: "COMPLETED",
        candidate_roles: ["operations_manager"],
        owner_role: "operations_manager",
        assignee_actor_id: "human:ops-manager-1",
        assignee_actor_type: "human",
        due_at: null,
        escalation_at: null,
        lease_version: 1,
        claimed_at: nowIso(-300),
        claimed_until: null,
        linked_approval_id: "ap-pending-001",
        reopen_count: 0,
        generation: 0,
        created_at: nowIso(-350),
        updated_at: nowIso(-280),
        task_run_state: "COMPLETED",
        stage_id: "Stage07",
        blocked_on_kind: null,
        blocked_on_ref: null,
        spawned_from_flag_id: "flag-001"
      }
    ],
    approvals: [
      {
        approval_id: "ap-pending-001",
        workflow_run_id: WORKFLOW_RUN_ID,
        task_run_id: "tr-exception-003",
        approval_kind: "business_decision",
        scope_kind: "stage",
        scope_ref: "Stage07",
        state: "PENDING",
        requested_by_task_run_id: "tr-exception-003",
        candidate_roles: ["operations_manager"],
        required_role: "operations_manager",
        requested_at: nowIso(-200),
        responded_at: null,
        response_kind: null,
        response_reason: null,
        decided_by_actor_id: null,
        decided_by_actor_type: null,
        generation: 0,
        created_at: nowIso(-200),
        updated_at: nowIso(-200)
      },
      {
        approval_id: "ap-responded-002",
        workflow_run_id: WORKFLOW_RUN_ID,
        task_run_id: "tr-claimed-002",
        approval_kind: "business_decision",
        scope_kind: "stage",
        scope_ref: "Stage06",
        state: "RESPONDED",
        requested_by_task_run_id: "tr-claimed-002",
        candidate_roles: ["dispatch_supervisor"],
        required_role: "dispatch_supervisor",
        requested_at: nowIso(-350),
        responded_at: nowIso(-320),
        response_kind: "approve",
        response_reason: "approved",
        decided_by_actor_id: "human:dispatch-supervisor-1",
        decided_by_actor_type: "human",
        generation: 1,
        created_at: nowIso(-350),
        updated_at: nowIso(-320)
      }
    ],
    flags: [
      {
        flag_id: "flag-001",
        workflow_run_id: WORKFLOW_RUN_ID,
        tenant_id: "tenant-a",
        domain_id: "domain-x",
        workflow_id: "schedule_planning.v1",
        partition_key: "SD-2026-03-07",
        kind: "no_show",
        severity: "high",
        state: "open",
        summary: "Courier C-104 did not report for shift",
        details_json: { reason_code: "no_show", zone_id: "berlin-east" },
        assigned_group: null,
        created_at: nowIso(-250),
        closed_at: null,
        created_by_actor_id: "human:dispatcher-1",
        created_by_actor_type: "human",
        source_event_id: null,
        dedupe_key: "scenario:no-show",
        updated_at: nowIso(-250)
      }
    ],
    pointers: [
      {
        workflow_run_id: WORKFLOW_RUN_ID,
        pointer_key: "official:schedule.published_schedule.workbook",
        scope_kind: "stage",
        scope_ref: "Stage06",
        artifact_kind: "schedule.published_schedule.workbook",
        artifact_version_id: "av-001",
        promotion_reason: "official_publish",
        promoted_by_task_run_id: "tr-claimed-002",
        approved_by_approval_id: "ap-responded-002",
        generation: 1,
        updated_at: nowIso(-100)
      }
    ],
    artifactVersions: [
      {
        artifact_version_id: "av-001",
        workflow_run_id: WORKFLOW_RUN_ID,
        task_run_id: null,
        artifact_kind: "schedule.published_schedule.workbook",
        artifact_role: "official_output",
        media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        storage_uri: "s3://artifacts/av-001.xlsx",
        content_digest: "sha256:abc123",
        byte_size: 1200,
        metadata_json: { source: "stage06" },
        parent_artifact_version_id: null,
        supersedes_artifact_version_id: null,
        lineage_note: null,
        created_at: nowIso(-120)
      },
      {
        artifact_version_id: "av-002",
        workflow_run_id: WORKFLOW_RUN_ID,
        task_run_id: "tr-exception-003",
        artifact_kind: "schedule.replan_delta.workbook",
        artifact_role: "official_output",
        media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        storage_uri: "s3://artifacts/av-002.xlsx",
        content_digest: "sha256:def456",
        byte_size: 980,
        metadata_json: { source: "stage07" },
        parent_artifact_version_id: null,
        supersedes_artifact_version_id: "av-001",
        lineage_note: null,
        created_at: nowIso(-90)
      }
    ],
    timelineEvents: [
      {
        sequence_no: 1,
        event_id: "evt-001",
        event_type: "workflow.run.created",
        occurred_at: nowIso(-600),
        recorded_at: nowIso(-600),
        tenant_id: "tenant-a",
        domain_id: "domain-x",
        actor: { id: "system:runtime", type: "system" },
        links: [{ id: WORKFLOW_RUN_ID, rel: "subject", type: "workflow_run" }],
        payload: { workflow_id: "schedule_planning.v1" }
      },
      {
        sequence_no: 2,
        event_id: "evt-002",
        event_type: "task.created",
        occurred_at: nowIso(-500),
        recorded_at: nowIso(-500),
        tenant_id: "tenant-a",
        domain_id: "domain-x",
        actor: { id: "system:runtime", type: "system" },
        links: [{ id: "ht-open-001", rel: "subject", type: "human_task" }],
        payload: { human_task_id: "ht-open-001", state: "OPEN" }
      },
      {
        sequence_no: 3,
        event_id: "evt-003",
        event_type: "approval.requested",
        occurred_at: nowIso(-200),
        recorded_at: nowIso(-200),
        tenant_id: "tenant-a",
        domain_id: "domain-x",
        actor: { id: "system:runtime", type: "system" },
        links: [{ id: "ap-pending-001", rel: "subject", type: "approval" }],
        payload: { approval_id: "ap-pending-001", state: "PENDING" }
      },
      {
        sequence_no: 4,
        event_id: "evt-004",
        event_type: "flag.created",
        occurred_at: nowIso(-250),
        recorded_at: nowIso(-250),
        tenant_id: "tenant-a",
        domain_id: "domain-x",
        actor: { id: "human:dispatcher-1", type: "human" },
        links: [{ id: "flag-001", rel: "subject", type: "flag" }],
        payload: { flag_id: "flag-001", state: "open" }
      }
    ],
    audit: {
      mutations: []
    },
    uploadedTaskAttachmentIds: new Set<string>(),
    uploadedApprovalAttachmentIds: new Set<string>(),
    uploadedFlagAttachmentIds: new Set<string>(),
    stage06ReviewedTaskIds: new Set<string>(),
    forceForbidden: false
  };
}
