---
id: TASK-0319
epic: EPIC-145
title: "Reserve K3 authority/lifecycle module contracts"
status: TODO
owners: ["platform", "security"]
reviewers: ["architect", "qa"]
depends_on: []
risk: medium
context_packs:
  - "codex/context/EPIC-145.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SPB2-T005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add catalog rows for lifecycle obligation, operational control, acceptance semantics, workaround override; mark conditional/post-MVP.

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

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-145` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Reserve K3 authority/lifecycle module contracts

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: Catalog reflects contracts without adding full K3 module to MVP critical path.
- Acceptance gate: `Catalog reflects contracts without adding full K3 module to MVP critical path.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Reserve K3 authority/lifecycle module contracts
- Review focus covered: real-project data governance; source triage; no false closure
- Refactor focus covered: keep K3/K12 fixture governance outside platform runtime assumptions
- Docs requirement covered: MASTER_Real_Project_Fixture_Governance.md; corpus ingest/source triage docs
- Rollback/recovery posture recorded: remove sanitized derivative; preserve quarantine manifest; no raw-data rollback needed because raw data must not be committed

## Source row mapping
- Source task ID: `SPB2-T005`
- Source phase: `schemas_and_contracts`
- Source priority: `P1`
- Source area: `data_governance/corpus_ingest/k3_shadow`
- Original depends_on: `schema catalog update`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: schema catalog update
- Recommended source branch: `analysis/capex-master-plan or feature/capex-fixture-governance`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
