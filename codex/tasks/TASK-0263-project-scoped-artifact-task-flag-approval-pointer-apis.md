---
id: TASK-0263
epic: EPIC-140
title: "Project-scoped artifact/task/flag/approval/pointer APIs"
status: DONE
completed_at: "2026-06-04T14:50:10+02:00"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0261", "TASK-0262"]
risk: high
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PROJ-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Every CAPEX list/detail/action is project-scoped and paginated.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-140.md`
- `codex/context/EPIC-140.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: project isolation tests; pagination tests
- Acceptance gate: `AT-PROJ-004; AT-SCALE-003`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: API filters; repository methods; indexes
- Review focus covered: no tenant/domain-wide leakage; server-side filtering
- Refactor focus covered: shared query helpers
- Docs requirement covered: API catalog
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `PROJ-003`
- Source phase: `P3 Project/access`
- Source priority: `P0`
- Source area: `backend/API`
- Original depends_on: `PROJ-001; PROJ-002`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed by adding project-scoped child route wrappers under `/api/v1/capex/projects/{project_id}` for workflow runs, workspaces, timeline events, human tasks, approvals, flags, artifacts, and pointers.
- Project child reads require project membership before delegation, assert child rows belong to the path project, and return not-found style denial for non-members or project mismatches.
- Shared read helpers now accept optional `project_id` filters before pagination for workflow runs, tasks, approvals, flags, pointers, artifacts, and timeline events.
- Existing global routes and row payloads remain compatible; project routes add project-scoped command names and `project_id` on returned child rows.
- No new schema migration was required; existing `workflow_runs.project_id`, `timeline_events.project_id`, and child `workflow_run_id` index coverage are documented and covered by schema parity tests.
- Evidence: `tests/runtime/api/test_capex_project_child_apis.py`, `tests/runtime/api/test_capex_project_access_api.py`, `tests/unit/test_api_route_registry.py`, `tests/contract/test_route_registry_framework_fitness.py`, and `tests/integration/test_capex_project_schema_parity.py`.
