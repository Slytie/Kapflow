# EPIC-123 - Schedule draft artifact-backed workpages (Stage04 draft weekly schedule workbook lane)

## Summary
Build the first schedule artifact-backed workpage vertical slice so the repo can prove that weekly schedule review can move from a composite landing page to a concrete Stage04 draft workbook edit lane without collapsing into Stage06 publication or live-dispatch control semantics.

This epic is intentionally narrow:
- **workflow:** `weekly_schedule_planning.v1`
- **editable artifact family:** `planning.draft_weekly_schedule.workbook`
- **landing surface:** canonical `/runs/:workflowRunId/workpages/schedule-v0`
- **artifact surface:** canonical `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`

It is intentionally **not** Stage06 published schedule editing, **not** Stage07 daily-seed editing, and **not** the broad workspace/task integration epic.

## Status
Started on 2026-03-26 through `TASK-0142`, which freezes the artifact family, route posture, and stage boundary. Follow-on implementation tasks are not yet queued in repo memory.

## Scope
### In scope
- repo-native schedule-artifact-path brief/plan and context pack
- contract/route freeze for the first schedule artifact-backed slice
- authority clarification for `planning.draft_weekly_schedule.workbook` versus `planning.manager_review.doc` versus Stage06/Stage07 outputs
- later backend/frontend implementation work inside the existing canonical run-backed workpage posture

### Out of scope
- `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0/drafts`
- editing `planning.manager_review.doc`
- Stage06 publish/approval/pointer-promotion flow
- Stage07 seed materialization or `live_dispatch.v1` day-of editing
- generic spreadsheet-editor/runtime scope
- broad workspace/human-task modernization

## Dependencies
- EPIC-120 (query-backed schedule workpage already validated)
- EPIC-122 (canonical run-backed schedule landing/discovery already validated)
- EPIC-030 (immutable artifact lineage and generic artifact-backed workpage read/submit family already exist)

## Recommended pattern cards (read cards first)
- `PATTERN-007`
- `PATTERN-009`

Context pack: `codex/context/EPIC-123.md`

## Current repo status / rationale
- The canonical run-backed schedule landing already exists at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0` and frontend `/runs/:workflowRunId/workpages/schedule-v0`.
- `weekly_schedule_planning.v1` Stage04 already emits a real `planning.draft_weekly_schedule.workbook` artifact and companion `planning.draft_weekly_schedule.doc`.
- The repo already has a generic artifact-backed workpage read/submit family from the EOD slice: `GET /api/v1/workpages/artifacts/{artifact_version_id}` plus `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`.
- `TASK-0142` is now complete, so the first schedule artifact-backed slice is frozen around the Stage04 draft workbook rather than Stage06 published schedule or Stage07 seed artifacts.
- The repo now treats `planning.draft_weekly_schedule.workbook` as an immutable draft-review artifact in the canonical run chain, while `planning.manager_review.doc` remains evidence only and official weekly truth still starts only at Stage06 pointer promotion.
- No schedule artifact-backed route implementation exists yet. This task intentionally stops before backend projection/submit or frontend artifact-route migration.

## Tasks
- TASK-0142 - DONE
- Follow-on implementation tasks - not yet queued

## Red-team question
Are we still proving one bounded schedule draft workbook edit lane inside the canonical run/artifact model, or are we quietly broadening into Stage06 publish semantics, Stage07/live-dispatch control, or generic workspace/editor scope before the first schedule artifact slice is frozen?
