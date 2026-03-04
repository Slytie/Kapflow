---
id: TASK-0046
epic: EPIC-080
title: "Build frontend shell, board/list HITL pages, and mock contract adapter"
status: DONE
owners: ["platform"]
reviewers: ["qa", "ops"]
depends_on: ["TASK-0044", "TASK-0045"]
risk: high
context_packs: ["codex/context/EPIC-080.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
The backend runtime/query substrate exists through Stage06 and Stage07, including board-oriented query contracts and a thin HTTP adapter.
Stage07 backend work is progressing on parallel branches, so frontend work must start now without blocking on a live backend deployment.

The frontend must be contract-first:
- read backend-owned snapshot fixture shapes,
- use a mock data-access adapter in this PR,
- keep workflow semantics server-authoritative.

## Objective
Create the first frontend foundation for the HITL operator surface:
- frontend workspace and app shell,
- route skeletons for board/list/detail workflows,
- reusable low-click components for cards, rows, actions, and drawer detail,
- repository/data-access boundary backed by snapshot fixtures,
- component/route tests that protect the interaction model.

## Non-goals
- Do not connect to a real backend API yet.
- Do not encode workflow/business transition semantics in the client.
- Do not implement drag-and-drop transitions.
- Do not create a second source of truth.
- Do not over-index on branding polish over interaction architecture.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/HITL_QUERY_CONTRACTS.md`
- `docs/planning/STEP_RUN_SCENARIO_HARNESS.md`
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TEST_MATRIX.md`
- `docs/patterns/cards/PATTERN-007.md`
- `docs/patterns/cards/PATTERN-009.md`
- `docs/patterns/sources/converted/Taiga_Front_UI_Architecture_Extraction_for_Ops_Console.md`
- `docs/patterns/sources/converted/Kanboard_Lightweight_UI_Plugin_Patterns_for_Orchestration_Ops_Console.md`
- `README.md`

## Source files to change
- `frontend/**` (new workspace)
- `fixtures/frontend_contracts/**` (new snapshot fixtures)
- `docs/planning/FRONTEND_ARCHITECTURE.md` (new)
- `docs/planning/FRONTEND_PAGE_MAP.md` (new)
- `docs/planning/FRONTEND_INTERACTION_RULES.md` (new)
- `docs/planning/FIRST_RUNTIME_SLICE.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `README.md`
- this task file

## Verification commands
- `cd frontend && npm install`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run test:run`
- `cd frontend && npm run build`

## Acceptance criteria
- Frontend workspace exists using a modern TS/React SPA stack.
- Initial routes/pages exist:
  - `/board`
  - `/my-work`
  - `/approvals`
  - `/exceptions`
  - `/runs`
  - `/runs/:workflowRunId`
  - `/official-outputs`
  - `/timeline`
- Shared shell exists with left nav, top filter bar, freshness indicator, and detail drawer host.
- Required low-click reusable components exist and are route-composed.
- Repository interfaces serve contract-shaped data from snapshot fixtures.
- UI code depends on repositories, not scattered fetch logic.
- Client stores presentation state only (filters, drawer, selection, local affordances).
- Client does not own workflow semantics or transition rules.
- Route/component/contract safety tests exist and pass.
- README/planning/status docs are updated and non-stale.

## Implementation notes
- Frontend is explicitly contract-first and mock-backed in this task.
- Snapshot fixtures must follow backend-owned field shapes from Stage06/Stage07 query contracts.
- Lane derivation can exist only as a presentation mapper over canonical fields and must stay small/tested.
- Detail descriptions stay hidden in compact cards/rows and are shown in drawer/detail views.

## Outcome
- Added `frontend/` workspace (React + TypeScript + Vite + React Router + TanStack Query + Vitest).
- Added app shell + required routes/pages and reusable low-click components.
- Added mock repository/data-access boundary over backend-owned fixtures in `fixtures/frontend_contracts/`.
- Added component tests, route tests, and repository/lane/reload contract safety tests.
- Added frontend architecture + page map + interaction rule planning docs.
