# EPIC-123 Context Pack - Schedule draft artifact-backed workpages

**Purpose (why you might open this):**
- You are implementing or reviewing the next workpage epic after EPIC-122.
- You need to keep the first schedule write lane anchored to the real Stage04 draft workbook artifact instead of drifting into publish/live-dispatch semantics.
- You need to avoid inventing an EOD-style draft-create route when the weekly workflow already materializes the initial draft artifact.

## Non-negotiable invariants to keep in mind
- Workpages remain derived surfaces; runtime rows/events/artifacts remain canonical truth.
- The current schedule landing at `/runs/:workflowRunId/workpages/schedule-v0` remains a run-backed, composite review surface until the artifact slice is implemented.
- The first schedule artifact-backed slice is anchored to `planning.draft_weekly_schedule.workbook`, not `planning.manager_review.doc`.
- `planning.published_weekly_schedule.workbook` remains the first official weekly truth; do not let a draft-edit page blur that boundary.
- `planning.daily_dispatch_seed.*` and `live_dispatch.v1` remain out of scope.
- Reuse the generic artifact-backed `GET/POST /api/v1/workpages/artifacts/{artifact_version_id}` family; do not invent schedule-specific artifact endpoints or a run-backed `schedule-v0/drafts` create route.
- Do not broaden into generic spreadsheet-editor/runtime scope or broad workspace/task modernization.
- Update repo-native docs/status/task memory in the same change set when the schedule artifact boundary changes.

## Contracts / docs to treat as authoritative
- `docs/planning/LOGISTICS_WORKPAGES_SCHEDULE_ARTIFACT_PATH_BRIEF.md`
- `docs/planning/LOGISTICS_WORKPAGES_SCHEDULE_ARTIFACT_PATH_PLAN.md`
- `docs/planning/epics/EPIC-123.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/planning/CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md`
- `docs/workflows/weekly_schedule_planning/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `frontend/src/app/App.tsx`
- `frontend/src/lib/repositories/workpagesRepository.ts`

## Required test coverage (tests-as-spec)
- `TASK-0142` is doc/contract-only: repo-memory and contract-doc consistency checks plus `python3.11 scripts/validate_repo.py --schemas-only`
- Later implementation tasks must add backend route/contract coverage for schedule artifact projection/submit and frontend route/repository coverage for the canonical nested schedule artifact route

## Current repo status
- Query-backed and run-backed schedule landing pages already exist and are validated.
- EPIC-121 already proved the first generic artifact-backed workpage read/submit family on EOD.
- `weekly_schedule_planning.v1` Stage04 already emits `planning.draft_weekly_schedule.workbook`, so the first schedule artifact slice does not need a new draft-create mutation.
- `TASK-0142` is now complete, so the repo has frozen the next schedule artifact boundary around the Stage04 draft workbook, reserved `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`, and explicitly kept Stage06 publish, Stage07 seeds, live dispatch, and workspace modernization out of scope.
- EPIC-123 is now open as the next workpage epic. Follow-on implementation tasks still need to be queued.

## Planned implementation order inside this epic
1. `TASK-0142` - DONE
2. Future backend schedule artifact projection/submit tranche - not yet queued
3. Future frontend schedule artifact-route migration tranche - not yet queued
4. Future demo/doc closeout tranche - not yet queued

## Preflight questions for future runs
- Does the repo still contain the post-`TASK-0142` freeze that anchors the schedule artifact slice to `planning.draft_weekly_schedule.workbook`?
- Do `docs/planning/HITL_HTTP_API_CONTRACTS.md`, `docs/planning/FRONTEND_PAGE_MAP.md`, and `docs/planning/CONTINUOUS_SCHEDULE_CONTROL_ARTIFACTS.md` still agree that there is no `schedule-v0/drafts` create route?
- Does the repo still keep `planning.manager_review.doc` as evidence only and `planning.published_weekly_schedule.workbook` as the first official weekly truth?
- Is the schedule landing still separate from live-dispatch day-of control semantics?

## Red-team questions for future runs
- Are we inventing a schedule draft-create endpoint even though Stage04 already produces the initial draft artifact?
- Are we quietly turning the first schedule artifact slice into Stage06 publish or pointer-promotion semantics?
- Are we letting the schedule artifact route drift into Stage07 seed editing or live-dispatch control?
- Are we broadening into a generic spreadsheet editor or workspace/task modernization before the bounded draft-workbook path is proven?
