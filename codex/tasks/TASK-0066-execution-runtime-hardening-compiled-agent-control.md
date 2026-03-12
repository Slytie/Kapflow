---
id: TASK-0066
epic: EPIC-070
title: "Execution-runtime hardening for compiled agent control, pinned semantics, and trace linkage"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security"]
depends_on: ["TASK-0065", "TASK-0061", "TASK-0062"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-025.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-005", "PATTERN-003"]
---

## Objective
Harden the canonical execution-runtime slice so compiled agent control semantics are auditable and reusable:
- persist pinned execution-semantics evidence artifacts (compiled execution spec + compile/source manifest),
- allow canonical evidence links directly to `execution_session`, `tool_execution`, and `policy_decision`,
- enforce execution event required-link semantics at runtime,
- add reusable execution-evidence helpers for future agent traces.

## Non-goals
- no `agent_runs` table,
- no shadow trace database,
- no public generalized orchestrator in this task,
- no second runtime truth path.

## Source Files Changed
- `src/onetruth/application/services/execution_evidence.py` (new)
- `src/onetruth/application/services/stage06_openai_sandbox.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `src/onetruth/infrastructure/events/event_store.py`
- `src/onetruth/infrastructure/definitions/control_layer.py`
- `tests/runtime/test_execution_session_runtime.py`
- `tests/runtime/test_logistics_control_layer_runtime_bridge.py`
- `tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `docs/planning/EXECUTION_SESSION_RUNTIME_MODEL.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0066-execution-runtime-hardening-compiled-agent-control.md`

## Verification Commands
- `pytest -q tests/runtime/test_execution_session_runtime.py`
- `pytest -q tests/runtime/test_logistics_control_layer_runtime_bridge.py`
- `pytest -q tests/runtime/api/test_stage06_openai_review_sandbox_api.py`

All commands passed on 2026-03-12.

## Acceptance Criteria Coverage
- Pinned execution semantics are persisted as immutable evidence artifacts:
  - `execution.compiled_spec.json`
  - `execution.compile_source_manifest.json`
- Evidence links can now attach directly to `execution_session`, `tool_execution`, and `policy_decision` with workflow-scope validation.
- Runtime `append_event` now validates registry-defined required link types and fails closed on missing execution links.
- No peer execution truth system was introduced; execution truth remains canonical runtime rows + timeline events + immutable artifacts.

## Completion Notes (2026-03-12)
- Added reusable execution-evidence helpers that prepare pinned semantics artifacts and execution-facet link payloads for future agent trace slices.
- Stage06 bounded sandbox now persists execution semantics evidence artifacts and links model evidence directly to execution session/tool/policy objects.
- Control-layer derived execution-session payloads now include compiled stage execution semantics and compile/source pins for replay-safe provenance.
- Runtime event append path now enforces required-link semantics from `schemas/events/event_type_registry.yaml`, and `execution.session.created` now emits the required `execution_spec` link.
