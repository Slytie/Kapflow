# EPIC-090 context pack - Acceptance, traces, and runtime scenarios

## What this epic now covers
EPIC-090 is no longer only about replay/acceptance traces.
It also covers the **runtime scenario harness** that will let an agent execute each step and prove the same semantics against the real runtime.

## Read this pack when
- adding or updating golden traces
- changing acceptance evidence requirements
- planning or implementing the runtime step-run scenario harness
- adding tests for conditional task spawning / explicit child-task lineage

## Read first
- `docs/planning/TEST_STRATEGY.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `fixtures/workflows/schedule_planning/README.md`

## Key reminders
- traces remain the first behavioral corpus
- runtime scenario tests must still assert authoritative events, not hidden internals
- seed example artifacts from the existing `template_pack/` folders
- child-task spawning must stay explicit, bounded, and idempotent
