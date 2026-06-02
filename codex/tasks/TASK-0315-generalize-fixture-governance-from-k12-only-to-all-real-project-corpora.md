---
id: TASK-0315
epic: EPIC-145
title: "Generalize fixture governance from K12-only to all real project corpora"
status: TODO
owners: ["platform", "security"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0233"]
risk: high
context_packs:
  - "codex/context/EPIC-145.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SPB2-T001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add real-project corpus quarantine policy and docs before any K3/K12 raw processing.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-145.md`
- `codex/context/EPIC-145.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: No raw real-project artifact is stored in repo/CI/release/log/package; policy exists and is referenced by fixture tasks.
- Acceptance gate: `No raw real-project artifact is stored in repo/CI/release/log/package; policy exists and is referenced by fixture tasks.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Generalize fixture governance from K12-only to all real project corpora
- Review focus covered: real-project data governance; source triage; no false closure
- Refactor focus covered: keep K3/K12 fixture governance outside platform runtime assumptions
- Docs requirement covered: MASTER_Real_Project_Fixture_Governance.md; corpus ingest/source triage docs
- Rollback/recovery posture recorded: remove sanitized derivative; preserve quarantine manifest; no raw-data rollback needed because raw data must not be committed

## Source row mapping
- Source task ID: `SPB2-T001`
- Source phase: `source_freeze_and_data_governance`
- Source priority: `P0`
- Source area: `data_governance/corpus_ingest/k3_shadow`
- Original depends_on: `PR000 rebaseline`
- Source-only dependency notes: `rebaseline`
- Recommended source branch: `analysis/capex-master-plan or feature/capex-fixture-governance`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
