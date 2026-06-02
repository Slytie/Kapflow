---
id: TASK-0234
epic: EPIC-137
title: "Release-bundle cleanliness + Cloud Build PR skeleton"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0233"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `MP-PR001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Remove tracked root node_modules residue; add root node_modules exclusion; add PR validation skeleton, branch-rule docs.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-137.md`
- `codex/context/EPIC-137.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CR-001 plus regression tests
- Acceptance gate: `Clean release bundle test passes; PR CI runs no production secrets.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Clean release bundle test passes; PR CI runs no production secrets.
- Review focus covered: CR-001
- Refactor focus covered: RF-001
- Docs requirement covered: update gate/docs/ADR if behavior changes
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `MP-PR001`
- Source phase: `P1 Platform Foundation`
- Source priority: `P0`
- Source area: `platform/readiness`
- Original depends_on: `PR000/G0`
- Source-only dependency notes: `/G0`
- Recommended source branch: `foundation/ip5`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Completion evidence
- Release/source-bundle hygiene now excludes `node_modules/` paths repo-wide.
- Cloud Build PR validation skeleton was added as a no-secret, no-deploy validation lane.
- Tracked `node_modules` residue was removed from repo truth before this task was closed.
