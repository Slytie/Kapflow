---
id: TASK-0217
epic: EPIC-133
title: "Converge the demo shell onto canonical workpage hosts and retire inline mutation logic"
status: DONE
owners: ["frontend", "backend"]
reviewers: ["architect"]
depends_on: ["TASK-0215"]
risk: medium
context_packs:
  - "codex/context/EPIC-133.md"
  - "codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md"
patterns: []
---

## Context
`/demo/logistics` remains useful as a shell/story entrypoint, and before this task `frontend/src/components/workpages/InlineLogisticsWorkpages.tsx` behaved like a second mutation engine for create/submit/history logic.

That duplicates canonical workpage behavior and increases fragility.

## Objective
Keep the demo shell as a discovery surface while removing it as an independent mutating orchestration path.

## Non-goals
- No removal of the top-level demo shell itself if it still serves the product/story need.
- No new product surface.

## Source files to read first
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/lib/repositories/workpagesRepository.ts`
- canonical workpage page/host components
- relevant demo/workpage route tests

## Source files to change
- demo shell components/pages
- shell navigation helpers
- inline-only repository helpers
- shared host components if needed
- relevant tests

## Plan
1. Decide the minimal safe end state:
   - preview-only handoff to canonical pages, or
   - embedded reuse of canonical hosts without duplicate mutation logic.
2. Remove duplicate create/submit/history orchestration from the inline demo path.
3. Preserve the demo shell’s value as navigation/story context without letting it own a second write boundary.
4. Add tests proving the demo shell no longer acts as an independent mutation engine.

## Verification
- frontend page/route tests for demo-shell behavior
- manual review of canonical-vs-demo mutation paths

## Acceptance criteria
- There is one primary mutation path per workpage surface.
- The demo shell no longer duplicates core artifact mutation orchestration.

## Execution notes
- Rewrote `frontend/src/pages/LogisticsDemoPage.tsx` so `/demo/logistics` now renders launcher cards for weekly planning, dispatch reporting, and live dispatch rather than embedding editable schedule/EOD workpages inline.
- Updated `frontend/src/app/AppShell.tsx` to preserve derived logistics `module` and `workflow_run_id` query context when navigating back to `/demo/logistics` from canonical logistics routes.
- Retired the duplicate inline mutation engine by deleting `frontend/src/components/workpages/InlineLogisticsWorkpages.tsx` and removing the inline-only history helpers from `frontend/src/lib/repositories/workpagesRepository.ts`.
- During the frontend fallout pass, aligned the run-backed schedule landing’s driver-preferences create handoff with the server-authored `action_ref` seam already used on the canonical artifact surfaces.
- Refreshed `frontend/src/pages/logisticsDemoPage.test.tsx` and `frontend/src/pages/logisticsWorkpageRoutes.test.tsx` so the demo shell is regression-protected as a launcher-only surface and retired `/demo/logistics/workpages/*` routes remain unresolved.
