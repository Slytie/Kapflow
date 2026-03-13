---
id: TASK-0072
epic: EPIC-025
title: "Iterative deterministic Stage04 route allocation, bounded repair moves, and stability-aware validation"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0071"]
risk: high
context_packs: ["codex/context/EPIC-025.md", "codex/context/EPIC-070.md"]
patterns: ["PATTERN-005", "PATTERN-009"]
---

## Context
The previous deterministic Stage04 build used a one-shot full-week candidate ranking pass. This task keeps deterministic services as the truth owner, but refactors the planner internals into a bounded partial-schedule allocation and repair loop over the richer day-resolution Stage04 inputs from TASK-0071.

## Objective
Implement deterministic iterative Stage04 planning so the weekly draft schedule is built through bounded allocation rounds instead of one monolithic selection pass. Specifically:
- maintain a partial weekly schedule state,
- allocate 5-10 routes per iteration,
- allow bounded local repair moves,
- enforce hard rules using driver-day availability and rolling-7 context,
- make previous-week stability explicit in scoring and review artifacts,
- keep the same Stage04 artifact keys while enriching their payloads.

## Non-goals
- no Responses API wrapper changes in this task,
- no new runtime object families,
- no publish/pointer changes,
- no generalized optimization framework beyond the bounded Stage04 planner.

## Source Files Changed
- `src/onetruth/application/services/schedule_control/__init__.py`
- `src/onetruth/application/services/schedule_control/candidate_generation.py`
- `src/onetruth/application/services/schedule_control/scoring.py`
- `src/onetruth/application/services/schedule_control/validation.py`
- `src/onetruth/application/services/schedule_control/rendering.py`
- `src/onetruth/application/services/schedule_control/planning_state.py`
- `src/onetruth/application/services/schedule_control/iterative_allocator.py`
- `src/onetruth/application/handlers/schedule_control.py`
- `tests/unit/test_schedule_control_scoring.py`
- `tests/unit/test_schedule_control_validation.py`
- `tests/unit/test_schedule_control_iterative_allocator.py`
- `tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py`
- `tests/runtime/test_logistics_weekly_agent_pilot.py`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0072-weekly-stage04-iterative-deterministic-allocation.md`

## Verification Run
- `make schema-validate` - passed (`VALIDATION PASSED`, 1358 checks passed)
- `PYTHONPATH=src pytest -q tests/unit/test_schedule_control_scoring.py tests/unit/test_schedule_control_validation.py` - passed (`........ [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py` - passed (`.. [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/test_logistics_weekly_agent_pilot.py` - passed (`... [100%]`)
- `PYTHONPATH=src python3 scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/logistics-weekly-stage04-pilot.db --pilot-key iterative-deterministic --openai-mode mock --json` - passed (`status=ok`; emitted both `weekly_stage04_agent_baseline` and `weekly_stage04_realistic_artifacts`)
- Extra focused unit coverage: `PYTHONPATH=src pytest -q tests/unit/test_schedule_control_iterative_allocator.py` - passed (`. [100%]`)

## Acceptance Criteria Coverage
- Deterministic Stage04 planning now uses an iterative partial-schedule allocation/repair loop instead of only one-shot global selection.
- The realistic planner batches 5-10 routes per iteration (with the tiny two-route smoke slice preserved as the small regression exception).
- Hard validation now checks driver-day availability state, overlap/rest, max shifts, and rolling-7 limits against the evolving partial schedule.
- Soft scoring now carries previous-week stability as a first-class term alongside coverage pressure, availability fit, target-shift gap, seniority, and reliability.
- Final Stage04 artifact keys remain unchanged, but the payloads now include per-iteration deltas, coverage summaries, churn/repair counts, uncovered routes, and review tradeoffs.
- The realistic weekly pilot now emits iteration-driven Stage04 outputs that expose harder coverage gaps without changing the runtime truth path.

## Completion Notes
- The deterministic allocator now grows the week as a partial schedule: choose the highest-pressure day/zone batch, evaluate candidates against the current schedule state, commit each accepted assignment immediately, then attempt a small local reassignment search before finalizing uncovered slots.
- Output artifacts still use the same Stage04 dataset keys, but `planning.candidate_schedule_delta.workbook`, `planning.validation_summary.doc`, and `planning.draft_weekly_schedule.*` now surface `iteration_deltas`, coverage/churn summaries, stability-aware scores, and repair counts so reviewers can see exactly what each deterministic round changed.
