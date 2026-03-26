# EPIC-122 Context Pack - Workflow-run-backed workpages

**Purpose (why you might open this):**
- You are implementing or reviewing the next workpage epic after the first artifact-backed EOD slice.
- You need to keep workpages aligned with canonical workflow runs rather than leaving them as demo-only entrypoints.
- You need to avoid forcing schedule into a premature write model or broadening into legacy workspace/task modernization.

## Non-negotiable invariants to keep in mind
- Workpages remain derived surfaces; runtime rows/events/artifacts remain canonical truth.
- Schedule remains composite and query-backed in this epic.
- EOD keeps the existing artifact-backed edit route and immutable workbook lineage.
- The new layer is **workflow-run-backed landing/access**, not a generic workpage builder.
- Do not collapse run-backed landing and artifact-backed editing into one ambiguous surface.
- Do not introduce runless artifact discovery or detached demo artifacts.
- Keep `/demo/logistics/workpages/*` as compatibility aliases after the canonical run-backed surfaces are proven; do not let them reclaim the primary access posture.
- Update repo-native docs/status/task memory in the same change set when visible route truth changes.

## Contracts / docs to treat as authoritative
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/LOGISTICS_WORKPAGES_V0_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_ARTIFACT_PATH_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_RUN_SURFACES_BRIEF.md`
- `docs/planning/epics/EPIC-122.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/workflows/weekly_schedule_planning/v1/OPERATING_MODEL.md`
- `docs/workflows/live_dispatch/v1/OPERATING_MODEL.md`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
- `fixtures/frontend_contracts/README.md`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`
- `frontend/src/lib/repositories/workpagesRepository.ts`

## Required test coverage (tests-as-spec)
- backend route/contract tests for run-backed schedule workpage responses
- backend route/contract tests for run-backed EOD landing/latest-draft-resolution responses
- backend-generated snapshot export/check coverage for the new run-backed routes
- frontend route/repository tests for `/runs/:workflowRunId/workpages/*`
- explicit loading/error/navigation tests for run-backed landing versus artifact-backed EOD editing handoff
- doc/task-memory updates when the active route posture changes

## Current repo status
- Query-backed schedule/EOD workpage routes already exist under `/demo/logistics/workpages/*`.
- The first artifact-backed EOD draft/create/read/submit slice is complete through `TASK-0136`.
- `TASK-0137` is complete, so the workflow-run-backed route family, alias posture, and minimal `run_context` / `draft_resolution` contract are now frozen.
- `TASK-0138` is complete, so the repo now exposes the first canonical run-backed workpage route at `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/schedule-v0` and the backend-owned snapshot `fixtures/frontend_contracts/workpage_schedule_v0_run_state.json`.
- `TASK-0139` is complete, so the repo now also exposes `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0` plus `POST /api/v1/workpages/workflow-runs/{workflow_run_id}/eod-v0/drafts`, along with backend-owned snapshots for the run-backed EOD landing and canonical create response.
- `TASK-0140` is complete, so the frontend now exposes canonical `/runs/:workflowRunId/workpages/schedule-v0`, `/runs/:workflowRunId/workpages/eod-v0`, and `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId` routes while preserving the validated workpage UI and demo aliases.
- `TASK-0141` is complete, so `/demo/logistics` now advertises the canonical run-backed schedule/EOD workpage routes as the primary discoverable path and the family-node drilldown card exposes run-specific workpage CTAs for weekly-planning and dispatch-reporting runs.
- EOD editing already lives on an artifact-backed route keyed by `artifact_version_id`.
- EPIC-122 is now closed. The next decision should be a new epic choice, not another hidden route-posture follow-up inside this epic.

## Planned implementation order inside this epic
1. `TASK-0138` - DONE
2. `TASK-0139` - DONE
3. `TASK-0140` - DONE
4. `TASK-0141` - DONE

## Preflight questions for future runs
- Does the repo still contain the expected post-`TASK-0136` baseline before you start backend/frontend implementation?
- Does the repo still contain the expected post-`TASK-0141` baseline before you start any new workpage epic that assumes canonical run-backed discovery is already in place?
- Does the route family in `docs/planning/HITL_HTTP_API_CONTRACTS.md` still match `docs/planning/FRONTEND_PAGE_MAP.md` and `docs/planning/LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN.md`?
- Is schedule still treated as composite/query-backed rather than one-artifact/write-backed?
- Does the EOD run-backed landing route clearly hand off to the existing artifact-backed edit route rather than duplicating write semantics?
- Are demo aliases and generated snapshots still aligned with the canonical route posture, with `/demo/logistics` advertising canonical `/runs/.../workpages/*` routes as primary?

## Red-team questions for future runs
- Are we quietly turning this epic into schedule write-path design?
- Are we deepening EOD finalization semantics before the workflow-run-backed access model is stable?
- Are we routing this epic through legacy workspace/task surfaces before that layer is modernized?
- Are we creating two competing canonical entry models instead of one run-backed model plus one artifact-backed EOD edit lane?
