# Prompt for TASK-0137 - Workflow-run-backed workpage contract, alias posture, and draft-resolution boundary

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0137-workflow-run-backed-workpage-contract-alias-posture-and-draft-resolution.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_BRIEF.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`

### What to figure out before coding
- Whether the assumed post-`TASK-0136` baseline is actually present in the repo.
- The smallest viable workflow-run-backed route family.
- The cleanest alias posture between `/demo/logistics/workpages/*` and `/runs/:workflowRunId/workpages/*`.
- The smallest contract addition needed for run context and EOD draft resolution.
- Which open questions must stay out of scope for this epic.

### Red-team checks
- Do not implement routes in this task.
- Do not start schedule write-path design.
- Do not broaden into final-packet/workspace integration.
- Do not overload artifact metadata on a run-backed landing page if it changes semantics.
- Do not leave the stop line ambiguous.

### Output required from Ask mode
- Short diagnosis of the current repo state for this task.
- Proposed route-family decision.
- Proposed alias/canonical posture.
- Proposed contract-extension decision.
- Exact files to add/change and why.
- Smallest validations that prove the docs/contract are coherent.
- Smallness check explaining why this still fits one bounded Codex task.

## Code mode prompt
Use this section only after the Ask-mode plan is reviewed and approved.

### Step 0 - Reload the minimum context
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/tasks/TASK-0137-workflow-run-backed-workpage-contract-alias-posture-and-draft-resolution.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`

### Implementation rules
- Keep this task doc/contract-only.
- Freeze the alias/canonical posture clearly enough that backend and frontend work can proceed without guesswork.
- Keep schedule query-backed/composite and EOD artifact-backed editing distinct.
- Update the task file with plan, commands run, outcomes, and follow-ups.

### Likely verification
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of the route-family/alias/contract decisions.
- Files changed and why.
- Commands run and results.
- Any doc/task-memory updates.
- Any open questions that should remain for `TASK-0138`..`TASK-0141` rather than being smuggled into this task.
