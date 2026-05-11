---
id: TASK-0153
epic: EPIC-125
title: "Wire the daily EOS intake, draft-reporting review workpage, finalize flow, and planning feedback handoff"
status: DONE
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0151"]
risk: high
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Why
The daily reporting lane is the authoritative source of actual-routes truth and must drive both the review workpage and future compliance inputs.

## Scope
- make the daily EOS upload task the authoritative intake for `reporting.eos_raw.workbook`
- add or expose the bounded workflow-native build from EOS raw input to `reporting.upd_draft.workbook`
- ensure the generated draft artifact opens in the existing EOD artifact-backed workpage
- add the bounded finalization path to `reporting.final_packet.workbook`
- ensure the existing reporting->planning handoff updates future actual-hours truth for compliance

## Out of scope
- finalization UX beyond the bounded operator lane
- new reporting document packet scope if workbook-first output is sufficient

## Acceptance signals
- an uploaded EOS workbook leads to a generated draft reporting artifact
- that artifact opens in the review workpage
- finalization produces the official workbook output and the planning feedback artifact

## Implemented loop
1. Seed or create a `dispatch_reporting.v1` run and a `Stage01/eos_input_intake` human task owned by `dispatch_supervisor`.
2. Upload required intake inputs through the existing subject upload endpoints:
   - required `reporting.eos_raw.workbook` as `official_input`
   - optional `reporting.eos_raw.doc` as `evidence`
3. Complete the intake task with the existing `outcome=complete`; backend maps it to `eos_inputs_ready`, validates the EOS workbook, deterministically creates `reporting.actuals_normalized.workbook`, seeds `reporting.upd_draft.workbook`, and upserts one `Stage04/final_packet_review` human task keyed to that draft version.
4. Review/edit through the existing `eod-v0` artifact-backed workpage, confirm review against the latest draft workbook, and complete the review task; backend requests one `Stage04` approval for `confirm_dispatch_reporting_packet`.
5. Approve the Stage04 approval through `POST /api/v1/approvals/{approval_id}/respond`; the approval response auto-finalizes daily truth by creating `reporting.final_packet.workbook`, promoting `official:reporting.final_packet.workbook`, and invoking the existing `reporting_actuals_to_future_planning` notify-only handoff.

## Stop lines kept
- no new workpage route family
- no new upload route
- no rich final-packet document renderer
- no re-review/reject loop widening beyond the bounded happy path
- no new planning-feedback mechanism outside the existing `reporting_actuals_to_future_planning` handoff

## Source files changed
- `src/onetruth/application/services/dispatch_reporting_build.py`
- `src/onetruth/application/services/dispatch_reporting_workbook.py`
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/handlers/human_tasks.py`
- `src/onetruth/application/handlers/approvals.py`
- `src/onetruth/application/handlers/logistics_handoff.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/api/routes/human_tasks.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/api/route_specs/human_tasks.py`
- `src/onetruth/cli/__main__.py`
- `frontend/src/components/ApprovalCard.tsx`
- `frontend/src/components/WorkspaceActionPanel.tsx`
- `frontend/src/lib/workspace/taskLabels.ts`
- `tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py`
- `tests/runtime/api/test_workpages_artifact_eod_contract.py`
- `tests/runtime/api/test_workspace_workpage_actions.py`
- `tests/runtime/helpers/workpage_runs.py`
- `tests/unit/test_task_requirements.py`
- `frontend/src/components/approvalCard.test.tsx`
- `frontend/src/components/workspaceTaskBoard.test.tsx`

## Verification
- `PYTHONPATH=src:.venv/lib/python3.9/site-packages python3.11 -m pytest tests/runtime/api/test_dispatch_reporting_finalize_loop_api.py tests/runtime/api/test_workpages_artifact_eod_contract.py tests/runtime/api/test_workspace_workpage_actions.py tests/unit/test_task_requirements.py -q`
- `cd frontend && ./node_modules/.bin/vitest run src/components/approvalCard.test.tsx src/components/workspaceTaskBoard.test.tsx src/components/detailDrawer.test.tsx src/components/taskCardWide.test.tsx src/lib/repositories/humanTasksRepository.test.ts src/pages/runWorkspacePage.test.tsx`
- `PYTHONPATH=src python3.11 scripts/validate_repo.py`

## Outcome
- Daily EOS intake is now a first-class `Stage01/eos_input_intake` human task with `artifact_role`-aware required uploads.
- Completing intake now deterministically builds the normalized-actuals workbook and the first editable EOD draft workbook inside canonical artifact truth.
- Stage04 review uses the existing EOD workpage and now supports a supported human-task `subject_link` surface in addition to the existing approval surface.
- Approving the Stage04 reporting approval now auto-finalizes `reporting.final_packet.workbook`, promotes official pointer truth, and triggers the existing planning-feedback handoff while failing closed on stale reviewed drafts.
