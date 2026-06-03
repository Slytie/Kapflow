# Supervisor prompt for EPIC-122 - Workflow-run-backed workpages

You are a Codex coding agent working in this repo.

This repo is optimized for fresh-session re-entry. Keep context tight and update repo-native memory as you go.

## Goal
Choose the next bounded task in EPIC-122 and confirm that the repo really matches the assumed post-`TASK-0136` baseline before any coding starts.

## Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-121.md`
- `docs/planning/epics/EPIC-122.md`
- `codex/context/EPIC-122.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_RUN_SURFACES_BRIEF.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `src/onetruth/api/routes/workpages.py`
- the workpage files that should exist after `TASK-0136`

## What to do in supervisor mode
- Confirm the repo really contains the expected outputs from `TASK-0136`. If not, stop and say the assumption is false and must be reconciled.
- Confirm which of `TASK-0137`..`TASK-0141` should run next.
- State whether any prerequisite contract/doc contradiction still exists.
- List the smallest context set the next task actually needs.
- Call out any doc/status files that must be updated by the next task.

## Red-team checks
- Do not start schedule write-path work.
- Do not reopen the first artifact-backed EOD slice unless the baseline is actually missing.
- Do not broaden into final-packet/workspace/human-task modernization.
- Do not let demo aliases remain the only active access model once canonical run-backed routes exist.
- Do not leave repo-memory/docs stale while route truth changes.

## Output required
- Next task id and title.
- Why it is the right next bounded tranche.
- Exact files to read first for that task.
- Key red-team risks for that task.
- Any blocking contradiction to resolve before coding.
