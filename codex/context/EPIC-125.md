# EPIC-125 Context Pack - Operational cadence demo

Purpose:
- You are reviewing or extending the active EPIC-125 operator-loop tranche after EPIC-124 closeout.
- You need to preserve one truthful weekly planning + minimal daily replan + daily reporting lane without inventing a second authority path.
- You need to keep the first serious local demo earlier than cadence automation and earlier than hardening.

## Non-negotiable invariants to keep in mind
- Workpages remain derived review/edit surfaces; runtime rows, events, artifacts, pointers, and promotions remain canonical truth.
- Keep the existing canonical workpage route families intact:
  - run-backed workpages under `/runs/:workflowRunId/workpages/*`
  - artifact-backed workpage routes under `/runs/:workflowRunId/workpages/*/artifacts/:artifactVersionId`
- Weekly Friday machine truth in this epic is Stage04-ready workbook input, not a new parser-owned raw-email truth path.
- Raw route email/doc may remain evidence, but not the authoritative operator input seam for EPIC-125.
- Manual daily schedule change must stay a live-dispatch delta lane, not algorithmic candidate generation and not widened weekly schedule editing.
- Update repo-native docs, task files, and status memory in the same change set whenever the operator-loop truth changes.

## Contracts and docs to treat as authoritative
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/planning/epics/EPIC-125.md`
- `codex/context/EPIC-125.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## TASK-0151 freeze
- `TASK-0151` is complete and doc-only.
- The first EPIC-125 operator lane is three loops only:
  - weekly Friday planning over Stage04-ready workbook inputs
  - minimal manual daily replan via `live_dispatch.v1` delta authority
  - daily reporting closeout via `dispatch_reporting.v1` EOS intake, draft review, finalization, and planning feedback
- The first local FE/BE demo milestone is after `TASK-0155`.
- The continuous production-shaped cadence milestone is after `TASK-0156`.
- EPIC-126 hardening stays deferred until after local demo feedback exists.

## Current repo status
- EPIC-124 is complete, so supported workspace items already expose bounded `workpage_actions[]`, and canonical run-backed/artifact-backed workpage routes are already live.
- `weekly_schedule_planning.v1` already has the bounded Stage04 build/review lane and official publish semantics.
- `dispatch_reporting.v1` now has the bounded daily EOS intake -> deterministic draft build -> Stage04 review -> finalize -> planning feedback lane, and the artifact-backed EOD review workpage remains the review surface.
- `live_dispatch.v1` already has weekly seed activation, route-delta intake, actual-hours binding, and official ordered-delta promotion semantics.
- `TASK-0151` has now made EPIC-125 repo-native and frozen the stop lines before any weekly/daily cadence behavior work begins.

## Active implementation order inside this epic
1. `TASK-0151` - Freeze operator-loop contract, authoritative inputs, and milestones
2. `TASK-0152` - Weekly Friday intake + Stage04 build/review/publish
3. `TASK-0153` - Daily EOS intake + EOD draft review/finalize + planning feedback
4. `TASK-0154` - Minimal manual daily replan via live-dispatch delta authority
5. `TASK-0155` - Local demo runbook, smoke path, and entrypoints
6. `TASK-0156` - External cadence tick + single-node production-shaped runbook
7. `TASK-0157` - Closeout, demo-feedback capture, and doc/status sync

## Post-task posture
- `TASK-0154` is the next bounded implementation tranche.
- Do not start EPIC-126 early.
- Do not add raw-email parser ownership, live-dispatch algorithmics, schedule Stage06/Stage07 widening, or an embedded scheduler in this epic.

## Smallest context set for the next task
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/planning/epics/EPIC-125.md`
- `docs/workflows/live_dispatch/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `src/onetruth/application/handlers/logistics_handoff.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/api/routes/workflow_runs.py`

## Red-team questions for future runs
- Are we quietly turning raw route email/doc into authoritative system input?
- Are we widening daily replan into live-dispatch candidate generation or ranking?
- Are we trying to move the local demo milestone later than necessary?
- Are we treating EPIC-126 hardening as permission to start broader scope before the first local operator demo is real?
