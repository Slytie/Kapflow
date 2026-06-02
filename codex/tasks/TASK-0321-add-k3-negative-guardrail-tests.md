---
id: TASK-0321
epic: EPIC-145
title: "Add K3 negative guardrail tests"
status: TODO
owners: ["platform", "security"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-145.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SPB2-T007` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
External officialness, normative references, replacement measures, procedures/training, lifecycle obligations, handover/acceptance.

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
- Source required tests: Guardrail tests fail if these artifacts self-close project state.
- Acceptance gate: `Guardrail tests fail if these artifacts self-close project state.`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Add K3 negative guardrail tests
- Review focus covered: real-project data governance; source triage; no false closure
- Refactor focus covered: keep K3/K12 fixture governance outside platform runtime assumptions
- Docs requirement covered: MASTER_Real_Project_Fixture_Governance.md; corpus ingest/source triage docs
- Rollback/recovery posture recorded: remove sanitized derivative; preserve quarantine manifest; no raw-data rollback needed because raw data must not be committed

## Source row mapping
- Source task ID: `SPB2-T007`
- Source phase: `acceptance_tests`
- Source priority: `P0`
- Source area: `data_governance/corpus_ingest/k3_shadow`
- Original depends_on: `K3 mini-fixture expected-output catalog`
- Source-only dependency notes: `K3 mini-fixture expected-output catalog`
- Recommended source branch: `analysis/capex-master-plan or feature/capex-fixture-governance`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
