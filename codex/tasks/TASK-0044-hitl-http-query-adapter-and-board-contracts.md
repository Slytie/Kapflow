---
id: TASK-0044
epic: EPIC-080
title: "Implement thin HITL HTTP/query adapter and board contracts over canonical runtime"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0043"]
risk: high
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-090.md", "codex/context/EPIC-040.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
TASK-0040 .. TASK-0043 implemented canonical runtime substrate, Stage06 scenario execution, and CLI-based query surfaces, but there is no stable HTTP adapter boundary for frontend/Kanban work to integrate against.

Backlog memory is also stale: several pre-runtime planning tasks still read as TODO even when partially or fully superseded by implemented runtime slices.

## Objective
Implement the first thin HTTP/query adapter over canonical runtime handlers and query surfaces while reconciling stale backlog status:
- add board-ready HTTP read endpoints for human tasks, approvals, workflow runs, pointers, and schedule-planning aggregate board view,
- add thin mutation endpoints for `claim_human_task`, `complete_human_task`, and `respond_approval` that delegate to existing canonical handlers,
- add scenario-backed API contract/mutation/scope tests,
- update planning/task/status docs so repository memory matches implementation reality.

## Non-goals
- Do not build the frontend.
- Do not implement Stage07 issue-loop behavior.
- Do not introduce a second source of truth or board-local state machine.
- Do not fork business semantics into API routes.
- Do not add websocket/live-sync complexity in this slice.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `codex/tasks/TASK-0040-runtime-scaffold-and-smoke-tests.md`
- `codex/tasks/TASK-0041-workflow-task-core-and-transactional-events.md`
- `codex/tasks/TASK-0042-approvals-artifacts-pointers-and-query-surfaces.md`
- `codex/tasks/TASK-0043-stage06-publish-scenario-and-runtime-harness.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `src/onetruth/api/main.py`
- `src/onetruth/api/dependencies.py` (new)
- `src/onetruth/api/errors.py` (new)
- `src/onetruth/api/routes/*.py` (new)
- `tests/runtime/helpers/runtime_api.py` (new)
- `tests/runtime/api/*.py` (new)
- `docs/planning/HITL_BOARD_ARCHITECTURE.md` (new)
- `docs/planning/HITL_HTTP_API_CONTRACTS.md` (new)
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `README.md`
- `codex/tasks/TASK-0029-event-registry-to-runtime-mapping.md`
- `codex/tasks/TASK-0030-artifact-store-and-schedule-delta-plan.md`
- `codex/tasks/TASK-0039-step-run-scenario-harness-for-agent-executed-flows.md`

## Generated / downstream artifacts impacted
- future HITL frontend/Kanban work can integrate in parallel against stable HTTP contracts
- runtime scenario corpus now exercises API boundary in addition to CLI boundary
- planning/task memory remains aligned with implementation reality

## Plan
1. Reconcile stale status of TASK-0029/0030/0031/0032/0039 against implemented runtime work.
2. Author board/API architecture and HTTP contract docs before finalizing endpoint behavior.
3. Implement thin ASGI adapter routes and request-context scope enforcement over canonical handlers.
4. Add scenario-backed API tests for read contracts, board aggregate contracts, mutations, idempotency retry stability, and cross-scope denial.
5. Update README + planning/status/task docs and run full verification loop.

## Verification
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `PYTHONPATH=src pytest -q tests/runtime/api`
- `pytest -q`

## Acceptance criteria
- stale planning/task status is reconciled where previous TODO wording is no longer accurate
- thin HTTP/query adapter exists over canonical runtime/query surfaces
- stable board-ready read endpoints exist:
  - `GET /api/v1/human-tasks`
  - `GET /api/v1/approvals`
  - `GET /api/v1/workflow-runs`
  - `GET /api/v1/workflow-runs/{workflow_run_id}`
  - `GET /api/v1/pointers`
  - `GET /api/v1/board/schedule-planning`
- minimum mutation endpoints exist and delegate to canonical handlers:
  - `POST /api/v1/human-tasks/{human_task_id}/claim`
  - `POST /api/v1/human-tasks/{human_task_id}/complete`
  - `POST /api/v1/approvals/{approval_id}/respond`
- `docs/planning/HITL_BOARD_ARCHITECTURE.md` exists and matches implemented choices
- `docs/planning/HITL_HTTP_API_CONTRACTS.md` exists and matches implementation
- scenario-backed API contract/mutation tests exist including cross-scope negatives
- this PR unblocks parallel frontend/Kanban work while preserving one-truth canonical runtime authority
- this PR reconciles stale planning/task state where implementation superseded old wording
- full repo verification passes

## Notes / decisions
- This slice is intentionally polling-friendly and stateless; no websocket/live-sync layer is added yet.
- Request context uses explicit tenant/domain/actor headers for scope-safe internal/admin API use until full authn/authz integration lands.

## Completion notes
- Reconciled stale backlog/task status:
  - TASK-0029 marked DONE with implementation-backed completion notes.
  - TASK-0039 marked DONE with implementation-backed completion notes.
  - TASK-0030 narrowed to remaining Stage07/base+delta design scope and marked IN_PROGRESS.
- Added thin ASGI HTTP adapter over canonical runtime handlers:
  - read endpoints for human tasks, approvals, workflow runs (list/detail), pointers, and Schedule Planning board aggregate.
  - mutation endpoints delegating to canonical handlers for claim, complete, and approval response.
- Added request-context scope enforcement via required headers (`tenant/domain/actor/roles`) with cross-scope denial behavior.
- Added scenario-backed API tests under `tests/runtime/api/` covering:
  - read contracts and filtering,
  - board aggregate contract and lane/card mapping,
  - mutation side effects and authoritative event emission parity,
  - cross-scope denial,
  - retry/idempotency stability.
- Added architecture/contract docs:
  - `docs/planning/HITL_BOARD_ARCHITECTURE.md`
  - `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- Updated README/planning/status/task memory docs and passed full verification loop.
