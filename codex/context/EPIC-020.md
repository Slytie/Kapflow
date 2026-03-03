# EPIC-020 Context Pack — Authoritative timeline + outbox (audit/reconstructability)

**Purpose (why you might open this):**

- You’re changing event emission, event schemas, or how we persist audit/timeline.
- You’re implementing degraded-mode export/index behavior.
- You’re deciding how workers wake up and resume from the canonical timeline without creating a second event store.

## Non-negotiable invariants to keep in mind
- Timeline is authoritative: emit events transactionally with state changes.
- Events must be strongly linked (tenant/domain, run, task, artifact, approval, execution objects).
- Degraded mode cannot lose the authoritative record (fail-open with later index/export).
- The timeline may wake derived consumers, but those consumers do not become the place where official truth is decided.

## Contracts / schemas to treat as authoritative
- `schemas/events/envelope.schema.json`
- `schemas/events/event_type_registry.yaml`
- `docs/architecture/event_model.md`
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/TEST_MATRIX.md`

## Relevant pattern cards (read cards first)
- `docs/patterns/cards/PATTERN-001.md`
- `docs/patterns/cards/PATTERN-003.md`
- `docs/patterns/cards/PATTERN-008.md`

## Required test coverage (tests-as-spec)
- Schema validation tests for events.
- Golden trace tests on event ordering and linking.
- Negative tests: missing links / wrong tenant must fail.
- Cursor / relay tests proving a missed wakeup can be recovered without duplicating authoritative state changes.

## Typical failure modes (red-team prompts)
- “What happens if the worker crashes mid-step?”
- “Can the same request run twice?”
- “Could this leak across tenants/domains?”
- “Does the audit timeline still reconstruct what happened?”
