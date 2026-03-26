---
id: TASK-0141
epic: EPIC-122
title: "Expose demo/story drilldown entrypoints and keep workflow-run-backed workpage docs/status synchronized"
status: TODO
owners: ["frontend", "backend"]
reviewers: ["qa"]
depends_on: ["TASK-0140"]
risk: medium
context_packs: ["codex/context/EPIC-122.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0140`, workflow-run-backed workpage routes should exist, but the logistics demo shell and repo-native docs/status memory still need to make that truth discoverable and durable for future runs.

## Objective
Expose truthful demo/story drilldown entrypoints into the new workflow-run-backed workpage routes and synchronize repo-native docs/status/task memory so future Codex sessions do not drift back to the old demo-only posture.

## Non-goals
- No schedule write-path work.
- No EOD final-packet/approval semantics.
- No broad workspace/human-task integration.
- No deprecation/removal of demo aliases unless the replacement posture is fully proven and documented.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- the workpage route/page files from `TASK-0140`

## Source files to change
- logistics demo shell drilldown/entrypoint files
- any small support files required for truthful route discovery
- docs/status/page-map/capability/epic/task-memory files touched by the new visible truth
- targeted regression tests for drilldown/navigation behavior
- the task file itself

## Plan
1. Add truthful drilldown entrypoints from the logistics demo shell into the canonical run-backed workpage routes.
2. Keep demo aliases/entrypoints coherent while the canonical routes become primary.
3. Update repo-native docs/status/task memory in the same change set.
4. Freeze route-discovery regressions in tests.

## Verification
- targeted frontend/backend regression tests for drilldown/navigation behavior
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- A user can discover the canonical run-backed workpage routes from the logistics demo/story drilldown surface.
- Repo-native docs/status/task memory all point at the same route posture.
- The slice leaves the next epic decision cleanly framed (schedule write boundary and/or broader workflow integration).

## Notes / decisions
This task is where the new canonical route posture becomes understandable to future fresh-session Codex runs, not just technically implemented.
