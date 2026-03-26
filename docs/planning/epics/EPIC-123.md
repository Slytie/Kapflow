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
Completed on 2026-03-26 through `TASK-0142`, `TASK-0143`, `TASK-0144`, and `TASK-0145`. The repo now implements the bounded Stage04 schedule artifact-backed workpage slice and closes EPIC-123 without broadening into Stage06 publish, Stage07 seed editing, or live-dispatch control.

## Scope
### In scope
- repo-native schedule-artifact-path brief/plan and context pack
- contract/route freeze for the first schedule artifact-backed slice
- authority clarification for `planning.draft_weekly_schedule.workbook` versus `planning.manager_review.doc` versus Stage06/Stage07 outputs
- backend schedule artifact projection/submit inside the existing generic artifact-backed workpage family
- frontend canonical schedule artifact route, landing handoff, and bounded artifact-edit UX inside the existing run-backed posture

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
- `TASK-0142` froze the first schedule artifact-backed slice around the Stage04 draft workbook rather than Stage06 published schedule or Stage07 seed artifacts.
- The repo now treats `planning.draft_weekly_schedule.workbook` as an immutable draft-review artifact in the canonical run chain, while `planning.manager_review.doc` remains evidence only and official weekly truth still starts only at Stage06 pointer promotion.
- The generic artifact-backed workpage family now implements schedule artifact projection and submit for `planning.draft_weekly_schedule.workbook`.
- The frontend now implements the canonical schedule artifact route at `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`, with landing-page handoff, bounded row editing, recent draft history, stale/conflict reopen, and truthful JSON download.
- The demo shell continues to discover schedule artifact editing through the canonical run-backed landing route rather than a demo-only artifact alias.

## Tasks
- TASK-0142 - DONE
- TASK-0143 - DONE
- TASK-0144 - DONE
- TASK-0145 - DONE

## Red-team question
Are we still proving one bounded schedule draft workbook edit lane inside the canonical run/artifact model, or are we quietly broadening into Stage06 publish semantics, Stage07/live-dispatch control, or generic workspace/editor scope before the first schedule artifact slice is frozen?
