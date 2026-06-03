> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Logistics workpages artifact path - repo-grounded implementation plan

## Why this exists
After `TASK-0131`, the active workpage routes are query-backed and server-authored. That proved the page contract. The next unproven part of the original goal is the **artifact-backed write loop**.

This plan defines the first bounded write path:
- **EOD only**
- **artifact-backed**
- **immutable version chain**
- **downloadable workbook output**
- **no generic editor scope expansion**

## Repo-grounded constraints that change the implementation
### 1) Artifact versions require a workflow run
The repo's canonical artifact store is not runless. `artifact_versions` already require `workflow_run_id`, and `supersedes_artifact_version_id` exists natively in the repository layer.

Implication:
- do not invent a free-floating demo artifact store just for workpages
- anchor the first EOD drafts inside a canonical `dispatch_reporting.v1` workflow run
- if necessary, resolve or create that run through a deterministic demo helper for the known service-date example

### 2) Dispatch reporting has authored workflow/artifact contracts but no repo template pack yet
`dispatch_reporting.v1` already defines `reporting.upd_draft.workbook` in its workflow/artifact contracts, but the repo currently lacks the corresponding `fixtures/workflows/dispatch_reporting/template_pack/` workbook fixtures.

Implication:
- this epic must add a bounded reporting template pack before artifact-backed draft creation is possible

### 3) Template registry support is currently too schedule-centric
The existing template-registry service defaults to `schedule_planning.v1` and a single registry path.

Implication:
- add bounded multi-workflow registry support so `dispatch_reporting.v1` can truthfully expose a template for `reporting.upd_draft.workbook`

### 4) The schedule page is still composite
The schedule page was always the right first read/query surface, but it is still composite across multiple weekly-planning sources.

Implication:
- do not force schedule into this epic's write model
- keep schedule query-backed while EOD proves the first artifact-backed path

## Frozen route family
### Existing query-backed routes (keep)
- `GET /api/v1/workpages/demo/schedule-v0`
- `GET /api/v1/workpages/demo/eod-v0`

### New artifact-backed EOD routes (this epic)
- `POST /api/v1/workpages/demo/eod-v0/drafts`
  - resolve or create the canonical demo `dispatch_reporting.v1` run
  - instantiate a new `reporting.upd_draft.workbook` artifact version from the template
- `GET /api/v1/workpages/artifacts/{artifact_version_id}`
  - project the artifact-backed EOD workpage from the workbook artifact version
- `POST /api/v1/workpages/artifacts/{artifact_version_id}/submit`
  - validate + materialize a **new** workbook artifact version that supersedes the base

### Frontend route posture
- keep `/demo/logistics/workpages/eod-v0` as the query-backed landing page
- add `/demo/logistics/workpages/eod-v0/artifacts/:artifactVersionId` as the artifact-backed full-page route

## Workbook compatibility envelope for the first slice
The first artifact-backed slice should use a **bounded semantic workbook**, not the raw EOS workbook.

Recommended Stage03 workbook contract:
- `RouteActuals` table
- `UpdCandidates` table
- `ManualCloseout` table
- `QualityWarnings` table (read-only)
- `ChangeLogStage03_UpdDraft` table (server-managed)
- optional `Lookups03` table for enum values

Rules:
- only table bodies are editable
- `ChangeLog*` is read-only in UI and appended server-side on submit
- warnings are surfaced explicitly; do not attempt formula-engine emulation
- row identity must be stable (explicit `RowID` column or documented key columns)

## Submit semantics
### Canonical loop
\[
A_v \xrightarrow{\text{project}} UI \xrightarrow{\Delta} A_{v+1}
\]

### Rules
- never mutate `A_v` in place
- submit must create `A_{v+1}` with `supersedes_artifact_version_id = A_v`
- explicit save/submit only; no per-keystroke artifact writes
- if `A_v` has already been superseded in the same draft chain, return a conflict and let the client reopen the latest version
- keep workbook download on the normal artifact route

## Snapshot policy
Backend-owned snapshots should now cover both:
- query-backed demo routes (already complete from EPIC-120)
- artifact-backed EOD read route and representative create/submit responses

These belong under `fixtures/frontend_contracts/` because they are backend-generated API fixtures.
Human-authored workpage planning fixtures remain under `fixtures/logistics/workpages/`.

## Epic task order
1. `TASK-0132` - freeze the artifact-backed contract, run anchoring, and route family
2. `TASK-0133` - add reporting template pack, registry support, and workbook adapter tests
3. `TASK-0134` - implement backend EOD artifact routes + generated snapshots
4. `TASK-0135` - migrate the EOD page to the artifact-backed route with submit/conflict/download UX
5. `TASK-0136` - expose demo entrypoints, recent-version history, and keep docs/status truthful

## Red-team guardrails
- Do not invent runless demo artifacts.
- Do not jump to schedule artifact-backed writes in this epic.
- Do not broaden into final-packet approval/pointer semantics.
- Do not leave the artifact-backed page on frontend-only local state once the backend routes exist.
- Do not let a missing reporting template pack force the implementation into ad hoc JSON-instead-of-workbook persistence.
- Do not rely on hidden spreadsheet formulas as authoritative truth.
