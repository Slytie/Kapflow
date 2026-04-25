---
id: TASK-0232
epic: EPIC-135
title: "Close EPIC-135 by retiring the manual scheduler UX and updating canonical demo truth"
status: TODO
owners: ["architect", "qa"]
reviewers: ["pm"]
depends_on: ["TASK-0231", "TASK-0230"]
risk: medium
context_packs:
  - "codex/context/EPIC-135.md"
  - "codex/context/UNIFIED_REPLAN_ARCHITECTURE_FINDINGS_2026-04-25.md"
patterns: ["docs-as-truth"]
---

## Why
The epic is not complete until the operator-facing to-do UX, canonical demo, and repo-native memory all reflect the new popup-led replan model instead of the old manual scheduler entrypoint.

## Scope
- remove the operator-facing manual scheduler task/action from the task strip, workspace action panel, and detail-drawer affordances
- keep canonical backend task/execution evidence intact
- update the canonical demo prep path with driver contacts and both greenfield/brownfield scenarios
- refresh epic/task/status/doc truth and close the epic with regressions

## Out of scope
- broader live-dispatch workpage productization
- contact-data authoring UI
- unrelated demo-shell redesign

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-135.md`
- `scripts/run_logistics_workpage_demo_prep.py`
- `docs/ops/runbooks/logistics_canonical_workpage_demo.md`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/pages/runWorkspacePage.test.tsx`

## Source files to change
- workspace/task/drawer UI affordances
- canonical demo seed/prep/runbook assets
- epic/task/status/index memory
- regression tests and snapshots

## Plan
1. Retire the old manual scheduler CTA from operator-facing to-do/task surfaces only after:
   - `TASK-0228` has replaced the current refresh-task creation path
   - `TASK-0226` exposes blocked / claim / running truth in the popup
   - `TASK-0231` provides the shared popup recovery/resume surface
   - `TASK-0230` has landed the later live-dispatch runtime surface if that task remains in-scope for the epic closeout
2. Leave backend task/execution truth intact for status projection and auditability.
3. Seed canonical demo contact data plus one greenfield and one brownfield replan path only after the corrected contract and popup behavior exist.
4. Update the canonical demo runbook to validate the shared popup, candidate list, phone numbers, and runtime status.
5. Close EPIC-135 with updated status/index memory and regression proof.

## Verification
- canonical demo prep regression
- focused workspace/task-surface tests proving the old scheduler CTA is gone
- focused popup/route-demand/sick-no-show regression tests
- `git diff --check`

## Acceptance criteria
- Operators no longer use a manual scheduler task/button to start the new flow.
- The old scheduler CTA is removed only after the replacement route-demand/replan path and popup recovery surface exist.
- The canonical demo proves greenfield activation, brownfield replacement, phone-number display, and runtime status.
- Repo-native epic/task/status truth is synchronized on closeout.
