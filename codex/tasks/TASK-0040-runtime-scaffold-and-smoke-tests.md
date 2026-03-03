---
id: TASK-0040
epic: EPIC-040
title: Instantiate runtime scaffold and smoke-tested substrate command boundary
status: DONE
owners:
- platform
reviewers:
- qa
- security
- ops
depends_on:
- TASK-0028
risk: high
context_packs:
- codex/context/EPIC-040.md
patterns:
- PATTERN-001
- PATTERN-002
- PATTERN-008
---

## Context
The repo has runtime architecture, invariants, schemas, and replay-first traces, but no concrete `src/onetruth/` runtime scaffold or stable runtime command boundary. This blocks Tranche 1 substrate execution work and runtime step tests.

## Objective
Create a small, real Stage 4 runtime scaffold that preserves one-truth invariants and is test-driven through a stable CLI boundary:
- runtime package scaffold under `src/onetruth/`,
- migrations scaffold under `alembic/`,
- minimal canonical substrate for append-only timeline events and durable consumer cursors,
- runtime smoke tests that drive CLI end-to-end.

## Non-goals
- Do not implement Schedule Planning Stage06 business logic in this task.
- Do not introduce a second workflow engine, second event store, or agent-only state authority.
- Do not rewrite existing contracts, payload schemas, or golden traces unless a test forces it.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/adr/ADR-003-stage4-runtime-architecture.md`
- `docs/architecture/invariants.md`
- `schemas/events/envelope.schema.json`
- `schemas/events/event_type_registry.yaml`
- `Makefile`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `PATTERN-001`
- `PATTERN-002`
- `PATTERN-008`

## Source files to change
- `pyproject.toml` (new)
- `src/onetruth/` (new scaffold and minimal runtime modules)
- `alembic.ini` (new)
- `alembic/` (new env + initial migration)
- `tests/runtime/` (new runtime CLI smoke tests)
- `Makefile`
- `README.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md` (only for material decisions)

## Generated / downstream artifacts impacted
- runtime scenario harness foundation for future `tests/runtime/scenarios/*`
- CI/runtime command surface and developer quickstart docs

## Plan
1. Create task/memory entries for runtime scaffold work.
2. Add minimal Python packaging plus runtime scaffold folders under `src/onetruth/`.
3. Add minimal SQLAlchemy models and Alembic migration for `timeline_events` and `consumer_cursors`.
4. Add a CLI boundary (`init-db`, `events append`, `events list`) with machine-parseable JSON output.
5. Add runtime smoke tests that run CLI end-to-end against a fresh SQLite DB.
6. Choose and document idempotency behavior at CLI boundary.
7. Update docs to reflect implementation reality and verify full repo loop.

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q tests/runtime`
- `pytest -q`

## Acceptance criteria
- Runtime scaffold exists at `src/onetruth/`, `alembic/`, and `tests/runtime/`.
- CLI provides stable JSON-output commands: `init-db`, `events append --json`, `events list --json`.
- Runtime tests execute CLI end-to-end: init DB, append/list timeline events, ordering and payload round-trip assertions, and idempotency behavior assertions.
- One-truth invariants are preserved: append-only canonical timeline events with durable consumer cursors; no shadow state engine introduced.
- README/planning/status docs are refreshed so paths and commands are accurate after implementation.
- Full validation loop and full pytest suite pass after changes.

## Notes / decisions
Idempotency behavior for duplicate `idempotency_key` at append boundary is explicit failure (`duplicate_idempotency_key` JSON error). This PR does not silently dedupe timeline appends.

## Completion notes
- Added runtime scaffold directories and package modules under `src/onetruth/`.
- Added initial substrate migration scaffold under `alembic/` and `alembic.ini`.
- Added CLI boundary and end-to-end smoke tests under `tests/runtime/`.
- Updated README/planning/status docs to reflect implemented scaffold reality.
