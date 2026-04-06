# EPIC-131 Context Pack - Completed Workpages v1 operator tranche

Purpose:
- Rehydrate the final boundary that landed for weekly logistics workpages.
- Use this pack for regression or maintenance work, not for reopening the product boundary.
- Treat the follow-on canonical-route/doc cleanup as completed under EPIC-126.

## Non-negotiable invariants
- Workpages remain derived surfaces over canonical workflow/task/event/artifact/pointer truth.
- `schedule-v0` edits only reassignment/on-call posture plus server recalculation.
- `route-demand-v0` owns route-demand edits separately from `schedule-v0`.
- `driver-preferences-v0` remains soft/advisory and never hard-blocks schedule preview/save/publish.
- Accepted history and draft lineage stay separate.
- Public workpage posture is canonical-only: run/kind-scoped backend routes and `/runs/:workflowRunId/workpages/*` frontend routes.

## Authoritative docs
- `docs/planning/epics/EPIC-131.md`
- `docs/planning/LOGISTICS_WORKPAGES_V1_HEATMAP_RECALC_ROUTE_DEMAND_AND_VERSIONING_PLAN.md`
- `docs/planning/LOGISTICS_WORKPAGES_V1_OPERATOR_READINESS_NOTE.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`

## Delivered sequence
1. `TASK-0201` - repo-native boundary freeze
2. `TASK-0202` - descriptor-backed contracts and accepted-series foundation
3. `TASK-0203` - schedule preview, pinned baselines, and drift guards
4. `TASK-0204` - schedule frontend redesign with live preview and split version rails
5. `TASK-0205` - `route-demand-v0` editor and schedule refresh follow-up
6. `TASK-0206` - `driver-preferences-v0` snapshot editor and soft advisory integration
7. `TASK-0207` - canonical route cutover, regression proof, and doc truth

## Deferred beyond this epic
- date-specific exceptions
- auto-rescheduling agent behavior
- broader post-v1 hardening and feedback cleanup
