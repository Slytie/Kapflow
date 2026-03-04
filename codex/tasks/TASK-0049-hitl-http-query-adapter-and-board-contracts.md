---
id: TASK-0049
epic: EPIC-080
title: "Extend thin HITL HTTP/query adapter and board contracts over canonical runtime"
status: DONE
owners: ["platform"]
reviewers: ["qa", "security", "ops"]
depends_on: ["TASK-0044", "TASK-0045", "TASK-0046", "TASK-0047"]
risk: high
context_packs: ["codex/context/EPIC-080.md", "codex/context/EPIC-040.md", "codex/context/EPIC-090.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
Canonical runtime substrate and Stage06/Stage07 scenario coverage are implemented and stable.  
Frontend shell work (TASK-0046) is in parallel and depends on a complete, stable, server-authoritative HTTP boundary that includes query/detail surfaces for tasks, approvals, flags, pointers, workflow runs, and timeline.

## Objective
Extend the existing thin HTTP/query adapter as an adapter-only layer over canonical runtime handlers:
- add missing board-ready read endpoints and detail endpoints,
- add missing mutation endpoint for flag state transition,
- keep scope enforcement strict via request context headers,
- add scenario-backed API contract tests and retry/cross-scope negatives,
- align README/planning/task memory to implemented API reality.

This PR exists to unblock parallel frontend/Kanban work while preserving one-truth semantics.

## Non-goals
- Do not build frontend UI in this PR.
- Do not create client-owned workflow logic or a second state machine.
- Do not move business semantics into API routes.
- Do not add websocket/live-sync complexity.
- Do not refactor canonical runtime substrate beyond adapter exposure needs.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/EVENT_EMISSION_MATRIX.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/planning/STAGE07_RUNTIME_MODEL.md`
- `codex/tasks/TASK-0043-stage06-publish-scenario-and-runtime-harness.md`
- `codex/tasks/TASK-0044-hitl-http-query-adapter-and-board-contracts.md`
- `codex/tasks/TASK-0045-stage07-issue-scoped-replan-loop.md`
- `codex/tasks/TASK-0046-frontend-shell-board-pages-and-mock-contract-adapter.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-009.md`

## Source files to change
- `src/onetruth/api/main.py`
- `src/onetruth/api/errors.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/api/routes/approvals.py`
- `src/onetruth/api/routes/flags.py`
- `src/onetruth/api/routes/timeline.py`
- `src/onetruth/api/routes/board.py`
- `tests/runtime/api/test_human_task_list_contract.py`
- `tests/runtime/api/test_approval_list_contract.py`
- `tests/runtime/api/test_board_schedule_planning_contract.py`
- `tests/runtime/api/test_cross_scope_api_denial.py`
- `tests/runtime/api/test_flag_list_contract.py`
- `tests/runtime/api/test_timeline_contract.py`
- `tests/runtime/api/test_flag_transition_via_api.py`
- `tests/runtime/api/test_api_retry_stability.py`
- `docs/planning/HITL_BOARD_ARCHITECTURE.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/TEST_MATRIX.md`
- `README.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- this task file

## Verification commands
- `make schema-validate`
- `make contract`
- `make replay`
- `make acceptance`
- `make runtime`
- `make runtime-api`
- `pytest -q`

## Acceptance criteria
- thin HTTP/query adapter covers required read endpoints:
  - `GET /api/v1/human-tasks`
  - `GET /api/v1/human-tasks/{human_task_id}`
  - `GET /api/v1/approvals`
  - `GET /api/v1/approvals/{approval_id}`
  - `GET /api/v1/flags`
  - `GET /api/v1/flags/{flag_id}`
  - `GET /api/v1/workflow-runs`
  - `GET /api/v1/workflow-runs/{workflow_run_id}`
  - `GET /api/v1/workflow-runs/{workflow_run_id}/timeline`
  - `GET /api/v1/pointers`
  - `GET /api/v1/board/schedule-planning`
- thin mutation endpoints delegate to canonical handlers:
  - `POST /api/v1/human-tasks/{human_task_id}/claim`
  - `POST /api/v1/human-tasks/{human_task_id}/complete`
  - `POST /api/v1/approvals/{approval_id}/respond`
  - `POST /api/v1/flags/{flag_id}/transition`
- request headers enforce tenant/domain scope; cross-scope list/detail/mutation attempts fail closed.
- `docs/planning/HITL_BOARD_ARCHITECTURE.md` and `docs/planning/HITL_HTTP_API_CONTRACTS.md` match implementation.
- scenario-backed API contract tests exist for tasks/approvals/flags/workflow/timeline/board plus retry stability and cross-scope denial.
- adapter-only posture remains explicit: no client-owned workflow logic.
- full repo verification loop passes.

## Notes
- Adapter-only contract: frontend can optimize presentation/interaction, but runtime semantics remain server-authoritative and are not duplicated client-side.

## Completion notes
- Added API read/detail endpoints for tasks, approvals, flags, workflow runs, run timeline, pointers, and schedule-planning board aggregate.
- Added API mutation delegate for `flags.transition` and confirmed all API mutations delegate to canonical command handlers.
- Added scenario-backed API coverage for flags, timeline, retry stability, and extended cross-scope denial checks.
- Refreshed backend-owned frontend snapshots after board lane/card contract updates and validated drift tests.
