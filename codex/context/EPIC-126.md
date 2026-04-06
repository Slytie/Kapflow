# EPIC-126 Context Pack - Completed Workpages v1 cleanup epic

Purpose:
- Finish cleanup after EPIC-131 without reopening the product boundary.
- Keep active repo truth aligned with the canonical-only workpage posture.
- Rehydrate the landed cleanup decisions if a later maintenance pass touches the same seams.

## Non-negotiable invariants
- Workpages remain derived surfaces over canonical runtime truth.
- No return to `/api/v1/workpages/demo/*`, `/api/v1/workpages/artifacts/*`, or `/demo/logistics/workpages/*`.
- Active action vocabulary is `open_route | create_then_open`.
- `/demo/logistics` stays as the shell entrypoint only.

## Authoritative docs
- `docs/planning/epics/EPIC-126.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- `docs/planning/FRONTEND_PAGE_MAP.md`
- `docs/planning/HITL_HTTP_API_CONTRACTS.md`
- `docs/planning/LOGISTICS_WORKPAGES_V1_OPERATOR_READINESS_NOTE.md`

## Delivered sequence
1. `TASK-0158` - internal cleanup and vocabulary normalization
2. `TASK-0159` - canonical regression, fixture, and guardrail hardening
3. `TASK-0160` - repo-truth closeout and active-doc synchronization

## Stop line
- No new app-facing epic is selected after this cleanup closeout.
- No new workpage surface is added here.
- Historical docs may stay historical, but active docs and active fixtures must reflect the canonical-only posture.
