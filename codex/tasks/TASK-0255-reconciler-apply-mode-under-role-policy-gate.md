---
id: TASK-0255
epic: EPIC-138
title: "Reconciler apply mode under role/policy gate"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0250", "TASK-0252", "TASK-0254"]
risk: high
context_packs:
  - "codex/context/EPIC-138.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR022` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Allow missing-only repairs only after republish/late policy and role checks; apply mode off by default.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-138.md`
- `codex/context/EPIC-138.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-012 plus regression tests
- Acceptance gate: `Apply repairs missing seed once; cannot change officialness; role gate passes.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Apply repairs missing seed once; cannot change officialness; role gate passes.
- Review focus covered: CR-012
- Refactor focus covered: none specified
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR022`
- Source phase: `P10 Deployment/Logistics readiness`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR017;PR019;PR021;PD-01;PD-02;PD-05`
- Source-only dependency notes: `PD-01;PD-02;PD-05`
- Recommended source branch: `production/logistics-hardening`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
