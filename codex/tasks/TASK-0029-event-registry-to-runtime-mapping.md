---
id: TASK-0029
epic: EPIC-020
title: Map the typed event registry to runtime emission points and tests
status: TODO
owners:
- platform
reviewers:
- sre
- qa
- security
depends_on:
- TASK-0006
- TASK-0023
- TASK-0037
- TASK-0028
risk: medium
context_packs:
- codex/context/EPIC-020.md
patterns:
- PATTERN-001
- PATTERN-003
- PATTERN-008
---

## Context
The event registry and payload schemas exist, and the runtime architecture is now chosen. What is still missing is the command/state-transition to event-emission matrix that tells implementation code exactly which authoritative events must be written, in what transaction boundary, and which tests prove coverage.

## Objective
Define the authoritative command -> event-emission matrix for Stage 4 runtime work and tie it to tests, traces, and required link/payload coverage, including the rule that parent task completion may emit child `task.run.created` / `task.created` events for follow-on work.

## Non-goals
- Do not invent new event types unless the registry and payload schemas are updated first.
- Do not let notification/export workers become the place where authoritative events are emitted.
- Do not treat advisory wakeups as substitutes for canonical timeline events.
- Do not create a hidden child-task side-effect path outside the canonical event model.

## Source files to read first
- `docs/planning/RUNTIME_BOOTSTRAP.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/architecture/event_model.md`
- `schemas/events/event_type_registry.yaml`
- `schemas/events/payloads/*.schema.json`
- `docs/planning/TEST_MATRIX.md`
- `fixtures/workflows/schedule_planning/golden_event_traces/*.jsonl`

## Context packs / patterns to consult
- `codex/context/EPIC-020.md`
- `PATTERN-001`
- `PATTERN-003`
- `PATTERN-008`

## Source files to change
- `docs/planning/EVENT_EMISSION_MATRIX.md` (new)
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/planning/TEST_MATRIX.md`
- relevant traces under `fixtures/workflows/schedule_planning/golden_event_traces/` if the matrix exposes missing evidence
- runtime command handlers under `src/onetruth/application/commands/` once implementation starts

## Generated / downstream artifacts impacted
- replay tests
- acceptance oracles
- audit/export feeds
- notification/export workers

## Plan
1. Enumerate the authoritative command/state transitions in the first runtime slice.
2. Map each transition to required event(s), payload schema, required links, and transaction boundary.
3. Make task-completion -> child-task creation explicit, including parent completion, child task-run creation, child human-task creation, and idempotency keys.
4. Mark whether each registry event is first-slice, later-slice, or trace-only today.
5. Tie the matrix to replay/acceptance/security/runtime-scenario tests so missing emissions are easy to detect.

## Verification
- every event type in `schemas/events/event_type_registry.yaml` has either a concrete producer or an explicit defer/not-in-slice note
- every first-slice command has an explicit emitted-event list
- traces and tests cover the Stage06 publish path, Stage07 delta path, policy gate, degraded-mode cases, and child-task spawn cases
- no document implies authoritative events are emitted outside the same commit as the authoritative state change
- child-task creation has explicit parent-causation and idempotency coverage

## Acceptance criteria
- runtime emission points are explicit enough that command handlers can be implemented without guessing
- required links and payload schemas are tied to each emitted event
- first-slice and later-slice event coverage are clearly separated
- tests/traces that prove emission correctness are named

## Notes / decisions
The emission matrix should live as a planning/source doc, not as hidden logic inside the first runtime implementation.
