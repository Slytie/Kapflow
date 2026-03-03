---
id: TASK-0041
epic: EPIC-040
title: "Implement workflow/task core substrate with transactional event emission"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0040"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-020.md", "codex/context/EPIC-050.md"]
patterns: ["PATTERN-001", "PATTERN-002", "PATTERN-008"]
---

## Context
TASK-0040 established runtime scaffold, timeline events, consumer cursors, and a stable CLI smoke boundary. The next blocking gap is the first canonical workflow/task state substrate (`workflow_runs`, `task_runs`, `human_tasks`) with state mutations and authoritative timeline events committed in the same transaction.

## Objective
Implement the first canonical workflow/task runtime core with:
- persistence and migrations for `workflow_runs`, `task_runs`, `human_tasks`,
- thin transaction-bound command handling for creating/claiming/completing work,
- CLI JSON boundary for run/task lifecycle operations,
- runtime tests proving happy path, concurrency, idempotency, and negative-case behavior,
- documentation alignment so repo memory reflects implemented runtime behavior.

## Non-goals
- Do not implement approvals.
- Do not implement artifact versions or pointers.
- Do not implement Schedule Planning Stage06 business logic.
- Do not implement HTTP APIs/UI.
- Do not implement the full conditional child-task spawn evaluator.
- Do not create any second authoritative state machine or event path.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `codex/tasks/TASK-0040-runtime-scaffold-and-smoke-tests.md`
- `codex/tasks/TASK-0029-event-registry-to-runtime-mapping.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/event_model.md`
- `schemas/events/event_type_registry.yaml`
- `schemas/events/payloads/workflow.run.created.schema.json`
- `schemas/events/payloads/task.run.created.schema.json`
- `schemas/events/payloads/task.created.schema.json`
- `schemas/events/payloads/task.claimed.schema.json`
- `schemas/events/payloads/task.completed.schema.json`
- `schemas/events/payloads/task.run.state_changed.schema.json`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `codex/context/EPIC-020.md`
- `codex/context/EPIC-050.md`
- `PATTERN-001`
- `PATTERN-002`
- `PATTERN-008`

## Source files to change
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/repositories/workflow_runs.py` (new)
- `src/onetruth/infrastructure/repositories/task_runs.py` (new)
- `src/onetruth/infrastructure/repositories/human_tasks.py` (new)
- `src/onetruth/application/handlers/workflow_task_lifecycle.py` (new)
- `src/onetruth/cli/__main__.py`
- `alembic/versions/*` (new migration for workflow/task tables)
- `tests/runtime/*` (new lifecycle coverage tests)
- `docs/planning/EVENT_EMISSION_MATRIX.md` (new)
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/planning/TEST_MATRIX.md`
- `README.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Generated / downstream artifacts impacted
- runtime step-run harness foundation (future `tests/runtime/scenarios/*`)
- CI/runtime regression coverage for transactional event emission
- future Stage06/Stage07 implementation PRs that extend task completion into child spawn flows

## Plan
1. Add canonical workflow/task current-state tables plus migration/bootstrap DDL.
2. Implement thin repositories and transaction-bound lifecycle handlers.
3. Extend CLI with run/task create/claim/complete/show/list commands.
4. Emit required authoritative events in the same transaction as state changes.
5. Add runtime tests for happy path, concurrency, idempotency, and negative conditions.
6. Document event emission matrix and runtime state/idempotency decisions.

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q tests/runtime`
- `pytest -q`

## Acceptance criteria
- `workflow_runs`, `task_runs`, and `human_tasks` exist with migration/bootstrap support.
- CLI lifecycle operations exist for run/task create, task claim, and task completion.
- Each lifecycle command emits authoritative events in the same transaction as row mutations.
- Runtime tests cover happy path, concurrency, idempotency behavior, and negative cases.
- `docs/planning/EVENT_EMISSION_MATRIX.md` exists and matches implemented behavior.
- README/planning/status/task docs are updated and non-stale.
- Implementation is lineage-ready for future child-task spawning extension (lineage fields present and completion flow structurally extensible), but does not implement the full spawn evaluator yet.

## Notes / decisions
To keep local smoke tests CI-safe, SQLite remains default for runtime tests while preserving PostgreSQL-first architecture intent.

## Completion notes
- Added canonical persistence support for `workflow_runs`, `task_runs`, and `human_tasks` in runtime bootstrap DDL and Alembic migration.
- Implemented transaction-bound lifecycle handlers and CLI commands for run/task create and human-task claim/complete.
- Added implementation-backed event emission matrix and updated planning/README memory docs.
- Added runtime coverage for happy path, concurrency, idempotency, and negative lifecycle cases.
