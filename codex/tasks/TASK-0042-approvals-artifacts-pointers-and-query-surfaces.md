---
id: TASK-0042
epic: EPIC-040
title: "Implement approvals, artifact versions, pointers, and query-ready runtime surfaces"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0041"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-020.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-008"]
---

## Context
TASK-0041 delivered canonical workflow/task lifecycle substrate and transactional event emission through a stable CLI boundary. The next blocking slice is approvals + artifact versions + audited pointer promotion in the same substrate, plus stable read contracts for future human-in-the-loop board/query work.

## Objective
Implement the next canonical substrate slice with:
- persistence and migrations for `approvals`, `artifact_versions`, and `artifact_pointers`,
- thin transaction-bound command handlers for request/respond approval, create artifact version, and promote pointer,
- CLI JSON boundaries for command and read/list surfaces,
- authoritative lifecycle event emission in the same transaction as canonical row mutations,
- runtime tests for happy path, idempotency, conflict/race behavior, and negative cases,
- documentation/task memory updates so no runtime docs stay stale.

## Non-goals
- Do not build HTTP APIs.
- Do not build frontend/Kanban UI.
- Do not implement full Schedule Planning Stage06 business flow.
- Do not implement full projection/coherence engine.
- Do not implement full conditional child-task spawn evaluator.
- Do not introduce a second source of truth or shadow UI state.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `codex/tasks/TASK-0041-workflow-task-core-and-transactional-events.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/promotion_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `schemas/events/event_type_registry.yaml`
- approval/artifact/pointer payload schemas in `schemas/events/payloads/`

## Source files to change
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/repositories/approvals.py` (new)
- `src/onetruth/infrastructure/repositories/artifact_versions.py` (new)
- `src/onetruth/infrastructure/repositories/artifact_pointers.py` (new)
- `src/onetruth/infrastructure/repositories/workflow_runs.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/cli/__main__.py`
- `alembic/versions/*` (new migration for approvals/artifacts/pointers)
- `tests/runtime/*` (new runtime coverage)
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md` (new)
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md` (only if implementation diverges)
- `README.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`

## Generated / downstream artifacts impacted
- future Stage06 publish-path runtime scenarios
- future board/Kanban read-model/API work through stable CLI query contracts
- acceptance/runtime evidence coverage for approval/promotion semantics

## Plan
1. Add canonical tables + migration for approvals, artifact versions, and artifact pointers.
2. Add repositories and transactional handlers for request/respond approval, create artifact version, and promote pointer.
3. Extend CLI with JSON-in/JSON-out command + list/show boundaries for approvals/artifacts/pointers.
4. Add runtime tests for happy path, idempotency, concurrency/conflicts, and cross-linkage.
5. Add implementation-backed event emission matrix updates and HITL query contracts.
6. Update README/planning/status memory docs and verify full repo loop.

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q tests/runtime`
- `pytest -q`

## Acceptance criteria
- Canonical `approvals`, `artifact_versions`, and `artifact_pointers` tables exist with migration support.
- Transaction-bound lifecycle handlers exist for:
  - `request_approval`
  - `respond_approval`
  - `create_artifact_version`
  - `promote_pointer`
- Each command mutates canonical rows and appends authoritative events in the same transaction.
- CLI provides stable JSON command and query surfaces for approvals/artifacts/pointers.
- Runtime tests cover happy path, idempotency, race/conflict handling, and negative cases.
- `docs/planning/HITL_QUERY_CONTRACTS.md` exists and matches implemented CLI read surfaces.
- `docs/planning/EVENT_EMISSION_MATRIX.md` reflects implemented command/event behavior.
- README/planning/status docs are updated and non-stale.
- Full repo verification passes.
- This slice is lineage-ready for future conditional child-task spawning and publish-path integration, but does not yet implement the full spawn evaluator or Stage06 business flow.

## Notes / decisions
- This PR explicitly unblocks canonical publish/promotion flows, future Stage06 schedule publishing, and future human-in-the-loop board/query surfaces.

## Completion notes
- Added canonical substrate persistence and migration support for `approvals`, `artifact_versions`, and `artifact_pointers`.
- Added transactional runtime handlers and CLI commands for approval request/response, artifact-version creation, and pointer promotion (plus show/list query surfaces).
- Implemented same-transaction authoritative event emission for:
  - `approval.requested`
  - `approval.responded`
  - `artifact.version.created`
  - `artifact.pointer.promoted`
  - `artifact.pointer.drift_detected` (when reviewed/promoted versions differ)
- Added runtime test coverage for happy path, idempotency, negative finalization, conflict/race behavior, and cross-linkage chain coherence.
- Added `docs/planning/HITL_QUERY_CONTRACTS.md` and updated runtime planning/readme docs to match implementation reality.
