# CURRENT_FOCUS.md

## Stage
Stage 4 - Vertical Slice MVP (repo merged around one truth system)

## Current milestone
Runtime bootstrap is now explicit. The repo is ready for the first code scaffold under `src/onetruth/` + `alembic/`, starting with the canonical runtime substrate and the Schedule Planning Stage06 publish path.

### Recently completed runtime-bootstrap tranche
- TASK-0028 - Translated the runtime object model into a concrete Stage 4 runtime architecture, repo layout, persistence model, and first implementation slice
- Added `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md`
- Added `docs/adr/ADR-003-stage4-runtime-architecture.md`
- Refreshed stale Codex routing: EPIC-040 / EPIC-050 no longer route default runtime work through Payroll, and missing context packs now exist for EPIC-025 / EPIC-030 / EPIC-060
- Expanded TASK-0029 .. TASK-0032 briefs so a fresh coding agent knows what to create, where it should live, and how to verify it

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
1. TASK-0029 - Map the typed event registry to runtime emission points and tests
2. TASK-0039 - Design the step-run scenario harness for agent-executed flows and conditional task spawning
3. TASK-0030 - Translate promotion semantics and schedule delta rules into artifact-store design
4. TASK-0031 - Design the projection coherence harness
5. TASK-0032 - Prototype generator for runbook packs and CompanyOS IR

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
- Do not start with UI, exporters, or generalized microservices before the canonical substrate and Schedule Planning Stage06 path exist.

## Notes
- Schedule Planning remains the first runtime implementation and debugging wedge.
- The Stage 4 debug objective remains an end-to-end fully-agentive Schedule Planning flow.
- First code should live under `src/onetruth/` and `alembic/` as described in `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md`.
- Build order after scaffold: canonical timeline + core runtime tables -> Stage06 publish path and follow-on review/info loops -> step-run scenario harness -> Stage07 issue loop -> execution sessions/policy gate -> projections/generator.
- Payroll remains the secondary linear approval-heavy reference workflow and governance benchmark.
- Payroll golden traces remain placeholder-only; do not treat Payroll as the primary replay corpus yet.
- AT-SCH-001 .. AT-SCH-007 have stable golden-trace mappings for replay and acceptance work.
