# HITL_BOARD_ARCHITECTURE.md

This note defines the current board/query HTTP architecture for human-in-the-loop runtime operations.

## 1) Authority and boundaries
1. The board is a derived read/write surface over canonical runtime truth.
2. Board lane placement is server-derived from authoritative `human_tasks.state` and `approvals.state`.
3. Exception/flag work remains server-authoritative but is read via `GET /api/v1/flags` (not a client-owned state model).
4. Query surfaces are normalized, filterable, and stable, with explicit HTTP contracts documented separately.
5. Initial refresh is polling-friendly and stateless (`GET` endpoints); websocket/live-sync is deferred.
6. Mutations are thin server-side transitions over existing canonical command handlers.
7. Tenant/domain boundaries are enforced server-side for every list/detail/mutation endpoint.
8. Initial board target is Schedule Planning human-task/approval workflow plus exception visibility.

## 2) Lane derivation rules
Server board lanes:
- `human_tasks.open` for `human_tasks.state=OPEN`
- `human_tasks.claimed` for `human_tasks.state=CLAIMED`
- `approvals.pending` for `approvals.state=PENDING`
- `approvals.responded` for `approvals.state=RESPONDED`
- `human_tasks.completed` for `human_tasks.state=COMPLETED`

Frontend presentation lanes (for low-click operator scanability) are mapped in one dedicated mapper from canonical fields; they are not authoritative semantics.

## 3) Queue ordering
Default lane/card ordering policy:
- lane order: `human_tasks.open` -> `human_tasks.claimed` -> `approvals.pending` -> `approvals.responded` -> `human_tasks.completed`
- human-task cards: due date ascending, then claim timestamp, then stable ID tie-break
- approval cards: requested timestamp ascending, then responded timestamp, then stable ID tie-break

This ordering is deterministic for repeated polling reads.

## 4) Filtering dimensions
Primary filters:
- human tasks: `workflow_run_id`, `state`, `stage_id`, `task_kind`, `assignee_actor_id`, `owner_role`
- approvals: `workflow_run_id`, `state`, `approval_kind`, `required_role`
- flags: `workflow_run_id`, `state`, `kind`, `severity`, `assigned_group`
- workflow runs: `workflow_id`, `tenant_id`, `domain_id`, `state`
- pointers: `workflow_run_id`, `scope_kind`, `scope_ref`, `artifact_kind`
- board aggregate: workflow/task/approval filters reused from the above surfaces

## 5) Pagination strategy
Initial pagination uses offset/limit query parameters:
- `limit` default `100`, max `500`
- `offset` default `0`

## 6) Board aggregate composition
`GET /api/v1/board/schedule-planning` composes:
- scoped workflow run summaries (`workflow_runs[]`),
- scoped pointer summaries (`pointers[]`),
- lane metadata (`lanes[]` with deterministic order and counts),
- card rows (`cards[]`) from canonical human-task + approval queues,
- summary counts for dashboard metrics.

Flags are queried separately (`GET /api/v1/flags`) and composed in frontend presentation.

## 7) Detail-view data needs
Board/list/detail UI hydrates details through canonical endpoints:
- queue/detail aggregate: `GET /api/v1/workflow-runs/{workflow_run_id}`
- timeline feed: `GET /api/v1/timeline-events`
- scoped rows: `GET /api/v1/human-tasks`, `GET /api/v1/approvals`, `GET /api/v1/flags`, `GET /api/v1/pointers`
- inline attachments/documents:
  - list: subject-scoped artifact endpoints (`/human-tasks/{id}/artifacts`, `/approvals/{id}/artifacts`, `/flags/{id}/artifacts`, `/workflow-runs/{id}/artifacts`)
  - upload: subject-scoped artifact upload endpoints (`.../artifacts/upload`)
  - download: `GET /api/v1/artifacts/{artifact_version_id}/download`

## 8) Why frontend does not own runtime semantics
- Runtime transitions and idempotency stay in canonical handlers (`tasks claim`, `tasks complete`, `approvals respond`).
- API routes delegate to those handlers and do not reimplement lifecycle semantics.
- Board/list/detail state is always reconstructible from canonical rows + authoritative timeline events.
- This prevents creation of a second workflow engine in frontend state.
