---
id: TASK-0136
epic: EPIC-121
title: "Expose demo entrypoints, recent-version history, and doc/status sync for the artifact-backed EOD slice"
status: DONE
owners: ["frontend", "backend"]
reviewers: ["qa"]
depends_on: ["TASK-0135"]
risk: medium
context_packs: ["codex/context/EPIC-121.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0135`, the artifact-backed EOD path should work end to end, but it still needs truthful launch points, recent-version discoverability, and final doc/status cleanup so future Codex runs do not drift.

## Objective
Polish the first artifact-backed slice so it is discoverable from the logistics demo shell, exposes recent-version lineage/history cleanly, and leaves the repo-native docs/status/task memory truthful.

## Non-goals
- No schedule write path.
- No final-packet or approval/pointer flow.
- No broad workspace/human-task integration project.
- No generic multi-page history browser outside the EOD slice.

## Source files to read first
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/EPICS.md`
- `docs/planning/TASK_INDEX.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- the artifact-backed EOD files/tests from `TASK-0134` and `TASK-0135`
- `frontend/src/pages/LogisticsDemoPage.tsx`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`

## Source files to change
- logistics demo shell entrypoints/navigation affordances for artifact-backed EOD drafts
- any small backend/frontend support files required for recent-version history display
- docs/status/task-memory files touched by the new visible truth
- regression tests for entrypoints/history/shell behavior
- the task file itself with outcomes and follow-ups

## Plan
1. Add truthful create entrypoints from the logistics demo shell into the artifact-backed EOD route while keeping the query landing page preview/create-only.
2. Make recent-version history easy to inspect from the artifact-backed page by reusing canonical workflow-run artifact truth.
3. Update repo-native docs/status/task memory to reflect the finished capability.
4. Freeze shell regressions so `/demo/logistics/*` remains coherent.

## Verification
- targeted frontend/backend regression tests for entrypoint and history behavior
- doc/status consistency check
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- A user can discover and enter the artifact-backed EOD slice from the logistics demo shell.
- The artifact-backed page exposes recent version lineage/history clearly enough for demo use.
- The repo-native docs/status/task memory are all updated in the same change set.
- The task leaves the next epic decision cleanly framed (workspace/task integration and/or schedule artifact boundary).

## Notes / decisions
This task is where the slice becomes understandable to future fresh-session Codex runs, not just technically functional.

## Outcome
- The logistics demo shell now exposes `Open EOD preview` and `Create editable EOD draft` in the existing backend-demo-workpages header group, and draft creation navigates using the backend-owned `draft.route`.
- The artifact-backed EOD page now loads a bounded recent draft history panel from `GET /api/v1/workflow-runs/{workflow_run_id}/artifacts`, filtered to the `reporting.upd_draft.workbook` chain for `demo_workpage_id=eod-v0`.
- Recent history now shows `Current`, `Latest`, and `Superseded` labels plus reopen actions for previous/current/latest versions without adding a new backend route family.
- The workflow-run artifact list contract now truthfully exposes the EOD workbook versions created by the bounded demo slice, so the frontend history panel reads canonical run/artifact truth instead of frontend-local state.
- Repo-memory/docs now mark EPIC-121's first bounded slice complete and frame the next move as a new epic choice rather than hidden widening inside this slice.

## Verification notes
- `npm --prefix frontend run test:run -- src/lib/repositories/workpagesRepository.test.ts src/pages/logisticsDemoPage.test.tsx src/pages/dispatchReportWorkpagePage.test.tsx src/pages/logisticsWorkpageRoutes.test.tsx`
- `npm --prefix frontend run typecheck`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py`
- `python3 scripts/validate_repo.py --schemas-only`

## Follow-ups
- Choose the next epic deliberately: deeper dispatch-reporting/workspace integration versus a future schedule artifact boundary.
