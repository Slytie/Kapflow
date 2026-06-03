# Prompt for TASK-0138 - Backend run-backed schedule workpage route and snapshot

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0138-backend-workflow-run-backed-schedule-workpage-query-route-and-snapshot.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`

### What to figure out before coding
- The cleanest builder/service seam for run-backed schedule workpage projection.
- Which run-side data/artifacts are authoritative for the backend payload.
- The smallest route/route-spec change that matches the frozen contract.
- How to extend snapshot export/check flows without confusing source fixture classes.

### Red-team checks
- Do not broaden into EOD or schedule writes.
- Do not serve a planning fixture verbatim as the active route payload.
- Do not let selected-day preview drift into live-dispatch authority.
- Do not skip docs/snapshot updates when the route becomes real.

### Output required from Ask mode
- Short diagnosis of the backend schedule run-backed route slice.
- Proposed files/components/tests.
- The builder/service boundary and why it is the right seam.
- The snapshot-export impact.
- Docs that must be updated when the route becomes real.
- Smallness check explaining why this still fits one bounded Codex task.

## Code mode prompt
Use this section only after the Ask-mode plan is reviewed and approved.

### Step 0 - Reload the minimum context
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/tasks/TASK-0138-backend-workflow-run-backed-schedule-workpage-query-route-and-snapshot.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `tests/runtime/helpers/frontend_snapshots.py`

### Implementation rules
- Keep the route backend-owned and contract-shaped.
- Build from canonical weekly-run truth rather than a planning fixture.
- Extend backend-owned snapshot export/check flows in the same change set.
- Update docs/status/task-memory if visible route truth changes.
- Update the task file with plan, commands run, outcomes, and follow-ups.

### Likely verification
- targeted runtime/API tests for the new route
- snapshot export/check tests
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of the run-backed schedule route added.
- Files changed and why.
- Commands run and results.
- Any doc/task-memory updates.
- Any follow-on work that should remain in `TASK-0140` or `TASK-0141` rather than being smuggled into this task.
