---
id: TASK-0275
epic: EPIC-148
title: "Storage quota, backup and restore gate"
status: TODO
owners: ["platform", "sre"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0242", "TASK-0254", "TASK-0270"]
risk: high
context_packs:
  - "codex/context/EPIC-148.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `INGEST-010` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Define storage tier, quota, backup, restore rehearsal and object-store decision.

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
storage decision note; restore_proof for fixture corpus

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: backup/restore smoke; artifact download after restore
- Acceptance gate: `BACKUP-RESTORE; AT-SCALE-010`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: storage decision note; restore_proof for fixture corpus
- Review focus covered: auth-before-read after restore; no raw data leak
- Refactor focus covered: storage adapter boundary
- Docs requirement covered: capacity-and-backup docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `INGEST-010`
- Source phase: `P10 Capacity/deployment`
- Source priority: `P0`
- Source area: `ops/storage`
- Original depends_on: `INGEST-005; PR009; PR021`
- Converted repo dependencies: TASK-0242, TASK-0254, TASK-0270
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
