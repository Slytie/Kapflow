---
id: TASK-0207
epic: EPIC-131
title: "Close the epic with regressions, docs, compatibility cleanup, and deferred-item markers"
status: TODO
owners: ["qa", "backend", "frontend"]
reviewers: ["architect"]
depends_on: ["TASK-0203", "TASK-0204", "TASK-0205", "TASK-0206"]
risk: medium
context_packs:
  - "codex/context/EPIC-131.md"
  - "codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md"
patterns: []
---

## Context
This epic changes backend contracts, schedule preview/save behavior, route-demand propagation, and frontend navigation semantics. It needs a deliberate closeout pass.

## Objective
Finish the epic with regression coverage, docs updates, compatibility cleanup, and explicit deferral markers for remaining non-v1 items.

## Non-goals
- No new product scope.
- No auto-agent re-scheduling.
- No date-specific exceptions workpage.

## Source files to read first
- all files touched by TASK-0202 through TASK-0206
- workflow docs and current capability docs that reference workpages
- relevant backend + frontend tests

## Source files to change
- tests across backend runtime / API / frontend interaction layers
- docs/planning and any architecture/status docs affected
- compatibility shims and deprecated fields no longer needed

## Plan
1. Add regression tests for:
   - schedule preview recalculation,
   - pinned calculation evidence,
   - accepted-series navigation,
   - route-demand drift propagation,
   - preference advisory cues,
   - separation of accepted history and draft lineage.
2. Clean up deprecated or misleading contract fields where the migration is complete.
3. Update docs and deferred-item markers for:
   - date-specific exceptions,
   - auto-rescheduling agent,
   - any remaining accepted-series scope-key follow-up.
4. Produce a short operator/readiness note explaining the new schedule / route-demand / preferences separation.

## Verification
- targeted backend runtime / API tests
- targeted frontend tests / snapshots
- docs reviewed for consistency with frozen SME decisions

## Acceptance criteria
- Regressions cover the main product and architectural seams introduced by this epic.
- Compatibility debt is reduced rather than increased.
- Deferred items are explicit and do not remain hidden assumptions.
