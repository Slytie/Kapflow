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

Stage04 input resolution is fail-closed and typed:
- the runtime resolves Stage04 bridge/input slots from an explicit weekly authored dataset-key registry,
- that registry is validated against repo-native workflow source (`WORKFLOW_CONTRACT.yaml`, `ARTIFACT_MAP.yaml`, `EXECUTION_PROFILE.yaml`),
- compiled `required_evidence_keys` must contain the exact authored Stage04 bridge keys with no conflicting alias-equivalent keys.

## Responses function-calling loop
Runner:
- `OpenAIResponsesFunctionCallingRunner`

Behavior:
- submits an initial Responses request with bounded Stage04 prompts + function tool specs,
- sends a compact model-facing Stage04 context summary instead of embedding the full context-pack artifact in the initial prompt,
- accepts zero/one/many `function_call` items per model turn,
- executes deterministic tools,
- appends matching `function_call_output` items using model-returned `call_id`,
- sends compact model-facing tool outputs back to the model while preserving full deterministic tool outputs in runtime evidence artifacts,
- persists per-turn request/result evidence as the loop advances,
- enforces authored `no_progress_ticks` from compiled Stage04 control metadata,
- requires an explicit deterministic finalize tool call before any Stage04 draft artifacts are materialized,
- retries `rate_limit_exceeded` Responses calls inside the same turn with bounded `Retry-After`/message-derived backoff before failing the execution,
- continues until a turn returns no function calls or the authored stop budget is exhausted.

Budget source:
- Stage04 method-package stop policy (`max_tool_calls`) from compiled control metadata.

## Deterministic tools exposed
Only deterministic Stage04 tools are exposed:
- `get_stage04_context`
- `preview_stage04_next_iteration`
- `apply_stage04_next_iteration`
- `get_stage04_validation_summary`
- `get_stage04_iteration_analysis`
- `finalize_weekly_stage04_draft_outputs`

These tools map to deterministic schedule-control behavior only:
- preview/apply execute bounded deterministic allocation rounds,
- validation/iteration analysis are read-only review helpers,
- finalize persists the existing draft-only Stage04 artifact keys from the already-executed deterministic state.

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

Shared helper posture:
- weekly Stage04 uses the same `execution_evidence.py` helper surface as Stage06 for stable execution IDs, artifact-root resolution, and prepared evidence persistence,
- local/dev/test runs should set `ONETRUTH_ARTIFACT_ROOT` to a temp or output-specific directory when isolation matters,
- default fallback `.onetruth_artifacts/` remains local-only live evidence and is not a fixture source.

Evidence captures:
- full context pack payload plus the compact model-facing initial context summary,
- per-turn request/response metadata,
- function calls, parsed compact `function_call_output` payloads, full evidence tool outputs, and progress accounting,
- response/request ids and usage,
- request retry attempts/history when rate limiting occurs,
- execution trace summary including turn evidence refs, finalize state, and exhausted retry details.

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

Pilot selection posture:
- `weekly_stage04_realistic_artifacts` is the default real-network Stage04 pilot and is pinned to the over-capacity `PW-2026-W12` source-material contract under `fixtures/logistics/weekly_stage04_realistic_source_material.yaml`,
- `weekly_stage04_actual_ops_lab` is an explicit-only Stage04 pilot pinned to the Sunday-start `PW-2026-W13` actual-ops lab package under `fixtures/logistics/weekly_stage04_actual_ops_lab_source_material.yaml`,
- `weekly_stage04_agent_baseline` remains available as the tiny `PW-2026-W10` smoke/regression pilot for local/mock coverage,
- when `scripts/run_logistics_weekly_agent_pilot.py` is invoked with `--openai-mode mock` and no explicit `--pilot`, it still runs only the baseline + realistic pilots by default,
- when `scripts/run_logistics_weekly_agent_pilot.py` is invoked with `--openai-mode real` and no explicit `--pilot`, it still runs only the realistic over-capacity pilot by default,
- the actual-ops lab pilot must be selected explicitly with `--pilot weekly_stage04_actual_ops_lab` or `--pilot all`.
- that realistic real-network pilot applies a pilot-scoped `ONETRUTH_OPENAI_MODEL=gpt-5-mini` override only for the live Stage04 call; shared repo defaults remain unchanged and effective TPM limits still depend on the active project/org tier instead of hardcoded assumptions.

Inspection packets are canonical-reference-heavy and include:
- workflow/task/execution/tool/policy/artifact IDs,
- evidence coverage by artifact kind (`execution.*`, `runtime.*`, Stage04 output kinds),
- iteration-level route allocation, repair, uncovered-route, and tradeoff analysis derived from canonical Stage04 artifacts,
- runtime turn-by-turn function/progress summaries derived from canonical evidence artifacts,
- timeline events of interest and derived inspection routes,
- canonical CLI query commands for debugging.

## Real-network e2e gate
Weekly Stage04 real-network tests remain deliberately gated:
- required env gate 1: `ONETRUTH_RUN_OPENAI_E2E=1`
- required env gate 2: `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E=1`
- required secret: `OPENAI_API_KEY`

Coverage file:
- `tests/integration_openai/test_weekly_stage04_openai_real_e2e.py`

That dual-gated real-network Stage04 e2e now exercises the realistic over-capacity weekly pilot rather than the tiny two-route smoke scenario.

Current live-token posture:
- the dominant TPM driver is cumulative repeated `function_call_output` context, not the initial prompt,
- Stage04 therefore keeps full `runtime.context_pack.json` and `runtime.tool_result.json` evidence artifacts for reviewability while sending compact model-facing summaries/deltas across live turns,
- the realistic mock/runtime regression suite guards this compact surface by checking request-size ceilings, omission of oversized repeated fields, preserved full evidence payloads, and bounded 429 retry behavior.
