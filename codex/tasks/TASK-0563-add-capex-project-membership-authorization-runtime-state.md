---
id: TASK-0563
epic: EPIC-140
title: "Add CAPEX project/membership/authorization runtime state"
status: DONE
completed_at: "2026-06-05T10:42:12+02:00"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0240"]
risk: high
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P0-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add capex_project, project_membership, authorization projection, project-scoped helpers.

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
- Source required tests: CB2-T003 plus access projection tests
- Acceptance gate: `NU-GATE-003`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Additive migration; project auth service; route dependency helper
- Review focus covered: No workflow_run-as-project shortcut; server-side enforcement
- Refactor focus covered: Additive schema; no broad auth rewrite
- Docs requirement covered: Update runtime state and architecture docs
- Rollback/recovery posture recorded: Runtime flag prevents CAPEX activation until project access gates pass

## Source row mapping
- Source task ID: `NU-CB-P0-003`
- Source phase: `P3 project access`
- Source priority: `P0`
- Source area: `capex/access`
- Original depends_on: `W1 CED-002; PR007`
- Source-only dependency notes: `W1 CED-002`
- Recommended source branch: `foundation/capex-project-access`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Completed on `2026-06-05T10:42:12+02:00`.
- Added additive `capex_project_authorization`, `capex_project_feature`, and `capex_user_project_view` runtime projection tables through Alembic and SQLite bootstrap parity.
- Added projection refresh/rebuild helpers under the CAPEX platform project-access layer; direct `project_memberships` remain authoritative and projections are deterministic read models.
- Project create and membership grant commands refresh projections inside the command transaction, while `AuthorizedProjectsQuery` now reads projection-backed rows without changing public CAPEX project API shapes.
- `capex.runtime_activation` is seeded as disabled by default, so closing EPIC-140 does not activate CAPEX runtime/product behavior.
