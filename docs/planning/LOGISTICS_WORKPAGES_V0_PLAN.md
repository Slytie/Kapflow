# Logistics workpages v0 - repo-grounded implementation plan

## Why this exists
The repo now has a strong canonical runtime/artifact substrate and a primary logistics operator shell at `/demo/logistics`, but it still lacks a full-page work surface for logistics operators.

The next application package is therefore **not** a generic artifact editor. It is a bounded workpage slice:
- **Schedule workpage v0** grounded in `weekly_schedule_planning.v1`
- **End-of-day report workpage v0** grounded in `dispatch_reporting.v1`

## Current repo grounding
### What already exists
- Primary operator/demo route: `/demo/logistics`
- Canonical three-workflow family story: `GET /api/v1/stories/logistics-three-workflow`
- Frontend repository/query seams under `frontend/src/lib/repositories/`
- Stable React/Vite/TanStack Query shell with drawer-first detail for existing task-centric surfaces
- Repo-native normalized weekly scheduling examples under `docs/workflows/weekly_schedule_planning/v1/examples/`
- Repo-native normalized dispatch reporting examples under `docs/workflows/dispatch_reporting/v1/examples/`

### What does not exist yet
- no workpage routes
- no workpage repository/type surface
- no workpage API contract
- no artifact-linked workpage projection/submit backend
- no logistics-family template registry for workpage pages

### Repo-specific nuances that change execution
- `weekly_schedule_planning.v1` explicitly owns the **pre-week / Friday** weekly build. Day-of replan belongs to `live_dispatch.v1`.
- `dispatch_reporting.v1` explicitly separates normalized actuals, UPD draft generation, manager review, and final packet output. The EOD page therefore belongs closer to the **draft/review** portion of the reporting flow than to Stage05 final output.
- `fixtures/frontend_contracts/` are backend-owned generated API snapshots. Workpage fixtures are a **different class** of artifact and must remain human-authored planning/test fixtures under `fixtures/logistics/workpages/`.
- `frontend/src/app/AppShell.tsx` currently treats only the exact path `/demo/logistics` as a logistics-shell route. The workpage tranche must treat `/demo/logistics/*` as logistics routes, and the new pages should be sibling routes under `AppShell`, not nested inside `LogisticsDemoPage.tsx`.

## Architectural decision
### Start here
Start FE development from:

`normalized examples -> WorkpageViewModel -> full-page UI`

and **not yet** from:

`artifact bytes -> extractor -> editor -> new artifact version`

### Why
Because the repo already has strong normalized examples and a primary logistics demo shell, but it does not yet have the backend workpage projection/submit contract. The lowest-risk way to begin is to stabilize the frontend page contract first.

## Authority model for this tranche
The invariant remains:
- runtime/backend truth is authoritative,
- UI is derived,
- and the first workpage tranche must **not** invent a second truth path.

Therefore, in v0:
- workpage pages are derived from example data,
- edits remain local/demo-scoped,
- and no artifact mutation or pointer semantics are introduced in the UI.

## Preflight alignment before coding
Before `TASK-0124` begins real FE work, confirm all of the following:
- the EPIC-120 planning/context/task files are present in the repo tree,
- the schedule page is still on the weekly-planning side of the boundary,
- the EOD page is still on the reporting draft/review side of the boundary,
- the EOD example family is internally consistent,
- and the route shape still treats `/demo/logistics` as the primary entrypoint.

If any of the above drift, fix the repo-native docs/fixtures first.

## Workpage contract direction
The first shared type should be a small `WorkpageViewModel` with:
- top-level metadata (`workpage_id`, `title`, `workflow_id`, `dataset_key`, `mode`, `source_examples`, `summary`, `validation`)
- a section union limited to:
  - `summary_cards`
  - `table`
  - `note_panel`
  - `form`
  - `checklist`
  - `history_stub`

Important constraint:
- page-specific detail belongs inside section payloads,
- not as global top-level fields that try to predict every future workpage shape.

## Example data seam
The initial repository seam is intentionally honest:
- it is example-backed,
- it is replaceable,
- and it should be named accordingly.

Acceptable first locations:
- `frontend/src/lib/repositories/workpagesRepository.ts`
- or a clearly named equivalent under `frontend/src/lib/workpages/`

What it should do in v0:
- return the schedule example view model,
- return the EOD example view model,
- and avoid implying a server contract that does not exist yet.

What it should not do yet:
- parse YAML in the browser runtime,
- fetch `/api/v1/workpages/*`,
- or simulate save/submit semantics.

## Fixture strategy
Two fixture classes now matter:

### Backend-owned frontend contract snapshots
- live under `fixtures/frontend_contracts/`
- generated from real runtime scenario state
- used to freeze existing HTTP/query surfaces

### Workpage FE planning/test fixtures
- live under `fixtures/logistics/workpages/`
- human-authored
- derived from repo-native normalized examples and the product brief
- used to freeze the early page contract

Do not blur those two classes together.

## Schedule workpage v0
Route:
- `/demo/logistics/workpages/schedule-v0`

Grounding:
- `weekly_schedule_planning.v1`
- weekly review posture
- selected-day preview only

Must render:
- week summary
- daily demand and coverage table
- selected-day preview
- driver roster/detail excerpt
- a boundary note that day-of truth remains in `live_dispatch.v1`
- selected-day local what-if inputs
- history stub

Must not imply:
- authoritative day-of dispatch editing
- spreadsheet cloning
- backend save/submit

## End-of-day report workpage v0
Route:
- `/demo/logistics/workpages/eod-v0`

Grounding:
- `dispatch_reporting.v1`
- draft/review posture
- `reporting.upd_draft.workbook` semantics

Must render:
- top summary cards
- formula-integrity warning panel
- route actuals table
- manual closeout form
- UPD candidate checklist
- history stub

Must not imply:
- Stage05 final-packet authority
- PDF generation
- source-workbook formula emulation

## Route integration
### Shell behavior
`AppShell` must:
- treat `/demo/logistics/*` as logistics-shell routes,
- keep the logistics nav entry active for those routes,
- and keep secondary detail routes visible across the logistics-shell prefix.

### Page behavior
The workpages must be:
- sibling routes under `AppShell`,
- full pages,
- and separate from the drawer-first detail flow used on the existing task-centric pages.

### Entry points
The primary discoverability path is still `/demo/logistics`.
That page should add truthful links to the two workpages without turning them into the new app root.

## Testing order
### 1. View-model tests
Freeze the mapping from repo examples into the frontend `WorkpageViewModel` shape.

### 2. Page render tests
Prove the schedule page and the EOD page render the expected sections from example data.

### 3. Edit/interaction tests
Prove bounded manual fields and table edits behave deterministically in UI state.

### 4. Route integration tests
Prove the new routes mount as **sibling routes under `AppShell`**, treat `/demo/logistics/*` as logistics-shell routes, and keep `/demo/logistics` as the primary entrypoint.

## Explicit non-goals
- no generic artifact editor
- no live-dispatch morning page in this tranche
- no backend workpage HTTP contract yet
- no artifact version submit semantics yet
- no drag/drop layout builder yet
- no spreadsheet formula engine emulation
- no attempt to reproduce raw Excel layout

## Future phases after v0 FE is validated
### Phase 2 - backend projection
Add:

`(artifact_version, template) -> WorkpageViewModel`

### Phase 3 - backend submit / compile
Add:

`(base_artifact_version, patch) -> new_artifact_version`

Those phases are intentionally deferred until the page contract is validated by FE prototype work.

## Documentation maintenance rules for this build
Every EPIC-120 Codex task must update repo-native memory in the same change set when relevant.

Minimum docs to review/update when touched by the task:
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- the matching `codex/tasks/TASK-....md` file

Update these too when the change affects them:
- `docs/planning/FRONTEND_ARCHITECTURE.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`

## Codex execution order
1. `TASK-0123` - freeze scope/product brief/fixtures/docs routing
2. `TASK-0124` - run preflight alignment and add the workpage view-model contract + example data seam
3. `TASK-0125` - build schedule workpage v0 page + tests
4. `TASK-0126` - build EOD workpage v0 page + tests
5. `TASK-0127` - integrate routes/entrypoints and reconcile docs/capability surfaces

## Red-team guardrails
Before any code lands, verify all of the following remain true:
- The page is a **full page**, not a drawer retrofit.
- The task is anchored to `/demo/logistics`, not the legacy schedule-only surfaces.
- The code is building a repo-native frontend page contract, not inventing a fake backend API.
- The EOD page is a guided operational form, not a spreadsheet clone.
- The EOD page is anchored to reporting draft/review semantics, not Stage05 final-output semantics.
- The schedule page is about **weekly planning review + selected-day preview**, not a live-dispatch control tower.
- Workpage fixtures remain distinct from backend-owned frontend contract snapshots.
- Repo-native docs/status/task memory remain current in the same PR.
