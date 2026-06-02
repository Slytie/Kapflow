---
id: TASK-0306
epic: EPIC-148
title: "Scale benchmark harness and CI/manual gates"
status: TODO
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: ["TASK-0273"]
risk: high
context_packs:
  - "codex/context/EPIC-148.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `TEST-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Benchmark 1k/5k/50x1k/fixture corpus with relation cardinality.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-148.md`
- `codex/context/EPIC-148.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: latency/query count gates
- Acceptance gate: `AT-SCALE-007..010`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: benchmark scripts; baseline reports
- Review focus covered: no target-scale claims without evidence
- Refactor focus covered: parameterized harness
- Docs requirement covered: capacity docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `TEST-003`
- Source phase: `P10 Capacity`
- Source priority: `P0`
- Source area: `testing/performance`
- Original depends_on: `INGEST-008`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
