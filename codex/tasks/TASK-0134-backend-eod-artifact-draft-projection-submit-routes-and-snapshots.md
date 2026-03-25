---
id: TASK-0134
epic: EPIC-121
title: "Implement backend EOD artifact draft/projection/submit routes and generated snapshots"
status: TODO
owners: ["backend"]
reviewers: ["frontend", "qa"]
depends_on: ["TASK-0133"]
risk: high
context_packs: ["codex/context/EPIC-121.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0133`, the repo should be able to resolve a real reporting template and round-trip bounded edits back into workbook bytes.

The next step is to expose the first artifact-backed EOD route family while staying inside the canonical run/artifact model.

## Objective
Implement the backend routes that make the first artifact-backed EOD slice real:
- create or resolve a demo draft artifact version
- project an artifact-backed workpage from that artifact version
- submit to a new superseding workbook artifact version
- generate backend-owned snapshots for frontend use

## Non-goals
- No schedule write path.
- No final-packet approval/pointer flow.
- No human-task/workspace integration unless a bounded existing lane makes it trivial.
- No generic artifact editor runtime.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_ARTIFACT_PATH_PLAN.md`
- `docs/planning/epics/EPIC-121.md`
- `src/onetruth/api/route_registry.py`
- `src/onetruth/api/routes/artifacts.py`
- `src/onetruth/api/routes/` and `src/onetruth/api/route_specs/`
- `src/onetruth/infrastructure/repositories/artifact_versions.py`
- template/adapter files added by `TASK-0133`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`
- logistics-three-workflow story seed helpers/tests if reused for demo run resolution

## Source files to change
- new workpage route/route-spec files for artifact-backed EOD surfaces
- backend builder/service modules for draft creation, artifact projection, and submit
- targeted runtime/API tests
- snapshot-export/check helper(s) and generated snapshot file(s)
- docs/task-memory files touched by the new route truth
- the task file itself with outcomes and follow-ups

## Plan
1. Add the draft creation route for EOD and anchor it to a canonical reporting run.
2. Add the artifact-backed read route for workpage projection.
3. Add the submit route that creates a new superseding workbook artifact version.
4. Add route/contract tests and generated snapshots.

## Verification
- targeted runtime/API tests for create/read/submit routes
- snapshot export/check coverage
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The backend can create a first EOD workbook draft artifact version from the reporting template.
- The backend can project an artifact-backed EOD workpage from `artifact_version_id`.
- Submit creates a **new** workbook artifact version with `supersedes_artifact_version_id` set.
- Generated frontend snapshots exist for representative create/read/submit flows.

## Notes / decisions
The backend should reuse canonical artifact ingestion/creation patterns where possible rather than inventing a side-channel store for workbook bytes.
