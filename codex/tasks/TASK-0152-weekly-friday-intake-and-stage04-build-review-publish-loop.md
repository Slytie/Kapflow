---
id: TASK-0152
epic: EPIC-125
title: "Wire the weekly Friday intake and Stage04 build/review/publish loop around Stage04-ready inputs"
status: DONE
owners: ["backend", "frontend"]
reviewers: ["qa"]
depends_on: ["TASK-0151"]
risk: high
context_packs: ["codex/context/EPIC-125.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Why
The repo already has the bounded weekly Stage04 planning lane and schedule review workpage. The first production-shaped loop must wire truthful weekly intake into that lane and publish the reviewed draft officially.

## Scope
- add the minimal weekly intake task/requirement policy for Stage04-ready inputs
- wire the exact operator path for required weekly inputs
- create or expose the bounded Stage04 planner/agent action inside the operational loop
- create the review-draft-schedule task when a draft artifact exists
- auto-publish the reviewed weekly schedule workbook from Stage06 approval response
- keep the schedule lane bounded to the current Stage04 draft/edit/publish scope

## Out of scope
- Stage07 editing UI
- live-dispatch algorithmics
- raw route-email parsing

## Acceptance signals
- a reviewer can walk the repo from weekly intake to a published weekly schedule workbook
- the review workpage is part of the loop
- official weekly output is pointer-backed and truthful

## Implemented loop
1. Seed or create a `weekly_schedule_planning.v1` run and a `Stage04/weekly_input_intake` human task owned by `schedule_planner`.
2. Upload required Stage04-ready inputs through the existing subject upload endpoints:
   - required `planning.route_slot_requirements.workbook` as `official_input`
   - required `planning.approved_availability.workbook` as `official_input`
   - required `planning.driver_capabilities.workbook` as `official_input`
   - optional `planning.actual_hours_snapshot.workbook` as `official_input`
   - optional `planning.route_horizon.doc` / `planning.route_horizon.workbook` as `evidence`
3. Complete the intake task with the existing `outcome=complete`; backend maps it to `inputs_ready` and upserts one `Stage04/work_item` build task.
4. Complete the Stage04 build task with `outcome=complete`; backend requires the latest `planning.draft_weekly_schedule.workbook` and upserts one `Stage05/final_review` task keyed to that draft artifact version.
5. Review/edit through the existing `schedule-v0` artifact-backed workpage, upload `planning.manager_review.doc`, confirm review against the latest draft workbook, and complete the final-review task; backend requests one `Stage06` approval for `publish_weekly_base_schedule`.
6. Approve the Stage06 approval through `POST /api/v1/approvals/{approval_id}/respond`; the approval response auto-publishes weekly truth by creating `planning.publish_packet.doc`, creating `planning.published_weekly_schedule.workbook`, and promoting `official:planning.published_weekly_schedule.workbook`.

## Stop lines kept
- no new workpage route family
- no `schedule-v0/drafts` create route
- no Stage07 seed materialization from weekly publish
- no live-dispatch activation side effect from weekly publish
- no raw route-email parser truth
- no separate frontend Publish button

## Source files changed
- `src/onetruth/application/services/task_requirements.py`
- `src/onetruth/application/services/task_actionability.py`
- `src/onetruth/application/handlers/human_tasks.py`
- `src/onetruth/application/handlers/approvals.py`
- `src/onetruth/application/handlers/pointers.py`
- `frontend/src/lib/types/contracts.ts`
- `frontend/src/lib/api/onetruthApi.ts`
- `frontend/src/lib/repositories/humanTasksRepository.ts`
- `frontend/src/lib/workspace/taskLabels.ts`
- `frontend/src/components/TaskCardWide.tsx`
- `frontend/src/components/WorkspaceTaskBoard.tsx`
- `frontend/src/components/WorkspaceActionPanel.tsx`
- `frontend/src/components/DetailDrawer.tsx`
- `tests/unit/test_task_requirements.py`
- `tests/runtime/api/test_weekly_publish_loop_api.py`
- `frontend/src/components/workspaceTaskBoard.test.tsx`
- `frontend/src/components/detailDrawer.test.tsx`
- `frontend/src/components/taskCardWide.test.tsx`
- `frontend/src/lib/repositories/humanTasksRepository.test.ts`

## Verification
- `PYTHONPYCACHEPREFIX=/tmp/pycache PYTHONPATH=src python3.11 -m pytest tests/unit/test_task_requirements.py tests/runtime/api/test_weekly_publish_loop_api.py -q`
- `cd frontend && npm run test:run -- --fileParallelism=false src/components/detailDrawer.test.tsx src/components/workspaceTaskBoard.test.tsx src/components/taskCardWide.test.tsx src/lib/repositories/humanTasksRepository.test.ts`
- `PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/python -m compileall -q src tests`

## Outcome
- Weekly intake is now a first-class `Stage04/weekly_input_intake` human task with explicit `artifact_role`-aware required uploads.
- Weekly `complete` actions now map to the bounded intake/build/review semantics without changing the public UI payload shape.
- Stage06 approval approval now auto-publishes the weekly schedule workbook and official pointer truth, while failing closed if the reviewed draft is stale.
- The frontend now exposes `Run Stage04 Build`, sends required-upload `artifact_role`, and uses intake/build/review wording on weekly task surfaces.
