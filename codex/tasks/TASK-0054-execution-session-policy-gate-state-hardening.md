---
id: TASK-0054
epic: EPIC-070
title: "Execution-session policy-gate state hardening and reconcile dedupe coverage"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security"]
depends_on: ["TASK-0052", "TASK-0053"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Objective
Close the remaining bounded runtime-hardening gap in the Stage06 OpenAI path by:
- making policy-gate wait state explicit in canonical execution-session lifecycle (`WAITING_POLICY -> RUNNING` on allow),
- emitting authoritative session state-change evidence for policy-allow transitions,
- proving reconcile behavior on partially completed sessions does not duplicate completed tool/evidence effects.

## Non-goals
- No generalized orchestrator or open-ended tool loops.
- No new truth path outside canonical runtime rows/events/artifacts.
- No new UI/operator surfaces.

## Source Files Changed
- `src/onetruth/application/services/stage06_openai_sandbox.py`
- `src/onetruth/application/handlers/workflow_task_lifecycle.py`
- `tests/runtime/test_execution_session_runtime.py`
- `docs/planning/EXECUTION_SESSION_RUNTIME_MODEL.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TEST_MATRIX.md`
- `README.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`

## Verification Commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q tests/runtime/test_execution_session_runtime.py`
- `pytest -q`
- `PYTHONPATH=src pytest -q tests/integration_openai/test_stage06_openai_real_e2e.py` (gated; only when env configured)

## Acceptance Criteria
- Stage06 bounded flow enters canonical `WAITING_POLICY` before model execution and transitions to `RUNNING` only after explicit policy allow.
- Policy-allow transition emits authoritative `execution.session.state_changed` evidence.
- Reconcile of stale partial sessions does not duplicate already completed tool execution events or evidence artifacts.
- Existing allowed/denied/failed/retry/reconcile execution runtime coverage remains green.
