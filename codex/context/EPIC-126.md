# EPIC-126 Context Pack - Workpages v1 hardening and closeout

Purpose:
- You are reviewing or extending the deferred hardening tranche that follows EPIC-125.
- You should only use this context after the first local operator demo has happened and real feedback exists.
- You need to tighten the first operator lane without reopening major product-scope questions.

## Non-negotiable invariants to keep in mind
- Workpages remain derived surfaces; runtime rows, events, artifacts, and pointers remain canonical truth.
- Hardening is feedback-driven. Do not invent polish work for hypothetical flows.
- Do not broaden into new workflow-family scope, raw-email parser ownership, live-dispatch algorithmics, or generic spreadsheet/runtime ambitions.
- Route cleanup must preserve one canonical route truth and not create a second workpage family or shell.

## Contracts and docs to treat as authoritative
- `docs/planning/epics/EPIC-126.md`
- `codex/context/EPIC-126.md`
- `docs/planning/LOGISTICS_WORKPAGES_OPERATIONAL_CADENCE_PLAN.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/status/DECISIONS_SINCE_LAST.md`
- the final EPIC-125 closeout docs and verification logs once they exist

## Current repo status
- EPIC-125 is now active, but the first local operator demo and continuous production-shaped cadence milestones are not implemented yet.
- EPIC-126 remains explicitly deferred until after that feedback exists.

## Intended implementation order inside this epic
1. `TASK-0158` - Triage first-demo feedback and land the highest-value UX corrections
2. `TASK-0159` - Harden regression, observability, and failure-state truth
3. `TASK-0160` - Freeze Workpages v1 boundary, clean up route posture, and close doc truth

## Stop line
- No new workflow-family scope.
- No live-dispatch candidate generation or ranking.
- No Stage06/Stage07 schedule workpage widening.
- No generic email ingestion or spreadsheet-runtime expansion.
