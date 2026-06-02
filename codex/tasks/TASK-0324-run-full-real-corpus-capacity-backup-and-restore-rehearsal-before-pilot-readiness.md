---
id: TASK-0324
epic: EPIC-148
title: "Run full real-corpus capacity, backup, and restore rehearsal before pilot readiness"
status: TODO
owners: ["platform", "sre"]
reviewers: ["security", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-148.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SAFE-D-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Validate real blob ingest, extraction, search/evidence binding, DB+artifact-root restore, digest checks, auth-before-read after restore.

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

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-148` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Full Safety Pass D result; pilot readiness evidence

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: Restore rehearsal passes with sanitized real fixture and selected deployment topology.
- Acceptance gate: `SPD-G001;SPD-G002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Full Safety Pass D result; pilot readiness evidence
- Review focus covered: no pilot-ready claim from metadata-only rehearsal
- Refactor focus covered: storage/index topology isolated behind documented interfaces
- Docs requirement covered: deployment capacity and backup docs
- Rollback/recovery posture recorded: block pilot; revert storage/index claims to development-only

## Source row mapping
- Source task ID: `SAFE-D-001`
- Source phase: `capacity_pilot_safety`
- Source priority: `P0`
- Source area: `capacity/storage/restore`
- Original depends_on: `sanitized fixture; selected storage/index backend; deployed test environment`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: sanitized fixture; selected storage/index backend; deployed test environment
- Recommended source branch: `feature/capex-capacity-gates`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
