# HITL_HTTP_API_CONTRACTS.md

Stable HTTP contracts for the thin HITL adapter over canonical runtime/query surfaces.

These contracts are:
- server-authoritative projections over canonical runtime truth,
- machine-parseable JSON for board/list/detail UIs,
- intentionally narrow to avoid a duplicate semantics layer.

## 1) Base path and request context headers
Base path:
- `/api/v1`

Required request headers:
- `x-onetruth-tenant-id`
- `x-onetruth-domain-id`
- `x-onetruth-actor-id`
- `x-onetruth-actor-type` (`human|agent|service|system`)
- `x-onetruth-actor-roles` (comma-separated)

Scope enforcement:
- every request is filtered/validated by `(tenant_id, domain_id)` from headers,
- cross-scope detail/mutation attempts fail closed,
- there is no global/unscoped fallback.

## 2) Response envelopes
Success:
- `{"status":"ok", ...}`

Error:
- `{"status":"error","error":{"code":"...","message":"...","details":{...}}}`

## 3) Read endpoint contracts
### 3.1 Human task queue
Endpoint:
- `GET /api/v1/human-tasks`

Filters:
- `workflow_run_id`, `state`, `stage_id`, `task_kind`, `assignee_actor_id`, `owner_role`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.human_tasks.list","human_tasks":[...],"page":{"limit":100,"offset":0}}`

Human-task row shape (`human_tasks[]`):
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
- `spawned_from_flag_id`

### 3.2 Approval queue
Endpoint:
- `GET /api/v1/approvals`

Filters:
- `workflow_run_id`, `state`, `approval_kind`, `required_role`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.approvals.list","approvals":[...],"page":...}`

Approval row shape (`approvals[]`):
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

### 3.3 Flag/issue queue
Endpoint:
- `GET /api/v1/flags`

Filters:
- `workflow_run_id`, `state`, `kind`, `severity`, `assigned_group`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.flags.list","flags":[...],"page":...}`

Flag row shape (`flags[]`):
- `flag_id`
- `workflow_run_id`
- `tenant_id`
- `domain_id`
- `workflow_id`
- `partition_key`
- `kind`
- `severity`
- `state`
- `summary`
- `details_json`
- `assigned_group`
- `created_at`
- `closed_at`
- `created_by_actor_id`
- `created_by_actor_type`
- `source_event_id`
- `dedupe_key`
- `updated_at`

### 3.4 Workflow run summaries
Endpoint:
- `GET /api/v1/workflow-runs`

Filters:
- `workflow_id`, `tenant_id`, `domain_id`, `state`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.workflow_runs.list","workflow_runs":[...],"page":...}`

Workflow run summary row shape:
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
- `active_issue_count`

### 3.5 Workflow run detail
Endpoint:
- `GET /api/v1/workflow-runs/{workflow_run_id}`

Response:
- `{"status":"ok","command":"api.workflow_runs.detail","workflow_run":{...},"human_tasks":[...],"approvals":[...],"artifact_versions":[...],"pointers":[...],"flags":[...],"summary":{...}}`

### 3.6 Timeline feed
Endpoint:
- `GET /api/v1/timeline-events`

Filters:
- `workflow_run_id`, `event_type`, `since_sequence_no`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.timeline_events.list","events":[...],"page":...}`

Timeline row shape (`events[]`):
- `sequence_no`
- `event_id`
- `event_type`
- `occurred_at`
- `recorded_at`
- `tenant_id`
- `domain_id`
- `actor`
- `links`
- `payload`

### 3.7 Pointer/current-official summaries
Endpoint:
- `GET /api/v1/pointers`

Filters:
- `workflow_run_id`, `scope_kind`, `scope_ref`, `artifact_kind`, `limit`, `offset`

Response:
- `{"status":"ok","command":"api.pointers.list","pointers":[...],"page":...}`

Pointer row shape:
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

### 3.8 Schedule-planning board aggregate
Endpoint:
- `GET /api/v1/board/schedule-planning`

Common filters:
- `workflow_run_id`, `workflow_id`, `workflow_state`
- task filters: `stage_id`, `task_kind`, `task_state`, `assignee_actor_id`, `owner_role`
- approval filters: `approval_state`, `approval_kind`, `required_role`
- pointer filters: `scope_kind`, `scope_ref`, `artifact_kind`
- pagination: `limit`, `offset`

Response:
- `{"status":"ok","command":"api.board.schedule_planning","board":{...}}`

Board object shape:
- `board_id`
- `filters`
- `lanes[]` (`lane`, `label`, `position`, `card_count`)
- `cards[]` (`card_type`: `human_task|approval`)
- `page`
- `workflow_runs[]`
- `pointers[]`
- `summary`

### 3.9 Artifact/document rows and downloads
Endpoints:
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/{artifact_version_id}`
- `GET /api/v1/artifacts/{artifact_version_id}/download`

Subject-linked read endpoints:
- `GET /api/v1/human-tasks/{human_task_id}/artifacts`
- `GET /api/v1/approvals/{approval_id}/artifacts`
- `GET /api/v1/flags/{flag_id}/artifacts`
- `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts`

List filters (`GET /api/v1/artifacts`):
- `workflow_run_id`, `subject_kind`, `subject_id`, `artifact_kind`, `limit`, `offset`

Artifact row shape (`artifact_versions[]`):
- `artifact_version_id`
- `workflow_run_id`
- `task_run_id`
- `artifact_kind`
- `artifact_role`
- `media_type`
- `storage_uri`
- `content_digest`
- `byte_size`
- `metadata_json`
- `parent_artifact_version_id`
- `supersedes_artifact_version_id`
- `lineage_note`
- `created_at`
- `links[]` (`artifact_version_id`, `workflow_run_id`, `subject_kind`, `subject_id`, `relation_kind`, `created_at`, `created_by_actor_id`, `created_by_actor_type`)

Download response:
- `{"status":"ok","command":"api.artifacts.download","artifact_version":{...},"content_base64":"...","byte_size":123}`

Notes:
- downloads are artifact-backed (no alternate file subsystem),
- subject endpoints are convenience views over canonical `artifact_links`.

## 4) Mutation endpoint contracts
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

### 4.4 Upload artifact/document attachment
Endpoints:
- `POST /api/v1/artifacts/ingest`
- `POST /api/v1/human-tasks/{human_task_id}/artifacts/upload`
- `POST /api/v1/approvals/{approval_id}/artifacts/upload`
- `POST /api/v1/flags/{flag_id}/artifacts/upload`
- `POST /api/v1/workflow-runs/{workflow_run_id}/artifacts/upload`

Body (subject upload):
- `artifact_kind`
- `artifact_role`
- `file_name`
- `media_type` (optional)
- `content_base64` or `source_path` (dev/local)
- `metadata_json` (optional)
- `relation_kind` (optional, default `attachment`)
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.<subject>.artifacts.upload","subject_kind":"...","subject_id":"...","artifact_version":{...},"ingress":{...}}`

Rules:
- upload creates canonical immutable artifact versions and emits authoritative events,
- no mutable/secondary attachment store is allowed,
- scope checks apply to subject and workflow ownership before upload.

### 4.5 Run bounded Stage06 OpenAI review sandbox
Endpoint:
- `POST /api/v1/human-tasks/{human_task_id}/stage06-agent-review`

Body:
- `idempotency_key`

Response:
- `{"status":"ok","command":"api.human_tasks.stage06_agent_review","human_task_id":"...","result":{...}}`

Result shape (`result`):
- `classification` (`outcome`, `rationale_summary`, `evidence_refs`, `suggested_follow_on_task_kind`)
- `model_metadata` (`response_id`, `request_id`, `model`, `usage`, `attempts`, `requested_at`, `completed_at`)
- `input_artifacts` (canonical input artifact refs used for model context)
- `evidence_artifact` (canonical artifact-version row for captured model evidence)
- `completion_result` (canonical `tasks.complete` result including spawned children)

Rules:
- this endpoint is intentionally narrow to Stage06 `review_packet` tasks,
- model output is schema-constrained and used only to select existing canonical completion outcome values,
- follow-on workflow truth is emitted only via existing completion/spawn handlers (no API-side workflow semantics).

## 5) Semantic rule
These HTTP contracts expose canonical state and transitions. They do not create a second semantics layer, and they do not make client-side workflow logic authoritative.
