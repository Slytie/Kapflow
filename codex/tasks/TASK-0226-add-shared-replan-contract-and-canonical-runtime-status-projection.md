---
id: TASK-0226
epic: EPIC-135
title: "Add shared replan contract blocks and canonical runtime-status projection"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0225"]
risk: high
context_packs:
  - "codex/context/EPIC-135.md"
  - "codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md"
patterns: []
---

## Why
The shared popup cannot support greenfield and brownfield replanning until the backend can project proposal, candidate, and runtime-status truth through one additive contract instead of the current weekly-draft-only shape.

## Objective
Add server-authored replan contract blocks for the schedule popup and drive “agent is working” state from canonical runtime objects rather than local mutation heuristics.

## Non-goals
- adding driver phone numbers
- implementing candidate ranking logic
- redesigning the popup UI
- live-dispatch agent runtime work

## Source files to read first
- `src/onetruth/application/services/logistics_workpages_shared.py`
- `src/onetruth/application/read_commands/runtime_views.py`
- `frontend/src/lib/types/workpages.ts`
- `frontend/src/lib/types/contracts.ts`
- `frontend/src/components/workpages/LogisticsScheduleWorkpagePageContent.tsx`
- `frontend/src/components/workpages/ScheduleWorkpageSurface.tsx`

## Source files to change
- backend workpage contract/projection builders
- runtime read-command helpers or view adapters
- frontend contract/workpage types
- schedule popup tests, snapshots, and mock handlers

## Plan
1. Extend schedule-related workpage contracts with additive `replan_context`, `proposal_state`, `proposal`, candidate-group placeholders, and `execution_status`.
2. Build `execution_status` from canonical `task_run`, `human_task`, `execution_session`, and `tool_execution` truth for the active replan context.
3. Surface blocked states for:
   - missing Stage04 inputs before publish
   - missing published live-dispatch seed prerequisites after publish
   - claimed/running task contexts that cannot be reused safely
4. Update frontend workpage types and repository parsing so the popup can render the new blocks without client-side reconstruction.
5. Add backend-owned snapshots and mock/test handlers that preserve the same contract shape in loading, blocked, running, ready, and failed states.

## Verification
- backend workpage contract tests for proposal/runtime-status blocks
- frontend workpage API parsing tests
- schedule popup route tests covering blocked/running/ready states
- `npm --prefix frontend run typecheck`

## Acceptance criteria
- The schedule popup contract now carries additive server-authored replan and runtime-status blocks.
- “Agent is working” can be rendered from canonical runtime truth alone.
- Missing prerequisite states fail closed through explicit contract state rather than silent disabled buttons or local-only messages.
