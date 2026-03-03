---
id: TASK-0038
epic: EPIC-090
title: "Author Schedule Planning fully-agentive golden traces and acceptance oracles"
status: DONE
owners:
- platform
- qa
reviewers:
- security
- ops
depends_on:
- TASK-0033
- TASK-0037
risk: high
context_packs: []
patterns:
- PATTERN-001
- PATTERN-008
---

## Context
Schedule Planning is now the primary runtime/debug wedge, and the repo needs golden traces that demonstrate both the base/replan semantics and the fully-agentive whole-flow objective.

## Objective
Author JSONL golden traces and acceptance oracles for the Schedule Planning runtime/debug wedge, including the fully-agentive path.

## Non-goals
- Do not implement the runtime.
- Do not fake authoritative state outside the canonical event model.
- Do not drop Payroll as a secondary reference corpus.

## Source files to read first
- `docs/workflows/schedule_planning/v1/ACCEPTANCE_CRITERIA.md`
- `docs/planning/TEST_MATRIX.md`
- `schemas/events/envelope.schema.json`
- `schemas/events/event_type_registry.yaml`
- `schemas/events/payloads/` (once added)
- existing Schedule Planning golden traces under `fixtures/workflows/schedule_planning/golden_event_traces/`

## Context packs / patterns to consult
- `PATTERN-001`
- `PATTERN-008`

## Source files to change
- `fixtures/workflows/schedule_planning/golden_event_traces/*.jsonl`
- fixture README files if scenario coverage expands
- acceptance/test docs if scenario IDs need sharpening

## Generated / downstream artifacts impacted
- replay tests
- acceptance oracles
- approval packets / live ops packet examples

## Plan
1. Define the canonical scenario set for Schedule Planning.
2. Author happy-path and negative traces, including the fully-agentive path.
3. Validate traces against the envelope, registry, and payload schemas.
4. Document how replay/acceptance suites consume them.

## Verification
- JSONL traces parse cleanly.
- Traces validate against the event envelope and payload schemas.
- Scenario coverage matches the stable IDs in `docs/planning/TEST_MATRIX.md`.

## Acceptance criteria
- Schedule Planning has golden traces for happy path, drift, fully-agentive whole-flow, lease expiry, degraded mode, and cross-scope denial
- traces are suitable for replay and acceptance oracles
- trace coverage proves the fully-agentive objective without bypassing canonical approvals/pointers/events

## Notes / decisions
Keep trace scenarios stable so future runtime work can treat them as executable memory.


## Completion notes
- Completed in the repo-native semantic-closure tranche on 2026-03-02.
