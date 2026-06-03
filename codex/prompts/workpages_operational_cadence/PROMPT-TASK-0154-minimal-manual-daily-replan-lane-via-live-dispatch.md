# Prompt for TASK-0154 - Minimal manual daily replan lane via live dispatch

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0154-minimal-manual-daily-replan-lane-via-live-dispatch.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/domains/logistics/current-state/LOGISTICS_WEEKLY_TO_LIVE_HANDOFF_RUNTIME.md`
- `src/onetruth/application/handlers/logistics_handoff.py`
- `tests/runtime/test_logistics_handoff_runtime.py`

### What to figure out before coding
- The smallest live-dispatch slice that supports manual daily schedule change without algorithmic candidate generation.
- How to reuse the existing seed activation, route-delta intake, actual-hours binding, and official delta promotion seams.
- Whether any review/approval path needs bounded UI or task surfacing in this epic.

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
- `codex/tasks/TASK-0154-minimal-manual-daily-replan-lane-via-live-dispatch.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/domains/logistics/current-state/LOGISTICS_WEEKLY_TO_LIVE_HANDOFF_RUNTIME.md`
- `src/onetruth/application/handlers/logistics_handoff.py`
- relevant live-dispatch runtime tests

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
