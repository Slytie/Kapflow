# EVENT_EMISSION_MATRIX.md

Implementation-backed command-to-event matrix for runtime code under `src/onetruth/`.

Current scope includes TASK-0041 + TASK-0042 substrate commands plus TASK-0043/TASK-0045 business-slice completion-driven child spawning:
- workflow/task core lifecycle commands
- approval/artifact/pointer lifecycle commands
- Stage06 completion outcome -> child task emission mapping
- Stage07 flag/issue lifecycle + lease recovery/reconcile mappings
- all authoritative events emitted in the same transaction as canonical state changes
- TASK-0044/TASK-0049 HTTP adapter mutations now delegate to these same command handlers (no separate API-side event semantics)
- TASK-0047 frontend snapshot export is a derived read-only workflow over scenario runs and emits no additional authoritative event types
- TASK-0051 document-corpus ingress + attachment upload paths now delegate to canonical artifact-version creation semantics (no attachment-side event fork)

## Minimal state set currently in code
- `workflow_runs`: `OPEN`, `COMPLETED`
- `task_runs`: `READY`, `IN_PROGRESS`, `COMPLETED`
- `human_tasks`: `OPEN`, `CLAIMED`, `COMPLETED`
- `approvals`: `PENDING`, `RESPONDED`
- `flags`: `open`, `triage`, `blocked`, `resolved`, `closed`, `waived`

## create_workflow_run (`runs create`)
- Canonical rows mutated:
  - `workflow_runs` insert
- Events emitted:
  - `workflow.run.created`
- Transaction rule:
  - row insert + event append commit atomically
- Idempotency behavior:
  - optional command `idempotency_key` maps to `runs.create.workflow.run.created`
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
  - duplicate scoped activation key fails explicitly (`duplicate_workflow_activation`)
- Race/conflict behavior:
  - scoped unique constraint enforces one activation winner per scope
- Stage06 integration note:
  - provides stable workflow scope IDs used by downstream task/approval/artifact/pointer commands

## create_task_run (`tasks create`)
- Canonical rows mutated:
  - `task_runs` insert
  - optional `human_tasks` insert when `create_human_task=true`
- Events emitted:
  - always `task.run.created`
  - `task.created` when `create_human_task=true`
- Transaction rule:
  - task row(s) + emitted event(s) commit atomically
- Idempotency behavior:
  - optional command `idempotency_key` maps to:
    - `tasks.create.task.run.created`
    - `tasks.create.task.created` (when human task is created)
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
  - duplicate activation key in workflow scope fails explicitly (`duplicate_task_activation`)
- Race/conflict behavior:
  - uniqueness on `(workflow_run_id, activation_key)` prevents duplicate task-run creation
- Stage06 integration note:
  - lineage/spawn columns already exist for future child-task evaluator extension

## claim_human_task (`tasks claim`)
- Canonical rows mutated:
  - `human_tasks` `OPEN -> CLAIMED` + assignee/lease metadata
  - `task_runs` `READY -> IN_PROGRESS` when applicable
- Events emitted:
  - `task.claimed`
  - `task.run.state_changed` when task-run state transitions
- Transaction rule:
  - claim updates + emitted event(s) commit atomically
- Idempotency behavior:
  - command `idempotency_key` required by payload contract
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - racing claims fail closed; exactly one claim can win
- Stage06 integration note:
  - ownership/lease semantics are stable for future board-driven work routing

## complete_human_task (`tasks complete`)
- Canonical rows mutated:
  - `human_tasks` `CLAIMED -> COMPLETED`
  - parent `task_runs` `IN_PROGRESS|READY -> COMPLETED`
  - optional child `task_runs` insert (explicit follow-on task run)
  - optional child `human_tasks` insert (claimable follow-on human task)
- Events emitted:
  - `task.completed`
  - `task.run.state_changed`
  - optional `task.run.created` (child follow-on task)
  - optional `task.created` (child follow-on human task)
- Transaction rule:
  - parent completion updates, optional child inserts, and all emitted events commit atomically in one transaction
- Idempotency behavior:
  - command `idempotency_key` required by payload contract
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - completion is rejected unless task is claimed by the completing actor (`task_not_completable`)
  - duplicate spawned-child activation key fails closed (`duplicate_spawned_task_activation`)
- Stage06 completion outcome mapping now in code:
  - `review_requires_more_information` -> child `Stage06` / `information_request` / `spawn_rule_id=stage06_request_missing_information`
  - `review_requests_changes` -> child `Stage05` / `work_item` / `spawn_rule_id=stage06_request_changes_to_draft`
  - `draft_is_publish_ready` -> child `Stage06` / `final_review` / `spawn_rule_id=stage06_final_publish_review`
- Child lineage fields persisted now:
  - `spawned_from_task_run_id`
  - `spawn_rule_id`
  - `spawn_cause_kind=task_completion`
  - `spawn_cause_event_id` (parent `task.completed` event id)
  - `spawn_depth`
  - `spawn_budget_key`
- Stage06 integration note:
  - this command is now the implementation-backed Stage06 spawn boundary and remains lineage-ready for a future broader spawn evaluator without adding a second truth path

## request_approval (`approvals request`)
- Canonical rows mutated:
  - `approvals` insert with `state=PENDING`
- Events emitted:
  - `approval.requested`
- Transaction rule:
  - approval insert + event append commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - key maps to `approvals.request.approval.requested`
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - duplicate `approval_id` fails explicitly (`duplicate_approval_id`)
- Stage06 integration note:
  - approval rows now provide canonical decision objects that can gate publish/promote operations

## respond_approval (`approvals respond`)
- Canonical rows mutated:
  - `approvals` atomic transition `PENDING -> RESPONDED`
  - response verb, rationale, decision actor, responded timestamp, generation increment
- Events emitted:
  - `approval.responded`
- Transaction rule:
  - approval transition + event append commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - key maps to `approvals.respond.approval.responded`
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - second/conflicting response is rejected explicitly (`approval_not_respondable`)
- Stage06 integration note:
  - response outcome is now auditable and linkable to pointer promotion authorization

## create_artifact_version (`artifacts create-version`)
- Canonical rows mutated:
  - `artifact_versions` immutable insert
- Events emitted:
  - `artifact.version.created`
- Transaction rule:
  - artifact-version insert + event append commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - key maps to `artifacts.create-version.artifact.version.created`
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - duplicate `artifact_version_id` fails explicitly (`duplicate_artifact_version_id`)
- Stage06 integration note:
  - establishes canonical immutable version rows used by publish/promotion flows

## ingest_artifact_document (`artifacts ingest`, `artifacts seed-corpus`, subject upload endpoints)
- Canonical rows mutated:
  - `artifact_versions` immutable insert
  - optional `artifact_links` inserts for linked subjects (`workflow_run`, `human_task`, `approval`, `flag`)
- Events emitted:
  - `artifact.version.created`
- Transaction rule:
  - blob ingress metadata, artifact insert, optional link inserts, and event append commit atomically through canonical artifact handler
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - duplicate `artifact_version_id` fails explicitly (`duplicate_artifact_version_id`)
  - invalid cross-scope subject links fail closed (`cross_scope_*_mismatch`)
- Integration note:
  - this is the canonical path for example-document corpus seeding and inline attachment uploads; no second attachment truth model exists

## promote_pointer (`pointers promote`)
- Canonical rows mutated:
  - `artifact_pointers` insert on first promotion for `(workflow_run_id, pointer_key)`
  - optional update on repoint when `expected_generation` is supplied and matches
- Events emitted:
  - `artifact.pointer.promoted`
  - `artifact.pointer.drift_detected` when `reviewed_artifact_version_id` differs from promoted version
- Transaction rule:
  - pointer mutation + emitted event(s) commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - key maps to:
    - `pointers.promote.artifact.pointer.promoted`
    - `pointers.promote.artifact.pointer.drift_detected` (when drift event is emitted)
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - first promotion wins for an uninitialized pointer key
  - conflicting promotion without `expected_generation` fails closed (`pointer_conflict`)
  - repoint requires optimistic generation match; mismatch fails explicitly (`pointer_generation_mismatch`)
  - pointer scope/kind mismatch on same key fails explicitly (`pointer_definition_mismatch`)
- Minimal policy checks in this slice:
  - `promotion_reason=official_publish` requires `approved_by_approval_id` referencing a `RESPONDED` approval with `response_kind=approve`
  - `promotion_reason=official_major_replan` requires the same approved response and a Stage07-scoped approval (`scope_ref=Stage07`)
- Stage07 drift visibility rule:
  - when `reviewed_base_artifact_version_id` is supplied, drift is computed against the current base pointer target (`base_pointer_key`, default `official:schedule.published_schedule.workbook`)
  - stale reviewed base emits `artifact.pointer.drift_detected` while allowing promotion (visibility-required policy)
- Stage06 integration note:
  - handler already supports approval-linked promotion and can be called directly from future Stage06 publish path logic

## Stage07 additions (TASK-0045)
### create_flag (`flags create`)
- Canonical rows mutated:
  - `flags` insert
- Events emitted:
  - `flag.created`
- Transaction rule:
  - canonical insert + event append commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - key maps to `flags.create.flag.created`
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
  - duplicate workflow dedupe key fails explicitly (`duplicate_flag_dedupe`)
- Race/conflict behavior:
  - duplicate `flag_id` fails explicitly (`duplicate_flag_id`)

### transition_flag_state (`flags transition`)
- Canonical rows mutated:
  - `flags` state transition + close timestamp updates when terminal
- Events emitted:
  - `flag.state_changed`
- Transaction rule:
  - canonical transition + event append commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - key maps to `flags.transition.flag.state_changed`
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)
- Race/conflict behavior:
  - illegal transitions fail closed (`illegal_flag_transition`)
  - transition races fail explicitly (`flag_transition_conflict`)

### activate_stage07_issue_from_flag (`stage07 activate-issue`)
- Canonical rows mutated:
  - `task_runs` insert (Stage07 `exception_triage`) with `spawned_from_flag_id`
  - `human_tasks` insert (OPEN) for claimable issue triage
- Events emitted:
  - `task.run.created`
  - `task.created`
- Transaction rule:
  - task/human inserts + emitted events commit atomically
- Idempotency / dedupe behavior:
  - activation dedupe key is activation key `(workflow_run_id, flag_id, task_kind, generation)`
  - repeated wakeups/retries return existing canonical row (`deduped=true`) and do not duplicate events
  - optional command `idempotency_key` maps to:
    - `stage07.activate-issue.task.run.created`
    - `stage07.activate-issue.task.created`
- Race/conflict behavior:
  - activation unique constraint prevents duplicate roots for same issue generation
  - cross-workflow flag references fail closed

### complete_human_task Stage07 outcomes (`tasks complete`)
- Canonical rows mutated:
  - same parent completion transitions as core path
  - optional Stage07 child task/human inserts on supported outcomes
- Additional Stage07 outcome mapping:
  - `replan_requires_missing_information` -> child Stage07 `information_request` (`stage07_request_issue_information`)
  - `resolution_creates_child_issue` -> child Stage07 `exception_triage` (`stage07_follow_on_exception_triage`)
  - `major_replan_is_ready_for_review` -> child Stage07 `final_review` (`stage07_final_replan_review`)
- Same-transaction rule:
  - parent completion + child creation + authoritative events commit atomically
- Dedupe/bounds behavior:
- retries with same completion idempotency key fail explicit (`duplicate_idempotency_key`) with no duplicate children
- Stage07 spawn depth and per-issue child budget are bounded in service policy

## Execution-session runtime hardening (TASK-0052)
### create_execution_session (`execution-sessions create`)
- Canonical rows mutated:
  - `execution_sessions` insert
- Events emitted:
  - `execution.session.created`
  - `execution.session.state_changed` (when initial state is not `CREATED`)
- Transaction rule:
  - row insert + event append commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - duplicate idempotency fails explicitly (`duplicate_idempotency_key`)

### request_tool_execution (`tool-executions request`)
- Canonical rows mutated:
  - `tool_executions` insert (`REQUESTED`)
  - `execution_sessions.tool_call_count` increment
- Events emitted:
  - `tool.execution.requested`
- Transaction rule:
  - request row + counter update + event append commit atomically
- Idempotency behavior:
  - non-empty command `idempotency_key` required
  - per-session duplicate tool idempotency key dedupes to existing row (no duplicate event)

### evaluate_policy_decision (handler-internal in Stage06 path)
- Canonical rows mutated:
  - `policy_decisions` insert
  - `tool_executions.state` -> `APPROVED` or `DENIED`
  - optional `execution_sessions.state` transition (`FAILED`/`WAITING_APPROVAL` on non-allow)
- Events emitted:
  - `tool.execution.approved` or `tool.execution.denied`
  - optional `execution.session.state_changed`
- Transaction rule:
  - policy row + tool/session transitions + event append commit atomically
- Idempotency behavior:
  - non-empty idempotency key required
  - duplicate idempotency key fails explicitly (`duplicate_idempotency_key`)

### complete_tool_execution (handler-internal in Stage06/reconcile paths)
- Canonical rows mutated:
  - `tool_executions.state` -> `COMPLETED` / `FAILED` / `CANCELED`
  - output artifact IDs + completion/error metadata persisted
- Events emitted:
  - `tool.execution.completed` (`payload.result` = `succeeded|failed|canceled`)
- Transaction rule:
  - tool transition + event append commit atomically
- Idempotency behavior:
  - non-empty idempotency key required
  - duplicate idempotency fails explicitly

### transition_execution_session_state (`execution-sessions transition`)
- Canonical rows mutated:
  - `execution_sessions.state` (+ `closed_at` for terminal states)
- Events emitted:
  - `execution.session.state_changed`
- Transaction rule:
  - session transition + event append commit atomically
- Idempotency behavior:
  - non-empty idempotency key required
  - duplicate idempotency fails explicitly

### run_stage06_openai_review_sandbox (`POST /api/v1/human-tasks/{id}/stage06-agent-review`)
- Canonical rows mutated:
  - `execution_sessions` create/transition
  - `tool_executions` request/approve-or-deny/complete
  - `policy_decisions` allow/deny record
  - `artifact_versions` evidence insert (`schedule.stage06.review_ai_evidence.json`) when model call is allowed and succeeds
  - standard `human_tasks` + `task_runs` completion/spawn mutations through `complete_human_task`
- Events emitted:
  - execution lifecycle: `execution.session.created`, `execution.session.state_changed`
  - tool lifecycle: `tool.execution.requested`, `tool.execution.approved|denied`, `tool.execution.completed` (allowed/failure/reconcile paths)
  - evidence + workflow lifecycle: `artifact.version.created`, then `task.completed` / `task.run.state_changed` (+ optional child spawn events)
- Transaction rule:
  - each canonical mutation step is committed through existing command transaction boundaries
  - no non-canonical side channel is used
- Idempotency / retry behavior:
  - API base `idempotency_key` expands into bounded sub-keys for session/tool/policy/evidence/complete transitions
  - deterministic execution IDs derived from `(workflow_run_id, task_run_id, base_idempotency_key)` prevent duplicate canonical effects on replay
  - replay of the same base key fails closed (`duplicate_execution_request`)
- Policy behavior:
  - policy decision is explicit and persisted before model/tool execution
  - denied/require-approval paths emit canonical denial evidence and skip model execution
  - allowed path emits completion evidence and proceeds through canonical task completion

### sweep_leases (`maintenance sweep-leases`)
- Canonical rows mutated:
  - reopen expired claimed `human_tasks` rows
  - optional `task_runs` `IN_PROGRESS -> READY`
- Events emitted:
  - `task.lease_expired`
  - `task.run.state_changed` (when task run reopened)
- Transaction rule:
  - reopen transitions + event append commit atomically
- Recovery behavior:
  - chosen policy in this slice is reopen-same-row (no escalation child task)

### reconcile_stage07 (`maintenance reconcile-stage07`)
- Canonical rows mutated:
  - none when deduped
  - otherwise delegates to Stage07 activation command to create missing issue root task/human rows
- Events emitted:
  - none on no-op dedupe
  - on create, same events as activation (`task.run.created`, `task.created`)
- Transaction rule:
  - each activation attempt uses canonical activation transaction semantics
- Recovery behavior:
  - dropped wakeups are repaired without duplicating root issue tasks

### reconcile_executions (`maintenance reconcile-executions`)
- Canonical rows mutated:
  - stale `tool_executions` in open states transition to `FAILED`
  - stale `execution_sessions` in open states transition to `FAILED`
- Events emitted:
  - `tool.execution.completed` (`result=failed`, timeout reason)
  - `execution.session.state_changed` (`reason=reconcile_timeout`)
- Transaction rule:
  - reconcile updates and emitted events for each processed session commit atomically
- Recovery behavior:
  - stale partial sessions are failed with visible evidence
  - repeated reconcile runs do not duplicate terminal effects

## HTTP adapter delegation (TASK-0044/TASK-0049)
- `POST /api/v1/human-tasks/{human_task_id}/claim` delegates to `claim_human_task` semantics above.
- `POST /api/v1/human-tasks/{human_task_id}/complete` delegates to `complete_human_task` semantics above.
- `POST /api/v1/human-tasks/{human_task_id}/stage06-agent-review` delegates to bounded Stage06 sandbox service + canonical handlers above.
- `POST /api/v1/approvals/{approval_id}/respond` delegates to `respond_approval` semantics above.
- `POST /api/v1/flags/{flag_id}/transition` delegates to `transition_flag_state` semantics above.
- `POST /api/v1/artifacts/ingest` delegates to `ingest_artifact_document` semantics above.
- `POST /api/v1/human-tasks/{human_task_id}/artifacts/upload` delegates to `ingest_artifact_document` semantics above.
- `POST /api/v1/approvals/{approval_id}/artifacts/upload` delegates to `ingest_artifact_document` semantics above.
- `POST /api/v1/flags/{flag_id}/artifacts/upload` delegates to `ingest_artifact_document` semantics above.
- `POST /api/v1/workflow-runs/{workflow_run_id}/artifacts/upload` delegates to `ingest_artifact_document` semantics above.
- No additional event types are emitted by API routes; all authoritative events are emitted by canonical handlers within the same transaction boundary already defined in this matrix.
