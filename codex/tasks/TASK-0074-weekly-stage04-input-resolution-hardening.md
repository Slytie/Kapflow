---
id: TASK-0074
epic: EPIC-070
title: "Weekly Stage04 input-resolution hardening over authored dataset-key bindings"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0067", "TASK-0068", "TASK-0069"]
risk: medium
context_packs: ["codex/context/EPIC-025.md", "codex/context/EPIC-070.md"]
patterns: ["PATTERN-003", "PATTERN-005"]
---

## Objective
Replace the weekly Stage04 OpenAI agent's brittle suffix-based required-artifact lookup with a stronger typed resolution path driven by authored dataset-key bindings, while preserving current weekly Stage04 semantics and deterministic draft-only behavior.

## Non-goals
- no weekly/live business-semantics changes,
- no workflow-pack redesign,
- no publish/pointer-promotion behavior changes,
- no generalized artifact-binding framework beyond this bounded Stage04 hardening.

## Source Files Changed
- `src/onetruth/application/services/schedule_control/stage04_input_registry.py`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `tests/runtime/test_weekly_stage04_execution_runtime.py`
- `tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`
- `docs/planning/WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0074-weekly-stage04-input-resolution-hardening.md`

## Verification Run
- `PYTHONPATH=src pytest -q tests/runtime/test_weekly_stage04_execution_runtime.py` - passed (`.... [100%]`)
- `PYTHONPATH=src pytest -q tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py` - passed (`.. [100%]`)
- `python -m compileall -q src tests scripts` - could not run in this environment (`python` was not installed)
- `python3 -m compileall -q src tests scripts` - passed after rerunning outside the sandbox because the sandboxed invocation hit macOS Python cache `PermissionError` writes under `~/Library/Caches/com.apple.python`

## Acceptance Criteria Coverage
- Weekly Stage04 input resolution now uses explicit typed slot bindings over exact authored dataset keys rather than suffix matching.
- The resolver validates its slot registry against the weekly workflow contract, artifact map, and execution profile.
- Compiled Stage04 control metadata now fails closed for missing required bindings or alias-equivalent conflicting keys.
- Regression coverage exists for missing-key, ambiguous-key, and missing-runtime-input cases while keeping the happy path intact.

## Completion Notes
- Introduced a small Stage04 input registry helper in the schedule-control package so the weekly agent can resolve direct bridge inputs and optional upstream inputs from one typed authored surface.
- Kept deterministic Stage04 build semantics unchanged; the hardening is limited to how the agent locates canonical input artifacts before execution.
- Added regression coverage for missing authored bridge bindings, conflicting alias-equivalent keys, and missing runtime inputs without changing the Stage04 happy path.
- Verification results and environment-specific command adjustments are recorded above, and `git diff --check` also passed as a final sanity check.
