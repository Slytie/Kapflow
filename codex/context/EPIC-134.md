# EPIC-134 Context Pack - Minimal canonical workpage demo enablement

Purpose:
- Make the already-landed canonical workpages cheap and reliable to demo.
- Keep the implementation bounded to demo enablement, not new product scope.

Status:
- Active as of `2026-04-06`.
- `TASK-0221` is complete as the repo-memory freeze; `TASK-0222` through `TASK-0224` remain.

## Non-negotiable invariants
- Validate workpage behavior on canonical `/runs/:workflowRunId/workpages/*` routes.
- `/demo/logistics` may remain launcher/narrative context, but it is not the semantic validation surface.
- The default demo-prep path should be deterministic, idempotent, and should not require OpenAI.
- No new public APIs, no demo-only truth path, and no second demo mode.
- Multi-week accepted-history seeding and route-demand auto-drift seeding remain out of scope for the first demo.

## Authoritative docs
- `docs/planning/epics/EPIC-134.md`
- `docs/planning/LOGISTICS_WORKPAGE_DEMO_ENABLEMENT_PLAN.md`
- `codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/epics/EPIC-125.md`
- `docs/planning/epics/EPIC-131.md`
- `docs/planning/epics/EPIC-133.md`

## Repo-grounded findings
1. `scripts/run_logistics_local_demo.py` only seeds scaffold state; it does not create the schedule draft or driver-preferences snapshot needed for the new canonical workpages.
2. The full prep procedure currently lives in `tests/runtime/api/test_logistics_local_demo_smoke_api.py` rather than a user-facing script.
3. Supported-env verification in a clean Python `3.11` install is green for the weekly Stage04 API, the dispatch-reporting finalize loop, the local demo smoke, and the dispatch-reporting workbook unit lane, so the imported Stage04 diagnosis is stale.
4. The remaining `TASK-0222` gap is dependency honesty: a partial Python `3.11` environment without `openpyxl` currently misclassifies dispatch-reporting workbook parsing failure as `unsupported_eos_workbook_shape` instead of a missing runtime dependency.
5. The canonical read-side workpage surfaces are otherwise already present, so the follow-on implementation should stay small.

## Preferred implementation shape
- correct the stale local-demo diagnosis and missing-dependency classification first,
- add a tiny deterministic service/script pair for demo prep,
- emit canonical routes in machine-readable JSON,
- document the exact backend/frontend startup and walkthrough steps.

## What this epic is not
- not a new app-facing product epic
- not a story-shell redesign
- not an OpenAI runtime demo
- not a multi-week demo-seeding effort

## Stop line
The smallest successful outcome is:
- one repaired smoke path,
- one prep command,
- one short runbook,
- canonical routes only.
