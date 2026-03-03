# ADR-003 - Stage 4 runtime architecture

## Status
Accepted

## Decision
Stage 4 runtime will be instantiated as a **Python modular monolith** with:
- runtime code under `src/onetruth/`
- PostgreSQL for canonical current-state rows plus append-only `timeline_events`
- a pluggable object-store adapter for immutable artifact contents
- background workers for decider/reconciliation, lease expiry, projection rendering, exports, and later generator work

The canonical event timeline will also serve as the relay surface for derived consumers via durable cursors.
Stage 4 will **not** use an external workflow engine as the source of runtime truth, and it will **not** start with microservices.

## Why
The repo now has contract-closed semantics, runtime object schemas, typed event payloads, and a Schedule Planning-first test corpus. The remaining risk was implementation ambiguity.

The chosen architecture best preserves:
- one truth system
- one workflow/task/approval/event substrate
- transactional coupling between state change and timeline emission
- a small enough operational footprint for the first vertical slice

## Consequences
- the first runtime scaffold should create `src/onetruth/`, `alembic/`, and `tests/runtime/`
- the first code slice should prove the Schedule Planning Stage06 publish path before generalized abstractions or UI work
- `timeline_events` remains the canonical event substrate; derived consumers advance from durable cursors rather than a rival authoritative outbox
- artifact bytes remain separate from artifact officialness; pointers and pointer events decide officialness
- future decomposition or external orchestration engines would require a new ADR because they risk introducing a second truth surface
