---
id: TASK-0127
epic: EPIC-120
title: "Integrate workpage entrypoints into the logistics demo shell and keep docs/status truth synchronized"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0125", "TASK-0126"]
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
Once the two pages exist, the repo needs truthful route entrypoints, page-map updates, and status/capability reconciliation so future Codex sessions and contributors do not work from stale assumptions.

## Objective
Integrate the schedule and EOD workpage routes into the primary logistics demo shell and reconcile the repo-native docs/status/task memory around the new surfaces.

## Non-goals
- No backend artifact/workpage API.
- No generic navigation overhaul.
- No hidden route surfaces without doc updates.

## Source files changed
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- route integration tests
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- routing and task-memory docs

## Verification
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:run -- logistics`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The workpage routes are reachable from the primary logistics demo shell.
- `AppShell` correctly treats `/demo/logistics/*` as logistics-shell routes.
- Page-map and capability docs tell the truth about what now exists.
- Current-focus/decision docs capture the new visible product posture.
- The repo does not gain an undocumented or stale workpage surface.
