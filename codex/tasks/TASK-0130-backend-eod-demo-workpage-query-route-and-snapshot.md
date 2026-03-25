---
id: TASK-0130
epic: EPIC-120
title: "Implement the backend EOD demo workpage query route and generated contract snapshot"
status: DONE
owners: ["backend"]
reviewers: ["frontend", "qa"]
depends_on: ["TASK-0128"]
risk: medium
context_packs: ["codex/context/EPIC-120.md"]
patterns: ["PATTERN-007", "PATTERN-009"]
---

## Context
After `TASK-0128`, the repo has a frozen workpage query contract and route family. The EOD page already exists on the frontend, but its active data path is still local/example-backed.

## Objective
Add the backend demo workpage query surface for the EOD page, backed by the consistent partial 2026-03-16 dispatch-reporting example family, and generate a backend-owned contract snapshot for it.

## Non-goals
- No frontend page migration yet.
- No schedule route work in this task except shared workpage route-family reuse.
- No submit/materialize semantics.
- No artifact-backed EOD path yet.
- Do not try to reproduce raw workbook formulas.

## Source files to read first
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_V0_PLAN.md`
- `docs/workflows/dispatch_reporting/v1/WORKFLOW_CONTRACT.yaml`
- `docs/workflows/dispatch_reporting/v1/OPERATING_MODEL.md`
- `docs/workflows/dispatch_reporting/v1/examples/*`
- `fixtures/logistics/workpages/eod_report_workpage_v0_view_model_example.yaml`
- `src/onetruth/api/route_registry.py`
- `src/onetruth/api/routes/` and `src/onetruth/api/route_specs/`
- `tests/runtime/helpers/frontend_snapshots.py`
- `fixtures/frontend_contracts/README.md`

## Source files to change
- backend route/route-spec files for the EOD workpage query surface
- backend service/query builder for the EOD demo workpage payload
- snapshot-export helper(s) and generated snapshot file(s)
- targeted route/contract tests
- docs/task-memory files touched by the new query surface
- the task file itself with outcomes and follow-ups

## Plan
1. Add the EOD demo workpage backend builder from the consistent 2026-03-16 reporting example family.
2. Add `GET /api/v1/workpages/demo/eod-v0`.
3. Add route/contract tests for the new endpoint.
4. Extend backend-owned snapshot export/check flows with an EOD workpage snapshot.

## Verification
- targeted runtime/API tests for the new route
- frontend snapshot export/check coverage for the new workpage snapshot
- `python3 scripts/validate_repo.py --schemas-only`

## Acceptance criteria
- The backend returns a stable EOD workpage contract for `eod-v0`.
- The payload is built from the consistent dispatch-reporting example family, not served directly from the hand-authored workpage YAML fixture.
- The route remains aligned to reporting draft/review semantics (`reporting.upd_draft.workbook`), not final-packet semantics.
- A backend-generated EOD workpage snapshot exists under `fixtures/frontend_contracts/`.

## Notes / decisions
Surface formula-integrity warnings explicitly in the contract. Do not attempt workbook-formula emulation in this task.

## Outcomes
- Extended the shared demo workpage query seam so `GET /api/v1/workpages/demo/eod-v0` resolves through the existing `workpages.demo.detail` route family rather than adding a parallel route.
- Built the backend EOD payload from the consistent 2026-03-16 QDCI/DVC4 partial dispatch-reporting example family under `docs/workflows/dispatch_reporting/v1/examples/`.
- Kept the route aligned to `reporting.upd_draft.workbook` semantics, surfaced formula-integrity warnings explicitly, and froze honest partial-source-derived summary values instead of serving the hand-authored fixture verbatim.
- Extended the shared frontend snapshot export path and committed `fixtures/frontend_contracts/workpage_eod_v0_state.json` as a backend-owned API contract fixture.

## Verification run
- `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_api_route_registry.py tests/runtime/api/test_workpages_demo_schedule_contract.py tests/runtime/api/test_workpages_demo_eod_contract.py`
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `PYTHONPATH=src python3.11 scripts/export_frontend_snapshots.py --check`
- `python3.11 scripts/validate_repo.py --schemas-only`
