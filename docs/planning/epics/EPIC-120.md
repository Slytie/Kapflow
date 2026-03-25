# EPIC-120 - Logistics workpages v0 (schedule + end-of-day report)

## Summary
Build the first full-page logistics work surfaces as **frontend-first, fixture-backed prototypes** on top of the existing primary demo shell.

This epic exists to validate the page contract and operator UX for two concrete workpages:
- weekly schedule review + selected-day preview
- end-of-day reporting draft/review

It is intentionally **not** a generic artifact editor epic.

## Scope
### In scope
- repo-native product brief for workpages v0
- repo-native workpage plan and view-model examples
- frontend `WorkpageViewModel` contract + example data seam
- `/demo/logistics/workpages/schedule-v0`
- `/demo/logistics/workpages/eod-v0`
- route/page/component tests proving the pages render and behave from example data
- documentation and task-memory updates that keep the repo truthful while this slice lands

### Out of scope
- backend workpage API
- artifact-linked submit/materialize semantics
- generic template builder / drag-drop editor
- live-dispatch morning workpage
- driver self-service
- spreadsheet formula-engine emulation

## Dependencies
- EPIC-025 (logistics workflow packs and normalized examples already exist)
- EPIC-080 (primary logistics demo shell and frontend route/repository posture already exist)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-120.md`

## Current Repo Status (2026-03-25 implementation pass)
- Primary logistics UI entrypoint is `/demo/logistics`.
- Workpage routes now exist as fixture-backed full-page surfaces under `/demo/logistics/workpages/*`.
- There is still no backend workpage projection/submit contract.
- The repo now carries a consistent partial 2026-03-16 QDCI/DVC4 example family for the first EOD workpage.
- `weekly_schedule_planning.v1` owns the weekly base plan; day-of replan belongs to `live_dispatch.v1`.
- `dispatch_reporting.v1` separates normalized actuals, draft packet generation, review, and final output; the first EOD workpage aligns to `reporting.upd_draft.workbook` semantics rather than Stage05 final packet semantics.
- This epic remains frontend-first by design: the page contract landed before backend artifact projection/submit work.

## Tasks
- TASK-0123
- TASK-0124
- TASK-0125
- TASK-0126
- TASK-0127

## Red-team question
Are we quietly building a generic artifact editor, a live-dispatch console, or a second client-side truth model instead of the bounded schedule/EOD workpage slice this epic actually intends?
