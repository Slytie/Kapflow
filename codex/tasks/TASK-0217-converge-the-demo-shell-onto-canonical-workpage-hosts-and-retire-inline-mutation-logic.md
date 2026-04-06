---
id: TASK-0217
epic: EPIC-133
title: "Converge the demo shell onto canonical workpage hosts and retire inline mutation logic"
status: TODO
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
`/demo/logistics` is still useful as a shell/story entrypoint, but `frontend/src/components/workpages/InlineLogisticsWorkpages.tsx` currently behaves like a second mutation engine for create/submit/history logic.

That duplicates canonical workpage behavior and increases fragility.

## Objective
Keep the demo shell as a discovery surface while removing it as an independent mutating orchestration path.

## Non-goals
- No removal of the top-level demo shell itself if it still serves the product/story need.
- No new product surface.

## Source files to read first
- `frontend/src/components/workpages/InlineLogisticsWorkpages.tsx`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- canonical workpage page/host components
- relevant demo/workpage route tests

## Source files to change
- demo shell components/pages
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
