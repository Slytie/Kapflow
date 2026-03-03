# DECISIONS_SINCE_LAST.md

Record any decisions made since the last session so a fresh Codex run can rehydrate quickly.

## 2026-03-03 (Stage07 issue-scoped replan loop)
- Added canonical `flags` substrate with runtime states `open`, `triage`, `blocked`, `resolved`, `closed`, `waived`; transitions are enforced server-side and recorded via `flag.created` / `flag.state_changed`.
- Chosen Stage07 issue activation key and dedupe model: `(workflow_run_id, flag_id, task_kind, generation)`; duplicate wakeups/activation retries return existing canonical issue task instead of creating a second root issue task.
- Implemented Stage07 completion outcome mappings in the authoritative `tasks complete` transaction path:
  - `replan_requires_missing_information` -> Stage07 `information_request`
  - `resolution_creates_child_issue` -> Stage07 `exception_triage`
  - `major_replan_is_ready_for_review` -> Stage07 `final_review`
- Chosen major-replan approval gate: `pointers.promote` with `promotion_reason=official_major_replan` requires a canonical approved response and Stage07 approval scope; otherwise promotion fails closed.
- Chosen drift-detection rule for Stage07 promotion: compare `reviewed_base_artifact_version_id` against the current base pointer target (`base_pointer_key`, defaulting to `official:schedule.published_schedule.workbook`); emit `artifact.pointer.drift_detected` when stale, while allowing promotion.
- Chosen lease-expiry recovery behavior: reopen the same claimed human-task row (clear assignee/lease, increment reopen counters/version), emit `task.lease_expired`, and move task run `IN_PROGRESS -> READY` with `task.run.state_changed` evidence.
- Added Stage07 reconcile path to recover dropped wakeups by ensuring open flags have issue-root tasks via activation-key dedupe, without duplicating canonical root tasks.

## 2026-03-03 (HITL HTTP/query adapter + backlog reconciliation)
- Added the first thin HTTP adapter over canonical runtime/query surfaces under `src/onetruth/api/`; API routes delegate mutation semantics to existing canonical handlers (`claim_human_task_command`, `complete_human_task_command`, `respond_approval_command`) rather than reimplementing business lifecycle logic.
- Chosen board lane derivation rules for initial Schedule Planning board aggregate:
  - human tasks: `OPEN -> human_tasks.open`, `CLAIMED -> human_tasks.claimed`, `COMPLETED -> human_tasks.completed`
  - approvals: `PENDING -> approvals.pending`, `RESPONDED -> approvals.responded`
- Chosen board/query pagination strategy: offset/limit (`limit` default 100, max 500; `offset` default 0) for initial stable contracts.
- Chosen API auth-context approach for this internal/dev slice: explicit request headers `x-onetruth-tenant-id`, `x-onetruth-domain-id`, `x-onetruth-actor-id`, `x-onetruth-actor-type`, `x-onetruth-actor-roles` with mandatory server-side scope enforcement and no unscoped fallback.
- Chosen refresh model: polling-friendly stateless GET contracts first; websocket/live-sync intentionally deferred.
- Reconciled stale backlog status to match implemented runtime reality:
  - TASK-0029 moved to DONE (event emission matrix now implementation-backed in runtime handlers/tests)
  - TASK-0039 moved to DONE (scenario harness now implemented in fixtures/tests/docs)
  - TASK-0030 narrowed to remaining Stage07/base+delta artifact-store design work and moved to IN_PROGRESS.

## 2026-03-03 (Stage06 publish slice + scenario harness)
- Implemented the first narrow Schedule Planning Stage06 runtime behavior inside canonical `tasks complete`: parent completion can now create explicit child tasks in the same transaction with persisted lineage fields (`spawned_from_task_run_id`, `spawn_rule_id`, `spawn_cause_kind`, `spawn_cause_event_id`, `spawn_depth`, `spawn_budget_key`).
- Finalized first Stage06 completion outcome names in code:
  - `review_requires_more_information` -> child Stage06 `information_request`
  - `review_requests_changes` -> child Stage05 `work_item`
  - `draft_is_publish_ready` -> child Stage06 `final_review`
- Chosen retry behavior for parent completion replays remains explicit-failure idempotency: retrying the same completion command idempotency key fails with `duplicate_idempotency_key`, and no duplicate child task rows/events are emitted.
- Added implementation-backed Stage06 scenario fixtures and CLI-driven scenario harness tests; harness seeds synthetic template-pack completed examples into temp storage and registers canonical artifact versions before scenario steps.
- Query-contract stability approach is now test-backed via runtime contract tests that assert stable JSON row shapes for human task queue, approval queue, pointer summary, and workflow run summary surfaces.

## 2026-03-03 (approvals + artifact versions + pointer promotions substrate)
- Added canonical substrate tables for `approvals`, `artifact_versions`, and `artifact_pointers` with matching migration and SQLite bootstrap DDL support.
- Chosen minimal approval state set in the first implementation:
  - `PENDING`
  - `RESPONDED`
- Approval responses are single-finalization: only `PENDING -> RESPONDED` is allowed, and duplicate/conflicting second responses are rejected (`approval_not_respondable`).
- Chosen artifact-version idempotency behavior: `artifacts create-version` requires non-empty command `idempotency_key`; duplicate keys fail explicitly (`duplicate_idempotency_key`) with no duplicate canonical row and no duplicate `artifact.version.created` event.
- Chosen pointer conflict/race behavior:
  - first promotion wins for an uninitialized pointer key,
  - conflicting promotion without `expected_generation` fails closed (`pointer_conflict`),
  - repoint requires optimistic generation match (`pointer_generation_mismatch` on mismatch).
- Chosen minimal pointer policy gate: `promotion_reason=official_publish` requires `approved_by_approval_id` bound to a `RESPONDED` approval with `response_kind=approve`; otherwise promotion fails closed.
- Added stable CLI list/show read surfaces (`runs/tasks/approvals/artifacts/pointers`) and documented them as HITL query contracts to unblock parallel board/UI work without introducing a second truth path.

## 2026-03-03 (workflow/task core substrate + transactional lifecycle events)
- Added canonical current-state tables for the first workflow/task substrate slice: `workflow_runs`, `task_runs`, and `human_tasks` (with lineage-ready spawn fields on `task_runs`).
- Chosen minimal first-implementation states:
  - `workflow_runs`: `OPEN`, `COMPLETED`
  - `task_runs`: `READY`, `IN_PROGRESS`, `COMPLETED`
  - `human_tasks`: `OPEN`, `CLAIMED`, `COMPLETED`
- Lifecycle commands now commit canonical row changes and authoritative event appends in the same transaction for:
  - `runs create`
  - `tasks create`
  - `tasks claim`
  - `tasks complete`
- Claim and complete command idempotency keys are required and duplicate keys fail explicitly (`duplicate_idempotency_key`) with no duplicate canonical effect and no duplicate emitted lifecycle events.
- Completion flow is explicitly structured to support future same-transaction child task emission (`task.run.created`, `task.created`) without introducing a second truth path; full spawn-evaluator semantics remain out of scope for this slice.

## 2026-03-03 (runtime scaffold command boundary + smoke substrate)
- Added the first concrete runtime scaffold under `src/onetruth/`, `alembic/`, and `tests/runtime/` as TASK-0040.
- Established the first stable runtime CLI command boundary: `init-db`, `events append --json`, and `events list --json`.
- Chose explicit idempotency behavior for timeline append in this scaffold: duplicate `idempotency_key` fails with a machine-parseable error (`duplicate_idempotency_key`); no silent dedupe path is used.
- Local smoke tests use SQLite by default and initialize substrate tables through Alembic when available, with a SQLite bootstrap fallback when Alembic/SQLAlchemy are unavailable in constrained environments. PostgreSQL remains the primary target architecture.

## 2026-03-03 (conditional task spawning and step-run test planning)
- Stage 4 now explicitly allows **conditional follow-on task spawning**: completing a task may create one or more child task runs for information requests, re-review, final review, or issue-scoped child work.
- Child-task creation must stay inside the same workflow run and remain explicit through `task.run.created` / `task.created`; no new hidden side-effect path or separate `task.spawned` truth system is introduced.
- The first runtime implementation should create deterministically implied child tasks in the same transaction as the parent completion or approval response, reserving the decider/reconciler for timers, flags, and repair.
- Added `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` and TASK-0039 so future runtime work must include step-run tests where an agent executes each step and the test asserts authoritative truth.
- The workflow `template_pack/` folders already contain synthetic completed example artifacts and are now the planned seed inputs for runtime scenario tests; the validator now checks that both empty templates and completed examples exist.

## 2026-03-03 (runtime bootstrap locked for development)
- Stage 4 runtime will start as a **Python modular monolith** under `src/onetruth/`, not as an external workflow engine and not as early microservices.
- The canonical persistence substrate is **PostgreSQL current-state tables + append-only `timeline_events`**, with immutable artifact blobs stored behind a pluggable object-store adapter.
- `timeline_events` will also serve as the **outbox substrate** for derived consumers; wakeups may use notifications/polling, but consumer truth is a cursor over the canonical timeline.
- The first code slice is **core substrate + Schedule Planning Stage06 publish path**, followed by the Stage07 issue-scoped replan loop.
- `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md` are now the authoritative implementation-architecture entrypoints for fresh-session Codex work.
- Completed TASK-0028 and refreshed stale routing/context so default runtime work no longer incorrectly points fresh agents to Payroll traces.

## 2026-03-03 (test-first harness adoption)
- Adopted a pytest-backed Stage 4 TDD harness rooted in schemas, golden traces, and acceptance scenario oracles rather than prose-only guidance.
- Added `docs/planning/TDD_IMPLEMENTATION_PLAN.md` so fresh-session Codex runs can start from a stable test-first workflow.
- Added a non-authoritative reference replay reducer and stable `AT-SCH-001` .. `AT-SCH-007` scenario catalog under `tests/helpers/` to make the existing traces executable.
- Added a dedicated `schedule_policy_gate_enforced.jsonl` trace so AT-SCH-007 (sandbox/policy gate) now has first-class trace coverage.
- Default verification flow for runtime work is now `make schema-validate`, `make contract`, `make replay`, `make acceptance`, then implementation-specific suites.

## 2026-03-02 (semantic closure before runtime planning)
- Added a shared governance vocabulary and machine-readable registry for actor taxonomy, approval response verbs, approval outcomes, and approval permission actions.
- Canonical actor taxonomy is now `human | agent | service | system`; stale `user` actor types were removed from authoritative schemas.
- Canonical approval permission actions are now `approval.request` and `approval.respond`; stale `approval.grant` wording was removed.
- Schedule Planning now carries explicit temporal partition semantics: service interval, logical date, timezone, catchup policy, backfill policy, and stage-rerun policy.
- Workflow contracts now distinguish `event_inventory.platform_required` from `event_inventory.workflow_required` so runtime/task/execution events are no longer implicit.
- Added a tool-class registry, workflow-pack schemas, runtime object schemas, event payload schemas, and a concrete sandbox policy schema.
- Added a repo validation harness (`scripts/validate_repo.py`) and Makefile targets so a fresh agent can validate contracts and traces before starting runtime work.
- Added Schedule Planning golden traces for happy path, fully-agentive whole flow, drift after review, lease expiry recovery, degraded mode survivability, and cross-scope denial.

## 2026-03-02 (schedule-first Stage 4 pivot)
- Stage 4 now treats `schedule_planning.v1` as the primary runtime/debug wedge.
- The primary Stage 4 acceptance objective is a fully-agentive Schedule Planning flow where designated agent principals can execute every in-scope task while preserving the same canonical task, approval, event, and pointer substrate.
- This fully-agentive objective is a debugging and validation posture, not permission to create a second agent-only truth system.
- Payroll remains in Stage 4 as the secondary reference workflow used to validate the shared substrate against a linear approval-heavy path.
- Added `docs/workflows/payroll/v1/OPERATING_MODEL.md` so both workflow packs now expose the full authored surface declared by the authority model.

## 2026-02-28
- Added `schedule_planning.v1` as a second Stage 4 workflow contract pack for a same-day delivery operator; at that point Payroll remained the primary implementation slice (later superseded by the 2026-03-02 schedule-first pivot).
- Schedule Planning is partitioned by `ScheduleDateID` (`SD-YYYY-MM-DD`) and uses the same `(tenant_id, domain_id)` scoping model as Payroll.
- Published schedules are treated as stable base plans; live-day changes must be recorded as new artifact versions / replan deltas rather than silent edits.
- Availability artifacts for scheduling may store coded leave/absence types, but must not store medical or disciplinary detail.

## 2026-02-28 (merger update)
- The repo now explicitly adopts one truth system: immutable objects + append-only events + audited pointers.
- The CompanyOS packet is preserved as philosophy, mathematics, threat model, and lowering target, not as a second authored workflow-definition system.
- Per-workflow authored semantics now include two repo-native execution-overlay files: `DECISION_CATALOG.yaml` and `EXECUTION_PROFILE.yaml`.
- Generated runbook packs, tool matrices, approval logs, and CompanyOS IR are treated as generated derivatives, not authoritative source.
- Business execution and agentic execution will share one event system, one approval model, and one run model.
