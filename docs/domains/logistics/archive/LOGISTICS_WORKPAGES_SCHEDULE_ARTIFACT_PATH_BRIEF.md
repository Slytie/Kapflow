> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Logistics workpages schedule artifact path - product brief

## Purpose
This brief freezes the next product step after the workflow-run-backed access epic. The goal is to prove, with one bounded vertical slice, that the weekly schedule workpage can connect to a real Stage04 draft workbook artifact and save meaningful edits back into a **new immutable draft workbook version** without breaking the repo's one-truth model or blurring the publish/live-dispatch boundary.

## What this epic is
The next epic is the **first schedule artifact-backed workpage slice**.

The first slice is intentionally narrow:
- **workflow family:** `weekly_schedule_planning.v1`
- **artifact family:** `planning.draft_weekly_schedule.workbook`
- **landing surface:** canonical run-backed schedule page first
- **edit surface:** canonical artifact page under `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`
- **review boundary:** Stage04 draft-review plus Stage05 manager feedback, not Stage06 publish

## Why Stage04 draft workbook first
This is the right first schedule write lane because:
- Stage04 already emits a real `planning.draft_weekly_schedule.workbook` artifact inside the canonical run chain.
- It is the closest existing schedule artifact to human review/edit without becoming official weekly truth.
- It keeps manager review and publication downstream rather than pretending the workpage itself publishes the schedule.
- It avoids inventing an EOD-style draft-create route when the weekly workflow already materializes the initial draft.

## What the operator should eventually be able to do
From the canonical run-backed schedule landing, the operator should be able to:
1. open the current weekly-planning review page for a real workflow run,
2. open a concrete draft schedule workbook version,
3. edit bounded schedule-review content in a guided UI,
4. explicitly submit to create a **new immutable draft workbook artifact version**,
5. return to the existing manager-review/publish flow outside the page.

## What remains out of scope
- no Stage06 published schedule editing
- no Stage07 daily seed editing
- no `live_dispatch.v1` day-of replan console
- no `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts`
- no generic workpage/spreadsheet editor runtime
- no broad workspace/task modernization folded into this epic

## Product boundary
The workpage remains a **derived editing surface**. The Stage04 draft workbook remains the canonical draft-review artifact.

\[
A_v \xrightarrow{\text{project}} UI \xrightarrow{\text{submit}} A_{v+1}
\]

The product promise is not “edit the official published schedule in the browser.”
The product promise is “edit the bounded draft-review schedule content through a better page, while preserving immutable workbook artifacts and leaving official publication to the existing Stage06 flow.”

## User-visible route posture
Frozen canonical posture:
- keep `/runs/:workflowRunId/workpages/schedule-v0` as the run-backed landing page,
- reserve `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId` as the first artifact-backed schedule route,
- reuse the existing backend artifact projection/submit family,
- do **not** add a first-slice `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts`.

The existing `/demo/logistics/workpages/schedule-v0` page remains a compatibility/read-only review surface; it is not the primary edit model for this epic.
