# EPIC-020 - Authoritative TimelineEvent + Outbox + Degraded mode

## Summary
Freeze the shared event model for business execution and agentic execution.

## Why this epic exists (risk retired)
Retires the risk of missing audit truth and prevents a second event system from emerging beside the business timeline.

## Scope
### In scope
- timeline envelope
- event type registry
- event payload contracts
- degraded mode semantics
- business + execution-facet event taxonomy

### Out of scope
- full deterministic replay
- mature WorkGraph implementation

## Dependencies
- EPIC-010
- EPIC-015

## Key decisions / constraints
- one timeline, not separate business and agent timelines
- derived stores may degrade; authoritative event persistence may not silently disappear

## Recommended pattern cards (read cards first)
- `PATTERN-001`
- `PATTERN-003`
- `PATTERN-008`

Context pack: `codex/context/EPIC-020.md`

Also see `docs/patterns/PATTERN_INDEX.yaml` for the full tagged library.

## Deliverables
- `schemas/events/envelope.schema.json`
- `schemas/events/event_type_registry.yaml`
- `schemas/events/payloads/*`
- `docs/architecture/event_model.md`
- `docs/ops/degraded_mode.md`

## Definition of Done
- event envelope and registry cover both business and execution-facet events
- degraded mode is explicit, visible, and testable
- payload requirements are machine-readable for the canonical events

## Tasks
- TASK-0003
- TASK-0006
- TASK-0007
- TASK-0029
- TASK-0037
