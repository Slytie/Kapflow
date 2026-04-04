---
id: TASK-0202
epic: EPIC-131
title: "Add backend workpage descriptors, calculated contract blocks, and accepted-series queries"
status: TODO
owners: ["backend"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0201"]
risk: high
context_packs:
  - "codex/context/EPIC-131.md"
  - "codex/context/WORKPAGE-DEPENDENCY-AND-CALCULATION-RATIONALE.md"
  - "codex/context/WORKPAGE-CONTRACT-SKETCHES-SCHEDULE-ROUTE-DEMAND-PREFERENCES.md"
patterns: []
---

## Context
The repo has the right primitives, but workpage-kind identity, dependency resolution, lineage, accepted history, and actionability are still too scattered. This task establishes the backend contract foundation for the corrected operator slice.

## Objective
Introduce backend-owned workpage descriptors and contract/query helpers that can serve:
- `schedule-v0`
- `route-demand-v0`
- `driver-preferences-v0`

and expose:
- `artifact_state`
- `dependencies[]`
- `calculations`
- `draft_lineage`
- `accepted_series`
- `actions[]`

This task must also add the explicit accepted-series grouping key that current repo review could not find on saved/published schedule artifacts.

## Non-goals
- No full schedule preview logic yet.
- No complete route-demand editor yet.
- No final frontend rendering overhaul in this task.

## Source files to read first
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/api/route_specs/workpages.py`
- `src/onetruth/application/handlers/workpages.py`
- `src/onetruth/application/services/logistics_workpages.py`
- `src/onetruth/api/routes/workflow_runs.py`
- `src/onetruth/application/handlers/approvals.py`
- `src/onetruth/infrastructure/repositories/*` relevant artifact / pointer helpers

## Source files to change
- `src/onetruth/api/route_specs/workpages.py`
- `src/onetruth/api/routes/workpages.py`
- `src/onetruth/application/handlers/workpages.py`
- new or extracted descriptor/query helpers under `src/onetruth/application/services/`
- `src/onetruth/application/services/logistics_workpages.py`
- tests for route contracts and workpage actions

## Plan
1. Add a `WorkpageDescriptor` layer or equivalent backend-owned definition for `schedule-v0`, `route-demand-v0`, and `driver-preferences-v0`.
2. Add kind-scoped canonical artifact routes so the artifact API is no longer only family-inferred.
3. Extend workpage contract building to support the calculated blocks and separate accepted-series vs draft-lineage data.
4. Add accepted-series query helpers over `planning.published_weekly_schedule.workbook`, grouped by a stable explicit series key.
5. Keep compatibility aliases only where needed; do not let them remain the semantic source of truth.

## Verification
- Existing workpage route tests updated and passing.
- New tests proving accepted-series queries do not mix drafts.
- New tests proving descriptor-based workpage action projection remains actor-scoped.

## Acceptance criteria
- `schedule-v0`, `route-demand-v0`, and `driver-preferences-v0` have explicit backend descriptors.
- Workpage contracts can carry calculated blocks and accepted-series data.
- Accepted-series data is distinct from draft lineage in the contract and tests.
- Artifact-backed routes are canonical and kind-scoped.
