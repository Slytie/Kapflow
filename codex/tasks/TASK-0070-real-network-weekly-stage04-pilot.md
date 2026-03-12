---
id: TASK-0070
epic: EPIC-070
title: "Real-network weekly Stage04 pilot runner, inspection packet hardening, and dual-gated e2e coverage"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0069", "TASK-0065", "TASK-0054"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-005", "PATTERN-009"]
---

## Objective
Add a reproducible weekly Stage04 pilot runner for the logistics wedge with mock and real OpenAI modes, a canonical-reference-heavy inspection packet contract, and a deliberate dual-gated weekly real-network integration test path without removing existing Stage06 real-network coverage.

## Non-goals
- no Stage04 publish/pointer promotion authority changes,
- no agent-only truth path outside canonical workflow/task/approval/event/pointer/runtime objects,
- no unconditional real-network CI execution.

## Source Files Changed
- `src/onetruth/application/services/logistics_weekly_agent_pilot.py`
- `scripts/run_logistics_weekly_agent_pilot.py`
- `tests/runtime/test_logistics_weekly_agent_pilot.py`
- `tests/integration_openai/test_weekly_stage04_openai_real_e2e.py`
- `.github/workflows/agent_api.yml`
- `Makefile`
- `README.md`
- `docs/planning/WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0070-real-network-weekly-stage04-pilot.md`

## Verification Run
- `python3 scripts/validate_repo.py --schemas-only` - passed
- `PYTHONPATH=src python3 scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/logistics-weekly-stage04-pilot.db --pilot-key verify-task-0070-fresh --openai-mode mock --json` - passed
- `PYTHONPATH=src pytest -q tests/runtime/test_logistics_weekly_agent_pilot.py tests/runtime/test_weekly_stage04_execution_runtime.py tests/runtime/api/test_weekly_stage04_openai_agent_api.py tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py` - passed
- `PYTHONPATH=src pytest -q tests/integration_openai/test_weekly_stage04_openai_real_e2e.py` - passed (skipped: dual real-network gate not enabled)
- `PYTHONPATH=src pytest -q tests/integration_openai/test_stage06_openai_real_e2e.py` - passed (skipped: real-network gate not enabled)

## Acceptance Criteria Coverage
- Added a weekly Stage04 logistics pilot service/runner with deterministic IDs and repeat-safe reuse semantics keyed by `(pilot_key, pilot_id)`.
- Pilot now supports `openai_mode=mock|real` while preserving canonical workflow/task/artifact/execution truth and using the existing bounded Stage04 runtime path.
- Inspection packets now include canonical IDs, evidence-by-kind references, timeline events of interest, derived inspection routes, and canonical CLI query commands for debugging.
- Added gated weekly real-network e2e coverage under `tests/integration_openai/test_weekly_stage04_openai_real_e2e.py`.
- Enforced recommended dual gate for weekly real-network path: `ONETRUTH_RUN_OPENAI_E2E=1` and `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1`.
- Kept Stage06 real-network test file and gating intact.

## Completion Notes (2026-03-12)
- CI posture was simplified from a future placeholder weekly directory to real `tests/integration_openai` execution, with weekly Stage04 real-network execution intentionally controlled by the additional weekly env gate.
- Added Makefile targets for deliberate weekly real-network invocation (`integration-openai-weekly-stage04`) and reproducible weekly pilot execution (`logistics-weekly-stage04-pilot`).
- Documentation/status records now point to the new pilot runner, inspection packet contract, and dual-gated weekly real-network path.
