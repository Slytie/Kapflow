import { http, HttpResponse } from "msw";

import { buildBoardContract, buildWorkflowRunDetail, createContractState } from "@/test/api/contractState";

const ok = (payload: Record<string, unknown>) => HttpResponse.json({ status: "ok", ...payload });

let state = createContractState();

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
  })
];
