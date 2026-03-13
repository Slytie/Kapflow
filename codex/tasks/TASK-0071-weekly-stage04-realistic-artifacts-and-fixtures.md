---
id: TASK-0071
epic: EPIC-025
title: "Realistic Stage04 weekly artifacts, fixture ingestion, and hard-case pilot seeds"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0068", "TASK-0070"]
risk: high
context_packs: ["codex/context/EPIC-025.md", "codex/context/EPIC-070.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-005", "PATTERN-009"]
---

## Context
The current weekly Stage04 deterministic slice was real but still built around toy planning inputs. The real uploaded examples show operations already think in driver-by-day roster states and daily route demand. This task upgrades the Stage04 input surface and pilot/fixture layer so the weekly planner can consume realistic day-resolution planning data while preserving the existing workflow/stage/runtime architecture.

## Objective
Upgrade the Stage04 input surface and pilot fixture layer so the weekly planner can consume realistic day-resolution planning data while preserving the existing architecture. Specifically:
- keep the same artifact kinds already consumed by Stage04,
- enrich those artifact payloads to carry driver-day availability, previous-week state, rolling-7 compliance inputs, and policy metadata,
- add a realistic hard weekly pilot/fixture builder using the real spreadsheet/email patterns,
- keep the existing tiny 2-driver pilot as a smoke/regression fixture.

## Non-goals
- no iterative planner logic in this task,
- no Stage04 Responses tool-loop changes in this task,
- no publish/pointer authority changes,
- no new workflow or stage IDs,
- no second truth system or mutable history ledger.

## Baseline Confirmed Before Changes
- `PYTHONPATH=src pytest -q tests/unit/test_schedule_control_bundle_builder.py` - passed (`.. [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py` - passed (`. [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/test_logistics_weekly_agent_pilot.py` - passed (`.. [100%]`)
- `PYTHONPATH=src python3 scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/task0071-baseline.db --pilot-key task0071-baseline --openai-mode mock --json` - passed (`status=ok`, pilot `weekly_stage04_agent_baseline`)

## Source Files Changed
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/weekly_schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/weekly_schedule_planning/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/logistics_ops_family/v1/METHOD_PACKAGES.yaml`
- `src/onetruth/application/services/schedule_control/route_slot_requirements.py`
- `src/onetruth/application/services/schedule_control/bundle_builder.py`
- `src/onetruth/application/services/schedule_control/rendering.py`
- `src/onetruth/application/services/schedule_control/validation.py`
- `src/onetruth/application/services/schedule_control/__init__.py`
- `src/onetruth/application/services/logistics_weekly_agent_pilot.py`
- `fixtures/scenarios/logistics/weekly_schedule_build_deterministic_slice.yaml`
- `fixtures/logistics/weekly_stage04_realistic_source_material.yaml`
- `tests/unit/test_schedule_control_bundle_builder.py`
- `tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py`
- `tests/runtime/test_logistics_weekly_agent_pilot.py`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0071-weekly-stage04-realistic-artifacts-and-fixtures.md`

## Verification Run
- `make schema-validate` - passed (`VALIDATION PASSED`, 1357 checks passed)
- `PYTHONPATH=src pytest -q tests/unit/test_schedule_control_bundle_builder.py` - passed (`... [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/scenarios/test_weekly_schedule_build_deterministic_slice.py` - passed (`.. [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/test_logistics_weekly_agent_pilot.py` - passed (`... [100%]`)
- `PYTHONPATH=src python3 scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/logistics-weekly-stage04-pilot.db --pilot-key realistic-artifacts --openai-mode mock --json` - passed (`status=ok`; pilot suite emitted both `weekly_stage04_agent_baseline` and `weekly_stage04_realistic_artifacts`)

## Acceptance Criteria Coverage
- Existing Stage04 artifact kinds remain the same, but their payloads now support realistic day-resolution planning inputs.
- Bundle parsing remains backward compatible with the existing tiny smoke fixture.
- A realistic hard weekly pilot fixture now exists and uses deterministic roster/email source material derived from the real uploaded examples.
- The realistic pilot preserves canonical artifact/evidence/runtime behavior and remains draft-only.
- Ops-relevant fields such as driver-day state, previous-week state, rolling-7 inputs, and policy signals are now present in Stage04 planning inputs.

## Completion Notes
- Stage04 route-slot, driver-capability, availability, and actual-hours payload parsing is now additive: richer fields are supported while the original tiny fixture shape still parses unchanged.
- The Stage04 input bundle now renders daily demand summaries plus per-driver profiles with planning-week day states, prior-week state, rolling-7 compliance snapshots, and policy metadata.
- Added a shared deterministic 40-driver realistic source-material fixture and a new realistic Stage04 pilot path without changing workflow IDs, stage IDs, runtime truth semantics, or the bounded Responses tool loop.
- The realistic hard-case source keeps total weekly demand at 112 shifts across 40 active drivers, preserving the “below four shifts per driver across the week” property while remaining harder than the tiny smoke slice because many driver-days are intentionally blocked or restricted.
