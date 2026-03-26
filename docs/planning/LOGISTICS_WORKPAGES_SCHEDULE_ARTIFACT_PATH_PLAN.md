# Logistics workpages schedule artifact path - repo-grounded implementation plan

## Why this exists
After EPIC-122, the repo now has:
- a canonical run-backed schedule landing page under `/runs/:workflowRunId/workpages/schedule-v0`,
- a real Stage04 `planning.draft_weekly_schedule.workbook` artifact in `weekly_schedule_planning.v1`,
- and a generic artifact-backed workpage read/submit family already proven on the EOD slice.

This plan defines the next bounded schedule write path:
- **Stage04 draft workbook only**
- **artifact-backed**
- **immutable version chain**
- **no Stage06 publish semantics**
- **no live-dispatch/day-of expansion**

## Repo-grounded constraints that shape this epic
### 1) The initial editable draft already exists
`weekly_schedule_planning.v1` Stage04 already emits `planning.draft_weekly_schedule.workbook`.

Implication:
- do not invent a `schedule-v0/drafts` create route,
- do not add a demo-only draft seed lane,
- treat the first schedule artifact slice as “open/edit a real draft artifact version,” not “manufacture a fresh draft.”

### 2) Stage05 manager review is evidence, not the editable artifact
The weekly workflow already reserves `planning.manager_review.doc` for Stage05 review evidence and change-routing decisions.

Implication:
- keep `planning.manager_review.doc` out of the artifact-backed workpage identity,
- keep the edit surface on the Stage04 draft workbook, not the Stage05 review packet.

### 3) Official weekly truth starts only at Stage06
`planning.published_weekly_schedule.workbook` is still the first official weekly truth and remains guarded by review/approval/pointer-promotion semantics.

Implication:
- do not let the first schedule artifact-backed workpage mutate or masquerade as Stage06 publication,
- keep publish semantics outside this epic.

### 4) Stage07 and live dispatch remain downstream
`planning.daily_dispatch_seed.*` are handoff outputs into `live_dispatch.v1`, not the bounded schedule draft-edit lane.

Implication:
- keep daily seed materialization and day-of replan out of scope,
- keep the schedule artifact slice on the weekly-planning side of the boundary.

### 5) The generic artifact workpage family already exists
The repo already implements:
- `GET /api/v1/workpages/artifacts/{artifact_version_id}`
- `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`

Implication:
- reuse the generic artifact-backed workpage family for schedule,
- do not invent schedule-specific artifact endpoints in the first slice.

## Frozen route posture from TASK-0142
### Existing run-backed landing (keep)
- `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0`
- frontend `/runs/:workflowRunId/workpages/schedule-v0`

### Implemented artifact-backed schedule posture
- frontend `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`
- backend `GET /api/v1/workpages/artifacts/{artifact_version_id}`
- backend `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`

### Explicitly not part of the first slice
- no `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts`
- no demo-first schedule artifact route requirement

## Editable artifact envelope for the first slice
### Editable artifact
- `planning.draft_weekly_schedule.workbook`

### Adjacent read-only evidence
- `planning.draft_weekly_schedule.doc`
- `planning.validation_summary.doc`
- `planning.manager_review.doc`

### Downstream official outputs that remain out of scope
- `planning.published_weekly_schedule.workbook`
- `planning.daily_dispatch_seed.doc`
- `planning.daily_dispatch_seed.workbook`

## Submit semantics
### Canonical loop
\[
A_v \xrightarrow{\text{project}} UI \xrightarrow{\Delta} A_{v+1}
\]

### Rules
- never mutate `A_v` in place
- submit must create `A_{v+1}` as a new immutable `planning.draft_weekly_schedule.workbook` version in the same workflow-run lineage
- explicit save/submit only; no per-keystroke artifact writes
- no publish, pointer promotion, or daily-seed materialization from this surface
- manager review and publish continue through their existing Stage05/Stage06 semantics outside the workpage

## Snapshot policy
The implemented backend-generated snapshots now cover:
- a representative schedule artifact-backed read response,
- a representative submit/create-new-version response,
- and the route payloads needed by the active frontend migration.

These should live under `fixtures/frontend_contracts/` because they are backend-generated API fixtures. Human-authored workpage planning fixtures remain distinct under `fixtures/logistics/workpages/`.

## Epic task order
1. `TASK-0142` - DONE
2. `TASK-0143` - DONE
3. `TASK-0144` - DONE
4. `TASK-0145` - DONE

## Implemented slice outcome
- The generic artifact-backed workpage family now projects `planning.draft_weekly_schedule.workbook` into a bounded schedule artifact page and persists immutable superseding versions on submit.
- The canonical frontend artifact route is now live at `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`.
- The run-backed schedule landing remains the canonical entrypoint and now discovers the newest draft workbook artifact from workflow-run artifact truth.
- The frontend artifact page supports bounded row edits, explicit submit, recent-history reopen, stale/conflict reopen, and truthful JSON download.

## Red-team guardrails
- Do not invent a schedule draft-create endpoint when Stage04 already emits the draft workbook.
- Do not switch the first schedule edit surface onto `planning.manager_review.doc`.
- Do not broaden into Stage06 publish/pointer semantics.
- Do not broaden into Stage07 seed editing or `live_dispatch.v1` day-of control.
- Do not turn this epic into a generic spreadsheet editor/runtime project.
- Do not route the first slice through workspace/task modernization unless a later bounded task proves that seam is already truthful and ready.
