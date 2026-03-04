---
id: TASK-0050
epic: EPIC-070
title: "Add a narrow OpenAI Responses API sandbox path for Stage06 review classification"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops", "security"]
depends_on: ["TASK-0048", "TASK-0049"]
risk: high
context_packs: ["codex/context/EPIC-070.md"]
patterns: ["PATTERN-006", "PATTERN-007", "PATTERN-009"]
---

## Context
TASK-0048 and TASK-0049 established the frontend/API/query surfaces and backend-owned snapshots over canonical runtime truth.
Stage06/Stage07 runtime slices, example document fixtures, and artifact ingress are already present.

This task adds one bounded real-model path to learn from a real integration run before broadening execution architecture.

## Objective
Implement one narrow, real OpenAI Responses API path for Stage06 review outcome classification that:
- takes canonical artifact-backed inputs from the example document corpus,
- requests schema-constrained structured output,
- persists model evidence/results in canonical artifact/event truth,
- drives follow-on workflow truth only through existing canonical handlers,
- adds gated real e2e tests plus non-network structural coverage.

## Non-goals
- Do not build generalized multi-agent orchestration.
- Do not add open-ended tool execution, web search, or MCP integration.
- Do not add websocket/live-sync complexity.
- Do not make network/OpenAI tests part of the default fast suite.
- Do not create any second source of truth for model outputs or decisions.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/TEST_MATRIX.md`
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `tests/runtime/helpers/scenario_harness.py`
- `fixtures/scenarios/schedule_planning/stage06_publish_happy.yaml`

## Source files to change
- `src/onetruth/integrations/openai/**` (new narrow OpenAI Responses adapter)
- `src/onetruth/application/services/**` (new bounded Stage06 sandbox runner)
- `src/onetruth/infrastructure/artifacts/**` (input/evidence helpers)
- `src/onetruth/api/routes/human_tasks.py` (sandbox endpoint)
- `src/onetruth/api/main.py` (route wiring)
- `tests/unit/**` + `tests/runtime/api/**` + `tests/integration_openai/**` (mock/contract/gated-real coverage)
- `docs/planning/OPENAI_API_E2E_SANDBOX_SPIKE.md` (new)
- `README.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Verification commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `pytest -q`
- `PYTHONPATH=src pytest -q tests/unit/test_openai_* tests/runtime/api/test_stage06_*`
- `PYTHONPATH=src pytest -q tests/integration_openai` (gated real network run)
- `cd frontend && npm run build`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run test:run`

## Acceptance criteria
- Narrow OpenAI adapter exists under `src/onetruth/integrations/openai/` and uses the Responses API.
- Stage06 review classification uses schema-constrained structured output (`outcome`, `rationale_summary`, `evidence_refs`, nullable schema-bound follow-on kind).
- Inputs come from canonical artifact/doc ingress paths and example document fixtures.
- Canonical evidence artifact(s) and metadata are persisted; no log-only output path.
- Follow-on workflow truth is emitted only through existing canonical task completion/spawn handlers.
- At least one real e2e integration test exists and is opt-in/gated; default fast suite remains deterministic and network-free.
- README/docs/task memory are updated with no stale future-tense statements.

## Implementation notes
- This is a narrow real-integration spike, not the final generalized execution/session architecture.
- The integration is contract-first and uses canonical artifact truth from the existing example corpus.
- The client/server presentation surfaces remain subordinate to canonical runtime semantics.
- The real OpenAI e2e test must remain manual/nightly/gated, not default PR gate.

## Outcome
- Added bounded OpenAI Responses adapter under `src/onetruth/integrations/openai/` with strict Stage06 structured-output validation and retry/error normalization.
- Added Stage06 sandbox runner under `src/onetruth/application/services/stage06_openai_sandbox.py` that:
  - reads canonical Stage06 artifact-backed input from existing artifact rows/storage URIs,
  - executes bounded classification,
  - persists canonical evidence artifact (`schedule.stage06.review_ai_evidence.json`),
  - completes task via existing `complete_human_task_command` so follow-on truth remains canonical.
- Added API mutation endpoint `POST /api/v1/human-tasks/{human_task_id}/stage06-agent-review` with scope enforcement and normalized config/provider failure mapping.
- Added tests:
  - `tests/unit/test_openai_responses_adapter.py`
  - `tests/runtime/api/test_stage06_openai_review_sandbox_api.py`
  - `tests/integration_openai/test_stage06_openai_real_e2e.py` (gated via `ONETRUTH_RUN_OPENAI_E2E=1`)
- Added/updated docs: architecture note, HTTP contract, event matrix, test matrix, runtime slice status, README runbook instructions, and decision log.

Verification run in this environment:
- `make schema-validate` -> PASS
- `make contract` -> PASS
- `make replay` -> PASS
- `make acceptance` -> PASS
- `make runtime` -> PASS
- `pytest -q` -> PASS
- `PYTHONPATH=src pytest -q tests/unit/test_openai_responses_adapter.py tests/runtime/api/test_stage06_openai_review_sandbox_api.py` -> PASS
- `make integration-openai` -> PASS (test skipped without `ONETRUTH_RUN_OPENAI_E2E=1`)
- `cd frontend && npm run build` -> BLOCKED (`npm: command not found`)
- `cd frontend && npm run typecheck` -> BLOCKED (`npm: command not found`)
- `cd frontend && npm run test:run` -> BLOCKED (`npm: command not found`)
