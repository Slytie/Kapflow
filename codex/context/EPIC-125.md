# EPIC-125 Context Pack - Operational cadence demo

Purpose:
- You are reviewing historical EPIC-125 operator-loop truth after closeout.
- You need to preserve one truthful weekly planning + minimal daily replan + daily reporting lane without inventing a second authority path.
- You should treat this pack as completed-history context, not as the active post-workpage plan of record.

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
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
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
- The continuous production-shaped cadence milestone is now landed through `TASK-0156`.
- At planning time, EPIC-126 hardening stayed deferred until after local demo feedback existed; that follow-on path is now completed history.

## Current repo status
- EPIC-124 is complete, so supported workspace items already expose bounded `workpage_actions[]`, and canonical run-backed/artifact-backed workpage routes are already live.
- `weekly_schedule_planning.v1` already has the bounded Stage04 build/review lane and official publish semantics.
- `dispatch_reporting.v1` now has the bounded daily EOS intake -> deterministic draft build -> Stage04 review -> finalize -> planning feedback lane, and the artifact-backed EOD review workpage remains the review surface.
- `live_dispatch.v1` already has weekly seed activation, route-delta intake, actual-hours binding, and official ordered-delta promotion semantics.
- `TASK-0152`, `TASK-0153`, and `TASK-0155` are now complete, so EPIC-125 already has the weekly operator lane, the daily reporting lane, and the weekly-first local demo surface.
- `TASK-0156` is now complete, so EPIC-125 also has the external cadence tick plus the first continuous single-node operator runbook.
- `TASK-0154` and `TASK-0157` are now complete, so EPIC-125 is closed as completed history.
- The first-demo feedback handoff is frozen in `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_EPIC125_CLOSEOUT_AND_FEEDBACK_NOTE.md`, and the downstream work is already reflected in completed EPIC-126 cleanup history plus the landed EPIC-131, EPIC-132, EPIC-133, and EPIC-134 tranches.

## Historical implementation order inside this epic
1. `TASK-0151` - Freeze operator-loop contract, authoritative inputs, and milestones
2. `TASK-0152` - DONE - Weekly Friday intake + Stage04 build/review/publish
3. `TASK-0153` - DONE - Daily EOS intake + EOD draft review/finalize + planning feedback
4. `TASK-0154` - DONE - Minimal manual daily replan via live-dispatch delta authority
5. `TASK-0155` - DONE - Local demo runbook, smoke path, and entrypoints
6. `TASK-0156` - DONE - External cadence tick + single-node production-shaped runbook
7. `TASK-0157` - DONE - Closeout, demo-feedback capture, and doc/status sync

## Post-closeout posture
- EPIC-125 is now completed history and should not be reopened for new runtime scope.
- Later feedback-consuming work is already reflected in completed EPIC-126 cleanup history plus the landed EPIC-131, EPIC-132, EPIC-133, and EPIC-134 tranches.
- If work returns to operator loops, start from current repo truth rather than treating this pack as the next active implementation queue.
- Do not add raw-email parser ownership, live-dispatch algorithmics, schedule Stage06/Stage07 widening, or an embedded scheduler in this epic.

## Smallest context set if work revisits this historical operator-loop tranche
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_EXEC_SUMMARY.md`
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
