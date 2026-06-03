> Document classification: historical logistics context. See `docs/domains/logistics/DOC_INVENTORY.yaml` for current authority.

# Logistics Stale Content Audit

Date: 2026-05-18

## Purpose
- Use the active canonical logistics demo as the keep-set for pre-production cleanup.
- Audit logistics content, pages, tasks, demo scripts, fixtures, and tests rather than shared runtime architecture.
- Distinguish four states:
  - `required-active`
  - `required-supporting`
  - `historical-doc-only`
  - `safe-removal-candidate`
  - `unresolved`

## Evidence Rule
An item is only safe to remove when all of the following are true:
- it is not part of the active logistics demo keep-set
- it is not required by the canonical demo prep/runbook path
- it is not required by the active frontend/backend smoke lanes
- it is not still wired into active shell navigation or route registration
- it is not still the declared source of truth in current status/planning docs

The current keep-set is:
- `/demo/logistics`
- `/runs/:workflowRunId/workpages/schedule-v0`
- `/runs/:workflowRunId/workpages/schedule-v0/artifacts/:artifactVersionId`
- `/runs/:workflowRunId/workpages/route-demand-v0`
- `/runs/:workflowRunId/workpages/route-demand-v0/artifacts/:artifactVersionId`
- `/runs/:workflowRunId/workpages/driver-preferences-v0`
- `/runs/:workflowRunId/workpages/driver-preferences-v0/artifacts/:artifactVersionId`
- `/runs/:workflowRunId/workpages/eod-v0`
- `/runs/:workflowRunId/workpages/eod-v0/artifacts/:artifactVersionId`
- `/runs/:workflowRunId/workspace`

## Keep Matrix
| Item | Status | Why it stays |
|---|---|---|
| `/demo/logistics` shell, `GET /api/v1/stories/logistics-three-workflow`, and `LogisticsDemoPageContent` | `required-active` | Current docs index, `CURRENT_FOCUS`, and `FRONTEND_PAGE_MAP` still name this as the primary logistics entrypoint and launcher for canonical workpages. |
| `schedule-v0`, `route-demand-v0`, `driver-preferences-v0`, and `eod-v0` run/artifact pages | `required-active` | These are the active canonical logistics surfaces and are the routes exercised by the current demo runbook and workpage smoke coverage. |
| `/runs/:workflowRunId/workspace` and `RunWorkspacePage` | `required-active` | This route is still in the agreed keep-set and is still described as the single-run operator workspace in `FRONTEND_PAGE_MAP`. |
| `scripts/run_logistics_workpage_demo_prep.py`, `scripts/run_logistics_demo_frontend.py`, and `docs/ops/runbooks/logistics_canonical_workpage_demo.md` | `required-supporting` | This is the supported deterministic prep path for the current canonical workpage demo. |
| Workpage/frontend snapshots for schedule, route-demand, driver-preferences, EOD, and workspace workpage actions | `required-supporting` | Active workpage tests and snapshot export/check flows still rely on these backend-owned fixtures. |
| Retired demo-workpage alias guardrails | `required-supporting` | `frontend/src/pages/logisticsWorkpageRoutes.test.tsx`, `tests/runtime/api/test_workpages_demo_schedule_contract.py`, `tests/runtime/api/test_workpages_demo_eod_contract.py`, and `tests/unit/test_workpages_active_source_guardrails.py` still enforce the canonical-only posture. |
| `THREE_WORKFLOW_DEMO_STORY.yaml`, the story endpoint tests, and the weekly-first logistics story seeds | `required-supporting` | The launcher shell still depends on the backend logistics story contract even though the canonical workpage demo runbook no longer uses the older full-loop walkthrough as its default validation path. |

## Inventory Results
### Safe removal candidates now
| Candidate | Status | Evidence | Replacement / note |
|---|---|---|---|
| `/board` and `frontend/src/pages/BoardPage.tsx` | `safe-removal-candidate` | `FRONTEND_PAGE_MAP` marks `/board` as a legacy schedule-only triage/regression view; `CURRENT_FOCUS` and `DECISIONS_SINCE_LAST` keep the logistics shell and canonical workpages as the active demo surfaces; `BoardPage.tsx` renders `LegacyScheduleNotice`. | No replacement needed for the active demo. Remove together with its repo helpers and tests. |
| `/timeline` and `frontend/src/pages/TimelinePage.tsx` | `safe-removal-candidate` | `FRONTEND_PAGE_MAP` marks `/timeline` as a legacy schedule-oriented event explorer; `TimelinePage.tsx` renders `LegacyScheduleNotice` and `Timeline (Legacy View)`. | No replacement needed for the active demo. |
| `/runs`, `/runs/:workflowRunId`, and `frontend/src/pages/RunsPage.tsx` + `RunDetailPage.tsx` | `safe-removal-candidate` | Not part of the keep-set; `RunsPage.tsx` renders `Workflow Runs (Legacy Detail Views)`; `RunDetailPage.tsx` renders `LegacyScheduleNotice`; these routes are secondary drill-down surfaces rather than active demo requirements. | Run/workpage discovery already happens through `/demo/logistics` and canonical workpage/workspace routes. |
| `/official-outputs` and `frontend/src/pages/OfficialOutputsPage.tsx` | `safe-removal-candidate` | Not part of the keep-set; `OfficialOutputsPage.tsx` renders `LegacyScheduleNotice` and `Official Outputs (Legacy Pointer List)`. | No replacement required for the active demo. |
| `/workspace` root redirect and `frontend/src/pages/WorkspaceHomePage.tsx` | `safe-removal-candidate` | Not part of the keep-set; page copy explicitly says the primary demo entrypoint is `/demo/logistics` and that this workspace route is legacy. | Keep `/runs/:workflowRunId/workspace`; remove only the root redirect surface. |
| Page-only frontend helpers behind the legacy surfaces | `safe-removal-candidate` | `boardRepository.ts`, `boardLaneMapper.ts`, `timelineRepository.ts`, and `pointersRepository.ts` are only consumed by the legacy routed pages plus repository tests. | Remove only after the corresponding pages/routes are removed. |
| Legacy frontend contract snapshots for board/run-detail/timeline/official outputs | `safe-removal-candidate` | `fixtures/frontend_contracts/stage06_publish_ready_board_state.json`, `run_detail_state.json`, `timeline_state.json`, and `official_outputs_pointers_state.json` only exist to back the legacy surfaces above. | Remove together with the page routes and snapshot generator entries. |

### Historical-doc-only cleanup
| Item | Status | Evidence | Cleanup needed |
|---|---|---|---|
| `codex/tasks/TASK-0202` through `TASK-0207` | `historical-doc-only` | These task files still say `status: TODO`, while `docs/planning/TASK_INDEX.md` already marks the same tasks `DONE` and `CURRENT_FOCUS` describes their functionality as landed. | Reconcile front matter and keep the task briefs as historical closeout records rather than active TODOs. |
| Older compatibility-alias posture docs | `historical-doc-only` | `DECISIONS_SINCE_LAST`, `EPIC-122`, and `LOGISTICS_WORKPAGES_RUN_SURFACES_PLAN` still contain older statements about `/demo/logistics/workpages/*` as compatibility aliases or active posture from earlier tranches. | Keep as history, but do not use them as active guidance. Add "historical context only" wording when they are touched. |
| `CURRENT_CAPABILITY_AND_CERTIFICATION_MATRIX` references to legacy page verification | `historical-doc-only` | It still records passed verification for `boardPage.test.tsx` and workspace demo scenarios that are outside the canonical workpage demo keep-set. | Keep the record, but treat it as history rather than a signal that those surfaces remain product-required. |

### Not safe to remove yet
| Item | Status | Why it is blocked |
|---|---|---|
| `scripts/run_logistics_local_demo.py`, `docs/ops/runbooks/logistics_local_demo_weekly_first.md`, and `fixtures/scenarios/logistics/weekly_first_local_demo_seed.yaml` | `unresolved` | The canonical workpage runbook calls this path older, but `/demo/logistics` still depends on the logistics story contract and repo memory still names the weekly-first local demo seed as the broader story/demo contract. This needs an explicit decision before removal. |
| `docs/planning/THREE_WORKFLOW_DEMO_STORY.yaml` | `required-supporting` | The active shell still uses the story endpoint defined here. The launcher script/default seed language may be older than the workpage demo posture, but the file is still active. |
| `scripts/run_schedule_workspace_demo.py` and its certification/demo docs | `unresolved` | The current keep-set still includes `/runs/:workflowRunId/workspace`, and the capability matrix plus runtime contract coverage still depend on this script. |
| `/my-work`, `/approvals`, `/exceptions` and their page files | `unresolved` | These routes are not part of the explicit keep-set, but they are still exposed in `AppShell` utility navigation and are not marked legacy in the repo the way board/timeline/runs are. They need an explicit product decision before removal. |
| `frontend/src/components/LegacyScheduleNotice.tsx` | `unresolved` | It is stale copy for truly legacy pages, but `RunWorkspacePage` still imports it even though `/runs/:workflowRunId/workspace` is in the keep-set. If the workspace stays, the notice copy should be replaced rather than the component simply deleted. |

## Safe-Removal Bundles
### Bundle A - Legacy routed regression pages
Scope:
- Remove route mounts from `frontend/src/app/App.tsx` for:
  - `/board`
  - `/timeline`
  - `/runs`
  - `/runs/:workflowRunId`
  - `/official-outputs`
  - `/workspace`
- Remove:
  - `frontend/src/pages/BoardPage.tsx`
  - `frontend/src/pages/TimelinePage.tsx`
  - `frontend/src/pages/RunsPage.tsx`
  - `frontend/src/pages/RunDetailPage.tsx`
  - `frontend/src/pages/OfficialOutputsPage.tsx`
  - `frontend/src/pages/WorkspaceHomePage.tsx`
- Remove or rewrite shell links in `frontend/src/app/AppShell.tsx` that still point at those routes.

Verification after Bundle A:
- `/demo/logistics` still loads and launches canonical workpages.
- `/runs/:workflowRunId/workspace` still loads.
- `make frontend-workpages-smoke` still passes.

### Bundle B - Legacy page-only helpers, tests, and snapshots
Scope:
- Remove legacy-page-only frontend helpers when Bundle A lands:
  - `frontend/src/lib/repositories/boardRepository.ts`
  - `frontend/src/lib/mappers/boardLaneMapper.ts`
  - `frontend/src/lib/repositories/timelineRepository.ts`
  - `frontend/src/lib/repositories/pointersRepository.ts`
- Remove the related tests and snapshot usage:
  - `frontend/src/pages/boardPage.test.tsx`
  - `frontend/src/pages/runsPage.test.tsx`
  - `frontend/src/pages/runDetailPage.test.tsx`
  - `frontend/src/lib/mappers/boardLaneMapper.test.ts`
  - repository tests that only exist to cover those helpers
- Remove backend-owned fixtures and snapshot generator entries for:
  - `stage06_publish_ready_board_state.json`
  - `run_detail_state.json`
  - `timeline_state.json`
  - `official_outputs_pointers_state.json`

Verification after Bundle B:
- `PYTHONPATH=src python3.11 scripts/export_frontend_snapshots.py --check`
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py`
- `npm --prefix frontend run typecheck`

### Bundle C - Repo-memory cleanup for stale logistics task truth
Scope:
- Reconcile `codex/tasks/TASK-0202` through `TASK-0207` so their front matter matches `TASK_INDEX`.
- Keep the files as historical implementation notes; do not delete them.
- When touching historical planning docs that still describe alias-era posture, add explicit wording that they are historical context rather than active route truth.

Verification after Bundle C:
- `TASK_INDEX` and task-brief statuses agree.
- `CURRENT_FOCUS` remains the active source of truth for demo posture.
- No active planning doc still describes `/demo/logistics/workpages/*` as an active public route family.

### Bundle D - Deferred demo-seed consolidation
Scope:
- Decide later whether the weekly-first local demo seed path can be retired.
- Only consider removal of:
  - `scripts/run_logistics_local_demo.py`
  - `docs/ops/runbooks/logistics_local_demo_weekly_first.md`
  - `fixtures/scenarios/logistics/weekly_first_local_demo_seed.yaml`
  - older story-demo-only tests/contracts

Current blocker:
- `/demo/logistics` still depends on the three-workflow story seam, and repo memory still keeps the weekly-first local demo path alive as a broader story/demo contract.

## Post-Cleanup Verification Checklist
- `docs/status/CURRENT_FOCUS.md`, `docs/planning/FRONTEND_PAGE_MAP.md`, and `docs/index.md` still agree on the active logistics entrypoints.
- `/demo/logistics` still loads and launches the correct canonical workpage routes.
- `schedule-v0`, `route-demand-v0`, `driver-preferences-v0`, and `eod-v0` still load from seeded demo data.
- Route-demand to schedule coverage handoff still works.
- Uncovered-route recovery still works on the main schedule page and inside the edit schedule popup.
- `/runs/:workflowRunId/workspace` still loads if it remains in scope.
- `make frontend-workpages-smoke` passes.
- `make PYTHON=python3.11 workpage-mutation-smoke` passes.
- `PYTHONPATH=src python3.11 scripts/export_frontend_snapshots.py --check` passes after any snapshot-set changes.
- `PYTHONPATH=src python3.11 -m pytest -q tests/runtime/contracts/test_frontend_snapshot_fixtures.py` passes after any snapshot-set changes.

## Recommended Removal Order
1. Bundle C first, because the task-status mismatch is pure stale memory and does not affect runtime behavior.
2. Bundle A next, because those pages are explicitly legacy and already outside the keep-set.
3. Bundle B immediately after Bundle A, because its helpers/snapshots only make sense if the legacy pages still exist.
4. Bundle D only after an explicit decision that the weekly-first story/demo path is no longer supported.
