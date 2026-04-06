# EPIC-133 Context Pack - Workpage fragility reduction and extensibility hardening

Purpose:
- Reduce the accidental complexity left after EPIC-131 and EPIC-132 so future workpages can be added without reintroducing fragility.
- This is still a bounded hardening epic, not a platform rewrite.

## Non-negotiable invariants
- Start only after EPIC-132 leaves a clean, green settlement baseline.
- Public workpage posture remains canonical-only.
- Workpages stay derived from canonical runtime/artifact truth.
- Schedule, route-demand, EOD, and driver-preferences remain distinct truth surfaces.
- The goal is to reduce accidental complexity, not invent a generic workpage DSL/runtime.

## Authoritative docs
- `docs/planning/epics/EPIC-133.md`
- `docs/planning/WORKPAGES_POST_EPIC131_STABILIZATION_AND_SETTLEMENT_PLAN.md`
- `codex/context/WORKPAGE_FORMAL_MODEL_AND_SETTLEMENT_RATIONALE.md`
- `codex/context/WORKPAGE_STABILITY_FINDINGS_2026-04-05.md`
- `docs/planning/epics/EPIC-131.md`
- `codex/context/EPIC-131.md`

## High-signal architectural debts to address
### 1. Client-owned lineage/history
Canonical artifact-backed pages now consume backend-authored `artifact_history` and accepted-entry `route` values from the workpage GET contract. The remaining client-side list/filter history helpers in `frontend/src/lib/repositories/workpagesRepository.ts` are now explicit inline-demo debt for `TASK-0217`, not the canonical page path.

### 2. Client-owned workflow intent
Canonical frontend create/submit flows now use server-authored `action_ref` values, and router state carries that bounded action handoff rather than raw subject meaning. Remaining raw `subject_link` behavior is compatibility/demo debt, not the canonical page path.

### 3. Dual mutation path
`frontend/src/components/workpages/InlineLogisticsWorkpages.tsx` still acts like a second mutation engine inside the demo shell.

### 4. Large concentration files
Current concentration points include:
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `frontend/src/components/workpages/InlineLogisticsWorkpages.tsx`
- `frontend/src/pages/LogisticsScheduleWorkpagePage.tsx`

## Preferred architectural direction
- backend-owned workpage descriptors stay as the registration seam
- backend-owned query surfaces should own lineage/latest/accepted history
- backend-owned actions should own workflow intent and authorization
- the demo shell should either reuse canonical hosts or hand off before mutation
- the frontend should consume bounded host/query/action seams rather than reconstructing semantics locally

## What this epic is not
- not a new feature epic
- not a general spreadsheet/runtime platform
- not an auto-agent rescheduling epic
- not a product-boundary reopen

## Stop line
When this epic is complete, adding another workpage kind should primarily mean:
- register descriptor/query/action pieces,
- add bounded frontend host rendering,
- add focused tests,

rather than editing many unrelated files and re-creating mutation logic in the client.
