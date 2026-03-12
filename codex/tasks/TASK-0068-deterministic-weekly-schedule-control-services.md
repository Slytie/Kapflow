---
id: TASK-0068
epic: EPIC-025
title: "Deterministic weekly schedule-control services for Stage04 runtime slice"
status: DONE
owners: ["platform"]
reviewers: ["ops", "qa"]
depends_on: ["TASK-0067"]
risk: high
context_packs: ["codex/context/EPIC-040.md", "codex/context/EPIC-025.md"]
patterns: ["PATTERN-003"]
---

## Objective
Implement deterministic Stage04 weekly schedule-control services as first-class runtime components, including:
- canonical bundle resolution from Stage04 bridge artifacts,
- route-slot expansion and deterministic candidate generation,
- hard-rule validation and soft scoring owned by deterministic code,
- artifact lowerings for Stage04 machine-checkable outputs,
- one runtime scenario proving deterministic weekly build works end-to-end.

## Non-goals
- no Stage06/Stage07 publication changes,
- no LLM-authored hard-rule feasibility path,
- no new parallel truth subsystem.

## Source Files Changed
- `src/onetruth/application/services/schedule_control/__init__.py`
- `src/onetruth/application/services/schedule_control/bundle_builder.py`
- `src/onetruth/application/services/schedule_control/route_slot_requirements.py`
- `src/onetruth/application/services/schedule_control/candidate_generation.py`
- `src/onetruth/application/services/schedule_control/validation.py`
- `src/onetruth/application/services/schedule_control/scoring.py`
- `src/onetruth/application/services/schedule_control/rendering.py`
- `src/onetruth/application/handlers/schedule_control.py`
- `src/onetruth/cli/__main__.py`
- `src/onetruth/application/services/logistics_handoff_runtime.py`
- `tests/runtime/helpers/scenario_harness.py`
- `tests/unit/test_schedule_control_bundle_builder.py`
- `tests/unit/test_schedule_control_validation.py`
- `tests/unit/test_schedule_control_scoring.py`
- `fixtures/scenarios/logistics/weekly_schedule_build_deterministic_slice.yaml`
- `tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0068-deterministic-weekly-schedule-control-services.md`

## Verification Run
- `pytest -q tests/unit/test_schedule_control_bundle_builder.py tests/unit/test_schedule_control_validation.py tests/unit/test_schedule_control_scoring.py`
- `pytest -q tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py`
- `pytest -q tests/unit/test_logistics_handoff_runtime.py tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py`
- `pytest -q tests/runtime/scenarios/test_logistics_weekly_to_live_golden_slice.py`
- `pytest -q tests/runtime/test_logistics_handoff_runtime.py`
- `pytest -q tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py tests/unit/test_schedule_control_scoring.py`
- `make schema-validate` (run three times)

All commands passed on 2026-03-12.

## Acceptance Criteria Coverage
- Stage04 deterministic service package now owns bundle resolution, route-slot expansion, candidate generation, hard validation, soft scoring, and Stage04 artifact lowering behavior.
- Runtime command surface (`schedule-control build-weekly`) now executes deterministic weekly build slice and materializes Stage04 artifacts idempotently.
- Runtime scenario (`weekly_schedule_build_deterministic_slice`) proves end-to-end deterministic output + retry-safe artifact identity.
- Existing handoff deterministic ranking behavior remains stable by reusing shared schedule-control scoring ranking utility.

## Completion Notes (2026-03-12)
- Added first-class deterministic weekly schedule-control services under `src/onetruth/application/services/schedule_control/` and kept feasibility logic out of generic task lifecycle handlers.
- Added bounded Stage04 runtime command integration via a dedicated handler + CLI + scenario harness action mapping.
- Landed focused unit tests for bundle-building/validation/scoring and a runtime scenario slice proving deterministic weekly Stage04 artifacts are produced replay-safely.
