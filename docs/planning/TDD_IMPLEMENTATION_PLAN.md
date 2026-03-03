# TDD_IMPLEMENTATION_PLAN.md

This document turns the Stage 4 TDD guidance into an implementation-ready working mode for the current repo state.

## Stage 4 posture
- **Primary runtime wedge:** `schedule_planning.v1`
- **Primary debug objective:** fully-agentive end-to-end Schedule Planning flow
- **Central rule:** no second truth system; tests may provide oracles, but they do not become source-of-truth semantics

## What now exists in the repo
The repo already provides five layers of executable memory:
1. **Contracts and schemas** under `schemas/`
2. **Golden traces** under `fixtures/workflows/schedule_planning/golden_event_traces/`
3. **Pytest oracle layer** under `tests/`
4. **Runtime bootstrap docs** under `docs/planning/RUNTIME_BOOTSTRAP.md` and `docs/planning/FIRST_RUNTIME_SLICE.md`
5. **Synthetic example artifacts** under each workflow `template_pack/` directory (`*_Example_COMPLETED.*` and `*_Template_EMPTY.*`)

Runtime implementation now also includes:
- CLI command boundary for timeline + workflow/task lifecycle operations under `src/onetruth/cli/__main__.py`
- canonical workflow/task current-state tables in the runtime substrate (`workflow_runs`, `task_runs`, `human_tasks`)
- runtime lifecycle coverage in `tests/runtime/test_workflow_task_core_cli.py`
- canonical approval/artifact/pointer tables in the runtime substrate (`approvals`, `artifact_versions`, `artifact_pointers`)
- CLI lifecycle boundaries for approvals/artifacts/pointers plus query-ready list/show surfaces for future HITL UI work
- runtime coverage in `tests/runtime/test_approvals_artifacts_pointers_cli.py`
- thin HTTP/query adapter under `src/onetruth/api/` with board-ready read endpoints and mutation delegates over canonical handlers
- scenario-backed API contracts/mutation coverage under `tests/runtime/api/`

The pytest layer is intentionally small and uses a **reference reducer** only to make trace expectations executable. It must never outrank the workflow packs or schemas.

Important replay nuance:
- replay uses **trace file order** as the authoritative replay order; timestamps are evidence fields and must be parseable, but they are not the sole ordering primitive.

## Working order for Codex
When implementing runtime code, follow this order:
1. read `AGENTS.md`
2. read `docs/status/CURRENT_FOCUS.md`
3. read the relevant task brief
4. read `docs/planning/RUNTIME_BOOTSTRAP.md`
5. read `docs/planning/FIRST_RUNTIME_SLICE.md`
6. read the Schedule Planning workflow pack
7. read `docs/planning/TEST_STRATEGY.md`, `docs/planning/TEST_MATRIX.md`, and this file
8. run:
   - `make schema-validate`
   - `make contract`
   - `make replay`
   - `make acceptance`

Then make changes in this order:
1. authoritative docs / schemas / traces
2. tests and oracle mappings
3. runtime implementation code

## Chosen code target locations
Once runtime work starts, put code in the chosen locations:
- `src/onetruth/` - runtime package root
- `alembic/` - database migrations
- `tests/runtime/` - runtime-specific tests once real code exists
- `fixtures/scenarios/` - scenario specs for step-run harness work once runtime exists

Do **not** let `tests/helpers/`, `scripts/`, or generated derivative folders become a shadow runtime implementation.

## Current executable suites
- `tests/contract/` - validator and repo-contract checks
- `tests/unit/` - reference reducer semantic checks
- `tests/replay/` - trace replay and final-state oracles
- `tests/acceptance/` - AT-SCH scenario evidence checks
- `tests/runtime/` - implementation-backed CLI runtime tests (timeline + workflow/task core lifecycle)
- `tests/runtime/` - implementation-backed CLI + API runtime tests (timeline + workflow/task/approval/artifact/pointer + Stage06 + board/query HTTP contracts)
- `tests/security/` - cross-scope and policy-gate negatives
- `tests/property/` - cross-trace invariants
- `tests/integration/` - machine-usable repo/trace checks

## Stable acceptance mapping
Each Schedule Planning acceptance scenario now has a dedicated oracle trace:
- `AT-SCH-001` -> `schedule_happy_path_publish_and_replan.jsonl`
- `AT-SCH-002` -> `schedule_drift_after_review.jsonl`
- `AT-SCH-003` -> `schedule_fully_agentive_whole_flow.jsonl`
- `AT-SCH-004` -> `schedule_lease_expiry_recovery.jsonl`
- `AT-SCH-005` -> `schedule_degraded_mode_survivability.jsonl`
- `AT-SCH-006` -> `schedule_cross_scope_denial.jsonl`
- `AT-SCH-007` -> `schedule_policy_gate_enforced.jsonl`

The stable mapping lives in `tests/helpers/scenario_catalog.py`.

## Important nuances for implementation
### 1) Tests are hierarchical
- **Schemas validate shape**
- **Replay validates state semantics**
- **Acceptance validates evidence bundles**

Do not skip straight to broad E2E work when replay or acceptance oracles can express the requirement more directly.

### 2) The reference reducer is not runtime code
`tests/helpers/reference_model.py` is a small test oracle.
It exists to answer questions like:
- what final state should this trace produce?
- which pointer target should be official?
- which approval outcome should be present?

It must remain intentionally small and easy to replace once real runtime code exists.

### 3) Golden traces are the first behavioral corpus
Before adding runtime services, use the traces to answer:
- what events must exist?
- what state transitions must be preserved?
- which negative cases are mandatory?

### 4) Negative cases are first-class
Cross-scope denial, policy-gate denial, drift-after-review, lease expiry, and degraded-mode traces are not side tests. They are part of the main correctness envelope.

### 5) Payroll is not yet the default runtime replay corpus
Payroll remains an important reference workflow, but its golden-trace directory is still placeholder-only.
Use Payroll to cross-check authored semantics and governance-heavy review, not as the default replay-first implementation wedge.

### 6) Step-run scenario harness status
Stage 4 now has a first implementation-backed runtime scenario harness slice where a scenario executes each step through the stable CLI interface and asserts authoritative truth:
- emitted events
- task lineage / spawned children
- approval outcomes
- pointer targets
- artifact version linkage

Implemented locations:
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `fixtures/scenarios/schedule_planning/*.yaml`
- `tests/runtime/scenarios/*.py`
- `tests/runtime/contracts/test_hitl_query_contracts_stage06.py`

Use the synthetic example artifacts in `fixtures/workflows/*/template_pack/` as seed inputs for those tests.
The runtime test should copy those files into temp storage and assign synthetic artifact version IDs rather than inventing a separate sample-data universe.

## Default verification commands
- `make schema-validate`
- `make contract`
- `make unit`
- `make replay`
- `make acceptance`
- `make security`
- `make test`
- `make generated-check`
