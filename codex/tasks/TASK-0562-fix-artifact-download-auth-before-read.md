---
id: TASK-0562
epic: EPIC-137
title: "Fix artifact download auth-before-read"
status: TODO
owners: ["platform", "security"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0235"]
risk: high
context_packs:
  - "codex/context/EPIC-137.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P0-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Refactor blob/artifact download so authorization occurs before any binary/blob read.

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

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-137` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Auth-before-read helper; injectable storage spy test; cross-scope denial test

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CB2-T001
- Acceptance gate: `NU-GATE-002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Auth-before-read helper; injectable storage spy test; cross-scope denial test
- Review focus covered: Security reviewer; no raw file read before scope check
- Refactor focus covered: Small local refactor in download path; no broad storage rewrite
- Docs requirement covered: Update security/runbook and test docs
- Rollback/recovery posture recorded: Feature-gate real CAPEX corpus ingest until fixed

## Source row mapping
- Source task ID: `NU-CB-P0-002`
- Source phase: `P1/P2 platform foundation`
- Source priority: `P0`
- Source area: `platform/security/blob`
- Original depends_on: `PR002`
- Converted repo dependencies: TASK-0235
- Recommended source branch: `foundation/auth-before-read`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
