---
id: TASK-0600
epic: EPIC-152
title: "Verify P0 activation blockers are closed or explicitly waived"
status: TODO
owners: ["platform", "sre"]
reviewers: ["security", "qa"]
depends_on: ["TASK-0589", "TASK-0590", "TASK-0591", "TASK-0592", "TASK-0593", "TASK-0594", "TASK-0595", "TASK-0596", "TASK-0597", "TASK-0598"]
risk: high
context_packs:
  - "codex/context/EPIC-152.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `PP-TASK-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Check approval.respond neutrality, auth-before-read, capex_project/project_membership, source_occurrence, SourceRef resolution, closure/waiver/lifecycle semantics, stale-command guards, semantic tests and CODEOWNERS gates.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-152.md`
- `codex/context/EPIC-152.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-152` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Verify P0 activation blockers are closed or explicitly waived

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: preflight checklist; regression evidence; CI gate evidence; data leak scan; restore rehearsal as applicable
- Acceptance gate: `PROD-PRE-G01`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Verify P0 activation blockers are closed or explicitly waived
- Review focus covered: evidence completeness; no waiver without owner/reason/expiry; no production activation from draft artifacts
- Refactor focus covered: none; preflight is evidence review, not broad implementation refactor
- Docs requirement covered: MASTER_Production_Preflight_Review.md; go/no-go memo
- Rollback/recovery posture recorded: no-go or conditional go; deactivate feature gates; preserve evidence and waiver trail

## Source row mapping
- Source task ID: `PP-TASK-002`
- Source phase: `P15 Capacity, backup/restore, and controlled pilot readiness`
- Source priority: `P0`
- Source area: `production-preflight`
- Original depends_on: `TP-TASK-001..TP-TASK-010; P0 blocker remediation; release/migration/activation governance`
- Converted repo dependencies: TASK-0589, TASK-0590, TASK-0591, TASK-0592, TASK-0593, TASK-0594, TASK-0595, TASK-0596, TASK-0597, TASK-0598
- Source dependency notes still to satisfy: P0 blocker remediation; release/migration/activation governance
- Recommended source branch: `release-candidate/* or activation/*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
