---
id: TASK-0143
epic: EPIC-123
title: "Implement backend schedule artifact projection, submit, and generated snapshots"
status: DONE
owners: ["backend"]
reviewers: ["qa"]
depends_on: ["TASK-0142"]
risk: high
context_packs: ["codex/context/EPIC-123.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
`TASK-0142` froze the first schedule artifact-backed slice around the Stage04 `planning.draft_weekly_schedule.workbook`. The repo still needed a real backend implementation over the generic artifact-backed workpage family before any frontend route could migrate to the canonical schedule artifact surface.

## Objective
Implement the backend schedule artifact-backed workpage slice by:
- teaching the generic artifact-backed workpage read/submit family to recognize `planning.draft_weekly_schedule.workbook`,
- projecting the stored Stage04 draft workbook JSON into a schedule workpage contract,
- materializing bounded row edits into a new immutable artifact version on submit,
- and generating backend-owned frontend snapshots for the schedule artifact read/submit contracts.

## Non-goals
- No `schedule-v0/drafts` create route.
- No Stage06 publish or pointer semantics.
- No Stage07/live-dispatch editing.
- No generic spreadsheet editor/runtime.
- No frontend route migration yet.

## Source files changed
- `src/onetruth/application/services/schedule_control/draft_workbook.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/handlers/artifacts.py`
- `src/onetruth/api/routes/workpages.py`
- `tests/runtime/helpers/workpage_runs.py`
- `tests/runtime/helpers/frontend_snapshots.py`
- `tests/unit/test_schedule_draft_workbook.py`
- `tests/runtime/api/test_workpages_artifact_schedule_contract.py`
- `fixtures/frontend_contracts/workpage_schedule_v0_artifact_state.json`
- `fixtures/frontend_contracts/workpage_schedule_v0_artifact_submit_response.json`

## Plan
1. Generalize the artifact-backed workpage route family to dispatch on both EOD and schedule artifact families.
2. Add a schedule-specific projector/materializer seam around the Stage04 draft workbook JSON payload.
3. Persist bounded row edits as a new immutable `planning.draft_weekly_schedule.workbook` version in the same run lineage.
4. Export backend-owned schedule artifact snapshots for the frontend contract layer.

## Verification
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/unit/test_schedule_draft_workbook.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_schedule_contract.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py`

## Acceptance criteria
- `GET /api/v1/workpages/artifacts/{artifact_version_id}` now serves a schedule artifact-backed workpage contract for Stage04 draft weekly schedule artifacts.
- `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit` now creates a new immutable schedule draft artifact version with bounded editable fields only.
- Schedule artifact submit conflicts return canonical nested `/runs/{workflow_run_id}/workpages/schedule-v0/artifacts/{artifact_version_id}` reopen routes.
- Backend-owned schedule artifact read/submit fixtures exist under `fixtures/frontend_contracts/`.

## Outcome
- The generic artifact-backed workpage route family now serves both EOD and schedule artifact-backed contracts.
- The repo has a bounded Stage04 draft-workbook projector/materializer seam for schedule artifact workpages.
- Schedule artifact submit now creates new immutable lineage versions and preserves the frozen Stage04 boundary.
- Backend-owned schedule artifact read/submit snapshots are now generated and committed.

## Commands run
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/unit/test_schedule_draft_workbook.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_schedule_contract.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 -m pytest -q tests/runtime/api/test_workpages_artifact_eod_contract.py`
- `PYTHONPATH=/tmp/onetruth-py311:src python3.11 scripts/export_frontend_snapshots.py`

## Follow-ups
- `TASK-0144` migrates the frontend to the canonical schedule artifact route and landing handoff.
- `TASK-0145` closes EPIC-123 in repo memory and demo/doc posture.
