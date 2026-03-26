# Prompt for TASK-0141 - Demo/story drilldowns and doc sync for workflow-run-backed workpages

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0141-demo-story-drilldowns-and-doc-sync-for-workflow-run-backed-workpages.md`
- `docs/planning/EPICS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- the workpage route/page files from `TASK-0140`

### What to figure out before coding
- The smallest truthful drilldown/entrypoint posture from the logistics demo shell into canonical run-backed workpage routes.
- Which docs/status files must change together so future Codex runs do not drift.
- Whether any shell regression remains for the new routes.
- What next-epic seam should remain clearly deferred.

### Red-team checks
- Do not broaden into workspace/task modernization.
- Do not hide the canonical routes behind undocumented assumptions.
- Do not leave capability/page-map/status docs stale.
- Do not start schedule writes or EOD finalization here.

### Output required from Ask mode
- Short diagnosis of the drilldown/doc-sync slice.
- Proposed files/tests/docs to update.
- Exact entrypoint posture from the logistics demo shell.
- Smallness check explaining why this still fits one bounded Codex task.

## Code mode prompt
Use this section only after the Ask-mode plan is reviewed and approved.

### Step 0 - Reload the minimum context
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/tasks/TASK-0141-demo-story-drilldowns-and-doc-sync-for-workflow-run-backed-workpages.md`
- `docs/planning/EPICS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`

### Implementation rules
- Keep `/demo/logistics` as the primary curated entrypoint.
- Make canonical run-backed workpage routes discoverable from the demo/story drilldown surface.
- Keep docs/status/task-memory synchronized in the same change set.
- Do not start new work beyond route discovery and memory truth.
- Update the task file with plan, commands run, outcomes, and follow-ups.

### Likely verification
- targeted frontend/backend regression tests for drilldown/navigation behavior
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of the new drilldown entrypoints and doc updates.
- Files changed and why.
- Commands run and results.
- Any status/capability/task-memory updates.
- Any follow-on work that should become the next epic rather than being smuggled into this task.
