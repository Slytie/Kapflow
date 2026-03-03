# Planning docs

Planning in this repo should answer four questions for a fresh contributor:
1. what is the current milestone?
2. what is authoritative?
3. what concrete runtime architecture has been chosen?
4. what is deferred but must not be forgotten?

Key files:
- `STAGE4_PLAN.md`
- `RUNTIME_BOOTSTRAP.md`
- `FIRST_RUNTIME_SLICE.md`
- `STEP_RUN_SCENARIO_HARNESS.md`
- `EPICS.md`
- `TASK_INDEX.md`
- `TEST_STRATEGY.md`
- `TEST_MATRIX.md`
- `TDD_IMPLEMENTATION_PLAN.md`
- `MERGER_BACKLOG.md`

Practical routing:
- `RUNTIME_BOOTSTRAP.md` answers the chosen stack, persistence model, and repo layout.
- `FIRST_RUNTIME_SLICE.md` answers what should be written first, where it should live, and what should wait.
- `STEP_RUN_SCENARIO_HARNESS.md` answers how agent-executed step tests should be structured once runtime code exists.
- `TDD_IMPLEMENTATION_PLAN.md` answers how to use schemas, traces, pytest oracles, and synthetic example artifacts while implementing.

For fresh-session execution:
- use `codex/context/` for short epic context packs,
- use `docs/patterns/` for external architecture references in card form,
- use `docs/research/AGENT_DIGEST.md` before opening long research notes.
