---
id: TASK-0052
epic: EPIC-070
title: "Execution sessions and policy-gated sandbox runtime hardening"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops", "security"]
depends_on: ["TASK-0050", "TASK-0051"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
TASK-0050 established a bounded Stage06 OpenAI sandbox path, and TASK-0051 hardened canonical example-document ingress.
The remaining gap is that execution/session/policy semantics are currently represented mostly by events and service behavior rather than first-class canonical runtime rows.

## Objective
Convert the bounded OpenAI spike into canonical execution-runtime behavior by implementing persistent and transactional:
- `execution_sessions`
- `tool_executions`
- `policy_decisions`

Then route the Stage06 sandbox flow through explicit session/tool/policy state transitions and events, with retry/recovery handling and canonical evidence linkage.

This task explicitly converts the narrow OpenAI spike into canonical runtime behavior.
Policy decisions and tool executions must become explicit truth, not implied side effects.

## Non-goals
- No generalized multi-agent orchestrator.
- No web-search/MCP/open-ended tool loops.
- No broadening to unrelated model use cases.
- No log-only or helper-only shadow execution truth.
- No full operator UI for execution sessions.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/OPENAI_API_E2E_SANDBOX_SPIKE.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/human_task_semantics.md`
- `docs/architecture/approval_model.md`
- `docs/architecture/promotion_semantics.md`
- `AGENTS.md`
- `LLM_RUNBOOK.md`

## Source files to change
- Runtime persistence:
  - `src/onetruth/infrastructure/db/models.py`
  - `src/onetruth/infrastructure/events/event_store.py`
  - `alembic/versions/20260304_0006_execution_session_runtime.py`
  - `src/onetruth/infrastructure/repositories/execution_sessions.py`
  - `src/onetruth/infrastructure/repositories/tool_executions.py`
  - `src/onetruth/infrastructure/repositories/policy_decisions.py`
- Runtime handlers/services:
  - `src/onetruth/application/handlers/workflow_task_lifecycle.py`
  - `src/onetruth/application/services/stage06_openai_sandbox.py`
- Boundaries:
  - `src/onetruth/cli/__main__.py`
  - `src/onetruth/api/routes/human_tasks.py`
  - `src/onetruth/api/errors.py`
- Runtime tests:
  - `tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
  - `tests/runtime/test_execution_session_runtime.py`
  - `tests/integration_openai/test_stage06_openai_real_e2e.py`
- Docs/memory:
  - `docs/planning/EXECUTION_SESSION_RUNTIME_MODEL.md`
  - `docs/planning/EVENT_EMISSION_MATRIX.md`
  - `docs/planning/FIRST_RUNTIME_SLICE.md`
  - `docs/planning/TEST_MATRIX.md`
  - `docs/status/DECISIONS_SINCE_LAST.md`
  - `README.md`
  - `docs/planning/TASK_INDEX.md`
  - `docs/status/CURRENT_FOCUS.md`

## Verification commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q tests/runtime/test_execution_session_runtime.py`
- `pytest -q tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `pytest -q`
- `PYTHONPATH=src pytest -q tests/integration_openai/test_stage06_openai_real_e2e.py` (gated)

## Acceptance criteria
- Canonical runtime tables/rows exist for execution sessions, tool executions, and policy decisions.
- Stage06 bounded OpenAI flow runs through explicit session/tool/policy lifecycle transitions.
- Policy allow/deny is explicit, auditable, and emitted as authoritative events.
- Denied and failed paths create canonical evidence/state without hidden side effects.
- Retry/recovery/reconcile paths do not duplicate canonical effects.
- Runtime tests cover allowed, denied, failed, retry/idempotent, and reconcile paths.
- Docs/README/task memory are updated and no stale future-tense remains for implemented behavior.
- Full verification loop is green.
