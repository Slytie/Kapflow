# HITL_HTTP_API_CONTRACTS.md

Stable HTTP contracts for the first HITL board/query adapter.

These contracts are:
- thin adapter surfaces over canonical runtime truth,
- derived/query-friendly views,
- machine-parseable JSON intended for parallel frontend/Kanban work.

## 1) Base URL and headers
Base path:
- `/api/v1`

Required request headers (current internal/dev auth-context model):
- `x-onetruth-tenant-id`
- `x-onetruth-domain-id`
- `x-onetruth-actor-id`
- `x-onetruth-actor-type` (`human|agent|service|system`)
- `x-onetruth-actor-roles` (comma-separated roles)

Scope enforcement:
- every endpoint is server-filtered by `(tenant_id, domain_id)` from headers,
- cross-scope detail/mutation requests are denied as not found,
- there is no unscoped/global read fallback.

## 2) Response envelopes
Success envelope:
- `{"status":"ok", ...}`

Error envelope:
- `{"status":"error","error":{"code":"...","message":"...","details":{...}}}`

## 3) Read contracts
### 3.1 Human task rows
Endpoint:
- `GET /api/v1/human-tasks`

Filters:
- `workflow_run_id`, `state`, `stage_id`, `task_kind`, `assignee_actor_id`, `owner_role`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.human_tasks.list","human_tasks":[...],"page":{"limit":100,"offset":0}}`

Row shape (`human_tasks[]`):
- `human_task_id`
- `workflow_run_id`
- `task_run_id`
- `task_kind`
- `state`
- `candidate_roles`
- `owner_role`
- `assignee_actor_id`
- `assignee_actor_type`
- `due_at`
- `escalation_at`
- `lease_version`
- `claimed_at`
- `claimed_until`
- `linked_approval_id`
- `reopen_count`
- `generation`
- `created_at`
- `updated_at`
- `task_run_state`
- `stage_id`
- `blocked_on_kind`
- `blocked_on_ref`

### 3.2 Approval rows
Endpoint:
- `GET /api/v1/approvals`

Filters:
- `workflow_run_id`, `state`, `approval_kind`, `required_role`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.approvals.list","approvals":[...],"page":...}`

Row shape (`approvals[]`):
- `approval_id`
- `workflow_run_id`
- `task_run_id`
- `approval_kind`
- `scope_kind`
- `scope_ref`
- `state`
- `requested_by_task_run_id`
- `candidate_roles`
- `required_role`
- `requested_at`
- `responded_at`
- `response_kind`
- `response_reason`
- `decided_by_actor_id`
- `decided_by_actor_type`
- `generation`
- `created_at`
- `updated_at`

### 3.3 Workflow run summary rows
Endpoint:
- `GET /api/v1/workflow-runs`

Filters:
- `workflow_id`, `tenant_id`, `domain_id`, `state`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.workflow_runs.list","workflow_runs":[...],"page":...}`

Row shape (`workflow_runs[]`):
- `workflow_run_id`
- `workflow_id`
- `workflow_version`
- `tenant_id`
- `domain_id`
- `partition_key`
- `logical_date`
- `activation_key`
- `state`
- `created_at`
- `updated_at`

### 3.4 Workflow run detail
Endpoint:
- `GET /api/v1/workflow-runs/{workflow_run_id}`

Response:
- `{"status":"ok","command":"api.workflow_runs.detail","workflow_run":{...},"human_tasks":[...],"approvals":[...],"artifact_versions":[...],"pointers":[...],"summary":{...}}`

### 3.5 Pointer/current-official rows
Endpoint:
- `GET /api/v1/pointers`

Filters:
- `workflow_run_id`, `scope_kind`, `scope_ref`, `artifact_kind`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.pointers.list","pointers":[...],"page":...}`

Row shape (`pointers[]`):
- `workflow_run_id`
- `pointer_key`
- `scope_kind`
- `scope_ref`
- `artifact_kind`
- `artifact_version_id`
- `promotion_reason`
- `promoted_by_task_run_id`
- `approved_by_approval_id`
- `generation`
- `updated_at`

### 3.6 Schedule Planning board aggregate
Endpoint:
- `GET /api/v1/board/schedule-planning`

Common filters:
- `workflow_run_id`, `workflow_id`, `stage_id`, `task_kind`, `task_state`, `approval_state`, `approval_kind`, `required_role`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.board.schedule_planning","board":{...}}`

Board object shape:
- `board_id`
- `filters`
- `lanes[]`:
  - `lane`
  - `label`
  - `position`
  - `card_count`
- `cards[]` (mixed `human_task` and `approval` rows)
- `page`
- `workflow_runs[]`
- `pointers[]`
- `summary`

Board card contract (minimum fields for Taiga-style board/list/detail rendering):
- `card_id`
- `card_type` (`human_task` or `approval`)
- `lane`
- `title`
- `workflow_run_id`
- `workflow_id`
- `task_kind` (human-task cards)
- `stage_id` (human-task cards)
- `state`
- `owner_role`
- `assignee_actor_id`
- `assignee_actor_type`
- `due_at`
- `claimed_at`
- `claimed_until`
- `blocked_on_kind`
- `blocked_on_ref`
- `linked_approval_count` / `linked_approval_states` (human-task cards)
- `approval_kind` / `required_role` / `requested_at` / `response_kind` (approval cards)

## 4) Mutation contracts
### 4.1 Claim human task
Endpoint:
- `POST /api/v1/human-tasks/{human_task_id}/claim`

Body:
- `lease_seconds`
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.human_tasks.claim","human_task_id":"...","result":{...}}`

### 4.2 Complete human task
Endpoint:
- `POST /api/v1/human-tasks/{human_task_id}/complete`

Body:
- `outcome`
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.human_tasks.complete","human_task_id":"...","result":{...}}`

### 4.3 Respond approval
Endpoint:
- `POST /api/v1/approvals/{approval_id}/respond`

Body:
- `response_kind`
- `response_reason`
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.approvals.respond","approval_id":"...","approval":{...}}`

## 5) Semantic rule
These HTTP contracts expose canonical state and transitions. They do not create a second semantics layer, and they do not make client-side workflow logic authoritative.
