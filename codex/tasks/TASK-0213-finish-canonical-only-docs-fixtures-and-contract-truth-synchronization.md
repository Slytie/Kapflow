---
id: TASK-0213
epic: EPIC-132
title: "Finish canonical-only docs, fixtures, and contract-truth synchronization"
status: DONE
owners: ["backend", "frontend", "qa"]
reviewers: ["architect"]
depends_on: ["TASK-0211", "TASK-0212"]
risk: medium
context_packs:
  - "codex/context/EPIC-132.md"
  - "codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md"
patterns: []
---

## Context
The canonical-only cleanup is legitimate, but active docs, fixtures, snapshot expectations, and route tests must all tell the same story about the public workpage posture.

## Objective
Make active docs, fixtures, snapshot expectations, and route-level tests all tell the same story about the public workpage posture.

## Non-goals
- No product-boundary changes.
- No reintroduction of public alias routes.
- No large architecture refactor.

## Source files to read first
- the docs/fixture/test files touched by active settlement work
- `docs/planning/epics/EPIC-131.md`
- `docs/planning/epics/EPIC-126.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Source files to change
- active docs/status pages
- frontend contract fixtures/readme
- route and artifact contract tests with stale wording/metadata expectations

## Plan
1. Decide whether demo-era metadata/labels are fully retired or intentionally retained as compatibility fields.
2. Apply that decision consistently across:
   - backend payloads,
   - tests,
   - fixtures,
   - active docs.
3. Keep alias-retirement tests explicit so the public route boundary stays protected.
4. Remove only stale fixtures/docs that are truly superseded.

## Verification
- targeted backend contract tests
- snapshot/export checks used by the repo for frontend contract truth
- manual review that active docs reflect the actual public routes and labels

## Acceptance criteria
- Active docs, fixtures, and tests are synchronized with the canonical-only posture.
- No stale demo-era wording remains in active truth unless it is an intentional compatibility field.
- Canonical-route expectations are explicit and regression-protected.

## Execution notes
- Kept `workpage.mode` / `workpage.source_examples` as compatibility fields for the current inner view-model seam instead of retiring them in this task.
- Removed stale human-facing wording from active canonical EOD truth so run-backed and artifact-backed surfaces no longer describe themselves as demo/example-backed queries.
- Updated active EOD landing truth to acknowledge the real immutable draft create/submit workbook lane instead of claiming manual closeout is local-only.
- Refreshed backend-owned frontend contract fixtures after the copy cleanup and kept retired demo-route / alias-route tests explicit.
