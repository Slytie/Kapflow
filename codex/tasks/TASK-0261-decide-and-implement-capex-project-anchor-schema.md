---
id: TASK-0261
epic: EPIC-140
title: "Decide and implement CAPEX project anchor schema"
status: DONE
completed_at: "2026-06-04T10:53:09+02:00"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0240", "TASK-0257"]
risk: high
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PROJ-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create stable project_id distinct from workflow_run_id; workflows execute within projects.

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
- Source required tests: migration/schema/API tests
- Acceptance gate: `AT-PROJ-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: capex_project table/projection or equivalent; ADR
- Review focus covered: project not workflow_run; auditability; backwards compatibility
- Refactor focus covered: small migration; isolated repository layer
- Docs requirement covered: project model docs; ADR-0002
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `PROJ-001`
- Source phase: `P3 Project/access`
- Source priority: `P0`
- Source area: `data-model/backend`
- Original depends_on: `PR007; CLEAN-001`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed by adding durable `capex_projects` runtime state, nullable `project_id` on `workflow_runs` and `timeline_events`, repository helpers, SQLAlchemy models, SQLite bootstrap DDL, and Alembic migration `20260604_0011`.
- ADR-006 records that `capex_projects.project_id` is the durable CAPEX root and `workflow_run_id` is only an execution identity.
- Project creation emits `capex.project.created`, stores project scope, and remains inactive for broader CAPEX runtime/product activation.
- Evidence: `tests/unit/test_capex_project_access.py`, `tests/runtime/api/test_capex_project_access_api.py`, and `tests/integration/test_capex_project_schema_parity.py`.
