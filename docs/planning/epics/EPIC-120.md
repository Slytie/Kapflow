# EPIC-120 - Logistics workpages v0 (schedule + end-of-day report)

## Summary
Build the first full-page logistics work surfaces and then move them onto the repo's normal **server-authoritative query path** without jumping straight into generic artifact editing.

This epic now spans two tightly bounded tranches:
1. **Tranche A (implemented through `TASK-0127`):** frontend-first, fixture-backed page validation under `/demo/logistics/workpages/*`
2. **Tranche B (started by `TASK-0128`):** server-owned demo query routes and frontend migration to those routes

The epic still exists to validate two concrete workpages only:
- weekly schedule review + selected-day preview
- end-of-day reporting draft/review

It is intentionally **not** a generic artifact editor epic.

## Scope
### In scope
- repo-native product brief and implementation plan for logistics workpages
- shared `WorkpageViewModel` / workpage query contract discipline
- full-page routes under `/demo/logistics/workpages/*`
- server-owned demo query surfaces for `schedule-v0` and `eod-v0`
- backend-owned generated frontend contract snapshots for those query surfaces
- frontend migration from local example adapters to HTTP-backed repositories
- documentation and task-memory updates that keep the repo truthful while this slice lands

### Out of scope
- backend workpage submit/materialize semantics
- generic template builder / drag-drop editor
- live-dispatch morning workpage
- driver self-service
- spreadsheet formula-engine emulation
- a generic one-artifact workpage assumption for every future page

## Dependencies
- EPIC-025 (logistics workflow packs and normalized examples already exist)
- EPIC-080 (primary logistics demo shell and frontend route/repository posture already exist)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-120.md`

## Current Repo Status (2026-03-25 post-`TASK-0130` backend demo routes)
- `/demo/logistics/workpages/schedule-v0` and `/demo/logistics/workpages/eod-v0` exist as full-page routes under `AppShell`.
- The active pages are still **frontend-local/example-backed** after `TASK-0130`; frontend migration has not started yet.
- Repo-native docs now freeze the post-v0 workpage query contract, route family, and snapshot policy.
- `GET /api/v1/workpages/demo/schedule-v0` and `GET /api/v1/workpages/demo/eod-v0` now exist as backend demo workpage query surfaces.
- `fixtures/frontend_contracts/workpage_schedule_v0_state.json` and `fixtures/frontend_contracts/workpage_eod_v0_state.json` now exist as backend-generated workpage query snapshots.
- The next correctness move is to migrate the frontend workpage routes onto the HTTP-backed repository seam.
- `weekly_schedule_planning.v1` still owns the **pre-week / Friday** weekly build. Day-of replan belongs to `live_dispatch.v1` and must not leak into the schedule workpage scope.
- `dispatch_reporting.v1` still separates normalized actuals, draft packet generation, review, and final packet output. The EOD page remains aligned to `reporting.upd_draft.workbook` semantics rather than Stage05 final output.
- The schedule page is **composite** over multiple weekly-planning example inputs. It must not be forced into a single-artifact identity too early.
- The EOD page is the better candidate for the **first future artifact-backed path** because it maps more naturally to one reporting packet/workbook family.
- The implemented EOD backend route is intentionally honest to its partial example family: summary cards are source-derived partial totals with explicit formula-integrity warnings, not fixture-only full-day totals.
- Workpage query snapshots, once generated from backend routes, belong in `fixtures/frontend_contracts/` because they are backend-owned generated API fixtures. The human-authored workpage fixtures under `fixtures/logistics/workpages/` remain a different class of artifact.

## Tasks
- TASK-0123
- TASK-0124
- TASK-0125
- TASK-0126
- TASK-0127
- TASK-0128
- TASK-0129
- TASK-0130
- TASK-0131

## Red-team question
Are we keeping the next batch bounded to **server-authoritative workpage queries** and a clean frontend migration, or are we quietly skipping ahead into artifact submit/materialize work before the shared query seam is proven?
