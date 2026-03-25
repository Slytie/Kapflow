---
id: TASK-0125
epic: EPIC-120
title: "Implement the weekly schedule review workpage v0 page and tests"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0124"]
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
The first logistics workpage proves that **weekly schedule review + selected-day preview** can be expressed as a full-page FE surface built from normalized weekly planning examples instead of a spreadsheet clone.

## Objective
Implement `/demo/logistics/workpages/schedule-v0` as a full-page, fixture-backed schedule workpage with focused render and interaction tests.

## Non-goals
- No live-dispatch morning page.
- No artifact-linked save/submit.
- No generic scheduler framework.
- No semantically authoritative day-of dispatch editing.

## Source files changed
- `frontend/src/pages/LogisticsScheduleWorkpagePage.tsx`
- `frontend/src/components/workpages/*`
- `frontend/src/app/App.tsx`
- schedule workpage tests

## Verification
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:run -- scheduleWorkpage`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The schedule workpage is a full page under `/demo/logistics/workpages/schedule-v0`.
- The page uses the shared workpage contract/repository seam.
- The UI looks like a weekly-planning review page with selected-day preview, not a spreadsheet clone.
- Any day-of controls are clearly local what-if inputs, not authoritative live-dispatch editing.
- Tests cover route render plus bounded local interactions.
