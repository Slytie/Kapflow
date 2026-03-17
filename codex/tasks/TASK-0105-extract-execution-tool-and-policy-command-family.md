---
id: TASK-0105
epic: EPIC-070
title: "Extract execution, tool, and policy command family"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0102"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-005", "PATTERN-006"]
---

## Context
The execution/tool/policy cluster still lives inside `workflow_task_lifecycle.py`, even though Stage06 sandbox and weekly Stage04 agent services already treat it as a distinct runtime facet. This keeps the agent-runtime services coupled to the largest handler module and hides execution-boundary logic behind unrelated workflow mutations.

## Objective
Extract the execution/tool/policy command family into a dedicated handler module (or small family of modules) so Stage06/Stage04 services no longer import execution semantics from `workflow_task_lifecycle.py`.

## Non-goals
- No semantic changes to policy decisions, execution-session states, or approval gating.
- No OpenAI integration redesign.
- No transport or tracing expansion beyond what the extracted family directly needs.

## Source files to read first
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/application/services/stage06_openai_sandbox.py`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/application/services/logistics_weekly_agent_pilot.py`
- `src/onetruth/application/services/execution_evidence.py`
- `src/onetruth/infrastructure/repositories/execution_sessions.py`
- `src/onetruth/infrastructure/repositories/tool_executions.py`
- `src/onetruth/infrastructure/repositories/policy_decisions.py`
- `tests/integration_openai/`
- `tests/runtime/`

## Context packs / patterns to consult
- `codex/context/EPIC-070.md`
- `codex/context/EPIC-040.md`
- `docs/patterns/cards/PATTERN-005.md`
- `docs/patterns/cards/PATTERN-006.md`

## Source files to change
- new `src/onetruth/application/handlers/execution_runtime.py` (or equivalent)
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- direct Stage06/Stage04 service call sites
- import-boundary tests
- targeted execution/tool/policy tests

## Generated / downstream artifacts impacted
- Task-memory and epic/context updates only.

## Plan
1. Extract the execution-session, tool-execution, and policy-decision command cluster behind a dedicated module.
2. Rewire Stage06/Stage04 services to import the extracted family directly.
3. Preserve behavior via thin wrappers in `workflow_task_lifecycle.py` until the legacy surface can shrink further.
4. Add contract tests so execution-runtime services no longer depend on the legacy hotspot.

## Verification
- targeted pytest for execution-session, tool-execution, and policy-decision flows
- representative Stage06 / Stage04 runtime tests
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- Execution-runtime services no longer import execution semantics from `workflow_task_lifecycle.py`.
- Execution/session/tool/policy semantics are unchanged.
- The remaining hotspot centrality is materially lower.

## Notes / decisions
This is still a single-node bounded-execution system. Do not use this extraction to smuggle in distributed runtime assumptions.

## Implementation notes (2026-03-17)
- Added `src/onetruth/application/handlers/execution_runtime.py` as the owner of `create_execution_session_command`, `request_tool_execution_command`, `evaluate_policy_decision_command`, `complete_tool_execution_command`, `transition_execution_session_state_command`, and `reconcile_executions_command`.
- Shrunk `src/onetruth/application/handlers/workflow_task_lifecycle.py` to thin lazy wrappers for that execution/runtime family while leaving execution read commands on `read_commands`.
- Rewired `src/onetruth/application/services/stage06_openai_sandbox.py`, `src/onetruth/application/services/weekly_stage04_openai_agent.py`, `src/onetruth/cli/__main__.py`, and `tests/runtime/test_execution_session_runtime.py` to consume the extracted execution seam directly.
- Extended `tests/contract/test_handler_import_boundaries.py` so extracted handlers and API/service/CLI layers cannot drift back to legacy execution imports.
- Added `tests/unit/test_execution_runtime_handler_compatibility.py` to lock the legacy-vs-extracted happy path in place.
