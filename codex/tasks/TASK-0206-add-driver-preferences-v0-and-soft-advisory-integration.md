---
id: TASK-0206
epic: EPIC-131
title: "Add driver-preferences-v0 and integrate it as a soft advisory schedule input"
status: TODO
owners: ["backend", "frontend"]
reviewers: ["pm", "qa"]
depends_on: ["TASK-0202"]
risk: medium
context_packs:
  - "codex/context/EPIC-131.md"
  - "codex/context/SME-DECISIONS-AND-GREY-AREAS-2026-04-04.md"
  - "codex/context/WORKPAGE-CONTRACT-SKETCHES-SCHEDULE-ROUTE-DEMAND-PREFERENCES.md"
patterns: []
---

## Context
Driver preferences are high priority, but they are not hard constraints in this tranche. They need their own traceable snapshot and must feed schedule cues without becoming a second mutable side store.

## Objective
Introduce a weekly-run `driver-preferences-v0` workpage and integrate its saved snapshot as a soft/advisory input to schedule calculations and highlighting.

## Non-goals
- No date-specific vacation / sick-day exception modeling here.
- No hard-blocking schedule validation from preferences in this task.

## Source files to read first
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/application/handlers/workpages.py`
- weekly scheduling workflow docs / schemas
- `frontend/src/lib/types/workpages.ts`
- `frontend/src/lib/api/onetruthApi.ts`

## Source files to change
- backend descriptor / route / handler files for `driver-preferences-v0`
- any new artifact family helpers and projection code
- schedule calculation / preview integration points for soft preferences
- frontend page/components for preferences editing
- targeted tests

## Plan
1. Add a weekly-run snapshot artifact family for driver day-of-week preferences.
2. Add `driver-preferences-v0` for the Sunday–Saturday preference grid.
3. Persist categories:
   - definitely_can_not_work
   - open_to_work
   - prefer_not_to_work
4. Feed the saved preference snapshot into schedule preview / calculation as a soft advisory input.
5. Surface preference-aware cues such as available-driver highlighting without making preferences blocking.

## Verification
- route / save tests for preferences workpage
- schedule preview tests showing preference state appears as advisory metadata only
- frontend rendering tests for the preference grid and schedule soft cues

## Acceptance criteria
- Driver preferences have their own editable snapshot surface.
- Preferences can be displayed and edited without introducing global mutable truth.
- Schedule calculations can consume preferences as advisory signals.
- Preferences do not block save or publish in this tranche.
