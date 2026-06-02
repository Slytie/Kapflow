---
id: TASK-0561
epic: EPIC-139
title: "Extract logistics side effects from approval.respond"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0233", "TASK-0234", "TASK-0235", "TASK-0236", "TASK-0237", "TASK-0238", "TASK-0239", "TASK-0240"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P0-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Make approval response domain-neutral; logistics publish/finalize/handoff move to domain hook registry.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-139.md`
- `codex/context/EPIC-139.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-139` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
ApprovalResponse-only handler; domain side-effect hook registry; logistics characterization tests

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CB2-T002 plus logistics regression tests
- Acceptance gate: `NU-GATE-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: ApprovalResponse-only handler; domain side-effect hook registry; logistics characterization tests
- Review focus covered: Approval does not imply officialness, closure, publish, handoff, or settlement
- Refactor focus covered: Domain hook extraction; no behavior mixing
- Docs requirement covered: Update architecture, runtime model, code-review checklist
- Rollback/recovery posture recorded: Disable CAPEX approval reuse until complete; preserve logistics baseline with characterization tests

## Source row mapping
- Source task ID: `NU-CB-P0-001`
- Source phase: `P1/P2 platform foundation`
- Source priority: `P0`
- Source area: `platform/approval`
- Original depends_on: `PR000-PR007`
- Converted repo dependencies: TASK-0233, TASK-0234, TASK-0235, TASK-0236, TASK-0237, TASK-0238, TASK-0239, TASK-0240
- Recommended source branch: `foundation/approval-domain-neutrality`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
