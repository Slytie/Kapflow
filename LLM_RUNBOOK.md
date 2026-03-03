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
- the relevant workflow pack (default: Schedule Planning)

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
- if you touch the fully-agentive Schedule Planning objective, preserve the same canonical task/approval/event/pointer path
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

## Stage 4 reminder
- Schedule Planning is the current runtime/debug wedge.
- The priority slice is a fully-agentive end-to-end debug flow.
- The first concrete code milestone is the Schedule Planning substrate + Stage06 publish path.
- Payroll remains a reference workflow used to validate shared semantics against a linear approval-heavy path.

## Default safe commands
- `make lint`
- `make test`
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make security`
- `make generated-check`
