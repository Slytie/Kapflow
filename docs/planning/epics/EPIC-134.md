# EPIC-134 - Minimal canonical workpage demo enablement

## Summary
Make it cheap and reliable to run a validation demo of the landed Workpages v1 changes without adding new product scope.

This epic starts after EPIC-133 and assumes the public workpage posture is already canonical-only.

## Status
Complete as of `2026-04-06`.

Current state:
- `TASK-0221` through `TASK-0224` are complete as the bounded demo-enablement tranche.
- Supported-env verification in a clean Python `3.11` install is green for the weekly Stage04 API, dispatch-reporting finalize loop, local demo smoke, and dispatch-reporting workbook unit lane.
- The deterministic prep path, canonical demo runbook, and lightweight regressions now exist without adding any new public demo-only runtime path.

## First-principles objective
Let:
- `S_seed` = the scaffolded weekly-first local demo state from `seed_weekly_first_logistics_local_demo(...)`
- `T_demo` = a deterministic, idempotent prep operator over canonical truth
- `S_demo = T_demo(S_seed)`
- `W_k = Π_k(S_demo)` for workpage kind `k`

The demo should validate `W_k` on the canonical workpage routes, not invent a parallel product path or a new demo-only truth mode.

## In scope
- freeze the minimal demo posture and assumptions in repo-native memory
- repair the broken weekly-first local demo smoke path
- add one deterministic canonical workpage demo-prep command
- emit canonical workpage routes, IDs, and URLs for the demo
- add a concise runbook and lightweight regression coverage for the prep path

## Out of scope
- new app-facing features
- story-shell redesign
- multi-week accepted-history seeding
- route-demand auto-drift seeding
- auto-rescheduling
- new demo-only runtime APIs or a second demo mode

## Dependencies
- EPIC-125
- EPIC-131
- EPIC-133

Context packs:
- `codex/context/EPIC-134.md`
- `codex/context/WORKPAGE_DEMO_GAP_FINDINGS_2026-04-06.md`

## Tasks
- `TASK-0221` - Freeze the minimal workpage demo boundary, canonical-route posture, and no-new-demo-mode rule
- `TASK-0222` - Correct the weekly-first local demo smoke diagnosis and reporting-intake runtime-dependency truth
- `TASK-0223` - Add a one-command canonical workpage demo-prep script
- `TASK-0224` - Add the demo runbook and a canonical workpage demo-prep regression

## Acceptance criteria
- The demo validates the existing canonical workpage surfaces under `/runs/:workflowRunId/workpages/*`.
- The default prep path is deterministic, idempotent, and does not require OpenAI.
- `/demo/logistics` remains launcher/narrative context only; it is not the semantic validation surface.
- A single documented prep command can materialize workpage-ready state and print canonical URLs.
- No new public demo-only runtime path is introduced.

## Key decision
Treat this epic as demo enablement over already-landed canonical workpages, not as a new app-facing product-expansion epic.
