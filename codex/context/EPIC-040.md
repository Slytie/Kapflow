# EPIC-040 Context Pack — Durable orchestrator core (runs, waits, retries, idempotency)

**Purpose (why you might open this):**

- You’re designing or changing workflow/task state machines, retries, timers, or child-run semantics.
- You’re adding a new WAIT condition (human approval, timer, external callback).
- You’re mapping runtime schemas into concrete tables, handlers, and code locations.

## Non-negotiable invariants to keep in mind
- There is one `workflow_run` / `task_run` truth system; `execution_session` is only an execution facet.
- Every retry boundary must be idempotent and deduped.
- No 'latest' references: always bind to artifact versions and record promotion pointers.
- Schedule Planning Stage07 reruns stay inside the same `workflow_run` and use issue-scoped activation keys plus generation.
- Authoritative state changes must update current-state rows and append timeline events in the same transaction.

## Contracts / schemas to treat as authoritative
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/orchestration_semantics.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/workflows/schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `schemas/runtime/*.schema.json`
- `schemas/events/envelope.schema.json`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-002.md`
- `docs/patterns/cards/PATTERN-003.md`
- `docs/patterns/cards/PATTERN-004.md`

## Required test coverage (tests-as-spec)
- Unit tests on state transitions (illegal transitions must fail).
- Replay/golden trace tests for AT-SCH-001, AT-SCH-003, AT-SCH-004, and AT-SCH-005.
- Concurrency/idempotency tests for duplicate commands and double-completion.
- Recovery tests proving a reconciler can recover a missed wakeup without duplicating task creation.

## Typical failure modes (red-team prompts)
- “What happens if the worker crashes mid-step?”
- “Can the same request run twice?”
- “Could this leak across tenants/domains?”
- “Does the audit timeline still reconstruct what happened?”
