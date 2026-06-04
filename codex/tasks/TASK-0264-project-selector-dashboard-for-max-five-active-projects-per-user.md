---
id: TASK-0264
epic: EPIC-140
title: "Project selector/dashboard for max-five active projects per user"
status: DONE
completed_at: "2026-06-04T14:50:10+02:00"
owners: ["frontend"]
reviewers: ["platform", "qa"]
depends_on: ["TASK-0262"]
risk: medium
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PROJ-004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create project selector optimized for about five active assigned projects.

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
- Source required tests: UI/access smoke tests
- Acceptance gate: `AT-PROJ-005`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: dashboard projection; user project list
- Review focus covered: no cross-project leakage; roles visible
- Refactor focus covered: shared project shell
- Docs requirement covered: UX docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `PROJ-004`
- Source phase: `P8 Workpages`
- Source priority: `P1`
- Source area: `frontend`
- Original depends_on: `PROJ-002`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed by adding `caller_role` to project list/detail payloads, a project dashboard projection at `GET /api/v1/capex/projects/{project_id}/dashboard`, and frontend CAPEX project API/repository methods.
- The dashboard projection is derived from canonical runtime objects and returns project metadata, caller role, counts, and small paged excerpts for recent runs and active work.
- The frontend adds quiet operational routes at `/capex/projects` and `/capex/projects/:projectId`, shows up to five active assigned projects by default, displays caller role, and links to existing run/work/task queues.
- No root redirects, logistics route changes, CAPEX production activation, raw corpus use, or official pointer-family behavior are implied by this selector/dashboard slice.
- Evidence: `tests/runtime/api/test_capex_project_child_apis.py`, `frontend/src/pages/capexProjectDashboardPage.test.tsx`, `frontend/src/lib/api/onetruthApi.capexProjects.test.ts`, `npm --prefix frontend run typecheck`, and `npm --prefix frontend run test:run -- src/pages/capexProjectDashboardPage.test.tsx src/lib/api/onetruthApi.capexProjects.test.ts`.
