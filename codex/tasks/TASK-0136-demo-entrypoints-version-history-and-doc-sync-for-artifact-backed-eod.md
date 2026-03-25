---
id: TASK-0136
epic: EPIC-121
title: "Expose demo entrypoints, recent-version history, and doc/status sync for the artifact-backed EOD slice"
status: TODO
owners: ["frontend", "backend"]
reviewers: ["qa"]
depends_on: ["TASK-0135"]
risk: medium
context_packs: ["codex/context/EPIC-121.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0135`, the artifact-backed EOD path should work end to end, but it still needs truthful launch points, recent-version discoverability, and final doc/status cleanup so future Codex runs do not drift.

## Objective
Polish the first artifact-backed slice so it is discoverable from the logistics demo shell, exposes recent-version lineage/history cleanly, and leaves the repo-native docs/status/task memory truthful.

## Non-goals
- No schedule write path.
- No final-packet or approval/pointer flow.
- No broad workspace/human-task integration project.
- No generic multi-page history browser outside the EOD slice.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- the artifact-backed EOD files/tests from `TASK-0134` and `TASK-0135`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`

## Source files to change
- logistics demo shell entrypoints/navigation affordances for artifact-backed EOD drafts
- any small backend/frontend support files required for recent-version history display
- docs/status/task-memory files touched by the new visible truth
- regression tests for entrypoints/history/shell behavior
- the task file itself with outcomes and follow-ups

## Plan
1. Add truthful create or open entrypoints from the query-backed EOD surface into the artifact-backed route.
2. Make recent-version history or lineage easy to inspect in the artifact-backed page.
3. Update repo-native docs/status/task memory to reflect the new capability.
4. Freeze shell regressions so `/demo/logistics/*` remains coherent.

## Verification
- targeted frontend/backend regression tests for entrypoint and history behavior
- doc/status consistency check
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- A user can discover and enter the artifact-backed EOD slice from the logistics demo shell.
- The artifact-backed page exposes recent version lineage/history clearly enough for demo use.
- The repo-native docs/status/task memory are all updated in the same change set.
- The task leaves the next epic decision cleanly framed (workspace/task integration and/or schedule artifact boundary).

## Notes / decisions
This task is where the slice becomes understandable to future fresh-session Codex runs, not just technically functional.
