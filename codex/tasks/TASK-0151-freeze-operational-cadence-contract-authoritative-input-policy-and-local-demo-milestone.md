---
id: TASK-0151
epic: EPIC-125
title: "Freeze the operational cadence contract, authoritative-input policy, and local-demo milestone"
status: DONE
owners: ["docs"]
reviewers: ["qa"]
depends_on: ["TASK-0150"]
risk: medium
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
Before coding the next operator loop, the repo needs one explicit contract for the first weekly planning, daily replan, and daily reporting cadence story.

## Objective
Freeze the bounded EPIC-125 operator-loop contract, authoritative inputs, and milestone names so later tasks can implement the loop without drifting into parser scope, live-dispatch algorithmics, or early hardening.

## Non-goals
- No runtime code, routes, schemas, or workpage behavior changes.
- No start on `TASK-0152` through `TASK-0157`.
- No EPIC-126 hardening work.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/epics/EPIC-124.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`

## Context packs / patterns to consult
- `codex/context/EPIC-125.md`
- `PATTERN-007`
- `PATTERN-009`

## Source files to change
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/planning/epics/EPIC-125.md`
- `docs/planning/epics/EPIC-126.md`
- `codex/context/EPIC-125.md`
- `codex/context/EPIC-126.md`
- `codex/prompts/workpages_operational_cadence/*`

## Generated / downstream artifacts impacted
- repo-native epic/task/context memory for EPIC-125 and EPIC-126
- the operational cadence executive summary and plan used by future Codex sessions
- prompt-pack routing for the next bounded operator-loop tasks

## Plan
1. Import the EPIC-125/126 planning package into repo-native docs, context packs, task briefs, and prompt pack files.
2. Freeze the weekly authoritative-input posture as Stage04-ready workbook input, not raw route email/doc.
3. Freeze the first daily schedule-change posture as a manual `live_dispatch.v1` delta lane, not widened weekly editing and not candidate generation.
4. Freeze the local-demo milestone after `TASK-0155` and the continuous production-shaped cadence milestone after `TASK-0156`.
5. Update top-level repo memory so EPIC-125 is active, `TASK-0151` is done, and `TASK-0152` is next.

## Verification
- `python3 scripts/validate_repo.py --schemas-only`
- repo-memory consistency check across epic/task/context/status files
- targeted `rg` checks that the stop line stays out of parser scope, live-dispatch algorithmics, and early EPIC-126 hardening

## Acceptance criteria
- EPIC-125 and EPIC-126 planning memory is repo-native.
- `TASK-0151` is marked complete and its frozen decisions are reflected in repo memory.
- The local-demo milestone and production-shaped cadence milestone are explicit and distinct.
- The repo does not imply that `TASK-0152` through `TASK-0157` or EPIC-126 started in this tranche.

## Outcome
- EPIC-125 and EPIC-126 are now repo-native across epic briefs, context packs, task files, planning docs, and the new operational-cadence prompt pack.
- The frozen EPIC-125 boundary is now explicit: weekly Friday machine truth is Stage04-ready workbook input, raw route email/doc remains evidence only, daily reporting truth stays in `dispatch_reporting.v1`, and daily schedule change is a minimal manual `live_dispatch.v1` delta lane.
- Repo memory now treats the first serious local FE/BE demo as the `TASK-0155` milestone and keeps continuous production-shaped cadence work deferred to `TASK-0156`.
- `TASK-0152` is now the next bounded implementation tranche, while EPIC-126 remains explicitly deferred until after local-demo feedback is real.

## Commands run
- `python3 scripts/validate_repo.py --schemas-only`
- `rg -n "EPIC-125|EPIC-126|TASK-0151|Stage04-ready|manual daily replan|raw route email|local demo" docs codex`

## Follow-ups
- `TASK-0152` should implement the weekly Friday intake and Stage04 build/review/publish loop against the frozen Stage04-ready input policy.
- `TASK-0153` should keep daily reporting truth inside `dispatch_reporting.v1` and reuse the existing EOD artifact-backed review surface.
- `TASK-0154` should keep day-of change strictly inside the minimal manual live-dispatch delta lane.
