# LLM_RUNBOOK.md - How to work in this repo

This repo assumes a stateless LLM that re-enters fresh each run. The repo is the externalized memory.

## The per-task workflow

### 0) Choose a task brief
- Create or pick a task in `codex/tasks/`.
- Keep scope small and reviewable.

### 1) Rehydrate context
Assume fresh session. Keep context small and task-specific.

Baseline reads (always):
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/STAGE4_PLAN.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/architecture/invariants.md`
- `schemas/events/envelope.schema.json`
- `schemas/events/event_type_registry.yaml`
- `scripts/validate_repo.py`
- the task file you are executing (`codex/tasks/TASK-*.md`)
- the relevant epic file (`docs/planning/epics/EPIC-*.md`) if applicable
- the relevant workflow pack (default for new agentic scheduling work: logistics weekly/live via `docs/workflows/logistics_ops_family/v1/`, `docs/workflows/weekly_schedule_planning/v1/`, and `docs/workflows/live_dispatch/v1/`; treat `schedule_planning.v1` as regression/reference-only unless explicitly needed)
- for workpage FE tasks, also load `docs/planning/LOGISTICS_WORKPAGES_V0_PLAN.md`, `docs/planning/LOGISTICS_WORKPAGES_V0_PRODUCT_BRIEF.md`, `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`, `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`, `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`, `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`, `docs/workflows/dispatch_reporting/v1/examples/*`, `fixtures/frontend_contracts/README.md`, and `fixtures/logistics/workpages/*`

Only when needed:
- Authority chain / source-of-truth changes:
  - `docs/architecture/AUTHORITY_MODEL.md`
  - `docs/architecture/DOCUMENT_STATUS_MATRIX.md`
  - `docs/architecture/DERIVATION_AND_GENERATION_POLICY.md`
  - `docs/architecture/LOWERING_CONTRACT.md`
- Orchestrator / approvals / tasks work:
  - `docs/architecture/governance_vocabulary.md`
  - `docs/architecture/orchestration_semantics.md`
  - `docs/architecture/approval_model.md`
  - `docs/architecture/human_task_semantics.md`
  - `docs/architecture/flag_model.md`
  - `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- Shared schema registries:
  - `schemas/policy/governance_vocabulary.yaml`
  - `schemas/policy/permissions.yaml`
  - `schemas/agentic/tool_class_registry.yaml`
  - `schemas/workflows/workflow_contract.schema.json`
  - `schemas/workflows/artifact_map.schema.json`
  - `schemas/runtime/*.schema.json`
  - `schemas/events/payloads/*.schema.json`
- Testing / retries / acceptance semantics:
  - `docs/planning/TEST_STRATEGY.md`
  - `docs/planning/TEST_MATRIX.md`
  - `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
  - `tests/README.md`
  - `tests/helpers/scenario_catalog.py`
- Productization / Workflow Lab planning:
  - `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`
  - `docs/planning/epics/EPIC-100.md`
  - `docs/planning/epics/EPIC-110.md`
  - `codex/context/EPIC-100.md`
  - `codex/context/EPIC-110.md`
- Deep reference:
  - epic context pack under `codex/context/`
  - pattern cards under `docs/patterns/cards/`
  - full research notes only if the task truly needs it

Default rule:
- cards first, then source notes if needed,
- workflow packs outrank pattern cards and research notes.

### 2) Plan changes before editing
In the task file:
- record a short plan
- list source files to change
- list generated artifacts impacted
- define verification checks
- record relevant pattern IDs if external pattern guidance influenced the design
- list the tests or traces that should fail first and then pass

For runtime work specifically:
- align the file locations with `docs/planning/RUNTIME_BOOTSTRAP.md`
- keep the first coding tranche inside `docs/planning/FIRST_RUNTIME_SLICE.md`
- use `docs/planning/STEP_RUN_SCENARIO_HARNESS.md` when planning step-by-step runtime tests
- do not invent a second stack, second package layout, or second event store

### 3) Implement in a tight loop
- edit repo-native source first
- do not invent stage IDs, dataset keys, approval IDs, or official outputs in downstream materials
- if a generated artifact needs a change, update the source and regeneration rule, not just the generated file
- do not let pattern cards or research notes override authoritative docs
- if you touch the fully-agentive logistics weekly/live objective, preserve the same canonical task/approval/event/pointer path
- if you touch productization or Workflow Lab, keep the default promotion model as reviewed release promotion, not direct lab-to-prod runtime mutation
- if you touch Workflow Lab, keep it non-authoritative: normalize and compare kernel behavior, do not create a second semantics compiler
- if you touch behavior, update the matching trace + scenario catalog + pytest oracle before runtime code
- if you touch runtime step tests, use the existing `template_pack/*_Example_COMPLETED.*` files as seed artifacts instead of inventing a second sample-data tree
- keep real runtime code under `src/onetruth/` once the scaffold exists; do not let `tests/helpers/` become a shadow runtime

### 4) Verify
Record:
- commands run
- outputs / results
- schema validations
- test suites run
- any source-to-generated consistency checks

Minimum verification commands:
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`

Add as needed:
- `make unit`
- `make security`
- `make property`
- `make test`

### 5) Update repo memory
- update `docs/status/CURRENT_FOCUS.md` if priorities changed
- update `docs/status/DECISIONS_SINCE_LAST.md` if a meaningful decision was made
- update the relevant epic/task files
- update architecture docs if the authority model or runtime semantics changed
- update pattern or research routing docs if you add a new external reference that future sessions should find

### 6) Open a PR
Include:
- what changed
- why
- source-of-truth impacts
- generated-derivative impacts
- tests and checks run
- risk notes

## Production + Workflow Lab reminder
- Productization now leads, but Workflow Lab Phase 0/1 can proceed in parallel as long as it stays thin, report-first, and non-authoritative.
- Treat production and lab as separate environments with the same kernel and release discipline but different state.
- `TASK-0121` and later Workflow Lab execution/comparison work are gated on the readiness checks in `docs/planning/PRODUCTION_AND_WORKFLOW_LAB_PLAN.md`.

## Stage 4 reminder
- For new agentic scheduling tasks, logistics weekly/live (`weekly_schedule_planning.v1 -> live_dispatch.v1`) is the default runtime/debug wedge.
- The priority slice is a fully-agentive end-to-end weekly/live logistics flow over the canonical substrate.
- Legacy `schedule_planning.v1` remains regression/reference-only for this routing posture.
- Payroll remains a reference workflow used to validate shared semantics against a linear approval-heavy path.

## Workpage v0 reminder
- The current application-facing FE slice is `EPIC-120`: fixture-backed full-page workpages for weekly schedule review and end-of-day reporting.
- Start from normalized examples -> `WorkpageViewModel` -> page UI.
- Do not start from a backend workpage API or a generic artifact editor.
- Keep the schedule page on the weekly-planning side of the boundary and the EOD page on the reporting draft/review side of the boundary.
- Keep workpage fixtures distinct from backend-owned `fixtures/frontend_contracts/` snapshots.
- Keep docs/status/task memory current in the same change set whenever routes or visible product truth change.

## Default safe commands
- `make lint`
- `make test`
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make security`
- `make generated-check`
