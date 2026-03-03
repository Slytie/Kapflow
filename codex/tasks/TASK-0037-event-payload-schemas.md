---
id: TASK-0037
epic: EPIC-020
title: "Add event payload schemas and registry bindings"
status: DONE
owners:
- platform
reviewers:
- sre
- qa
- security
depends_on:
- TASK-0034
- TASK-0036
risk: high
context_packs:
- codex/context/EPIC-020.md
patterns:
- PATTERN-001
- PATTERN-003
- PATTERN-008
---

## Context
The repo has an event envelope schema and an event-type registry, but payload contracts are still missing for most authoritative events. That leaves replay and emission mapping under-specified.

## Objective
Add machine-readable payload schemas for the canonical event types and bind them to the registry.

## Non-goals
- Do not redesign the event taxonomy.
- Do not turn event payloads into a second runtime model.
- Do not postpone key payload decisions into implementation code.

## Source files to read first
- `schemas/events/envelope.schema.json`
- `schemas/events/event_type_registry.yaml`
- `docs/architecture/event_model.md`
- `docs/architecture/orchestration_semantics.md`
- `schemas/runtime/` (new runtime object schemas)

## Context packs / patterns to consult
- `codex/context/EPIC-020.md`
- `PATTERN-001`
- `PATTERN-003`
- `PATTERN-008`

## Source files to change
- `schemas/events/event_type_registry.yaml`
- `schemas/events/payloads/*.schema.json`
- event-model docs if field expectations need sharpening

## Generated / downstream artifacts impacted
- golden traces
- replay tests
- event emission mapping
- projection coherence checks

## Plan
1. Prioritize business-critical events used by Schedule Planning acceptance and shared runtime semantics.
2. Define minimal required payload fields per event type.
3. Bind each event type to its payload schema.
4. Validate existing traces against envelope + payloads.

## Verification
- Event payload schemas parse successfully.
- Existing traces validate or fail with actionable mismatch output.
- Registry references payload contracts consistently.

## Acceptance criteria
- canonical event types have machine-readable payload requirements
- replay/acceptance fixtures can validate against envelope + payload schemas
- later runtime emission mapping can rely on typed contracts rather than prose only

## Notes / decisions
Start with the events required by the Schedule Planning acceptance objective and shared runtime invariants.


## Completion notes
- Completed in the repo-native semantic-closure tranche on 2026-03-02.
