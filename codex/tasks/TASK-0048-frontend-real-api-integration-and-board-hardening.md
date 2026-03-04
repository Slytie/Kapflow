---
id: TASK-0048
epic: EPIC-080
title: "Swap frontend repositories to real HITL API contracts and harden board/list/detail UX"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0046", "TASK-0044"]
risk: high
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
TASK-0046 delivered the route shell, low-click components, and mock-backed repository seam.
TASK-0044 delivered thin HITL HTTP/query endpoints over canonical runtime truth.

This task swaps frontend data access from snapshot/mock adapters to real HTTP contracts while keeping the frontend presentation-only.

## Objective
Integrate the frontend with real API-backed repositories and harden board/list/detail flows for production-like polling and error handling:
- replace mock repository implementations with HTTP-backed adapters behind the same repository boundary,
- preserve app shell, routes, and low-click component model,
- wire inline claim/complete/respond actions to real mutation endpoints,
- add integration tests against API contract-shaped endpoints,
- keep server/runtime authoritative and avoid client workflow semantics.

## Non-goals
- Do not move workflow semantics into the client.
- Do not implement drag-to-transition interactions.
- Do not add websocket/live-sync complexity in this slice.
- Do not redesign the full UI architecture.
- Do not introduce a second source of truth.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/FRONTEND_ARCHITECTURE.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/HITL_BOARD_ARCHITECTURE.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `codex/tasks/TASK-0046-frontend-shell-board-pages-and-mock-contract-adapter.md`
- `codex/tasks/TASK-0044-hitl-http-query-adapter-and-board-contracts.md`

## Source files to change
- `frontend/src/lib/api/**` (new HTTP client/config/idempotency/error helpers)
- `frontend/src/lib/repositories/**` (real API-backed implementations)
- `frontend/src/pages/**` (polling + loading/error/empty + mutation wiring)
- `frontend/src/components/**` (inline action callback wiring + hardened states)
- `frontend/src/test/**` (contract-aligned API integration test layer)
- `src/onetruth/api/main.py`
- `src/onetruth/api/routes/flags.py` (new)
- `src/onetruth/api/routes/timeline.py` (new)
- `tests/runtime/api/test_flag_list_contract.py` (new)
- `tests/runtime/api/test_timeline_events_list_contract.py` (new)
- docs/README/status/task index files listed below

## Verification commands
- `PYTHONPATH=src pytest -q tests/runtime/api`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run test:run`
- `cd frontend && npm run build`

## Acceptance criteria
- Frontend repositories use real `/api/v1` contracts instead of snapshot-only mock services.
- Board/my-work/approvals/exceptions/runs/run-detail/official-outputs/timeline routes remain intact.
- Inline claim/complete/respond flows call real mutation paths through repositories.
- Loading/error/empty/freshness/polling states are explicit and coherent.
- URL-synced filters remain presentation-only.
- Integration tests cover route loading, mutation round-trips, forbidden response handling, and reload stability.
- Documentation and README are updated and non-stale.

## Implementation notes
- This PR explicitly swaps snapshots -> real API adapters without changing workflow semantics.
- Frontend remains contract-first and server-authoritative.
- Client state remains presentation-only (filters, selection, drawer state, refresh affordances).
- Client must not own workflow/business transition semantics.

## Outcome
- Replaced snapshot mock service usage with real HTTP client/repository adapters.
- Added polling-friendly page queries with explicit loading/error/empty state panels.
- Wired low-click inline actions to canonical mutation endpoints (claim/complete/respond).
- Added frontend API integration tests using a contract-aligned test server layer.
- Added API read endpoints for flags/timeline events and matching runtime API contract tests.
- Verification run in this environment:
  - `PYTHONPATH=src pytest -q tests/runtime/api` -> PASS
  - `cd frontend && npm run typecheck` -> BLOCKED (`npm: command not found`)
  - `cd frontend && npm run test:run` -> BLOCKED (`npm: command not found`)
  - `cd frontend && npm run build` -> BLOCKED (`npm: command not found`)
