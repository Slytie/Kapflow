---
id: TASK-0218
epic: EPIC-133
title: "Split overloaded workpage modules and add architecture guardrails for bounded growth"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["architect"]
depends_on: ["TASK-0216", "TASK-0217"]
risk: medium
context_packs:
  - "codex/context/EPIC-133.md"
  - "codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md"
patterns: []
---

## Context
The post-EPIC-131 system is materially better, but several files remain heavy concentration points. That means future workpage growth can still re-accumulate fragility even after the repo is green.

## Objective
Reduce concentration and add guardrails so new workpage kinds extend the system through bounded seams instead of repeated large-file branching.

## Non-goals
- No giant rewrite.
- No generic workpage DSL.
- No feature expansion.

## Source files to read first
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `frontend/src/components/workpages/InlineLogisticsWorkpages.tsx`
- `frontend/src/pages/LogisticsScheduleWorkpagePage.tsx`
- existing route-registry/architecture-guardrail tests

## Source files to change
- overloaded backend workpage modules
- overloaded frontend workpage host/page modules
- tests or lightweight guardrails that protect the extracted seams

## Plan
1. Extract bounded backend modules around:
   - descriptor-owned query helpers,
   - mutation helpers,
   - per-workpage contract builders.
2. Extract bounded frontend host/page hooks/components where duplication is still high.
3. Add lightweight architecture guardrails or characterization tests so the new seams stay intentional.
4. Keep the change incremental: move code only when the owning boundary is clearer afterward.

## Verification
- targeted backend/frontend tests remain green after extraction
- any added architecture-guardrail tests pass
- file responsibility is visibly improved in the diff

## Acceptance criteria
- The most overloaded workpage files are smaller and more purpose-bounded.
- Future workpage additions can land through explicit seams instead of repeated large-file edits.
- The repo is more extensible without becoming a framework project.
