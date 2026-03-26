# Prompt for TASK-0140 - Frontend workflow-run-backed workpage routes and EOD artifact handoff

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0140-frontend-workflow-run-backed-workpage-routes-and-eod-artifact-handoff.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `docs/planning/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- generated snapshots from `TASK-0138` and `TASK-0139`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- current workpage pages/components/tests

### What to figure out before coding
- The smallest workflow-run-backed frontend route posture.
- How to preserve the validated page sections while changing route/data sources.
- Which loading/error/freshness/navigation states need explicit coverage.
- How demo aliases should coexist with canonical run-backed routes.

### Red-team checks
- Do not keep active routes on demo-only data after canonical backend routes exist.
- Do not reinterpret backend contracts silently in frontend code.
- Do not start schedule write-path behavior.
- Do not remove demo aliases before the canonical routes are proven and documented.

### Output required from Ask mode
- Short diagnosis of the frontend migration slice.
- Proposed files/components/tests.
- The route posture and why it fits the current shell.
- Loading/error/navigation behavior to freeze.
- Docs that must be updated when the migration becomes real.
- Smallness check explaining why this still fits one bounded Codex task.

## Code mode prompt
Use this section only after the Ask-mode plan is reviewed and approved.

### Step 0 - Reload the minimum context
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/tasks/TASK-0140-frontend-workflow-run-backed-workpage-routes-and-eod-artifact-handoff.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- generated snapshots from `TASK-0138` and `TASK-0139`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`

### Implementation rules
- Move canonical usage to workflow-run-backed routes.
- Preserve the artifact-backed EOD edit route as the explicit next step from run-backed EOD landing.
- Add explicit loading, error, and navigation handling.
- Keep workpage pages inside the existing shell.
- Update docs/status/task-memory in the same change set.
- Update the task file with plan, commands run, outcomes, and follow-ups.

### Likely verification
- `npm --prefix frontend run typecheck`
- targeted frontend tests for run-backed workpage routes/repository/pages
- snapshot/contract checks if relevant
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of the frontend run-backed route migration completed.
- Files changed and why.
- Commands run and results.
- Any doc/task-memory updates.
- Any follow-on work that should remain in `TASK-0141` rather than being smuggled into this task.
