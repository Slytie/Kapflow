# Prompt for TASK-0152 - Weekly Friday intake and Stage04 build/review/publish loop

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0152-weekly-friday-intake-and-stage04-build-review-publish-loop.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/api/routes/human_tasks.py`

### What to figure out before coding
- The minimal truthful weekly intake task and requirement mapping.
- Which existing Stage04 planner/agent and review/publish seams can be reused directly.
- How the reviewed draft becomes the official published weekly schedule without widening schedule scope.

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
- `codex/tasks/TASK-0152-weekly-friday-intake-and-stage04-build-review-publish-loop.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `src/onetruth/application/services/weekly_stage04_openai_agent.py`
- `src/onetruth/application/handlers/workpages.py`
- relevant route/handler/tests for weekly planning and pointers

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
