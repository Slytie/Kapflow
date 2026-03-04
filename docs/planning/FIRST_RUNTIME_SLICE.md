# FIRST_RUNTIME_SLICE.md

This document answers three questions for the first coding agent:
1. what code should be written first,
2. where should it live,
3. what should explicitly wait until later.

## 1) Candidate slice options

### Option A - Artifact store only
**Pros**
- easy to isolate
- useful for immutable-version semantics

**Cons**
- does not prove workflow/task/approval/event integration
- too small to validate the one-truth runtime substrate end to end

### Option B - Generic orchestrator skeleton first
**Pros**
- establishes runtime shape

**Cons**
- can drift into framework-building without proving real business semantics
- easy to produce abstractions before the Schedule Planning wedge constrains them

### Option C - Full Stage03 -> Stage07 fully-agentive runtime immediately
**Pros**
- exercises the whole wedge

**Cons**
- too large for the first implementation tranche
- increases the chance of hidden architecture mistakes before the substrate is stable

### Chosen first slice
**Canonical substrate + Schedule Planning Stage06 publish path**, followed immediately by the Stage07 issue-scoped replan loop.

Why this is the right first slice:
- it proves workflow/task state, human-task lease, approval binding, artifact version creation, and pointer promotion
- it proves that task completion may spawn follow-on task runs without creating a second truth path
- it is small enough to implement cleanly
- it keeps Schedule Planning, not generic abstraction work, in the driver's seat
- it leaves Stage07 as the next natural extension rather than an afterthought

## 2) First code scaffold to create

The first runtime PR creates the code locations chosen in `RUNTIME_BOOTSTRAP.md`:

```text
src/onetruth/
  api/
  application/
  domain/
  ports/
  infrastructure/
  workers/
  cli/

alembic/
  versions/

tests/runtime/
```

Minimum files to create in the first scaffold PR:
- `pyproject.toml`
- `src/onetruth/__init__.py`
- `src/onetruth/api/main.py`
- `src/onetruth/cli/__main__.py`
- `src/onetruth/infrastructure/db/session.py`
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/versions/20260303_0001_runtime_substrate.py`
- `tests/runtime/README.md`
- `tests/runtime/test_cli_timeline_smoke.py`

Goal of the scaffold PR:
- establish the package root and migration path
- make future PRs additive instead of re-litigating layout

Scaffold status:
- completed in TASK-0040, including CLI-driven smoke tests for `init-db`, `events append`, and `events list`.
- TASK-0041 now adds first canonical workflow/task current-state substrate behavior (`workflow_runs`, `task_runs`, `human_tasks`) and transactional lifecycle events via CLI.
- TASK-0042 now adds approvals + artifact versions + pointer promotion substrate behavior (`approvals`, `artifact_versions`, `artifact_pointers`) with transactional lifecycle events and query-ready CLI read surfaces.

## 3) Ordered implementation tranches

### Tranche 1 - Canonical persistence substrate
**Write first**
- `timeline_events`
- `consumer_cursors`
- `workflow_runs`
- `task_runs`
- `human_tasks`
- `approvals`
- `artifact_versions`
- `artifact_pointers` (canonical pointer table)

**Where**
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/repositories/`
- `alembic/versions/*`

**Tests**
- `tests/runtime/test_event_store.py`
- `tests/runtime/test_workflow_run_repo.py`
- `tests/runtime/test_task_claim_concurrency.py`
- `tests/runtime/test_pointer_promotion.py`

**Why first**
- every later feature depends on these tables and their transaction rules

Status:
- `timeline_events`, `consumer_cursors`, `workflow_runs`, `task_runs`, `human_tasks`, `approvals`, `artifact_versions`, and `artifact_pointers` are now implemented in the runtime substrate (TASK-0040 .. TASK-0042).

### Tranche 2 - Command kernel and state transitions
**Write next**
- workflow-run command handlers
- task-run command handlers
- human-task claim/complete handlers
- follow-on task spawn evaluator and child-task creation handlers
- approval request/respond handlers
- artifact version create/promote handlers

**Where**
- `src/onetruth/application/commands/`
- `src/onetruth/application/handlers/`
- `src/onetruth/domain/state_machines/`
- `src/onetruth/domain/policies/`

**Required first-slice commands**
- `create_workflow_run`
- `create_task_run`
- `create_human_task`
- `claim_human_task`
- `complete_human_task`
- `complete_task_and_spawn_follow_ons`
- `request_approval`
- `respond_approval`
- `create_artifact_version`
- `promote_pointer`

Status:
- commands through `promote_pointer` now exist at the CLI/handler substrate layer (TASK-0041 .. TASK-0042).
- full Stage06 business decider logic and full conditional child-task evaluator remain explicitly out of scope.

### Tranche 3 - Schedule Planning Stage03 -> Stage06 happy path plus review loops
**Write next**
- run creation with pinned Schedule Planning temporal context
- Stage03 / Stage04 / Stage05 / Stage06 task progression
- Stage05 / Stage06 conditional follow-on task spawning for information-request, re-review, and final-review paths
- Stage06 publish approval request/response
- base schedule artifact creation + pointer promotion

**Where**
- `src/onetruth/application/services/schedule_planning_decider.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/api/routes/tasks.py`
- `src/onetruth/api/routes/approvals.py`
- `src/onetruth/api/routes/artifacts.py`
- `tests/runtime/test_schedule_stage06_publish_path.py`
- `tests/runtime/test_task_completion_spawns_follow_ons.py`
- `tests/runtime/scenarios/test_schedule_stage06_publish_steps.py`

**Acceptance target**
- enough real runtime behavior to satisfy the semantics behind AT-SCH-001 for the Stage06 portion
- the runtime can show a completed review task spawning explicit follow-on work without hidden branching

Status:
- TASK-0043 now implements the first Stage06 runtime slice through CLI-driven scenario tests:
  - completing a Stage06 review task now spawns explicit child tasks for supported outcomes
  - Stage06 publish happy path is executable step-by-step through the canonical CLI boundary
  - Stage06 query/read contracts now have implementation-backed stability tests for future board/query UI work
- TASK-0044 now adds the first thin HTTP/query adapter over the same canonical runtime handlers:
  - board-ready read endpoints for human tasks/approvals/flags (list + detail), workflow runs (list + detail), run timeline, pointers, and Schedule Planning board aggregate
  - thin mutation endpoints for claim/complete/respond/flag-transition actions delegating to canonical command handlers
  - scenario-backed API contract tests and cross-scope denial coverage under `tests/runtime/api/`
- TASK-0049 extends API contract stability for frontend-safe integration:
  - adds explicit detail/timeline/flag contract coverage and retry-stability tests
  - adds board exception-card lane coverage and cross-scope denial expansion
- Full Stage03->Stage07 flow remains out of scope for this slice; Stage07 issue-loop substrate itself is now implemented in TASK-0045.

### Tranche 4 - Stage07 issue-scoped replan loop
**Write next**
- `flags`
- issue-triggered Stage07 task creation
- completion-driven Stage07 child-task spawning for info requests, re-review, and final review
- activation-key + generation dedupe
- spawn-budget enforcement
- lease expiry / recovery
- delta artifact promotion
- drift detection

**Where**
- `src/onetruth/application/commands/flags.py`
- `src/onetruth/workers/lease_sweeper.py`
- `src/onetruth/application/services/stage07_replan.py`
- `tests/runtime/test_stage07_issue_replan.py`
- `tests/runtime/test_lease_expiry_recovery.py`
- `tests/runtime/scenarios/test_schedule_stage07_spawn_steps.py`

**Acceptance target**
- semantics behind AT-SCH-001, AT-SCH-002, and AT-SCH-004
- dynamic loop behavior remains explicit, bounded, and idempotent

Status:
- TASK-0045 now implements the first Stage07 runtime slice:
  - canonical `flags` table + lifecycle commands (`flags create/transition/show/list`)
  - issue-scoped activation command (`stage07 activate-issue`) with activation-key+generation dedupe
  - Stage07 completion outcome -> explicit child-task spawn mappings with lineage
  - major-replan approval gate (`promotion_reason=official_major_replan`) through canonical approvals
  - delta artifact + pointer promotion flow with drift visibility (`artifact.pointer.drift_detected`)
  - lease-expiry reopen recovery + Stage07 reconcile commands (`maintenance sweep-leases`, `maintenance reconcile-stage07`)
  - scenario fixtures/tests and query-contract tests under `tests/runtime/scenarios/` and `tests/runtime/contracts/`
- TASK-0047 now exports backend-owned frontend snapshot fixtures from real Stage06/Stage07 runtime scenario states under `fixtures/frontend_contracts/`, with deterministic refresh tooling (`make frontend-snapshots`) and contract drift checks.
- TASK-0046 now implements the first frontend shell under `frontend/`:
  - route-based SPA skeleton for board/my-work/approvals/exceptions/runs/run-detail/official-outputs/timeline
  - reusable low-click components + drawer-first detail model
  - repository-bound data-access seam and frontend unit/route/contract-safety tests (`npm run test:run`)
- TASK-0048 now swaps frontend repositories to canonical `/api/v1` contracts:
  - HTTP-backed repositories for board/tasks/approvals/flags/runs/pointers/timeline
  - explicit polling/loading/error/empty/freshness behavior for board/list/detail pages
  - inline claim/complete/respond actions wired through repository mutation paths
  - contract-aligned frontend API integration tests with forbidden-response and reload-stability coverage
- TASK-0050 adds a bounded real-model sandbox path for Stage06 review classification:
  - narrow OpenAI Responses API adapter under `src/onetruth/integrations/openai/`
  - strict structured output schema for Stage06 outcomes (`draft_is_publish_ready`, `review_requires_more_information`, `review_requests_changes`)
  - canonical evidence artifact capture (`schedule.stage06.review_ai_evidence.json`) linked to input artifact refs
  - follow-on workflow truth still emitted only via existing `tasks.complete` handler
  - gated real-network e2e coverage under `tests/integration_openai/` plus always-on mock/contract tests
- TASK-0051 promotes example template-pack documents into an executable corpus and routes them through canonical artifact ingress:
  - manifest-driven corpus seeding under `fixtures/example_document_corpus/manifest.yaml`
  - canonical artifact-link substrate for task/approval/flag/workflow-run attachments (`artifact_links`)
  - CLI/API attachment upload/list/download paths backed by immutable `artifact_versions`
  - frontend inline upload/download actions wired to canonical repository/API boundaries
  - runtime/API tests for ingress determinism, linkage coherence, cross-scope denial, and snapshot refresh stability

### Tranche 5 - Execution facet + policy gate
**Write after Stage07**
- `execution_specs`
- `execution_sessions`
- `tool_executions`
- `policy_decisions`
- policy-gated tool execution flow

**Where**
- `src/onetruth/infrastructure/policy/`
- `src/onetruth/application/commands/execution.py`
- `src/onetruth/workers/decider.py`
- `tests/runtime/test_execution_policy_gate.py`

**Acceptance target**
- semantics behind AT-SCH-003 and AT-SCH-007

Status:
- TASK-0052 now implements the first canonical execution-runtime slice:
  - canonical persistence for `execution_sessions`, `tool_executions`, and `policy_decisions`
  - transactional lifecycle handlers and CLI boundary for session/tool/policy operations
  - bounded Stage06 OpenAI sandbox routed through explicit execution-session + policy-gated tool lifecycle
  - explicit allow/deny/failure/reconcile paths with authoritative timeline evidence
  - runtime tests for happy path, denial, idempotent retry, failure mapping, and reconcile recovery
- TASK-0054 adds the first realistic Schedule Planning pilot/operator-inspection slice:
  - reproducible pilot runner seeded from the canonical example corpus
  - Stage06 publish-ready and needs-information branches executed through bounded agent runtime rows
  - Stage07 issue/replan branch with inspectable approval/flag/pointer/artifact timeline evidence
  - per-run inspection packets (`inspection_packet.json` + `inspection_packet.md`) for operator walkthroughs
- broader generalized multi-agent orchestration remains intentionally out of scope.

### Tranche 6 - Projection coherence + generator prototype
**Write last in the Stage 4 bootstrap sequence**
- projection renderer + coherence harness
- generated runbook/IR prototype

**Where**
- `src/onetruth/workers/projection_worker.py`
- `src/onetruth/infrastructure/generation/`
- `build/generated/`
- `tests/runtime/test_projection_coherence.py`
- `tests/runtime/test_generator_lineage.py`

## 4) What should explicitly wait

Do not start with:
- Payroll runtime services
- an ops console UI
- external integrations/webhooks
- generalized multi-workflow abstraction layers
- a second event bus as source of truth
- microservice extraction
- bulk code generation before the hand-written substrate works

## 5) Verification expectations per tranche

Every tranche should still pass the repo-native verification loop:
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`

Then add tranche-local runtime tests.

For runtime tranches that expose task execution:
- include step-run scenario tests where the agent executes each step through a stable interface
- assert spawned follow-on tasks via authoritative events, not internal method calls
- seed artifact inputs from the synthetic `*_Example_COMPLETED.*` files in each workflow template pack

## 6) Handoff note for fresh-session Codex

If you are the first coding agent:
- do not re-decide the architecture
- do not change the package root unless there is an ADR-worthy reason
- start with the scaffold and core substrate
- keep the Stage06 publish path as the first business slice
- treat Stage07, the step-run scenario harness, execution/policy, projection coherence, and generator work as ordered follow-ons
