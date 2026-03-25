---
id: TASK-0126
epic: EPIC-120
title: "Implement the end-of-day draft/review workpage v0 page and tests"
status: DONE
owners: ["platform"]
reviewers: ["qa"]
depends_on: ["TASK-0124"]
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
The EOD report page proves that the repo can present dispatch closeout as a guided operational draft/review form with history posture instead of a workbook reproduction.

## Objective
Implement `/demo/logistics/workpages/eod-v0` as a full-page, fixture-backed end-of-day report workpage with focused render and interaction tests.

## Non-goals
- No PDF/report generation work.
- No backend upload/projection contract yet.
- No exact workbook summary-formula emulation.
- No Stage05 final-packet semantics in the first FE tranche.

## Source files changed
- `frontend/src/pages/DispatchReportWorkpagePage.tsx`
- `frontend/src/components/workpages/*`
- `frontend/src/app/App.tsx`
- EOD workpage tests

## Verification
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:run -- eodWorkpage`
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The EOD workpage is a full page under `/demo/logistics/workpages/eod-v0`.
- The page uses the shared workpage contract/repository seam.
- The UI behaves like a guided dispatch closeout draft/review form rather than a workbook clone.
- The page is anchored to `reporting.upd_draft.workbook` semantics, not final-packet semantics.
- Tests cover route render plus bounded manual interactions.
