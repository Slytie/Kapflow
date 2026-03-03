# HITL_BOARD_ARCHITECTURE.md

This note defines the first board/query HTTP architecture for human-in-the-loop runtime operations.

## 1) Authority and boundaries
1. The board is a derived read/write surface over canonical runtime truth.
2. Board lane placement is derived from authoritative `human_tasks.state` and `approvals.state`, never from client-owned workflow logic.
3. Query surfaces are normalized and filterable, with stable JSON contracts documented separately.
4. Initial refresh is polling-friendly and stateless (`GET` endpoints); websocket/live-sync is explicitly deferred.
5. Mutations are thin server-side transitions over existing canonical command handlers.
6. Optimistic UI is allowed later for visual responsiveness, but authoritative truth is always the server response and canonical state.
7. Tenant/domain boundaries are enforced server-side for every list/detail/mutation endpoint.
8. Initial board target is the human-task/approval workflow for Schedule Planning, not a generalized everything-board.

## 2) Lane derivation rules
Human-task lanes:
- `human_tasks.open` for `human_tasks.state=OPEN`
- `human_tasks.claimed` for `human_tasks.state=CLAIMED`
- `human_tasks.completed` for `human_tasks.state=COMPLETED`

Approval lanes:
- `approvals.pending` for `approvals.state=PENDING`
- `approvals.responded` for `approvals.state=RESPONDED`

No client-side lane logic is authoritative. Lanes are a server-derived projection over canonical rows.

## 3) Queue ordering
Default lane/card ordering policy:
- lane order: `open` -> `claimed` -> `approvals.pending` -> `approvals.responded` -> `completed`
- human-task cards: due date ascending, then claim timestamp, then stable ID tie-break
- approval cards: requested timestamp ascending, then responded timestamp, then stable ID tie-break

This ordering is deterministic for repeated polling reads.

## 4) Filtering dimensions
Read endpoints support practical filters without introducing new semantics.

Primary filters:
- human tasks: `workflow_run_id`, `state`, `stage_id`, `task_kind`, `assignee_actor_id`, `owner_role`
- approvals: `workflow_run_id`, `state`, `approval_kind`, `required_role`
- workflow runs: `workflow_id`, `tenant_id`, `domain_id`, `state`
- pointers: `workflow_run_id`, `scope_kind`, `scope_ref`, `artifact_kind`
- board aggregate: workflow/task/approval/scope filters reused from the above surfaces

## 5) Pagination strategy
Initial pagination uses offset/limit query parameters:
- `limit` default `100`, max `500`
- `offset` default `0`

This is intentionally simple and stable for the first board/API slice.

## 6) Why frontend does not own runtime semantics
- Runtime transitions and idempotency stay in canonical handlers (`tasks claim`, `tasks complete`, `approvals respond`).
- API routes delegate to those handlers; they do not reimplement lifecycle semantics.
- Board state is therefore always reconstructible from canonical rows + authoritative timeline events.
- This prevents creation of a second workflow engine in frontend state.
