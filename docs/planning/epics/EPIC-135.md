# EPIC-135 - Unified schedule replan popup and dynamic scheduling activation

## Summary
Turn `Edit Weekly Schedule` into one shared operator surface for greenfield and brownfield replanning without collapsing weekly-planning truth and live-dispatch truth into one ambiguous backend lane.

This epic starts after EPIC-134 and assumes the public workpage posture is already canonical-only.

## Status
Selected on `2026-04-25`. Corrected on `2026-04-25` after repo-level review against the authored workflow packs, runtime seams, and current actionability model.

Current state:
- `TASK-0225` through `TASK-0232` are the selected bounded tranche.
- No EPIC-135 runtime code is landed yet; the current repo change set corrects the epic/task/workflow-pack truth before implementation starts.

## First-principles objective
Use one operator-facing popup surface:

\[
U_{schedule} = \Pi_{popup}(S, C, R)
\]

while preserving lifecycle-based backend ownership:

\[
\text{before publish} \Rightarrow weekly\_schedule\_planning.v1
\]

\[
\text{after publish} \Rightarrow live\_dispatch.v1
\]

The popup is shared; the authority model is not.

## In scope
- freeze the shared-popup / dual-backend architecture in repo-native planning memory
- add a shared proposal/candidate/runtime-status contract for the schedule popup
- introduce mirrored weekly/live driver-contact bridge inputs for phone numbers
- reuse deterministic ranking/checking for top candidates and manual override support
- replace the current route-demand refresh-task path with pre-publish weekly replan activation
- auto-trigger scheduler execution for in-scope `0 -> N` route additions
- move post-publish sick/no-show and route increases onto live-dispatch-backed replan truth
- redesign `Edit Weekly Schedule` into a proposal-review + manual-override popup
- retire the operator-facing manual scheduler task UX only after the replacement flow and recovery surface exist

## Out of scope
- editing driver contact data in the UI
- storing phone numbers in driver capabilities
- a generalized live-dispatch workpage productization effort
- browser-side candidate ranking
- popup-only inferred “AI working” indicators
- mutation of the published weekly base schedule

## Dependencies
- EPIC-125
- EPIC-131
- EPIC-133
- EPIC-134
- EPIC-070

Context packs:
- `codex/context/EPIC-135.md`
- `codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md`

## Task stack
- `TASK-0225` - Freeze the unified schedule replan boundary, lifecycle split, prerequisite truth, and repo memory
- `TASK-0226` - Add shared replan contract blocks and canonical runtime-status projection
- `TASK-0227` - Add driver-contact authority and deterministic replan candidate/compliance projection
- `TASK-0228` - Implement the pre-publish weekly-backed replan adapter and in-scope greenfield trigger
- `TASK-0229` - Implement the post-publish live-dispatch replan adapter over base-seed plus delta truth
- `TASK-0230` - Add the live-dispatch agent runtime for greenfield auto-run and bounded brownfield escalation
- `TASK-0231` - Redesign `Edit Weekly Schedule` into the shared replan popup
- `TASK-0232` - Close EPIC-135 by retiring the manual scheduler UX and updating canonical demo truth

## Sequencing correction
- `TASK-0225` -> `TASK-0226`, `TASK-0227`
- `TASK-0226`, `TASK-0227` -> `TASK-0228`, `TASK-0229`
- `TASK-0228`, `TASK-0229` -> `TASK-0231`
- `TASK-0229` -> `TASK-0230`
- `TASK-0231`, `TASK-0230` -> `TASK-0232`

## Acceptance criteria
- The operator uses one shared schedule popup before and after publish, but backend ownership still splits weekly vs live dispatch by lifecycle state.
- In-scope `0 -> N` route additions auto-trigger scheduling without a manual task click and without leaving behind a hidden legacy refresh-task path.
- The popup shows top 3 picks, all other eligible candidates, blocked candidates, phone numbers, rolling-7/compliance context, and canonical runtime-backed status built from existing requirement/actionability/runtime truth.
- Post-publish sick/no-show and route increases create issue-scoped live-dispatch replan truth without mutating the published weekly base schedule.
- The operator-facing to-do/task-board no longer exposes the old manual scheduler entrypoint, but canonical task/execution/input evidence still exists in audit/run-detail/runtime surfaces.

## Key decision
The sustainable design is not “weekly owns everything” and not “live dispatch owns everything.” It is one shared popup surface over a lifecycle-split backend: weekly before publish, live dispatch after publish.
