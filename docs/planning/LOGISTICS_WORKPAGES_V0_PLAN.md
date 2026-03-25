# Logistics workpages v0 - repo-grounded implementation plan

## Why this exists
The repo now has a strong canonical runtime/artifact substrate, full-page workpage routes exist under the primary logistics demo shell, `TASK-0128` has frozen the next query contract, route family, and snapshot policy, and `TASK-0129` has landed the first backend schedule demo query surface plus generated snapshot.

This epic is still **not** a generic artifact editor. It remains a bounded workpage slice:
- **Schedule workpage v0** grounded in `weekly_schedule_planning.v1`
- **End-of-day report workpage v0** grounded in `dispatch_reporting.v1`

## Current repo grounding
### Baseline after `TASK-0129`
The repo now contains:
- full-page routes:
  - `/demo/logistics/workpages/schedule-v0`
  - `/demo/logistics/workpages/eod-v0`
- a shared frontend `WorkpageViewModel` contract
- local/example-backed workpage repositories or equivalent data seams
- route/page tests proving the pages render and behave from example data
- logistics-shell route classification for `/demo/logistics/*`
- repo-native docs freezing the post-v0 workpage query contract, route family, and snapshot policy
- backend schedule demo route: `GET /api/v1/workpages/demo/schedule-v0`
- backend-generated schedule snapshot: `fixtures/frontend_contracts/workpage_schedule_v0_state.json`

### What already exists beneath that baseline
- Primary operator/demo route: `/demo/logistics`
- Canonical three-workflow family story: `GET /api/v1/stories/logistics-three-workflow`
- Frontend repository/query seams under `frontend/src/lib/repositories/`
- Stable React/Vite/TanStack Query shell with drawer-first detail for existing task-centric surfaces
- Repo-native normalized weekly scheduling examples under `docs/workflows/weekly_schedule_planning/v1/examples/`
- Repo-native normalized dispatch reporting examples under `docs/workflows/dispatch_reporting/v1/examples/`
- Human-authored workpage planning fixtures under `fixtures/logistics/workpages/`

### What still does not exist after `TASK-0129`
- no backend EOD demo workpage query route yet
- no backend-generated EOD workpage snapshot yet
- no frontend migration onto the HTTP-backed workpage repository seam yet
- no artifact-linked workpage projection/submit backend yet
- no logistics-family template/runtime for generalized workpage pages

## Repo-specific nuances that change the remaining batch
- `weekly_schedule_planning.v1` explicitly owns the **pre-week / Friday** weekly build. Day-of replan belongs to `live_dispatch.v1`.
- `dispatch_reporting.v1` explicitly separates normalized actuals, UPD draft generation, manager review, and final packet output. The EOD page therefore remains closer to the **draft/review** portion of the reporting flow than to Stage05 final output.
- The **schedule page is composite** over multiple weekly-planning inputs. It should not be forced into a single-artifact identity just because the EOD page may later be artifact-backed.
- The **EOD page is the better first future artifact-backed candidate** because it maps naturally to one reporting packet/workbook family.
- `fixtures/frontend_contracts/` are backend-owned generated API snapshots. Once workpage demo routes exist, their query snapshots may live there because they are backend-generated, even if the underlying data originates from deterministic example packs.
- The human-authored source examples and workpage planning fixtures remain distinct under `docs/workflows/.../examples/` and `fixtures/logistics/workpages/`.

## Architectural decision for the remaining batch
### Start here
Move from:

`frontend-local examples -> WorkpageViewModel -> full-page UI`

to:

`backend-owned query contract -> backend demo projection -> frontend repository -> full-page UI`

### Do not start here yet
Do **not** jump directly to:

`artifact bytes -> extractor -> workpage submit -> new artifact version`

### Why
Because the repo's frontend architecture assumes server-owned query contracts, and the current workpages should not stay on a frontend-local data seam once the page contract is proven.

## Authority model for this tranche
The invariant remains:
- runtime/backend truth is authoritative,
- query contracts are server-owned projections,
- UI is derived,
- and this batch must still **not** invent a second truth path.

Therefore, in the remaining batch:
- workpage pages become **backend-query-backed**,
- edits remain local/demo-scoped,
- no artifact mutation or pointer semantics are introduced in the UI,
- and no submit/materialize API is added yet.

## Contract decision frozen in `TASK-0128`
### Route family
Freeze a route family that leaves room for both demo and future non-demo projections:
- `GET /api/v1/workpages/demo/{workpage_id}`
- reserve future siblings such as:
  - `GET /api/v1/workpages/artifacts/{artifact_version_id}`
  - `GET /api/v1/workpages/workflow-runs/{workflow_run_id}/{workpage_kind}`

Only the **demo** subfamily should be implemented in the remaining batch.

### Contract shape
Freeze a small server-owned workpage contract:

```ts
interface WorkpageContract {
  workpage: WorkpageViewModel;
  source: {
    mode: "demo" | "artifact_projection" | "run_projection";
    primary_dataset_key: string | null;
    source_dataset_keys: string[];
    source_artifact_version_id: string | null;
    source_refs: string[];
  };
  freshness: {
    generated_at: string;
    source_kind: string;
    source_version: string;
  };
}
```

Important nuance: `dataset_key` alone is not sufficient because the schedule page is composite. The next contract must support:
- `primary_dataset_key` for pages like EOD,
- plus `source_dataset_keys[]` for composite pages like schedule.

## Backend source choice for the remaining batch
### Schedule route (`schedule-v0`)
The backend route should build the workpage contract from the **weekly normalized example set**, not by simply serving the human-authored workpage fixture verbatim.

Use as source material:
- `route_slot_requirements_actual_ops_lab_v2.yaml`
- `approved_availability_actual_ops_lab_v1.yaml`
- `driver_capabilities_actual_ops_lab_v1.yaml`
- `actual_hours_snapshot_actual_ops_lab_v1.yaml`
- `stage04_input_bundle_actual_ops_lab_v2.yaml`

The human-authored workpage fixture remains a planning/oracle artifact, not the active source of truth for the route payload.

### EOD route (`eod-v0`)
The backend route should build the workpage contract from the **consistent partial 2026-03-16 dispatch-reporting example family**, not from an ad hoc frontend constant.

Use as source material:
- `eos_route_rows_2026_03_16_qdci_partial_example.yaml`
- `normalized_actuals_2026_03_16_qdci_partial_example.yaml`
- `upd_candidate_2026_03_16_qdci_partial_example.yaml`

Again, the human-authored workpage fixture remains a planning/oracle artifact rather than the live backend source.

## Snapshot policy
Once the backend demo routes exist, generate backend-owned snapshots such as:
- `fixtures/frontend_contracts/workpage_schedule_v0_state.json`
- `fixtures/frontend_contracts/workpage_eod_v0_state.json`

These are valid frontend contract fixtures because they are generated from backend routes.

## FE migration rule for the remaining batch
After backend demo routes exist:
- active routes under `/demo/logistics/workpages/*` must stop depending on frontend-local example adapters,
- pages should query through a repository backed by `onetruthApi`,
- local edit state remains layered on top of the fetched base contract,
- and loading/error/freshness surfaces should be explicit and tested.

## Testing order for the remaining batch
### 1. Backend EOD route tests (`TASK-0130`)
- prove `GET /api/v1/workpages/demo/eod-v0` returns a stable workpage contract
- export a backend-owned snapshot

### 2. Frontend migration tests (`TASK-0131`)
- repository/query wiring
- loading/error/freshness behavior
- route regression under `/demo/logistics/workpages/*`
- pages still preserve bounded local edit interactions

## Explicit non-goals for this batch
- no artifact submit/materialize path yet
- no generic artifact editor
- no live-dispatch morning page
- no workbook extraction/materialization runtime yet
- no drag/drop layout builder
- no spreadsheet formula engine emulation

## Deferred next batch after this one
The likely next batch after `TASK-0131` is:
- first **artifact-backed** EOD workpage read path,
- then first EOD submit/materialize path,
- while the schedule page remains composite/run-oriented until a stable packet/run projection is explicitly chosen.

That future batch should begin with the EOD page, not the schedule page.

## Documentation maintenance rules for this build
Every post-`TASK-0128` Codex task must update repo-native memory in the same change set when relevant.

Minimum docs to review/update when touched by the task:
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX.md`
- the matching `codex/tasks/TASK-....md` file

Update these too when the change affects them:
- `docs/planning/FRONTEND_ARCHITECTURE.md`
- `docs/planning/FRONTEND_INTERACTION_RULES.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `AGENTS.md`
- `LLM_RUNBOOK.md`
- `codex/CODEX_CONTEXT.yaml`
- `fixtures/frontend_contracts/README.md`

## Codex execution order for the remaining batch
1. `TASK-0130` - implement the backend EOD demo workpage query route + snapshot
2. `TASK-0131` - migrate the frontend pages to the HTTP-backed repository and harden UX/docs

## Red-team guardrails
Before any code lands in the remaining batch, verify all of the following remain true:
- The active workpage routes are moving toward **server-authoritative queries**, not staying forever on frontend-local demo data.
- The route family leaves room for both **artifact-backed** and **run/composite** future workpages.
- The schedule page is still **weekly planning review + selected-day preview**, not a live-dispatch control tower.
- The EOD page is still **draft/review**, not final-packet semantics.
- The backend demo routes build from domain/source examples rather than just serving hand-authored workpage fixtures verbatim.
- Backend-generated workpage snapshots remain distinct from the human-authored planning/oracle fixtures.
- Repo-native docs/status/task memory remain current in the same PR.
