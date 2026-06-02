---
id: TASK-0308
epic: EPIC-150
title: "Restructure documentation tree"
status: TODO
owners: ["architect"]
reviewers: ["platform", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-150.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `DOC-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create architecture/development/deployment/domains/decisions/reference hierarchy.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-150.md`
- `codex/context/EPIC-150.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: doc manifest/lint
- Acceptance gate: `docs gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: docs tree; doc owner/status fields
- Review focus covered: normative vs descriptive clear
- Refactor focus covered: doc movement only branches
- Docs requirement covered: documentation plan
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `DOC-001`
- Source phase: `P11 Docs/devflow`
- Source priority: `P0`
- Source area: `documentation`
- Original depends_on: `Pass3 accepted`
- Source-only dependency notes: `Pass3 accepted`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
