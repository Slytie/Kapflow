---
id: TASK-0069
epic: EPIC-070
title: "Weekly Stage04 OpenAI agent runtime over compiled control and Responses API function calling"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0066", "TASK-0068"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-025.md", "codex/context/EPIC-040.md", "codex/context/EPIC-060.md"]
patterns: ["PATTERN-005", "PATTERN-003"]
---

## Objective
Implement a bounded Stage04 weekly agent runtime slice that uses the OpenAI Responses API function-calling lifecycle over compiled Stage04 control metadata, exposes only deterministic Stage04 tools, and persists canonical execution evidence without introducing publish authority or a second truth path.

## Non-goals
- no background mode,
- no deprecated Assistants API usage,
- no Stage05/Stage06 bypass,
- no free-form model authority over official schedule publication,
- no generalized public multi-agent API framework.

## Source Files Changed
- `src/onetruth/integrations/openai/responses_agent_runner.py`
- `src/onetruth/integrations/openai/responses_adapter.py`
- `src/onetruth/integrations/openai/__init__.py`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/application/services/execution_evidence.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/api/main.py`
- `tests/unit/test_responses_agent_runner.py`
- `tests/runtime/test_weekly_stage04_execution_runtime.py`
- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`
- `tests/runtime/api/test_human_task_list_contract.py`
- `docs/planning/WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md`
- `README.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0069-weekly-stage04-openai-agent-runtime.md`

## Verification Run
- `make schema-validate`
- `PYTHONPATH=src pytest -q tests/unit/test_responses_agent_runner.py`
- `PYTHONPATH=src pytest -q tests/runtime/test_weekly_stage04_execution_runtime.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `PYTHONPATH=src pytest -q tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`
- `PYTHONPATH=src pytest -q tests/unit/test_openai_responses_adapter.py tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `PYTHONPATH=src pytest -q tests/runtime/api/test_human_task_list_contract.py tests/runtime/api/test_workspace_actionability.py tests/runtime/test_execution_session_runtime.py`

All commands passed on 2026-03-12.

## Acceptance Criteria Coverage
- Added a synchronous bounded Responses function-calling runner that supports zero/one/many function calls per turn and uses `call_id`-bound `function_call_output` continuation.
- Weekly Stage04 runtime now resolves execution semantics from compiled control metadata and pins execution session payloads without hardcoded execution-spec constants.
- Exposed only deterministic Stage04 tool functions to the model and kept the slice draft-only (no publish/pointer actions).
- Persisted canonical evidence artifacts for context packs, request turns, result turns, function call I/O, and execution traces linked to execution runtime objects.
- Added bounded API/actionability surface for claimed Stage04 `work_item` tasks plus deterministic unit/runtime/api/scenario tests.

## Completion Notes (2026-03-12)
- Added `POST /api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent` as a bounded Stage04 runtime entrypoint over canonical execution session/tool/policy objects.
- Reused existing deterministic schedule-control runtime (`schedule-control build-weekly`) as the model-callable Stage04 draft materialization tool, preserving replay-safe canonical artifact behavior.
- Extended execution evidence helpers with runtime context/request/result artifact support and locked test coverage for policy denial, idempotent retry behavior, and canonical evidence traceability.
