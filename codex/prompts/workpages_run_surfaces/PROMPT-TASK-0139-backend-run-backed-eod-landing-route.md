# Prompt for TASK-0139 - Backend run-backed EOD landing/draft-resolution route and snapshot

You are a Codex coding agent working in this repo.

## Ask mode prompt
Use this section in **Ask mode** first. Do not edit code yet.

### Step 0 - Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `codex/tasks/TASK-0139-backend-workflow-run-backed-eod-landing-draft-resolution-route-and-snapshot.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`

### What to figure out before coding
- The cleanest builder/service seam for run-backed EOD landing and draft resolution.
- Which reporting-run and artifact-chain facts are authoritative for the landing payload.
- How the route should represent create/open/latest-draft resolution without duplicating artifact-edit semantics.
- How to extend snapshot export/check flows for the new route.

### Red-team checks
- Do not broaden into submit/materialize work.
- Do not switch the page to final-packet semantics.
- Do not blur run-backed landing with artifact-backed editing.
- Do not skip docs/snapshot updates when the route becomes real.

### Output required from Ask mode
- Short diagnosis of the backend EOD run-backed route slice.
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
- `codex/tasks/TASK-0139-backend-workflow-run-backed-eod-landing-draft-resolution-route-and-snapshot.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `tests/runtime/helpers/frontend_snapshots.py`

### Implementation rules
- Keep the route backend-owned and contract-shaped.
- Resolve the latest draft from canonical run/artifact truth rather than frontend-local state.
- Keep actual workbook editing on the existing artifact-backed route.
- Extend backend-owned snapshot export/check flows in the same change set.
- Update docs/status/task-memory if visible route truth changes.
- Update the task file with plan, commands run, outcomes, and follow-ups.

### Likely verification
- targeted runtime/API tests for the new route
- snapshot export/check tests
- `python3 scripts/validate_repo.py --schemas-only`

### Deliverables in your final response
- Concise summary of the run-backed EOD landing/draft-resolution route added.
- Files changed and why.
- Commands run and results.
- Any doc/task-memory updates.
- Any follow-on work that should remain in `TASK-0140` or `TASK-0141` rather than being smuggled into this task.
