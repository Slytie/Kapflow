# Supervisor prompt for EPIC-125 - Operational cadence demo

You are a Codex coding agent working in this repo.

This repo is optimized for fresh-session re-entry. Keep context tight and update repo-native memory as you go.

## Goal
Choose the next bounded task in EPIC-125 and confirm that the repo really matches the assumed post-EPIC-124 baseline before any coding starts.

## Load context in this order
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-124.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- the workpage files that should exist after EPIC-123 and EPIC-124

## What to do in supervisor mode
- Confirm the repo really contains the expected outputs from EPIC-121..EPIC-124. If not, stop and say the assumption is false and must be reconciled.
- Confirm which of `TASK-0151`..`TASK-0157` should run next.
- State whether any prerequisite contract/doc contradiction still exists.
- List the smallest context set the next task actually needs.
- Call out any doc/status files that must be updated by the next task.

## Red-team checks
- Do not start hardening/closeout work from EPIC-126.
- Do not let raw route email become authoritative system input in this epic.
- Do not let minimal daily replan drift into live-dispatch candidate generation.
- Do not start a new embedded scheduler.
- Do not move the local-demo milestone later than necessary.

## Output required
- Next task id and title.
- Why it is the right next bounded tranche.
- Exact files to read first for that task.
- Key red-team risks for that task.
- Any blocking contradiction to resolve before coding.
