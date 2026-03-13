# Prompt for TASK-0082 — Move command idempotency to scoped command receipts

You are a Codex coding agent working in this repo.

This repo is optimized for stateless re-entry: assume a fresh session, keep context tight, and update repo-native memory as you go.

## Goal
Move client-visible retry semantics onto scoped command receipts so idempotency is bound to command scope rather than globally unique event keys.

## Prerequisites
- Depends on TASK-0076. Do not start coding if that dependency is incomplete or semantically unresolved.

## Guiding invariant
\[K = H(tenant,\ domain,\ subject,\ action,\ client\_key)\]

## Non-negotiable constraints
- A client retries a command, not an event append.
- Cross-scope use of the same client key must be safe.
- In-scope retries must remain idempotent and observable.

## Ask mode prompt

Use this section in **Ask mode** first. Do not edit code yet.

You are a Codex coding agent working in this repo.

This is `TASK-0082`: **Move command idempotency to scoped command receipts**.

### Step 0 — Load context in this order

- AGENTS.md
- LLM_RUNBOOK.md
- codex/CODEX_CONTEXT.yaml
- docs/status/CURRENT_FOCUS.md
- docs/planning/TASK_INDEX.md
- codex/tasks/TASK-0082-scoped-command-idempotency-receipts.md
- docs/planning/epics/EPIC-040.md
- codex/context/EPIC-040.md
- codex/context/EPIC-020.md
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-003.md`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/db/models.py`
- `docs/architecture/event_model.md`
- `docs/architecture/orchestration_semantics.md`
- `tests/runtime/api/test_board_retry_stability.py`

### What to figure out before coding
- Define the receipt scope precisely: tenant/domain + command + subject (and any other required dimensions).
- Plan the migration path so event idempotency remains an internal concern while command retries dedupe through receipts.
- Add tests that prove same-key retries within scope are safe and same-key requests across scopes do not collide.

### Red-team checks
- Do not redesign the entire event store just to fix retry semantics.
- Do not keep coupling command retries to event append keys via cleverer suffix concatenation.
- Avoid a generalized command-bus abstraction unless the task proves it is strictly necessary.

### Output required from Ask mode
- A short diagnosis of the current state of this task surface.
- A proposed change set in dependency order.
- The exact receipt-key scope and migration approach you propose.
- Exact files to change and why.
- The smallest tests that should fail first and then pass.
- Red-team risks and how you will avoid them.
- A smallness check explaining why this still fits one bounded Codex task.

### Stop conditions
- If the task is larger than one bounded tranche, split the follow-on work explicitly instead of silently expanding scope.
- If semantics are still ambiguous, propose the minimal docs/tests-as-spec change needed before any handler/runtime edits.
- If you find a dependency is not actually complete, say so and stop rather than coding on sand.

## Code mode prompt

Use this section only **after** the Ask-mode plan for `TASK-0082` has been reviewed and approved.

You are resuming `TASK-0082` in **Code mode**.

Implement only the approved scope for this task. Keep the change set tight. Update repo-native memory as you go.

### Step 0 — Reload the minimum context

- AGENTS.md
- LLM_RUNBOOK.md
- codex/tasks/TASK-0082-scoped-command-idempotency-receipts.md
- docs/planning/epics/EPIC-040.md
- codex/context/EPIC-040.md
- codex/context/EPIC-020.md
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/db/models.py`
- `docs/architecture/event_model.md`
- `docs/architecture/orchestration_semantics.md`
- `tests/runtime/api/test_board_retry_stability.py`

### Implementation rules
- Prefer tests/docs/spec updates first when the task calls for freezing semantics or preventing regression.
- Keep changes localized to the files named in the task unless the approved plan justified one extra seam.
- Update the matching task file with plan, commands run, outcomes, and any follow-on notes.
- If you touch authoritative semantics or trust boundaries, update the relevant architecture/status docs in the same change set.

### Source files likely to change
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/db/models.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `alembic/versions/*` (new migration)
- `tests/runtime/api/test_scoped_idempotency.py` (new)
- `tests/unit/test_command_receipts.py` (new)
- `docs/architecture/event_model.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-040.md`
- `codex/tasks/TASK-0082-scoped-command-idempotency-receipts.md`

### Verification to run
- `pytest tests/unit/test_command_receipts.py -q`
- `PYTHONPATH=src pytest tests/runtime/api/test_scoped_idempotency.py -q`
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of what changed.
- Files changed and why.
- Commands run and their results.
- Any docs/tests/task-memory updates.
- Any follow-on work that should become a separate task rather than being smuggled into this one.
