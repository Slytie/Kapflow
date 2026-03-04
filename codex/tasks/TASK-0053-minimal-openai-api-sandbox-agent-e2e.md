---
id: TASK-0053
epic: EPIC-070
title: "Minimal real OpenAI API sandbox/agent e2e spike"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security"]
depends_on: ["TASK-0051"]
risk: high
context_packs: ["codex/context/EPIC-070.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-007"]
---

## Objective
Deliver a bounded, real OpenAI Responses API spike for Stage06 review classification that proves:
- canonical artifact-backed input selection from the example corpus,
- strict structured output enforcement,
- canonical evidence artifact persistence,
- explicit workflow truth updates through canonical handlers,
- deterministic default mock coverage plus opt-in real-network integration coverage.

This is explicitly a bounded spike and produces the implementation inputs consumed by the execution-session hardening slice.

## Non-goals
- No generalized multi-agent orchestrator.
- No web search, MCP, or open-ended tool loops.
- No broad multi-use-case model framework.
- No default-on real-network API tests in CI.
- No second truth path for model outputs.

## Source Files To Read First
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/EXAMPLE_DOCUMENT_CORPUS_AND_ARTIFACT_INGRESS.md`
- `docs/planning/OPENAI_API_E2E_SANDBOX_SPIKE.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/architecture/RUNTIME_OBJECT_MODEL.md`
- `src/onetruth/application/services/stage06_openai_sandbox.py`
- `src/onetruth/integrations/openai/responses_adapter.py`

## Source Files To Change
- `src/onetruth/integrations/openai/responses_adapter.py`
- `src/onetruth/application/services/stage06_openai_sandbox.py`
- `src/onetruth/api/routes/human_tasks.py`
- `tests/unit/test_openai_responses_adapter.py`
- `tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `tests/integration_openai/test_stage06_openai_real_e2e.py`
- `docs/planning/OPENAI_API_E2E_SANDBOX_SPIKE.md`
- `README.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`

## Verification Commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q`
- `pytest -q tests/unit/test_openai_responses_adapter.py tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
- `PYTHONPATH=src pytest -q tests/integration_openai/test_stage06_openai_real_e2e.py` (gated)
- frontend checks (if tooling available):
  - `cd frontend && npm run typecheck`
  - `cd frontend && npm run test:run`
  - `cd frontend && npm run build`

## Acceptance Criteria
- Narrow OpenAI integration exists under `src/onetruth/integrations/openai/` using Responses API.
- Structured outputs are strict and schema-validated for Stage06 review classification.
- Input artifacts are selected via canonical artifact refs from seeded corpus data, not ad hoc filesystem paths.
- Canonical evidence artifacts are persisted, and authoritative events/workflow transitions are emitted through canonical handlers.
- Mock-path tests run in normal suites with deterministic behavior.
- Real-network integration test exists, is gated, and validates canonical evidence/workflow effects when enabled.
- Docs and README reflect exact gating/env requirements and canonical-vs-derived boundaries.
