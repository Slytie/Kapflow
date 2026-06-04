---
id: TASK-0265
epic: EPIC-140
title: "Project-scoped official pointer families"
status: DONE
completed_at: "2026-06-04T15:18:22+02:00"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0238", "TASK-0261"]
risk: high
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PROJ-005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Pointers and snapshots scoped by project_id + pointer_family + generation.

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
- Source required tests: stale generation tests; approval-not-pointer test
- Acceptance gate: `AT-OFFICIAL-004; NU-006`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: pointer family policy; expected-generation validation
- Review focus covered: no latest/approved shortcut
- Refactor focus covered: reuse generic pointer model carefully
- Docs requirement covered: pointer promotion guide
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `PROJ-005`
- Source phase: `P9 Officialness`
- Source priority: `P0`
- Source area: `backend/pointers`
- Original depends_on: `PROJ-001; PR005`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed by adding CAPEX project official pointer family support on top of the existing canonical `artifact_pointers` promotion substrate, without changing pointer ID format or adding a migration.
- Project official pointers map `project_id + pointer_family` to `scope_kind=capex_project`, `scope_ref={project_id}`, `pointer_key=official:{pointer_family}`, and `stream_key=capex-project:{project_id}:pointer-family:{pointer_family}` with existing generation/CAS behavior.
- Officialness still requires explicit pointer promotion; approval responses, latest artifact rows, and approved approvals do not move CAPEX project official pointers by themselves.
- Promotion enforces project membership and project ownership for workflow-run, artifact, approval, and task evidence before delegating to the canonical pointer promotion command.
- Added project official pointer routes under `/api/v1/capex/projects/{project_id}/official-pointers*` for list, detail, and promote. Existing generic pointer behavior for logistics/no-project flows remains unchanged.
- Evidence: `tests/unit/test_capex_official_pointer_families.py`, `tests/runtime/api/test_capex_project_official_pointer_api.py`, `tests/runtime/api/test_pointer_list_endpoint.py`, and route-registry/boundary contract coverage.
