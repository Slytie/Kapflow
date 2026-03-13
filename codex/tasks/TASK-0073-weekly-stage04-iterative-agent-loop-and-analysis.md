---
id: TASK-0073
epic: EPIC-070
title: "Iterative Stage04 Responses tool loop, per-iteration evidence, and realistic pilot analysis packet"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0071", "TASK-0072"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-025.md", "codex/context/EPIC-080.md"]
patterns: ["PATTERN-005", "PATTERN-009"]
---

## Context
The current Stage04 Responses wrapper is bounded and architecture-correct, but it still assumes a one-shot build: narrow tool catalog, aggregate end-of-run evidence, and an unconditional post-loop deterministic materialization. Once deterministic planning becomes iterative, the Stage04 agent should orchestrate those deterministic rounds, persist per-iteration evidence, and produce an analysis packet that ops can review.

## Objective
Upgrade the Stage04 Responses wrapper so it orchestrates the new iterative deterministic planner while staying within the current architecture. Specifically:
- replace the one-shot Stage04 tool catalog with bounded iterative deterministic tools,
- remove unconditional post-loop build/finalization,
- persist per-iteration canonical evidence,
- wire no-progress behavior to the authored Stage04 control metadata,
- produce a realistic weekly pilot inspection packet with iteration-level analysis.

## Non-goals
- no new workflow/stage/runtime object families,
- no background mode or generalized multi-agent runtime,
- no publish/pointer/Stage05/Stage06 authority changes,
- no free-form model-owned scheduling logic.

## Source files to read first
- `AGENTS.md`
- `codex/context/EPIC-070.md`
- `codex/context/EPIC-025.md`
- `docs/workflows/weekly_schedule_planning/v1/EXECUTION_PROFILE.yaml`
- `docs/workflows/logistics_ops_family/v1/METHOD_PACKAGES.yaml`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/integrations/openai/responses_agent_runner.py`
- `src/onetruth/application/services/execution_evidence.py`
- `src/onetruth/application/services/logistics_weekly_agent_pilot.py`
- `tests/unit/test_responses_agent_runner.py`
- `tests/runtime/test_weekly_stage04_execution_runtime.py`
- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`
- `tests/runtime/test_logistics_weekly_agent_pilot.py`
- `tests/integration_openai/test_weekly_stage04_openai_real_e2e.py`

## Context packs / patterns to consult
- `codex/context/EPIC-070.md`
- `docs/patterns/cards/PATTERN-005.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files changed
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/integrations/openai/responses_agent_runner.py`
- `src/onetruth/application/services/execution_evidence.py`
- `src/onetruth/application/services/logistics_weekly_agent_pilot.py`
- `src/onetruth/application/services/schedule_control/__init__.py`
- `src/onetruth/application/services/schedule_control/iterative_allocator.py`
- `src/onetruth/application/handlers/schedule_control.py`
- `tests/unit/test_responses_agent_runner.py`
- `tests/runtime/test_weekly_stage04_execution_runtime.py`
- `tests/runtime/api/test_weekly_stage04_openai_agent_api.py`
- `tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py`
- `tests/runtime/test_logistics_weekly_agent_pilot.py`
- `docs/planning/WEEKLY_STAGE04_OPENAI_AGENT_RUNTIME.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `codex/tasks/TASK-0073-weekly-stage04-iterative-agent-loop-and-analysis.md`

## Generated / downstream artifacts impacted
- Stage04 runtime evidence artifacts (`runtime.context_pack.json`, `runtime.tool_request.json`, `runtime.tool_result.json`, `execution.trace.json`)
- realistic pilot summary/inspection packet outputs
- optional real-network weekly Stage04 inspection packets under existing gates

## Plan
1. Replace the Stage04 tool catalog with bounded iterative tools (context, batch allocation, move proposal/application, validation, finalize).
2. Remove unconditional post-loop build/finalization; success should require explicit tool-driven finalization.
3. Add per-iteration request/result/evidence persistence and explicit progress accounting.
4. Enforce authored no-progress behavior for iterative Stage04 runs.
5. Update pilot inspection packet generation to include iteration-level metrics and tradeoff summaries.
6. Run the realistic mock pilot and archive before/after analysis outputs; then optionally run the existing dual-gated real-network e2e path.

## Verification
- `make schema-validate`
  - Passed.
- `PYTHONPATH=src pytest -q tests/unit/test_responses_agent_runner.py`
  - Passed (`4 passed`).
- `PYTHONPATH=src pytest -q tests/runtime/test_weekly_stage04_execution_runtime.py tests/runtime/api/test_weekly_stage04_openai_agent_api.py tests/runtime/scenarios/test_weekly_stage04_openai_agent_mocked_slice.py tests/runtime/test_logistics_weekly_agent_pilot.py`
  - Passed (`12 passed`).
- `PYTHONPATH=src python3 scripts/run_logistics_weekly_agent_pilot.py --db-url sqlite:///./.tmp/logistics-weekly-stage04-pilot.db --pilot-key iterative-agent --openai-mode mock --json`
  - Passed.
  - Outputs:
    - summary: `artifacts/pilot_runs/logistics_weekly_stage04_agent/iterative-agent/pilot_summary.json`
    - baseline packet: `artifacts/pilot_runs/logistics_weekly_stage04_agent/iterative-agent/weekly_stage04_agent_baseline/inspection_packet.json`
    - realistic packet: `artifacts/pilot_runs/logistics_weekly_stage04_agent/iterative-agent/weekly_stage04_realistic_artifacts/inspection_packet.json`
- Optional gated real-network check:
  - Not run.
  - `ONETRUTH_RUN_OPENAI_E2E` and `ONETRUTH_RUN_OPENAI_WEEKLY_AGENT_E2E` were both unset in the environment for this task run.

## Acceptance criteria
- Stage04 Responses runtime orchestrates iterative deterministic tools rather than a one-shot build tool.
- No unconditional post-loop build remains.
- Iteration-by-iteration evidence is canonical and reviewable.
- No-progress behavior is enforced from authored control metadata.
- Realistic mock pilot produces an inspection packet with route-allocation iterations, repair moves, stability deltas, uncovered-route summaries, and policy tradeoffs.
- Existing draft-only / no-pointer-promotion invariants remain true.

## Completion notes
- Replaced the Stage04 one-shot build tool with bounded deterministic `preview`, `apply`, `validation`, `iteration_analysis`, and `finalize` tools while keeping the model out of schedule truth ownership.
- Removed the unconditional post-loop build/finalization path; Stage04 draft artifacts now exist only after `finalize_weekly_stage04_draft_outputs` succeeds.
- Persisted per-turn canonical `runtime.tool_request.json` / `runtime.tool_result.json` evidence plus execution traces, including progress accounting and authored no-progress exhaustion.
- Upgraded the mock pilot inspection packets so they expose runtime turn summaries and iteration-level route allocation, uncovered-slot, repair, and tradeoff analysis directly from canonical artifacts/evidence.
- Preserved existing runtime ontology, Stage04/05/06 boundaries, draft-only behavior, and no-pointer-promotion invariants.

## Notes / decisions
- Keep the same runtime object ontology; inner tool iterations belong in evidence, not new canonical runtime rows.
- The model remains a search/orchestration controller over deterministic planner tools.
- The realistic pilot should surface hard tradeoffs rather than trying to pretend every driver can reach four shifts.
