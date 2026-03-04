# CURRENT_FOCUS.md

## Stage
Stage 4 - Vertical Slice MVP (repo merged around one truth system)

## Current milestone
Runtime scaffold bootstrap now includes canonical workflow/task/approval/artifact/pointer substrate under `src/onetruth/` + `alembic/` with a stable CLI lifecycle boundary:
- timeline substrate: `init-db`, `events append`, `events list`
- workflow/task substrate: `runs create/show/list`, `tasks create/claim/complete/show/list`
- approval/artifact/pointer substrate: `approvals request/respond/show/list`, `artifacts create-version/show/list`, `pointers promote/show/list`
- Stage07 issue substrate: `flags create/transition/show/list`, `stage07 activate-issue`, `maintenance sweep-leases`, `maintenance reconcile-stage07`
- thin HTTP/query adapter: `/api/v1/human-tasks`, `/api/v1/approvals`, `/api/v1/flags`, `/api/v1/workflow-runs`, `/api/v1/pointers`, `/api/v1/timeline-events`, `/api/v1/board/schedule-planning`, plus API mutation delegates for claim/complete/respond
Active coding milestone: TASK-0054 hardened policy-gated execution-session state semantics (`WAITING_POLICY -> RUNNING` on allow) and reconcile dedupe coverage, building on TASK-0053 bounded OpenAI e2e and TASK-0052 execution-runtime substrate; next active backlog item is TASK-0030 design closure work.

### Recently completed runtime-bootstrap tranche
- TASK-0028 - Translated the runtime object model into a concrete Stage 4 runtime architecture, repo layout, persistence model, and first implementation slice
- TASK-0040 - Instantiated the runtime scaffold (`src/onetruth/`, `alembic/`, `tests/runtime/`) with CLI-driven smoke tests for canonical timeline append/list behavior
- TASK-0041 - Implemented canonical workflow/task substrate tables (`workflow_runs`, `task_runs`, `human_tasks`) with transactional lifecycle event emission and runtime concurrency/idempotency coverage
- TASK-0042 - Implemented canonical approvals/artifacts/pointers substrate tables (`approvals`, `artifact_versions`, `artifact_pointers`) with transactional event emission and query-ready CLI list/show contracts for future HITL board work
- TASK-0043 - Implemented the first real Schedule Planning Stage06 publish slice with transactional completion-driven child task spawning, CLI-driven scenario fixtures/harness tests, and query-contract stability tests
- TASK-0044 - Implemented the first thin HITL HTTP/query adapter with board-ready read endpoints, mutation delegates over canonical handlers, scenario-backed API contracts, and cross-scope denial tests
- TASK-0045 - Implemented the first Schedule Planning Stage07 issue-scoped replan loop with canonical flags, deduped issue activation, major-replan approval gating, delta promotion/drift visibility, and lease-expiry recovery/reconcile scenario coverage
- TASK-0047 - Exported backend-owned frontend contract snapshots from real runtime scenarios under `fixtures/frontend_contracts/` with deterministic drift checks and snapshot contract tests
- TASK-0046 - Implemented frontend app shell + HITL route skeletons + low-click reusable components + mock repository boundary over backend-owned fixtures
- TASK-0048 - Swapped frontend repositories from mock snapshots to real `/api/v1` contracts, hardened loading/error/empty/freshness behavior, and added integration tests for claim/complete/respond flows
- TASK-0050 - Added bounded Stage06 OpenAI Responses API sandbox classification with strict structured outputs, canonical evidence artifact capture, and gated real-network e2e coverage
- TASK-0051 - Promoted template-pack completed examples into an executable document corpus with canonical artifact ingress, subject attachment linkage, API attachment surfaces, and backend-owned snapshot refresh integration
- TASK-0052 - Converted the bounded Stage06 OpenAI spike into canonical execution runtime behavior with transactional session/tool/policy lifecycle events, explicit policy allow/deny gating, idempotent retry handling, and stale-session reconcile recovery
- TASK-0053 - Locked the minimal OpenAI sandbox e2e spike as a bounded, canonical Stage06 path with deterministic mock coverage and opt-in real-network integration gating
- TASK-0054 - Hardened Stage06 policy-gate runtime semantics with explicit `WAITING_POLICY -> RUNNING` transition evidence and reconcile coverage proving no duplicate completed tool/evidence effects on stale-session recovery
- Added `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md`
- Added `docs/adr/ADR-003-stage4-runtime-architecture.md`
- Refreshed stale Codex routing: EPIC-040 / EPIC-050 no longer route default runtime work through Payroll, and missing context packs now exist for EPIC-025 / EPIC-030 / EPIC-060
- Reconciled stale backlog/task memory so TASK-0029 and TASK-0039 are now marked DONE, while TASK-0030 is narrowed to remaining Stage07/base+delta artifact-store design work

### Recently completed dynamic-loop clarification tranche
- Locked the rule that task completion may spawn explicit follow-on task runs for information requests, re-review, final review, and issue-scoped child work
- Added `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` and TASK-0039 so runtime step tests are now part of the plan instead of an implied future wish
- Extended Schedule Planning and Payroll workflow contracts with bounded `task_spawn_policy` / `spawn_rules`
- Added child-task lineage fields to the canonical TaskRun schema and `task.run.created` payload schema
- Added validator checks for spawn-rule completeness and for the existence of template-pack completed examples
- Added a design trace + unit test showing parent task completion spawning an explicit child task

### Recently completed semantic-closure tranche
- TASK-0034 - Canonicalized governance vocabulary and actor taxonomy
- TASK-0033 - Specified the fully-agentive Schedule Planning debug slice, temporal partition semantics, and issue activation keys
- TASK-0027 - Added full authored-surface validation and drift checks
- TASK-0035 - Tightened human-task and control-plane semantics for end-to-end agent execution
- TASK-0036 - Added runtime object schemas for canonical run/task/approval/execution objects
- TASK-0037 - Added event payload schemas and registry bindings
- TASK-0038 - Authored Schedule Planning golden traces and acceptance oracles
- Adopted a pytest-backed TDD harness with a stable AT-SCH scenario catalog and reference replay reducer

### Next tasks (priority order)
1. TASK-0030 - Complete Stage07/base+delta artifact-store design details (blob adapter + reconstruction semantics)
2. TASK-0031 - Design the projection coherence harness
3. TASK-0032 - Prototype generator for runbook packs and CompanyOS IR

## Test-first working mode
Before adding runtime services or API surfaces:
1. update authoritative docs / schemas / traces,
2. update the scenario catalog and pytest oracles,
3. then implement runtime code.

Default verification loop:
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make security`

## Recently completed merger work
- authority model and derivation policy
- curated vision / mathematics / threat-model docs
- decision catalogs and execution profiles for both workflows
- unified event / approval / orchestration / promotion docs
- runbook skeletons and CI / test-matrix guidance
- completed the Payroll authored workflow surface with an operating model
- re-scoped Stage 4 routing docs so Schedule Planning is the primary runtime/debug wedge
- closed the shared vocabulary, runtime-schema, payload-schema, and golden-trace gaps needed before implementation planning
- locked the first concrete runtime architecture and file-placement plan so implementation can start without stack drift

## Do not do
- Do not introduce a peer authored workflow-definition system beside the repo workflow packs.
- Do not hand-edit generated derivatives as if they were source.
- Do not create separate agent-run or human-decision truth models outside the canonical docs.
- Do not satisfy the fully-agentive test objective by inventing an agent-only state path that bypasses approvals, task runs, events, or pointer promotions.
- Do not let test helpers or the reference reducer outrank the workflow packs or schemas.
- Do not introduce a second source of truth in board/frontend work; UI must stay a derived surface over canonical runtime state and events.

## Notes
- Schedule Planning remains the first runtime implementation and debugging wedge.
- The Stage 4 debug objective remains an end-to-end fully-agentive Schedule Planning flow.
- First code should live under `src/onetruth/` and `alembic/` as described in `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md`.
- Build order after scaffold: canonical timeline + core runtime tables -> Stage06 publish path and follow-on review/info loops -> step-run scenario harness -> thin HTTP/query adapter -> Stage07 issue loop -> execution sessions/policy gate -> projections/generator.
- Payroll remains the secondary linear approval-heavy reference workflow and governance benchmark.
- Payroll golden traces remain placeholder-only; do not treat Payroll as the primary replay corpus yet.
- AT-SCH-001 .. AT-SCH-007 have stable golden-trace mappings for replay and acceptance work.
