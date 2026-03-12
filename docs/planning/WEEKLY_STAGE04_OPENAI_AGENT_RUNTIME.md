# WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md

## Scope
This document defines the bounded Stage04 weekly OpenAI runtime slice for `weekly_schedule_planning.v1`.

The slice is intentionally narrow:
- single-task entrypoint from a claimed Stage04 `work_item` human task,
- synchronous OpenAI Responses function-calling loop,
- deterministic Stage04 schedule-control tools only,
- draft-only outputs (no publish, no Stage05/Stage06 bypass).

## Runtime entrypoint
- API mutation: `POST /api/v1/human-tasks/{human_task_id}/weekly-stage04-openai-agent`
- Service: `run_weekly_stage04_openai_agent(...)`

Preconditions:
- task belongs to `weekly_schedule_planning.v1`,
- task is `Stage04` + `work_item`,
- task is `CLAIMED` by the requesting actor.

## Control metadata and pinning
Execution semantics are resolved from compiled control metadata, not hardcoded execution-spec constants:
- compile family control metadata from authored workflow family + method packages,
- resolve `weekly_schedule_planning:Stage04` stage spec,
- derive canonical execution-session payload via `derive_execution_session_payload`.

This provides:
- pinned `execution_spec_id`,
- pinned method package digest and stage-control digest,
- runtime bindings and stop policy from compiled metadata.

## Responses function-calling loop
Runner:
- `OpenAIResponsesFunctionCallingRunner`

Behavior:
- submits an initial Responses request with bounded Stage04 prompts + function tool specs,
- accepts zero/one/many `function_call` items per model turn,
- executes deterministic tools,
- appends matching `function_call_output` items using model-returned `call_id`,
- continues until a turn returns no function calls or turn budget is exhausted.

Budget source:
- Stage04 method-package stop policy (`max_tool_calls`) from compiled control metadata.

## Deterministic tools exposed
Only deterministic Stage04 tools are exposed:
- `get_stage04_context`
- `materialize_weekly_stage04_draft_outputs`
- `get_stage04_validation_summary`
- `render_stage04_ops_packet`

These tools map to deterministic schedule-control behavior and draft artifact materialization only.

No publish/pointer-promotion actions are exposed.

## Canonical execution and evidence
Canonical runtime lifecycle is preserved:
- `execution_sessions`
- `tool_executions`
- `policy_decisions`
- timeline events (`execution.session.*`, `tool.execution.*`)

Evidence artifacts linked to execution runtime objects:
- `execution.compiled_spec.json`
- `execution.compile_source_manifest.json`
- `runtime.context_pack.json`
- `runtime.tool_request.json`
- `runtime.tool_result.json`
- `execution.trace.json`

Evidence captures:
- context pack payload,
- per-turn request/response metadata,
- function calls and `function_call_output` payloads,
- response/request ids and usage,
- execution trace summary.

## Policy posture
Policy-gated before model execution:
- default allow roles: `schedule_planner`, `operations_manager`, `system_worker` (plus `system/service` actor types),
- explicit allow/deny/require-approval decisions recorded canonically,
- deny/require-approval paths fail closed without model execution.

## Verification suites
- `tests/unit/test_responses_agent_runner.py`
- `tests/runtime/test_weekly_stage04_execution_runtime.py`
- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`
- `tests/runtime/test_logistics_weekly_agent_pilot.py`

## Weekly Stage04 pilot runner
Reproducible pilot runner:
- script: `scripts/run_logistics_weekly_agent_pilot.py`
- service: `src/onetruth/application/services/logistics_weekly_agent_pilot.py`

Pilot behavior:
- seeds canonical Stage04 input artifacts (`route_slot_requirements`, `driver_capabilities`, `approved_availability`, `actual_hours`),
- creates and claims a Stage04 `work_item` human task,
- executes the bounded weekly Stage04 agent in `mock` or `real` mode,
- emits inspection packet artifacts (`inspection_packet.json` and `.md`) plus suite summary artifacts (`pilot_summary.json` and `.md`).

Inspection packets are canonical-reference-heavy and include:
- workflow/task/execution/tool/policy/artifact IDs,
- evidence coverage by artifact kind (`execution.*`, `runtime.*`, Stage04 output kinds),
- timeline events of interest and derived inspection routes,
- canonical CLI query commands for debugging.

## Real-network e2e gate
Weekly Stage04 real-network tests remain deliberately gated:
- required env gate 1: `ONETRUTH_RUN_OPENAI_E2E=1`
- required env gate 2: `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1`
- required secret: `OPENAI_API_KEY`

Coverage file:
- `tests/integration_openai/test_weekly_stage04_openai_real_e2e.py`
