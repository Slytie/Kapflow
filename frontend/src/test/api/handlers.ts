import { http, HttpResponse } from "msw";
import type { ArtifactVersionRow } from "@/lib/types/contracts";

import {
  buildBoardContract,
  buildWorkflowRunDetail,
  buildWorkflowRunWorkspace,
  createContractState
} from "@/test/api/contractState";

const ok = (payload: Record<string, unknown>) => HttpResponse.json({ status: "ok", ...payload });

let state = createContractState();

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

function templateContentBase64(templateId: string): string {
  if (typeof btoa === "function") {
    return btoa(`template:${templateId}`);
  }
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

function downloadedContentBase64(artifactVersionId: string): string {
  if (typeof btoa === "function") {
    return btoa(`artifact:${artifactVersionId}`);
  }
  return `artifact:${artifactVersionId}`;
}

export function resetApiState(): void {
  state = createContractState();
}

export function forceForbiddenResponses(value: boolean): void {
  state.forceForbidden = value;
}

export function mutationLog(): string[] {
  return [...state.audit.mutations];
}

export const handlers = [
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
      human_tasks: rows.slice(offset, offset + limit),
      page: { limit, offset }
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
      artifact_versions: listArtifactsForSubject("workflow_run", workflowRunId)
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

  http.get("*/api/v1/templates/:templateId/download", ({ params, request }) => {
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
    state.audit.mutations.push(`template-download:${templateId}`);
    return ok({
      command: "api.templates.download",
      template,
      content_base64: templateContentBase64(templateId),
      byte_size: 256
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

  http.get("*/api/v1/artifacts/:artifactVersionId/download", ({ params, request }) => {
    if (!inScope(request)) {
      return forbiddenWorkflowRun();
    }
    const artifactVersionId = String(params.artifactVersionId);
    const artifactVersion = state.artifactVersions.find(
      (artifact) => artifact.artifact_version_id === artifactVersionId
    );
    if (!artifactVersion) {
      return forbiddenWorkflowRun();
    }
    return ok({
      command: "api.artifacts.download",
      artifact_version: artifactVersion,
      content_base64: downloadedContentBase64(artifactVersionId),
      byte_size: artifactVersion.byte_size
    });
  })
];
