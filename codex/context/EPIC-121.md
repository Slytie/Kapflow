# EPIC-121 Context Pack - First artifact-backed workpage slice (EOD)

**Purpose (why you might open this):**
- You are implementing or reviewing the first artifact-backed workpage path.
- You need to keep the workpage aligned with the repo's canonical artifact/run model.
- You need to avoid broadening the first write path into a generic artifact editor or schedule write lane.

## Non-negotiable invariants to keep in mind
- Workbook `artifact_versions` remain canonical truth; the workpage is derived.
- Every meaningful save creates a **new immutable artifact version**.
- No in-place workbook mutation.
- No runless demo artifacts: the first EOD drafts must still live inside a canonical `dispatch_reporting.v1` workflow run.
- Keep the first artifact-backed slice to **EOD only**.
- Keep schedule query-backed/composite in this epic.
- Keep the page on **Stage03 draft/review** semantics (`reporting.upd_draft.workbook`), not final-packet semantics.
- Do not emulate spreadsheet formulas or raw workbook layout.
- Do not let the active artifact-backed page stay on frontend-local example data once backend routes exist.
- Update repo-native docs/status/task memory in the same change set when visible truth changes.

## Contracts / docs to treat as authoritative
- `docs/architecture/AUTHORITY_MODEL.md`
- `docs/planning/ARTIFACT_STORE_DESIGN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_V0_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_ARTIFACT_PATH_PLAN.md`
- `docs/domains/logistics/archive/LOGISTICS_WORKPAGES_ARTIFACT_PATH_BRIEF.md`
- `docs/planning/epics/EPIC-121.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/FRONTEND_ARCHITECTURE.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/ARTIFACT_MAP.yaml`
- `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
- `docs/workflows/dispatch_reporting/v1/examples/*`
- `fixtures/frontend_contracts/README.md`
- `fixtures/logistics/workpages/*`
- `src/onetruth/infrastructure/repositories/artifact_versions.py`
- `src/onetruth/application/services/template_registry.py`
- `src/onetruth/api/routes/artifacts.py`
- `frontend/src/app/App.tsx`
- `frontend/src/app/AppShell.tsx`

## Required test coverage (tests-as-spec)
- template-registry and template-pack coverage for the first reporting workbook template
- workbook adapter/materializer round-trip tests
- backend route/contract tests for draft creation, artifact-backed read, and submit
- backend-generated frontend snapshot coverage for artifact-backed EOD responses
- frontend artifact-backed EOD route tests for loading, dirty state, submit success, conflict, download, and lineage display
- doc/task-memory updates when capability truth changes

## Current repo status
- `TASK-0124`..`TASK-0133` are now complete.
- Query-backed workpage routes already exist under `/demo/logistics/workpages/*`.
- The EOD page already exists as a server-authored query-backed page.
- The artifact-backed EOD contract is now frozen in repo-native docs.
- The repo now contains the bounded reporting template pack, multi-workflow template registry, and first Stage03 workbook adapter/materializer seam needed for a truthful artifact-backed EOD path.

## Planned implementation order inside this epic
1. `TASK-0134`
2. `TASK-0135`
3. `TASK-0136`

## Preflight questions for future runs
- Does the repo now contain a bounded `dispatch_reporting.v1` template pack and registry entry for `reporting.upd_draft.workbook`?
- Are artifact-backed EOD drafts being anchored to canonical workflow runs rather than a runless demo store?
- Are submit semantics still explicit and immutable, without per-keystroke artifact writes?
- Are demo-shell entrypoints and repo-memory files still aligned with the active route posture?

## Red-team questions for future runs
- Are we quietly broadening this epic into a generic editor runtime?
- Are we forcing schedule into a write lane before its artifact boundary is stable?
- Are we slipping into final-packet/approval semantics before the first draft-backed write slice is stable?
- Are we bypassing the repo's artifact/run substrate instead of using it?
