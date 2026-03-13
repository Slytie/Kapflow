---
id: TASK-0082
epic: EPIC-040
title: "Move command idempotency to scoped command receipts"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0076"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-020.md"]
patterns: ["PATTERN-001", "PATTERN-003"]
---

## Context
Client-visible retry semantics are still coupled too closely to event append idempotency. The runtime needs scoped command receipts so retries are attached to commands within their subject scope, not to globally unique event keys.

## Objective
Move idempotency to scoped command receipts with a precise scope key, while keeping event idempotency an internal concern and preserving observable in-scope retry behavior.

## Non-goals
- No event-store redesign.
- No generalized command-bus abstraction.
- No change to unrelated workflow/runtime semantics.

## Source files to read first
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/context/EPIC-040.md`
- `codex/context/EPIC-020.md`
- `docs/architecture/event_model.md`
- `docs/architecture/orchestration_semantics.md`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/db/models.py`
- `tests/runtime/api/test_board_retry_stability.py`

## Context packs / patterns to consult
- `codex/context/EPIC-040.md`
- `codex/context/EPIC-020.md`
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-003.md`

## Source files to change
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `alembic/versions/*`
- `tests/runtime/api/test_scoped_idempotency.py`
- `tests/unit/test_command_receipts.py`
- `docs/architecture/event_model.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/tasks/TASK-0082-scoped-command-idempotency-receipts.md`

## Generated / downstream artifacts impacted
- Retry/idempotency runtime coverage and any receipt-related migrations.

## Plan
1. Define receipt-key scope precisely enough to make in-scope retries dedupe and cross-scope reuse safe.
2. Add persistence for scoped command receipts.
3. Shift client-visible retry semantics to the receipt layer while keeping event append idempotency internal.
4. Add unit/runtime tests for same-scope retry safety and cross-scope non-collision.

## Verification
- `pytest tests/unit/test_command_receipts.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_scoped_idempotency.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Clients retry commands, not event appends.
- Same-key retries within the same scope are idempotent and observable.
- Reusing the same client key across scopes is safe.
- The change stays bounded to scoped receipts rather than redesigning the runtime core.

## Notes / decisions
- Keep the scope explicit in docs and tests so it does not drift into ad hoc concatenation logic.
- Implemented on 2026-03-13 with a canonical `command_receipts` table/model/migration, scoped receipt helpers in `workflow_task_lifecycle.py`, replay-aware CLI/API success envelopes (`idempotent_replay` + `receipt`), and updated runtime coverage for replay, mismatch, and cross-scope key reuse.
