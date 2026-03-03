# tests/ - Test portfolio (Stage 4, Schedule-first)

This repo treats tests as **executable specifications** for the platform invariants.

Read first:
- `docs/planning/TEST_STRATEGY.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/TDD_IMPLEMENTATION_PLAN.md`

## Current posture
- **Primary runtime/debug wedge:** Schedule Planning v1
- **Primary acceptance objective:** a fully-agentive end-to-end Schedule Planning flow that still uses the canonical workflow/task/approval/event/pointer substrate
- **Secondary reference workflow:** Payroll v1 as the linear approval-heavy governance benchmark

## Directory purpose
- `helpers/` - non-authoritative test harness helpers used to turn schemas + golden traces into executable oracles
  - `reference_model.py` - small replay reducer used only for tests
  - `scenario_catalog.py` - stable AT-SCH scenario-to-trace mapping
  - `trace_loader.py` - JSONL trace loader
- `unit/` - deterministic reducer and invariant tests
- `integration/` - repository integration and CLI/trace usability checks
- `contract/` - validator and schema/trace contract checks
- `property/` - invariant tests that range across the whole trace corpus
- `replay/` - replay stored event histories (golden traces)
- `acceptance/` - AT-SCH acceptance oracles backed by golden traces
- `runtime/scenarios/` - planned future step-run tests where the real runtime is driven one command at a time
- `security/isolation/` - cross-tenant and cross-domain negative tests
- `security/agent/` - agent/tool/approval-path regression tests
- `chaos/` - scheduled failure-mode experiments (still mostly future work)

## Important nuance
The files in `tests/helpers/` are **not a second runtime implementation**. They are a deliberately small, non-authoritative oracle layer so a fresh Codex agent can start with:
- replayable behavioral expectations,
- stable scenario IDs,
- and concrete acceptance evidence requirements.

The authoritative source of truth still lives in:
- workflow packs under `docs/workflows/*/v1/`
- shared architecture docs under `docs/architecture/`
- schemas under `schemas/`
- golden traces under `fixtures/workflows/**/golden_event_traces/`
- synthetic example artifacts under `fixtures/workflows/*/template_pack/` for runtime scenario seeding

## Default commands
- `make schema-validate`
- `make contract`
- `make unit`
- `make replay`
- `make acceptance`
- `make security`
- `make test`

## Rule of thumb
Any change to workflow semantics should update, in order:
1. the authoritative docs/schemas,
2. the relevant golden traces,
3. the scenario catalog / replay or acceptance tests,
4. then any runtime implementation code.

## Replay nuance
- Trace file order is the authoritative replay order for the current oracle layer. Timestamps must remain parseable and sensible, but reducer tests should not silently replace file order with timestamp sorting.
