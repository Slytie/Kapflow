# EVENT_EMISSION_MATRIX.md

Implementation-backed command-to-event matrix for runtime code under `src/onetruth/`.

Current scope includes TASK-0041 + TASK-0042 substrate commands plus TASK-0043 Stage06 completion-driven child spawning:
- workflow/task core lifecycle commands
- approval/artifact/pointer lifecycle commands
- Stage06 completion outcome -> child task emission mapping
- all authoritative events emitted in the same transaction as canonical state changes
- TASK-0044 HTTP adapter mutations now delegate to these same command handlers (no separate API-side event semantics)

## Minimal state set currently in code
- `workflow_runs`: `OPEN`, `COMPLETED`
- `task_runs`: `READY`, `IN_PROGRESS`, `COMPLETED`
- `human_tasks`: `OPEN`, `CLAIMED`, `COMPLETED`
- `approvals`: `PENDING`, `RESPONDED`

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
- Minimal policy check in this slice:
  - `promotion_reason=official_publish` requires `approved_by_approval_id` referencing a `RESPONDED` approval with `response_kind=approve`
- Stage06 integration note:
  - handler already supports approval-linked promotion and can be called directly from future Stage06 publish path logic

## HTTP adapter delegation (TASK-0044)
- `POST /api/v1/human-tasks/{human_task_id}/claim` delegates to `claim_human_task` semantics above.
- `POST /api/v1/human-tasks/{human_task_id}/complete` delegates to `complete_human_task` semantics above.
- `POST /api/v1/approvals/{approval_id}/respond` delegates to `respond_approval` semantics above.
- No additional event types are emitted by API routes; all authoritative events are emitted by canonical handlers within the same transaction boundary already defined in this matrix.
