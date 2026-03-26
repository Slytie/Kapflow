import { http, HttpResponse } from "msw";
import type {
  ArtifactVersionRow,
  HumanTaskRow,
  HumanTaskSubgraph
} from "@/lib/types/contracts";
import eodArtifactCreateResponseSnapshot from "@fixtures/workpage_eod_v0_artifact_create_response.json";
import eodArtifactStateSnapshot from "@fixtures/workpage_eod_v0_artifact_state.json";
import eodArtifactSubmitResponseSnapshot from "@fixtures/workpage_eod_v0_artifact_submit_response.json";
import eodWorkpageStateSnapshot from "@fixtures/workpage_eod_v0_state.json";
import scheduleWorkpageStateSnapshot from "@fixtures/workpage_schedule_v0_state.json";

import {
  buildBoardContract,
  buildWorkflowRunDetail,
  buildWorkflowRunWorkspace,
  createContractState
} from "@/test/api/contractState";

const ok = (payload: Record<string, unknown>) => HttpResponse.json({ status: "ok", ...payload });

let state = createContractState();
let eodArtifactVersionCounter = 0;
const eodArtifactVersions = new Map<string, EodArtifactVersionState>();
const EOD_WORKFLOW_RUN_ID = "wr-eod-artifact-001";

interface EodArtifactVersionState {
  artifactVersionId: string;
  workflowRunId: string;
  fileName: string;
  createdAt: string;
  lineageNote: string | null;
  payload: Record<string, unknown>;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId: string | null;
  latestInChainArtifactVersionId: string;
}

function nowIso(): string {
  return new Date().toISOString();
}

function cloneJson<T>(value: T): T {
  return structuredClone(value);
}

function nextEodArtifactVersionId(): string {
  eodArtifactVersionCounter += 1;
  return `av-eod-artifact-${String(eodArtifactVersionCounter).padStart(3, "0")}`;
}

function artifactRoute(artifactVersionId: string): string {
  return `/demo/logistics/workpages/eod-v0/artifacts/${artifactVersionId}`;
}

function sortArtifactRowsAscending(left: ArtifactVersionRow, right: ArtifactVersionRow): number {
  const createdAtCompare = left.created_at.localeCompare(right.created_at);
  if (createdAtCompare !== 0) {
    return createdAtCompare;
  }
  return left.artifact_version_id.localeCompare(right.artifact_version_id);
}

function eodArtifactFileName(artifactVersionId: string): string {
  return `dispatch_reporting_stage03_${artifactVersionId}.xlsx`;
}

function findSectionByKind(payload: Record<string, unknown>, kind: string): Record<string, unknown> | null {
  const workpage = payload.workpage;
  if (!workpage || typeof workpage !== "object" || Array.isArray(workpage)) {
    return null;
  }
  const sections = (workpage as Record<string, unknown>).sections;
  if (!Array.isArray(sections)) {
    return null;
  }
  return (
    sections.find(
      (section) =>
        section &&
        typeof section === "object" &&
        !Array.isArray(section) &&
        (section as Record<string, unknown>).kind === kind
    ) as Record<string, unknown> | undefined
  ) ?? null;
}

function patchArtifactPayloadLineage(version: EodArtifactVersionState): void {
  const payload = version.payload;
  const artifactContext = payload.artifact_context;
  if (artifactContext && typeof artifactContext === "object" && !Array.isArray(artifactContext)) {
    const artifactContextRecord = artifactContext as Record<string, unknown>;
    artifactContextRecord.artifact_version_id = version.artifactVersionId;
    artifactContextRecord.workflow_run_id = version.workflowRunId;
    artifactContextRecord.supersedes_artifact_version_id = version.supersedesArtifactVersionId;
    artifactContextRecord.superseded_by_artifact_version_id = version.supersededByArtifactVersionId;
    artifactContextRecord.latest_in_chain_artifact_version_id = version.latestInChainArtifactVersionId;
    artifactContextRecord.download_path = `/api/v1/artifacts/${version.artifactVersionId}/download.bin`;
  }

  const freshness = payload.freshness;
  if (freshness && typeof freshness === "object" && !Array.isArray(freshness)) {
    const freshnessRecord = freshness as Record<string, unknown>;
    freshnessRecord.generated_at = nowIso();
    freshnessRecord.source_version = version.artifactVersionId;
  }

  const source = payload.source;
  if (source && typeof source === "object" && !Array.isArray(source)) {
    (source as Record<string, unknown>).source_artifact_version_id = version.artifactVersionId;
  }

  const workpage = payload.workpage;
  if (workpage && typeof workpage === "object" && !Array.isArray(workpage)) {
    (workpage as Record<string, unknown>).source_artifact_version_id = version.artifactVersionId;
  }

  const historySection = findSectionByKind(payload, "history_stub");
  if (historySection) {
    historySection.entries = [
      {
        label: "Current artifact version",
        value: version.artifactVersionId
      },
      {
        label: "Supersedes",
        value: version.supersedesArtifactVersionId ?? "Initial draft"
      },
      {
        label: "Latest draft in chain",
        value: version.latestInChainArtifactVersionId
      }
    ];
  }
}

function applyArtifactDraftEdits(
  payload: Record<string, unknown>,
  formValues: Record<string, unknown>,
  checklistValues: Array<{ item_id: string; selected: boolean; note: string }>
): void {
  const formSection = findSectionByKind(payload, "form");
  if (formSection) {
    const fields = formSection.fields;
    if (Array.isArray(fields)) {
      formSection.fields = fields.map((field) => {
        if (!field || typeof field !== "object" || Array.isArray(field)) {
          return field;
        }
        const fieldRecord = { ...(field as Record<string, unknown>) };
        const key = typeof fieldRecord.key === "string" ? fieldRecord.key : "";
        if (key && key in formValues) {
          fieldRecord.value = formValues[key];
        }
        return fieldRecord;
      });
    }
  }

  const checklistSection = findSectionByKind(payload, "checklist");
  if (checklistSection) {
    const items = checklistSection.items;
    if (Array.isArray(items) && items.length > 0) {
      const checklistById = new Map(checklistValues.map((value) => [value.item_id, value]));
      checklistSection.items = items.map((item) => {
        if (!item || typeof item !== "object" || Array.isArray(item)) {
          return item;
        }
        const itemRecord = { ...(item as Record<string, unknown>) };
        const itemId = typeof itemRecord.item_id === "string" ? itemRecord.item_id : "";
        const next = checklistById.get(itemId);
        if (next) {
          itemRecord.selected = next.selected;
          itemRecord.note = next.note;
        }
        return itemRecord;
      });
    }
  }
}

function buildEodArtifactPayload(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId: string | null;
  latestInChainArtifactVersionId: string;
  formValues?: Record<string, unknown>;
  checklistValues?: Array<{ item_id: string; selected: boolean; note: string }>;
}): Record<string, unknown> {
  const payload = cloneJson(eodArtifactStateSnapshot.workpage_state) as Record<string, unknown>;
  const workpage = payload.workpage as Record<string, unknown>;
  const source = payload.source as Record<string, unknown>;
  const freshness = payload.freshness as Record<string, unknown>;
  const artifactContext = payload.artifact_context as Record<string, unknown>;

  workpage.source_artifact_version_id = input.artifactVersionId;
  source.source_artifact_version_id = input.artifactVersionId;
  freshness.generated_at = nowIso();
  freshness.source_version = input.artifactVersionId;
  artifactContext.artifact_version_id = input.artifactVersionId;
  artifactContext.workflow_run_id = input.workflowRunId;
  artifactContext.supersedes_artifact_version_id = input.supersedesArtifactVersionId;
  artifactContext.superseded_by_artifact_version_id = input.supersededByArtifactVersionId;
  artifactContext.latest_in_chain_artifact_version_id = input.latestInChainArtifactVersionId;
  artifactContext.download_path = `/api/v1/artifacts/${input.artifactVersionId}/download.bin`;

  patchArtifactPayloadLineage({
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: eodArtifactFileName(input.artifactVersionId),
    createdAt: nowIso(),
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted artifact-backed EOD draft version."
      : "Initial artifact-backed EOD draft seeded from Stage03 template.",
    payload,
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  });

  applyArtifactDraftEdits(payload, input.formValues ?? {}, input.checklistValues ?? []);
  return payload;
}

function addEodArtifactVersion(input: {
  artifactVersionId: string;
  workflowRunId: string;
  supersedesArtifactVersionId: string | null;
  supersededByArtifactVersionId?: string | null;
  latestInChainArtifactVersionId: string;
  formValues?: Record<string, unknown>;
  checklistValues?: Array<{ item_id: string; selected: boolean; note: string }>;
}): EodArtifactVersionState {
  const createdAt = nowIso();
  const version: EodArtifactVersionState = {
    artifactVersionId: input.artifactVersionId,
    workflowRunId: input.workflowRunId,
    fileName: eodArtifactFileName(input.artifactVersionId),
    createdAt,
    lineageNote: input.supersedesArtifactVersionId
      ? "Submitted artifact-backed EOD draft version."
      : "Initial artifact-backed EOD draft seeded from Stage03 template.",
    payload: buildEodArtifactPayload({
      artifactVersionId: input.artifactVersionId,
      workflowRunId: input.workflowRunId,
      supersedesArtifactVersionId: input.supersedesArtifactVersionId,
      supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
      latestInChainArtifactVersionId: input.latestInChainArtifactVersionId,
      formValues: input.formValues,
      checklistValues: input.checklistValues
    }),
    supersedesArtifactVersionId: input.supersedesArtifactVersionId,
    supersededByArtifactVersionId: input.supersededByArtifactVersionId ?? null,
    latestInChainArtifactVersionId: input.latestInChainArtifactVersionId
  };
  eodArtifactVersions.set(version.artifactVersionId, version);
  return version;
}

function eodArtifactVersionRow(version: EodArtifactVersionState): ArtifactVersionRow {
  return {
    artifact_version_id: version.artifactVersionId,
    workflow_run_id: version.workflowRunId,
    task_run_id: null,
    artifact_kind: "reporting.upd_draft.workbook",
    artifact_role: "",
    media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    storage_uri: `memory://workpages/${version.fileName}`,
    content_digest: `sha256:${version.artifactVersionId}`,
    byte_size: 1024,
    metadata_json: {
      demo_workpage_id: "eod-v0",
      file_name: version.fileName,
      service_date: "2026-03-16",
      station_code: "DVC4",
      dsp_name: "QDCI"
    },
    parent_artifact_version_id: version.supersedesArtifactVersionId,
    supersedes_artifact_version_id: version.supersedesArtifactVersionId,
    lineage_note: version.lineageNote,
    created_at: version.createdAt,
    links: [
      {
        artifact_version_id: version.artifactVersionId,
        workflow_run_id: version.workflowRunId,
        subject_kind: "workflow_run",
        subject_id: version.workflowRunId,
        relation_kind: "subject",
        created_at: version.createdAt,
        created_by_actor_id: null,
        created_by_actor_type: null
      }
    ]
  };
}

function listWorkflowRunArtifacts(workflowRunId: string): ArtifactVersionRow[] {
  const eodArtifacts =
    workflowRunId === EOD_WORKFLOW_RUN_ID
      ? Array.from(eodArtifactVersions.values()).map(eodArtifactVersionRow)
      : [];
  return [...listArtifactsForSubject("workflow_run", workflowRunId), ...eodArtifacts].sort(
    sortArtifactRowsAscending
  );
}

function updateEodArtifactChainLatest(artifactVersionId: string, latestArtifactVersionId: string): void {
  let currentArtifactVersionId: string | null = artifactVersionId;
  while (currentArtifactVersionId) {
    const version = eodArtifactVersions.get(currentArtifactVersionId);
    if (!version) {
      break;
    }
    version.latestInChainArtifactVersionId = latestArtifactVersionId;
    patchArtifactPayloadLineage(version);
    currentArtifactVersionId = version.supersedesArtifactVersionId;
  }
}

function ensureEodArtifactDraft(): EodArtifactVersionState {
  const artifactVersionId = nextEodArtifactVersionId();
  return addEodArtifactVersion({
    artifactVersionId,
    workflowRunId: EOD_WORKFLOW_RUN_ID,
    supersedesArtifactVersionId: null,
    latestInChainArtifactVersionId: artifactVersionId
  });
}

function eodArtifactCreateResponse(version: EodArtifactVersionState): Record<string, unknown> {
  const payload = cloneJson(
    eodArtifactCreateResponseSnapshot.create_response
  ) as Record<string, unknown>;
  payload.draft = {
    artifact_version_id: version.artifactVersionId,
    route: artifactRoute(version.artifactVersionId),
    workflow_run_id: version.workflowRunId
  };
  return payload;
}

function eodArtifactSubmitResponse(
  version: EodArtifactVersionState,
  supersedesArtifactVersionId: string
): Record<string, unknown> {
  const payload = cloneJson(
    eodArtifactSubmitResponseSnapshot.submit_response
  ) as Record<string, unknown>;
  payload.submitted = {
    artifact_version_id: version.artifactVersionId,
    route: artifactRoute(version.artifactVersionId),
    supersedes_artifact_version_id: supersedesArtifactVersionId,
    workflow_run_id: version.workflowRunId
  };
  return payload;
}

function resetEodArtifactVersions(): void {
  eodArtifactVersionCounter = 0;
  eodArtifactVersions.clear();
}

const TEMPLATE_FIXTURES = [
  {
    template_id: "schedule.stage05.draft_schedule.workbook.empty.v1",
    workflow_id: "schedule_planning.v1",
    stage_id: "Stage05",
    dataset_key: "schedule.draft_schedule.workbook",
    artifact_kind: "schedule.draft_schedule.workbook",
    variant: "empty",
    media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    file_path:
      "fixtures/workflows/schedule_planning/template_pack/Stage05_Draft_Schedule_Triage/Stage05_Draft_Schedule_Triage_Spreadsheet_Template_EMPTY.xlsx",
    file_name: "Stage05_Draft_Schedule_Triage_Spreadsheet_Template_EMPTY.xlsx",
    description: "Empty Stage05 draft-schedule workbook template."
  },
  {
    template_id: "schedule.stage06.supervisor_review.doc.empty.v1",
    workflow_id: "schedule_planning.v1",
    stage_id: "Stage06",
    dataset_key: "schedule.supervisor_review.doc",
    artifact_kind: "schedule.supervisor_review.doc",
    variant: "empty",
    media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_path:
      "fixtures/workflows/schedule_planning/template_pack/Stage06_Supervisor_Review_Publish/Stage06_Supervisor_Review_Publish_Document_Template_EMPTY.docx",
    file_name: "Stage06_Supervisor_Review_Publish_Document_Template_EMPTY.docx",
    description: "Empty Stage06 supervisor-review document template."
  },
  {
    template_id: "schedule.stage07.exception_board.doc.empty.v1",
    workflow_id: "schedule_planning.v1",
    stage_id: "Stage07",
    dataset_key: "schedule.exception_board.doc",
    artifact_kind: "schedule.exception_board.doc",
    variant: "empty",
    media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_path:
      "fixtures/workflows/schedule_planning/template_pack/Stage07_Intraday_Exception_Control/Stage07_Intraday_Exception_Control_Document_Template_EMPTY.docx",
    file_name: "Stage07_Intraday_Exception_Control_Document_Template_EMPTY.docx",
    description: "Empty Stage07 exception-board document template."
  }
];

function defaultViewerActorRoles(request: Request): string[] {
  const actorRoles = Array.from(actorRolesFromRequest(request));
  if (actorRoles.length > 0) {
    return actorRoles;
  }
  return [
    "dispatch_supervisor",
    "schedule_planner",
    "fleet_coordinator",
    "operations_manager"
  ];
}

function viewerSessionFromRequest(request: Request): Record<string, unknown> {
  return {
    tenant_id: request.headers.get("x-onetruth-tenant-id") ?? state.tenantId,
    domain_id: request.headers.get("x-onetruth-domain-id") ?? state.domainId,
    actor_id: request.headers.get("x-onetruth-actor-id") ?? "human:frontend-operator",
    actor_type: request.headers.get("x-onetruth-actor-type") ?? "human",
    actor_roles: defaultViewerActorRoles(request),
    boundary_profile: "local_dev",
    request_context_mode: "trusted_headers",
    actor_switching_allowed: true
  };
}

function inScope(request: Request): boolean {
  const tenant = request.headers.get("x-onetruth-tenant-id");
  const domain = request.headers.get("x-onetruth-domain-id");
  if (state.forceForbidden) {
    return false;
  }
  return tenant === state.tenantId && domain === state.domainId;
}

function forbiddenWorkflowRun() {
  return HttpResponse.json(
    {
      status: "error",
      error: {
        code: "workflow_run_not_found",
        message: "workflow run not found",
        details: {}
      }
    },
    { status: 404 }
  );
}

function parseLimitOffset(url: URL): { limit: number; offset: number } {
  const limit = Number.parseInt(url.searchParams.get("limit") ?? "100", 10);
  const offset = Number.parseInt(url.searchParams.get("offset") ?? "0", 10);
  return {
    limit: Number.isNaN(limit) ? 100 : limit,
    offset: Number.isNaN(offset) ? 0 : offset
  };
}

function actorRolesFromRequest(request: Request): Set<string> {
  const rawRoles = request.headers.get("x-onetruth-actor-roles") ?? "";
  return new Set(
    rawRoles
      .split(",")
      .map((role) => role.trim())
      .filter(Boolean)
  );
}

function taskActionability(task: HumanTaskRow, request: Request) {
  const actorId = request.headers.get("x-onetruth-actor-id") ?? "human:frontend-operator";
  const actorType = request.headers.get("x-onetruth-actor-type") ?? "human";
  const actorRoles = actorRolesFromRequest(request);
  const roleMatch =
    task.candidate_roles.length === 0 ||
    task.candidate_roles.some((role) => actorRoles.has(role));
  const isAssignee =
    task.assignee_actor_id === actorId && task.assignee_actor_type === actorType;
  const availableActions: string[] = [];
  const blockingReasonCodes = [...(task.blocking_reason_codes ?? [])];

  if (task.state === "OPEN" && !task.assignee_actor_id && roleMatch) {
    availableActions.push("claim");
  } else if (task.state === "OPEN" && !roleMatch) {
    blockingReasonCodes.push("candidate_role_mismatch");
  }

  if (task.state === "CLAIMED" && isAssignee) {
    availableActions.push("complete");
  } else if (task.state === "CLAIMED" && !isAssignee) {
    blockingReasonCodes.push("claimed_by_other_actor");
  }

  if (task.state !== "COMPLETED") {
    availableActions.push("upload_attachment");
  }

  return {
    available_actions: [...new Set(availableActions)],
    missing_required_inputs: task.missing_required_inputs ?? [],
    blocking_reason_codes: [...new Set(blockingReasonCodes)]
  };
}

const COMPOSITE_TASK_SUBGRAPH_KINDS = new Set([
  "actual_hours_review",
  "planning_feedback_review",
  "dispatcher_review",
  "dispatch_seed_intake",
  "final_packet_review",
  "finalize_reporting_packet"
]);

function taskSubgraphMetadata(task: HumanTaskRow): {
  is_composite: boolean;
  expansion_kind: "none" | "task_subgraph";
  subgraph_ref: { human_task_id: string; endpoint: string } | null;
} {
  if (!COMPOSITE_TASK_SUBGRAPH_KINDS.has(task.task_kind)) {
    return {
      is_composite: false,
      expansion_kind: "none",
      subgraph_ref: null
    };
  }
  return {
    is_composite: true,
    expansion_kind: "task_subgraph",
    subgraph_ref: {
      human_task_id: task.human_task_id,
      endpoint: `/api/v1/human-tasks/${task.human_task_id}/subgraph`
    }
  };
}

function enrichHumanTaskForResponse(task: HumanTaskRow, request: Request): HumanTaskRow {
  return {
    ...task,
    ...taskActionability(task, request),
    ...taskSubgraphMetadata(task)
  };
}

function taskSubgraphTemplate(taskKind: string): {
  template_id: string;
  title: string;
  nodes: Array<{ node_id: string; label: string }>;
} | null {
  if (taskKind === "actual_hours_review" || taskKind === "planning_feedback_review") {
    return {
      template_id: "schedule_planning.feedback_review.v1",
      title: "Planning feedback review",
      nodes: [
        { node_id: "ingest_actual_hours", label: "Ingest actual-hours snapshot" },
        { node_id: "reconcile_plan_variance", label: "Reconcile plan variance" },
        { node_id: "draft_feedback_packet", label: "Draft planning feedback packet" },
        { node_id: "publish_feedback_handoff", label: "Publish feedback handoff" }
      ]
    };
  }
  if (taskKind === "dispatcher_review" || taskKind === "dispatch_seed_intake") {
    return {
      template_id: "live_dispatch.seed_intake.v1",
      title: "Live dispatch seed intake",
      nodes: [
        { node_id: "ingest_weekly_seed", label: "Ingest weekly seed package" },
        { node_id: "verify_route_delta", label: "Verify route delta inputs" },
        { node_id: "resolve_capacity_conflicts", label: "Resolve capacity conflicts" },
        { node_id: "dispatch_ready_confirmation", label: "Confirm dispatch readiness" }
      ]
    };
  }
  if (taskKind === "final_packet_review" || taskKind === "finalize_reporting_packet") {
    return {
      template_id: "dispatch_reporting.final_packet.v1",
      title: "Reporting packet closeout",
      nodes: [
        { node_id: "collect_route_metrics", label: "Collect route metrics" },
        { node_id: "reconcile_variance_notes", label: "Reconcile variance notes" },
        { node_id: "finalize_reporting_packet", label: "Finalize reporting packet" },
        { node_id: "notify_planning_feedback", label: "Notify planning feedback" }
      ]
    };
  }
  return null;
}

function taskSubgraphNodeStatuses(taskState: HumanTaskRow["state"], nodeCount: number): string[] {
  if (nodeCount <= 0) {
    return [];
  }
  if (taskState === "COMPLETED") {
    return Array.from({ length: nodeCount }, () => "completed");
  }
  if (taskState === "CLAIMED") {
    return Array.from({ length: nodeCount }, (_, index) => {
      if (index === 0) {
        return "completed";
      }
      if (index === 1) {
        return "in_progress";
      }
      if (index === 2) {
        return "ready";
      }
      return "not_started";
    });
  }
  return Array.from({ length: nodeCount }, (_, index) =>
    index === 0 ? "in_progress" : "not_started"
  );
}

function taskSubgraphArtifactRefs(task: HumanTaskRow) {
  const refsByArtifactId = new Map<
    string,
    { artifact_version_id: string; label: string; source_label: string }
  >();
  for (const artifact of state.artifactVersions) {
    const links = artifact.links ?? [];
    const hasTaskAttachment = links.some(
      (link) => link.subject_kind === "human_task" && link.subject_id === task.human_task_id
    );
    const hasTaskOutput = links.some(
      (link) => link.subject_kind === "task_run" && link.subject_id === task.task_run_id
    );
    if (!hasTaskAttachment && !hasTaskOutput) {
      continue;
    }
    const metadataName = artifact.metadata_json?.file_name;
    refsByArtifactId.set(artifact.artifact_version_id, {
      artifact_version_id: artifact.artifact_version_id,
      label:
        typeof metadataName === "string" && metadataName.length > 0
          ? metadataName
          : artifact.artifact_kind,
      source_label: hasTaskOutput ? "Task step output" : "Task attachment"
    });
  }
  return Array.from(refsByArtifactId.values());
}

function buildTaskSubgraph(task: HumanTaskRow): HumanTaskSubgraph | null {
  const template = taskSubgraphTemplate(task.task_kind);
  if (!template) {
    return null;
  }
  const statuses = taskSubgraphNodeStatuses(task.state, template.nodes.length);
  return {
    graph_id: `task_subgraph:${task.human_task_id}`,
    template_id: template.template_id,
    title: template.title,
    nodes: template.nodes.map((node, index) => ({
      node_id: node.node_id,
      label: node.label,
      node_kind: "step",
      status: statuses[index] as HumanTaskSubgraph["nodes"][number]["status"],
      row: 0,
      column: index,
      is_blocking: false
    })),
    edges: template.nodes.slice(0, -1).map((node, index) => ({
      edge_id: `${node.node_id}->${template.nodes[index + 1].node_id}`,
      from_node_id: node.node_id,
      to_node_id: template.nodes[index + 1].node_id,
      edge_kind: "linear",
      label: null
    })),
    freshness: {
      status: "fresh",
      as_of: task.updated_at,
      note: "Mock task subgraph freshness"
    },
    artifact_refs: taskSubgraphArtifactRefs(task)
  };
}

function listTemplatesFromQuery(url: URL) {
  const workflowId = url.searchParams.get("workflow_id");
  const stageId = url.searchParams.get("stage_id");
  const datasetKey = url.searchParams.get("dataset_key");
  const variant = url.searchParams.get("variant");
  return TEMPLATE_FIXTURES.filter((template) => {
    if (workflowId && template.workflow_id !== workflowId) {
      return false;
    }
    if (stageId && template.stage_id !== stageId) {
      return false;
    }
    if (datasetKey && template.dataset_key !== datasetKey) {
      return false;
    }
    if (variant && template.variant !== variant) {
      return false;
    }
    return true;
  });
}

function templateDownloadBody(templateId: string): string {
  return `template:${templateId}`;
}

function mutateTaskToClaimed(humanTaskId: string, actorId: string): boolean {
  const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
  if (!row || row.state !== "OPEN") {
    return false;
  }

  row.state = "CLAIMED";
  row.assignee_actor_id = actorId;
  row.assignee_actor_type = "human";
  row.lease_version += 1;
  row.claimed_at = new Date().toISOString();
  row.updated_at = row.claimed_at;
  row.task_run_state = "IN_PROGRESS";
  state.audit.mutations.push(`claim:${humanTaskId}`);
  return true;
}

function mutateTaskToCompleted(humanTaskId: string): boolean {
  const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
  if (!row || row.state !== "CLAIMED") {
    return false;
  }

  row.state = "COMPLETED";
  row.task_run_state = "COMPLETED";
  row.updated_at = new Date().toISOString();
  state.audit.mutations.push(`complete:${humanTaskId}`);
  return true;
}

function confirmTaskReview(
  humanTaskId: string,
  reviewedArtifactVersionIds: string[]
): { artifactVersion: ArtifactVersionRow; idempotentReplay: boolean } | null {
  const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
  if (!row || row.state !== "CLAIMED") {
    return null;
  }

  const existing = state.artifactVersions.find(
    (artifact) =>
      artifact.artifact_kind === "human_task.review_confirmation.json" &&
      artifact.metadata_json?.human_task_id === humanTaskId
  );
  if (existing) {
    state.confirmedReviewTaskIds.add(humanTaskId);
    state.audit.mutations.push(`confirm-review:${humanTaskId}`);
    return { artifactVersion: existing, idempotentReplay: true };
  }

  const artifactVersionId = `av-confirm-${state.artifactVersions.length + 1}`;
  const createdAt = new Date().toISOString();
  const artifactVersion: ArtifactVersionRow = {
    artifact_version_id: artifactVersionId,
    workflow_run_id: row.workflow_run_id,
    task_run_id: row.task_run_id,
    artifact_kind: "human_task.review_confirmation.json",
    artifact_role: "review_evidence",
    media_type: "application/json",
    storage_uri: `memory://confirm-review/${artifactVersionId}.json`,
    content_digest: `sha256:${artifactVersionId}`,
    byte_size: 256,
    metadata_json: {
      human_task_id: humanTaskId,
      reviewed_artifact_version_ids: reviewedArtifactVersionIds
    },
    parent_artifact_version_id: null,
    supersedes_artifact_version_id: null,
    lineage_note: null,
    created_at: createdAt,
    links: [
      {
        artifact_version_id: artifactVersionId,
        workflow_run_id: row.workflow_run_id,
        subject_kind: "human_task",
        subject_id: humanTaskId,
        relation_kind: "review_confirmation",
        created_at: createdAt,
        created_by_actor_id: "human:frontend-operator",
        created_by_actor_type: "human"
      }
    ]
  };

  state.artifactVersions.unshift(artifactVersion);
  state.confirmedReviewTaskIds.add(humanTaskId);
  state.audit.mutations.push(`confirm-review:${humanTaskId}`);
  return { artifactVersion, idempotentReplay: false };
}

function mutateApprovalResponse(approvalId: string, responseKind: string): boolean {
  const row = state.approvals.find((approval) => approval.approval_id === approvalId);
  if (!row || row.state !== "PENDING") {
    return false;
  }

  row.state = "RESPONDED";
  row.response_kind = responseKind;
  row.responded_at = new Date().toISOString();
  row.updated_at = row.responded_at;
  row.generation += 1;
  state.audit.mutations.push(`respond:${approvalId}:${responseKind}`);
  return true;
}

function workflowRunIdForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
): string | null {
  if (subjectKind === "workflow_run") {
    return subjectId;
  }
  if (subjectKind === "human_task") {
    return state.humanTasks.find((task) => task.human_task_id === subjectId)?.workflow_run_id ?? null;
  }
  if (subjectKind === "approval") {
    return state.approvals.find((approval) => approval.approval_id === subjectId)?.workflow_run_id ?? null;
  }
  return state.flags.find((flag) => flag.flag_id === subjectId)?.workflow_run_id ?? null;
}

function taskRunIdForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
): string | null {
  if (subjectKind === "human_task") {
    return state.humanTasks.find((task) => task.human_task_id === subjectId)?.task_run_id ?? null;
  }
  if (subjectKind === "approval") {
    return state.approvals.find((approval) => approval.approval_id === subjectId)?.task_run_id ?? null;
  }
  return null;
}

function addAttachmentArtifact(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string,
  payload: Record<string, unknown>
) {
  const workflowRunId = workflowRunIdForSubject(subjectKind, subjectId);
  if (!workflowRunId) {
    return null;
  }
  const artifactVersionId = `av-upload-${state.artifactVersions.length + 1}`;
  const createdAt = new Date().toISOString();
  const fileName =
    typeof payload.file_name === "string" && payload.file_name.length > 0
      ? payload.file_name
      : `${artifactVersionId}.txt`;

  const artifactVersion = {
    artifact_version_id: artifactVersionId,
    workflow_run_id: workflowRunId,
    task_run_id: taskRunIdForSubject(subjectKind, subjectId),
    artifact_kind:
      typeof payload.artifact_kind === "string" ? payload.artifact_kind : `attachment.${subjectKind}`,
    artifact_role:
      typeof payload.artifact_role === "string" ? payload.artifact_role : "evidence",
    media_type:
      typeof payload.media_type === "string" ? payload.media_type : "application/octet-stream",
    storage_uri: `memory://attachments/${artifactVersionId}`,
    content_digest: `sha256:${artifactVersionId}`,
    byte_size:
      typeof payload.content_base64 === "string" ? payload.content_base64.length : fileName.length,
    metadata_json: {
      file_name: fileName,
      source: "msw"
    },
    parent_artifact_version_id: null,
    supersedes_artifact_version_id: null,
    lineage_note: null,
    created_at: createdAt,
    links: [
      {
        artifact_version_id: artifactVersionId,
        workflow_run_id: workflowRunId,
        subject_kind: subjectKind,
        subject_id: subjectId,
        relation_kind: "attachment",
        created_at: createdAt,
        created_by_actor_id: "human:frontend-operator",
        created_by_actor_type: "human"
      }
    ]
  };

  state.artifactVersions.unshift(artifactVersion);

  if (subjectKind === "human_task") {
    state.uploadedTaskAttachmentIds.add(subjectId);
  } else if (subjectKind === "approval") {
    state.uploadedApprovalAttachmentIds.add(subjectId);
  } else if (subjectKind === "flag") {
    state.uploadedFlagAttachmentIds.add(subjectId);
  }

  state.audit.mutations.push(`upload:${subjectKind}:${subjectId}`);
  return artifactVersion;
}

function listArtifactsForSubject(
  subjectKind: "human_task" | "approval" | "flag" | "workflow_run",
  subjectId: string
) {
  return state.artifactVersions.filter((artifact) =>
    artifact.links?.some(
      (link) => link.subject_kind === subjectKind && link.subject_id === subjectId
    )
  );
}

function artifactDownloadBody(artifactVersionId: string): string {
  return `artifact:${artifactVersionId}`;
}

function binaryDownloadResponse(
  body: string,
  options: {
    fileName: string;
    mediaType: string;
    requestId: string;
  }
) {
  return new HttpResponse(body, {
    status: 200,
    headers: {
      "content-type": options.mediaType,
      "content-length": String(body.length),
      "content-disposition": `attachment; filename="${options.fileName}"`,
      "x-request-id": options.requestId
    }
  });
}

function buildStoryRun(
  input: {
    workflowRunId: string;
    workflowId: string;
    partitionKey: string;
    state: string;
    activeIssueCount: number;
  }
) {
  const now = new Date().toISOString();
  return {
    workflow_run_id: input.workflowRunId,
    workflow_id: input.workflowId,
    workflow_version: "v1",
    tenant_id: "tenant-a",
    domain_id: "domain-x",
    partition_key: input.partitionKey,
    logical_date: input.partitionKey,
    activation_key: `${input.workflowId}:${input.partitionKey}`,
    state: input.state,
    active_issue_count: input.activeIssueCount,
    created_at: now,
    updated_at: now
  };
}

function buildLogisticsStoryPayload(planningWeekId: string, request: Request, serviceDateId?: string) {
  const now = new Date().toISOString();
  const reportingRun = buildStoryRun({
    workflowRunId: "wr-report-001",
    workflowId: "dispatch_reporting.v1",
    partitionKey: serviceDateId ?? "SD-2026-03-06",
    state: "COMPLETED",
    activeIssueCount: 0
  });
  const weeklyRun = buildStoryRun({
    workflowRunId: "wr-weekly-001",
    workflowId: "weekly_schedule_planning.v1",
    partitionKey: planningWeekId,
    state: "OPEN",
    activeIssueCount: 1
  });
  const liveRun = buildStoryRun({
    workflowRunId: "wr-live-001",
    workflowId: "live_dispatch.v1",
    partitionKey: serviceDateId ?? "SD-2026-03-06",
    state: "OPEN",
    activeIssueCount: 1
  });
  const storyTasks = {
    weekly: state.humanTasks.find((task) => task.human_task_id === "ht-weekly-001"),
    live: state.humanTasks.find((task) => task.human_task_id === "ht-live-001"),
    reporting: state.humanTasks.find((task) => task.human_task_id === "ht-reporting-001")
  };
  const weeklyTask = storyTasks.weekly
    ? enrichHumanTaskForResponse(storyTasks.weekly, request)
    : null;
  const liveTask = storyTasks.live ? enrichHumanTaskForResponse(storyTasks.live, request) : null;
  const reportingTask = storyTasks.reporting
    ? enrichHumanTaskForResponse(storyTasks.reporting, request)
    : null;

  const pointers = [
    {
      workflow_run_id: weeklyRun.workflow_run_id,
      pointer_key: "official:planning.published_weekly_schedule.workbook",
      scope_kind: "stage",
      scope_ref: "Stage06",
      artifact_kind: "planning.published_weekly_schedule.workbook",
      artifact_version_id: "av-weekly-001",
      promotion_reason: "official_publish",
      promoted_by_task_run_id: "tr-weekly-stage06",
      approved_by_approval_id: "ap-weekly-stage06",
      generation: 1,
      updated_at: now
    },
    {
      workflow_run_id: reportingRun.workflow_run_id,
      pointer_key: "official:reporting.final_packet.workbook",
      scope_kind: "stage",
      scope_ref: "Stage05",
      artifact_kind: "reporting.final_packet.workbook",
      artifact_version_id: "av-reporting-001",
      promotion_reason: "official_publish",
      promoted_by_task_run_id: "tr-report-stage05",
      approved_by_approval_id: "ap-report-stage05",
      generation: 1,
      updated_at: now
    }
  ];

  const officialOutputArtifacts = [
    {
      artifact_version_id: "av-weekly-001",
      workflow_run_id: weeklyRun.workflow_run_id,
      task_run_id: "tr-weekly-stage06",
      artifact_kind: "planning.published_weekly_schedule.workbook",
      artifact_role: "official_output",
      media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      storage_uri: "memory://story/av-weekly-001.xlsx",
      content_digest: "sha256:weekly001",
      byte_size: 1024,
      metadata_json: {
        file_name: "weekly_schedule.xlsx"
      },
      parent_artifact_version_id: null,
      supersedes_artifact_version_id: null,
      lineage_note: null,
      created_at: now
    },
    {
      artifact_version_id: "av-reporting-001",
      workflow_run_id: reportingRun.workflow_run_id,
      task_run_id: "tr-report-stage05",
      artifact_kind: "reporting.final_packet.workbook",
      artifact_role: "official_output",
      media_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      storage_uri: "memory://story/av-reporting-001.xlsx",
      content_digest: "sha256:reporting001",
      byte_size: 960,
      metadata_json: {
        file_name: "dispatch_reporting_packet.xlsx"
      },
      parent_artifact_version_id: null,
      supersedes_artifact_version_id: null,
      lineage_note: null,
      created_at: now
    }
  ];

  return {
    story_id: "logistics_three_workflow_demo.v1",
    family: {
      family_id: "logistics_ops_family.v1",
      family_version: 1,
      contract_version: 1
    },
    partitions: {
      planning_week_id: planningWeekId,
      service_date_ids: [serviceDateId ?? "SD-2026-03-06"]
    },
    family_graph: {
      family_id: "logistics_ops_family.v1",
      family_version: 1,
      modules: [
        {
          module_id: "dispatch_reporting",
          workflow_id: "dispatch_reporting.v1",
          partition_kind: "ServiceDateID",
          activation_policy: "manual_or_event",
          status: "active",
          node_kind: "module",
          drilldown_kind: "workflow_run",
          drilldown_refs: [
            {
              workflow_run_id: reportingRun.workflow_run_id,
              workflow_id: reportingRun.workflow_id,
              partition_key: reportingRun.partition_key
            }
          ],
          artifact_refs: [
            {
              artifact_version_id: "av-reporting-001",
              label: "dispatch_reporting_packet.xlsx",
              source_label: "Official output"
            }
          ],
          selection_summary: "1 linked run, 1 downloadable artifact"
        },
        {
          module_id: "weekly_schedule_planning",
          workflow_id: "weekly_schedule_planning.v1",
          partition_kind: "PlanningWeekID",
          activation_policy: "manual_or_event",
          status: "active",
          node_kind: "module",
          drilldown_kind: "workflow_run",
          drilldown_refs: [
            {
              workflow_run_id: weeklyRun.workflow_run_id,
              workflow_id: weeklyRun.workflow_id,
              partition_key: weeklyRun.partition_key
            }
          ],
          artifact_refs: [
            {
              artifact_version_id: "av-weekly-001",
              label: "weekly_schedule.xlsx",
              source_label: "Official output"
            }
          ],
          selection_summary: "1 linked run, 1 downloadable artifact"
        },
        {
          module_id: "live_dispatch",
          workflow_id: "live_dispatch.v1",
          partition_kind: "ServiceDateID",
          activation_policy: "event_driven",
          status: "active",
          node_kind: "module",
          drilldown_kind: "workflow_run",
          drilldown_refs: [
            {
              workflow_run_id: liveRun.workflow_run_id,
              workflow_id: liveRun.workflow_id,
              partition_key: liveRun.partition_key
            }
          ],
          artifact_refs: [],
          selection_summary: "1 linked run, 0 downloadable artifacts"
        }
      ],
      edges: [
        {
          edge_id: "reporting_actuals_to_future_planning",
          source_module_id: "dispatch_reporting",
          target_module_id: "weekly_schedule_planning",
          source_stage_id: "Stage05",
          source_dataset_key: "reporting.final_packet.workbook",
          target_stage_id: "Stage03",
          target_dataset_key: "planning.actual_hours_snapshot.workbook",
          partition_transform_id: "service_day_to_future_planning_week",
          handoff_mode: "notify_only",
          writer_mode: "source_only",
          status: "active"
        },
        {
          edge_id: "weekly_seed_to_live_dispatch",
          source_module_id: "weekly_schedule_planning",
          target_module_id: "live_dispatch",
          source_stage_id: "Stage07",
          source_dataset_key: "planning.daily_dispatch_seed.workbook",
          target_stage_id: "Stage01",
          target_dataset_key: "dispatch.base_schedule_seed.workbook",
          partition_transform_id: "planning_week_to_service_date",
          handoff_mode: "materialize_seed",
          writer_mode: "target_materialize",
          status: "active"
        }
      ]
    },
    linked_workflow_runs: {
      weekly_schedule_planning: [weeklyRun],
      live_dispatch: [liveRun],
      dispatch_reporting: [reportingRun],
      summary: {
        weekly_schedule_planning_count: 1,
        live_dispatch_count: 1,
        dispatch_reporting_count: 1
      }
    },
    handoff_activity: {
      edges: [
        {
          edge_id: "weekly_seed_to_live_dispatch",
          execution_count: 1,
          status_counts: { activated: 1 },
          coherence_failed_count: 0,
          executions: [
            {
              edge_execution_id: "edge-weekly-live-001",
              edge_id: "weekly_seed_to_live_dispatch",
              source_workflow_run_id: weeklyRun.workflow_run_id,
              source_stage_id: "Stage07",
              source_artifact_version_id: "av-weekly-seed-001",
              target_workflow_id: liveRun.workflow_id,
              target_workflow_run_id: liveRun.workflow_run_id,
              target_stage_id: "Stage01",
              target_partition_key: liveRun.partition_key,
              status: "activated",
              created_at: now,
              updated_at: now,
              activated_at: now,
              source_workflow_run: weeklyRun,
              target_workflow_run: liveRun,
              coherence: {
                coherence_status: "passed"
              }
            }
          ]
        },
        {
          edge_id: "reporting_actuals_to_future_planning",
          execution_count: 1,
          status_counts: { prepared: 1 },
          coherence_failed_count: 0,
          executions: [
            {
              edge_execution_id: "edge-reporting-weekly-001",
              edge_id: "reporting_actuals_to_future_planning",
              source_workflow_run_id: reportingRun.workflow_run_id,
              source_stage_id: "Stage05",
              source_artifact_version_id: "av-reporting-actuals-001",
              target_workflow_id: weeklyRun.workflow_id,
              target_workflow_run_id: weeklyRun.workflow_run_id,
              target_stage_id: "Stage03",
              target_partition_key: planningWeekId,
              status: "prepared",
              created_at: now,
              updated_at: now,
              activated_at: null,
              source_workflow_run: reportingRun,
              target_workflow_run: weeklyRun,
              coherence: {
                coherence_status: "passed"
              }
            }
          ]
        }
      ],
      summary: {
        edge_execution_count: 2,
        coherence_failed_count: 0
      }
    },
    board: {
      lanes: [
        { lane: "flags.open", label: "Open Exceptions", position: 5, item_count: 1 },
        { lane: "human_tasks.open", label: "Open Tasks", position: 10, item_count: 1 },
        { lane: "human_tasks.claimed", label: "Claimed Tasks", position: 20, item_count: 1 },
        { lane: "approvals.pending", label: "Pending Approvals", position: 30, item_count: 1 },
        { lane: "approvals.responded", label: "Responded Approvals", position: 40, item_count: 0 },
        { lane: "human_tasks.completed", label: "Completed Tasks", position: 50, item_count: 1 },
        { lane: "flags.resolved", label: "Resolved Exceptions", position: 60, item_count: 0 },
        { lane: "flags.closed", label: "Closed Exceptions", position: 70, item_count: 0 }
      ],
      work_items: [
        {
          item_id: "flag:flag-live-001",
          item_type: "flag",
          lane: "flags.open",
          title: "Live dispatch route conflict",
          workflow_run_id: liveRun.workflow_run_id,
          workflow_id: liveRun.workflow_id,
          subject_id: "flag-live-001",
          kind: "route_conflict",
          severity: "high",
          state: "open",
          available_actions: ["upload_attachment", "download_attachment"],
          blocking_reason_codes: [],
          missing_required_inputs: [],
          linked_artifact_count: 1
        },
        {
          item_id: "human_task:ht-weekly-001",
          item_type: "human_task",
          lane:
            weeklyTask?.state === "CLAIMED"
              ? "human_tasks.claimed"
              : weeklyTask?.state === "COMPLETED"
                ? "human_tasks.completed"
                : "human_tasks.open",
          title: "Stage03 planning_feedback_review",
          workflow_run_id: weeklyRun.workflow_run_id,
          workflow_id: weeklyRun.workflow_id,
          subject_id: "ht-weekly-001",
          stage_id: weeklyTask?.stage_id ?? "Stage03",
          task_kind: weeklyTask?.task_kind ?? "planning_feedback_review",
          state: weeklyTask?.state ?? "OPEN",
          owner_role: weeklyTask?.owner_role ?? "schedule_planner",
          available_actions: weeklyTask?.available_actions ?? ["claim"],
          blocking_reason_codes: weeklyTask?.blocking_reason_codes ?? [],
          missing_required_inputs: weeklyTask?.missing_required_inputs ?? [],
          linked_artifact_count: 0
        },
        {
          item_id: "human_task:ht-live-001",
          item_type: "human_task",
          lane:
            liveTask?.state === "OPEN"
              ? "human_tasks.open"
              : liveTask?.state === "COMPLETED"
                ? "human_tasks.completed"
                : "human_tasks.claimed",
          title: "Stage01 dispatch_seed_intake",
          workflow_run_id: liveRun.workflow_run_id,
          workflow_id: liveRun.workflow_id,
          subject_id: "ht-live-001",
          stage_id: liveTask?.stage_id ?? "Stage01",
          task_kind: liveTask?.task_kind ?? "dispatch_seed_intake",
          state: liveTask?.state ?? "CLAIMED",
          owner_role: liveTask?.owner_role ?? "dispatch_supervisor",
          available_actions: liveTask?.available_actions ?? ["complete"],
          blocking_reason_codes: liveTask?.blocking_reason_codes ?? [],
          missing_required_inputs: liveTask?.missing_required_inputs ?? [],
          linked_artifact_count: 1
        },
        {
          item_id: "approval:ap-weekly-001",
          item_type: "approval",
          lane: "approvals.pending",
          title: "business_decision Stage07",
          workflow_run_id: weeklyRun.workflow_run_id,
          workflow_id: weeklyRun.workflow_id,
          subject_id: "ap-weekly-001",
          approval_kind: "business_decision",
          scope_kind: "stage",
          scope_ref: "Stage07",
          required_role: "operations_manager",
          state: "PENDING",
          available_actions: ["respond_approve", "respond_reject"],
          blocking_reason_codes: [],
          missing_required_inputs: [],
          linked_artifact_count: 1
        },
        {
          item_id: "human_task:ht-reporting-001",
          item_type: "human_task",
          lane:
            reportingTask?.state === "OPEN"
              ? "human_tasks.open"
              : reportingTask?.state === "CLAIMED"
                ? "human_tasks.claimed"
                : "human_tasks.completed",
          title: "Stage05 finalize_reporting_packet",
          workflow_run_id: reportingRun.workflow_run_id,
          workflow_id: reportingRun.workflow_id,
          subject_id: "ht-reporting-001",
          stage_id: reportingTask?.stage_id ?? "Stage05",
          task_kind: reportingTask?.task_kind ?? "finalize_reporting_packet",
          state: reportingTask?.state ?? "COMPLETED",
          owner_role: reportingTask?.owner_role ?? "operations_manager",
          available_actions: reportingTask?.available_actions ?? [],
          blocking_reason_codes: reportingTask?.blocking_reason_codes ?? [],
          missing_required_inputs: reportingTask?.missing_required_inputs ?? [],
          linked_artifact_count: 2
        }
      ],
      page: { limit: 100, offset: 0 },
      summary: {
        work_item_count: 5,
        human_task_count: 3,
        approval_count: 1,
        flag_count: 1,
        primary_actionable_count: 3,
        workflow_item_counts: {
          "weekly_schedule_planning.v1": 2,
          "live_dispatch.v1": 2,
          "dispatch_reporting.v1": 1
        }
      }
    },
    official_outputs: {
      pointers,
      pointer_outputs: pointers.map((pointer, index) => ({
        pointer,
        artifact_version: officialOutputArtifacts[index] ?? null
      })),
      official_output_artifacts: officialOutputArtifacts,
      coherence: {
        coherence_status: "passed"
      },
      summary: {
        pointer_count: 2,
        pointer_output_count: 2,
        official_output_artifact_count: 2,
        artifact_kind_counts: {
          "planning.published_weekly_schedule.workbook": 1,
          "reporting.final_packet.workbook": 1
        }
      }
    },
    freshness: {
      latest_event_sequence: 44,
      latest_event_recorded_at: now,
      max_workflow_run_updated_at: now,
      generated_at: now
    },
    coherence: {
      official_outputs: {
        coherence_status: "passed"
      },
      handoff_edges: [
        { edge_id: "weekly_seed_to_live_dispatch", coherence_failed_count: 0 },
        { edge_id: "reporting_actuals_to_future_planning", coherence_failed_count: 0 }
      ]
    }
  };
}

export function resetApiState(): void {
  state = createContractState();
  resetEodArtifactVersions();
}

export function forceForbiddenResponses(value: boolean): void {
  state.forceForbidden = value;
}

export function mutationLog(): string[] {
  return [...state.audit.mutations];
}

export const handlers = [
  http.get("*/api/v1/workpages/demo/schedule-v0", () =>
    HttpResponse.json(scheduleWorkpageStateSnapshot.workpage_state)
  ),
  http.get("*/api/v1/workpages/demo/eod-v0", () =>
    HttpResponse.json(eodWorkpageStateSnapshot.workpage_state)
  ),
  http.post("*/api/v1/workpages/demo/eod-v0/drafts", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const version = ensureEodArtifactDraft();
    state.audit.mutations.push(`workpage-eod-draft-create:${version.artifactVersionId}`);
    return ok({
      command: "api.workpages.eod_drafts.create",
      draft: (eodArtifactCreateResponse(version).draft as Record<string, unknown>) ?? {}
    });
  }),
  http.get("*/api/v1/workpages/artifacts/:artifactVersionId", ({ params, request }) => {
    if (!inScope(request)) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_not_found",
            message: "artifact-backed workpage not found",
            details: {
              artifact_version_id: String(params.artifactVersionId)
            }
          }
        },
        { status: 404 }
      );
    }

    const artifactVersionId = String(params.artifactVersionId);
    const version = eodArtifactVersions.get(artifactVersionId);
    if (!version) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_not_found",
            message: "artifact-backed workpage not found",
            details: {
              artifact_version_id: artifactVersionId
            }
          }
        },
        { status: 404 }
      );
    }

    patchArtifactPayloadLineage(version);
    return HttpResponse.json(version.payload);
  }),
  http.post("*/api/v1/workpages/artifacts/:artifactVersionId/submit", async ({ params, request }) => {
    if (!inScope(request)) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_not_found",
            message: "artifact-backed workpage not found",
            details: {
              artifact_version_id: String(params.artifactVersionId)
            }
          }
        },
        { status: 404 }
      );
    }

    const artifactVersionId = String(params.artifactVersionId);
    const baseVersion = eodArtifactVersions.get(artifactVersionId);
    if (!baseVersion) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_not_found",
            message: "artifact-backed workpage not found",
            details: {
              artifact_version_id: artifactVersionId
            }
          }
        },
        { status: 404 }
      );
    }

    if (baseVersion.supersededByArtifactVersionId) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "workpage_artifact_conflict",
            message: "artifact-backed workpage already has a newer draft",
            details: {
              artifact_version_id: artifactVersionId,
              latest_artifact_version_id: baseVersion.latestInChainArtifactVersionId,
              workflow_run_id: baseVersion.workflowRunId,
              route: artifactRoute(baseVersion.latestInChainArtifactVersionId)
            }
          }
        },
        { status: 409 }
      );
    }

    const body = (await request.json()) as {
      form_values?: Record<string, unknown>;
      checklist_values?: Array<{
        item_id: string;
        selected: boolean;
        note: string;
      }>;
    };
    const submittedArtifactVersionId = nextEodArtifactVersionId();
    const submittedVersion = addEodArtifactVersion({
      artifactVersionId: submittedArtifactVersionId,
      workflowRunId: baseVersion.workflowRunId,
      supersedesArtifactVersionId: artifactVersionId,
      latestInChainArtifactVersionId: submittedArtifactVersionId,
      formValues:
        body.form_values && typeof body.form_values === "object" && !Array.isArray(body.form_values)
          ? body.form_values
          : {},
      checklistValues: Array.isArray(body.checklist_values) ? body.checklist_values : []
    });
    baseVersion.supersededByArtifactVersionId = submittedArtifactVersionId;
    patchArtifactPayloadLineage(baseVersion);
    updateEodArtifactChainLatest(submittedArtifactVersionId, submittedArtifactVersionId);

    state.audit.mutations.push(
      `workpage-eod-artifact-submit:${artifactVersionId}:${submittedArtifactVersionId}`
    );
    return ok({
      command: "api.workpages.artifact.submit",
      submitted: (eodArtifactSubmitResponse(submittedVersion, artifactVersionId)
        .submitted as Record<string, unknown>) ?? {}
    });
  }),
  http.get("*/api/v1/viewer", ({ request }) =>
    ok({
      command: "api.viewer.bootstrap",
      viewer_session: viewerSessionFromRequest(request)
    })
  ),

  http.get("*/api/v1/board/schedule-planning", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const taskState = url.searchParams.get("task_state");
    const assigneeActorId = url.searchParams.get("assignee_actor_id");

    const board = buildBoardContract(state);
    let cards = board.cards.slice();
    if (workflowRunId) {
      cards = cards.filter((card) => card.workflow_run_id === workflowRunId);
    }
    if (taskState) {
      cards = cards.filter((card) => card.card_type !== "human_task" || card.state === taskState);
    }
    if (assigneeActorId) {
      cards = cards.filter(
        (card) => card.card_type !== "human_task" || card.assignee_actor_id === assigneeActorId
      );
    }

    const scopedBoard = {
      ...board,
      cards,
      summary: {
        ...board.summary,
        card_count: cards.length,
        human_task_count: cards.filter((card) => card.card_type === "human_task").length,
        approval_count: cards.filter((card) => card.card_type === "approval").length
      }
    };

    return ok({
      command: "api.board.schedule_planning",
      board: scopedBoard
    });
  }),

  http.get("*/api/v1/stories/logistics-three-workflow", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const url = new URL(request.url);
    const planningWeekId = url.searchParams.get("planning_week_id");
    if (!planningWeekId) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "invalid_query_parameter",
            message: "planning_week_id is required",
            details: { parameter: "planning_week_id" }
          }
        },
        { status: 400 }
      );
    }
    const serviceDateId = url.searchParams.get("service_date_id") ?? undefined;
    return ok({
      command: "api.stories.logistics_three_workflow",
      story: buildLogisticsStoryPayload(planningWeekId, request, serviceDateId)
    });
  }),

  http.get("*/api/v1/human-tasks", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const stateFilter = url.searchParams.get("state");
    const assigneeActorId = url.searchParams.get("assignee_actor_id");

    let rows = state.humanTasks.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }
    if (assigneeActorId) {
      rows = rows.filter((row) => row.assignee_actor_id === assigneeActorId);
    }

    return ok({
      command: "api.human_tasks.list",
      human_tasks: rows.slice(offset, offset + limit).map((row) => enrichHumanTaskForResponse(row, request)),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/human-tasks/:humanTaskId", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const humanTaskId = String(params.humanTaskId);
    const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
    if (!row) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "human_task_not_found",
            message: "human task not found",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 404 }
      );
    }
    return ok({
      command: "api.human_tasks.detail",
      human_task: enrichHumanTaskForResponse(row, request)
    });
  }),

  http.get("*/api/v1/human-tasks/:humanTaskId/subgraph", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const humanTaskId = String(params.humanTaskId);
    const row = state.humanTasks.find((task) => task.human_task_id === humanTaskId);
    if (!row) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "human_task_not_found",
            message: "human task not found",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 404 }
      );
    }
    const metadata = taskSubgraphMetadata(row);
    if (!metadata.is_composite) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_subgraph_not_available",
            message: "task does not expose a composite subgraph",
            details: { human_task_id: humanTaskId, task_kind: row.task_kind }
          }
        },
        { status: 409 }
      );
    }
    const subgraph = buildTaskSubgraph(row);
    if (!subgraph) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_subgraph_not_available",
            message: "task does not expose a composite subgraph",
            details: { human_task_id: humanTaskId, task_kind: row.task_kind }
          }
        },
        { status: 409 }
      );
    }
    return ok({
      command: "api.human_tasks.subgraph",
      human_task_id: humanTaskId,
      is_composite: true,
      expansion_kind: "task_subgraph",
      subgraph
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/claim", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const actorId = request.headers.get("x-onetruth-actor-id") ?? "human:frontend-operator";
    const humanTaskId = String(params.humanTaskId);
    const okMutation = mutateTaskToClaimed(humanTaskId, actorId);
    if (!okMutation) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_not_claimable",
            message: "human task cannot be claimed",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 409 }
      );
    }

    return ok({
      command: "api.human_tasks.claim",
      human_task_id: humanTaskId,
      result: { ok: true }
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/complete", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    const okMutation = mutateTaskToCompleted(humanTaskId);
    if (!okMutation) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_not_completable",
            message: "human task cannot be completed",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 409 }
      );
    }

    return ok({
      command: "api.human_tasks.complete",
      human_task_id: humanTaskId,
      result: { ok: true }
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/confirm-review", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    const body = (await request.json()) as { reviewed_artifact_version_ids?: string[] };
    const reviewedArtifactVersionIds = Array.isArray(body.reviewed_artifact_version_ids)
      ? body.reviewed_artifact_version_ids.filter((value): value is string => typeof value === "string")
      : [];
    const confirmed = confirmTaskReview(humanTaskId, reviewedArtifactVersionIds);
    if (!confirmed) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "task_not_completable",
            message: "review confirmation requires a claimed task",
            details: { human_task_id: humanTaskId }
          }
        },
        { status: 409 }
      );
    }
    return ok({
      command: "api.human_tasks.confirm_review",
      human_task_id: humanTaskId,
      result: {
        artifact_version: confirmed.artifactVersion,
        idempotent_replay: confirmed.idempotentReplay
      }
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/stage06-agent-review", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    const task = state.humanTasks.find((row) => row.human_task_id === humanTaskId);
    if (!task) {
      return forbiddenWorkflowRun();
    }

    state.stage06ReviewedTaskIds.add(humanTaskId);
    state.audit.mutations.push(`stage06:${humanTaskId}`);
    return ok({
      command: "api.human_tasks.stage06_agent_review",
      human_task_id: humanTaskId,
      result: {
        classification: {
          outcome: "draft_is_publish_ready",
          rationale_summary: "Mock AI review result for workspace test flow",
          evidence_refs: []
        },
        completion_result: {
          ok: true
        }
      }
    });
  }),

  http.get("*/api/v1/human-tasks/:humanTaskId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const humanTaskId = String(params.humanTaskId);
    return ok({
      command: "api.human_tasks.artifacts.list",
      artifact_versions: listArtifactsForSubject("human_task", humanTaskId)
    });
  }),

  http.post("*/api/v1/human-tasks/:humanTaskId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const humanTaskId = String(params.humanTaskId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("human_task", humanTaskId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.human_tasks.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/approvals", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const stateFilter = url.searchParams.get("state");

    let rows = state.approvals.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }

    return ok({
      command: "api.approvals.list",
      approvals: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.post("*/api/v1/approvals/:approvalId/respond", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const approvalId = String(params.approvalId);
    const body = (await request.json()) as { response_kind?: string };
    const responseKind = body.response_kind ?? "approve";
    const okMutation = mutateApprovalResponse(approvalId, responseKind);
    if (!okMutation) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "approval_not_respondable",
            message: "approval cannot be responded",
            details: { approval_id: approvalId }
          }
        },
        { status: 409 }
      );
    }

    const updated = state.approvals.find((row) => row.approval_id === approvalId);
    return ok({
      command: "api.approvals.respond",
      approval_id: approvalId,
      approval: updated
    });
  }),

  http.get("*/api/v1/approvals/:approvalId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const approvalId = String(params.approvalId);
    return ok({
      command: "api.approvals.artifacts.list",
      artifact_versions: listArtifactsForSubject("approval", approvalId)
    });
  }),

  http.post("*/api/v1/approvals/:approvalId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const approvalId = String(params.approvalId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("approval", approvalId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.approvals.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/flags", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const stateFilter = url.searchParams.get("state");
    const severity = url.searchParams.get("severity");

    let rows = state.flags.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }
    if (severity) {
      rows = rows.filter((row) => row.severity === severity);
    }

    return ok({
      command: "api.flags.list",
      flags: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/flags/:flagId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const flagId = String(params.flagId);
    return ok({
      command: "api.flags.artifacts.list",
      artifact_versions: listArtifactsForSubject("flag", flagId)
    });
  }),

  http.post("*/api/v1/flags/:flagId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const flagId = String(params.flagId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("flag", flagId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.flags.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/workflow-runs", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const stateFilter = url.searchParams.get("state");

    let rows = state.workflowRuns.slice();
    if (stateFilter) {
      rows = rows.filter((row) => row.state === stateFilter);
    }

    return ok({
      command: "api.workflow_runs.list",
      workflow_runs: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/workflow-runs/:workflowRunId", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const workflowRunId = String(params.workflowRunId);
    let detail;
    try {
      detail = buildWorkflowRunDetail(state, workflowRunId);
    } catch {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.workflow_runs.detail",
      ...detail
    });
  }),

  http.get("*/api/v1/workflow-runs/:workflowRunId/workspace", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const workflowRunId = String(params.workflowRunId);
    let workspace;
    try {
      workspace = buildWorkflowRunWorkspace(state, workflowRunId);
    } catch {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.workflow_runs.workspace",
      workspace
    });
  }),

  http.get("*/api/v1/workflow-runs/:workflowRunId/artifacts", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const workflowRunId = String(params.workflowRunId);
    return ok({
      command: "api.workflow_runs.artifacts.list",
      artifact_versions: listWorkflowRunArtifacts(workflowRunId)
    });
  }),

  http.post("*/api/v1/workflow-runs/:workflowRunId/artifacts/upload", async ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const workflowRunId = String(params.workflowRunId);
    const body = (await request.json()) as Record<string, unknown>;
    const artifactVersion = addAttachmentArtifact("workflow_run", workflowRunId, body);
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.workflow_runs.artifacts.upload",
      artifact_version: artifactVersion
    });
  }),

  http.get("*/api/v1/templates", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const templates = listTemplatesFromQuery(url);
    return ok({
      command: "api.templates.list",
      registry: {
        id: "schedule_planning.template_registry",
        workflow_id: "schedule_planning.v1",
        version: 1
      },
      templates: templates.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/templates/:templateId/download.bin", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const templateId = String(params.templateId);
    const template = TEMPLATE_FIXTURES.find((item) => item.template_id === templateId);
    if (!template) {
      return HttpResponse.json(
        {
          status: "error",
          error: {
            code: "template_not_found",
            message: "template not found",
            details: { template_id: templateId }
          }
        },
        { status: 404 }
      );
    }
    state.audit.mutations.push(`template-download-bin:${templateId}`);
    return binaryDownloadResponse(templateDownloadBody(templateId), {
      fileName: template.file_name,
      mediaType: template.media_type,
      requestId: `httpreq_template_${templateId}`
    });
  }),

  http.get("*/api/v1/pointers", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");

    let rows = state.pointers.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.workflow_run_id === workflowRunId);
    }

    return ok({
      command: "api.pointers.list",
      pointers: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/timeline-events", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }

    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const eventType = url.searchParams.get("event_type");

    let rows = state.timelineEvents.slice();
    if (workflowRunId) {
      rows = rows.filter((row) => row.links.some((link) => link.id === workflowRunId));
    }
    if (eventType) {
      rows = rows.filter((row) => row.event_type === eventType);
    }

    rows.sort((a, b) => b.sequence_no - a.sequence_no);

    return ok({
      command: "api.timeline_events.list",
      events: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/artifacts", ({ request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const url = new URL(request.url);
    const { limit, offset } = parseLimitOffset(url);
    const workflowRunId = url.searchParams.get("workflow_run_id");
    const subjectKind = url.searchParams.get("subject_kind");
    const subjectId = url.searchParams.get("subject_id");

    let rows = state.artifactVersions.slice();
    if (workflowRunId) {
      rows = rows.filter((artifact) => artifact.workflow_run_id === workflowRunId);
    }
    if (subjectKind && subjectId) {
      rows = rows.filter((artifact) =>
        artifact.links?.some(
          (link) => link.subject_kind === subjectKind && link.subject_id === subjectId
        )
      );
    }

    return ok({
      command: "api.artifacts.list",
      artifact_versions: rows.slice(offset, offset + limit),
      page: { limit, offset }
    });
  }),

  http.get("*/api/v1/artifacts/:artifactVersionId/download.bin", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const artifactVersionId = String(params.artifactVersionId);
    const eodArtifactVersion = eodArtifactVersions.get(artifactVersionId);
    if (eodArtifactVersion) {
      state.audit.mutations.push(`artifact-download-bin:${artifactVersionId}`);
      return binaryDownloadResponse(artifactDownloadBody(artifactVersionId), {
        fileName: eodArtifactVersion.fileName,
        mediaType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        requestId: `httpreq_artifact_${artifactVersionId}`
      });
    }
    const artifactVersion = state.artifactVersions.find(
      (artifact) => artifact.artifact_version_id === artifactVersionId
    );
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    state.audit.mutations.push(`artifact-download-bin:${artifactVersionId}`);
    return binaryDownloadResponse(artifactDownloadBody(artifactVersionId), {
      fileName:
        (typeof artifactVersion.metadata_json?.file_name === "string" &&
        artifactVersion.metadata_json.file_name.length > 0
          ? artifactVersion.metadata_json.file_name
          : `${artifactVersionId}`),
      mediaType: artifactVersion.media_type || "application/octet-stream",
      requestId: `httpreq_artifact_${artifactVersionId}`
    });
  })
];
