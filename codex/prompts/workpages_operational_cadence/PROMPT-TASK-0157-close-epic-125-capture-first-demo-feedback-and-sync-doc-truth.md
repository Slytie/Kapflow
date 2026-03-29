# Prompt for TASK-0157 - Close EPIC-125, capture first-demo feedback, and sync doc truth

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0157-close-epic-125-capture-first-demo-feedback-and-sync-doc-truth.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`

### What to figure out before coding
- Which docs/status/task-memory files must change together so fresh-session Codex runs remain truthful.
- How to record first-demo feedback themes without starting hardening work early.
- What exact stop line should be handed to EPIC-126.

### Red-team checks
- Keep this task within EPIC-125 scope.
- Do not broaden into EPIC-126 hardening work.
- Do not weaken artifact or pointer authority.
- Do not widen schedule beyond the agreed bounded lane.

### Output required from Ask mode
- Short diagnosis of the current repo state for this task.
- Proposed files/components/tests.
- The boundary decision and why it is the right seam.
- Docs that must be updated when this becomes real.
- Smallness check explaining why this still fits one bounded Codex task.

## Code mode prompt
Use this section only after the Ask-mode plan is reviewed and approved.

### Step 0 - Reload the minimum context
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/tasks/TASK-0157-close-epic-125-capture-first-demo-feedback-and-sync-doc-truth.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- relevant planning/status/context docs touched in EPIC-125

### Implementation rules
- Keep the change bounded to this task’s seam.
- Preserve the existing canonical workpage route families.
- Update the task file with plan, commands run, outcomes, and follow-ups.

### Likely verification
- `python3 scripts/validate_repo.py --schemas-only`
- targeted backend/frontend/runtime checks appropriate to the slice

### Deliverables in your final response
- Concise summary of the work completed.
- Files changed and why.
- Commands run and results.
- Any doc/task-memory updates.
- Any follow-on work that should remain in later EPIC-125 tasks rather than being smuggled into this task.
