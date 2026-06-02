---
id: TASK-0273
epic: EPIC-141
title: "Batch artifact link/provenance hydration"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0263"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `INGEST-008` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Eliminate N+1 link loading on CAPEX pages.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-141.md`
- `codex/context/EPIC-141.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: query count tests; 5k artifacts benchmark
- Acceptance gate: `AT-SCALE-006`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: batch loaders; paginated list/detail split
- Review focus covered: no unbounded lists; query plan reviewed
- Refactor focus covered: shared relation loader
- Docs requirement covered: performance guide
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `INGEST-008`
- Source phase: `P5 Performance`
- Source priority: `P0`
- Source area: `backend/repository`
- Original depends_on: `PROJ-003`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
