---
id: TASK-0545
epic: EPIC-151
title: "Add hold/freeze minimal blocker model"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-151.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W8-S09` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Hold/freeze constraints for promotion/closure/supersession

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-151.md`
- `codex/context/EPIC-151.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-151` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Implementation artifact(s) implied by W8-S09; source wave W8; CED-linked design note; tests; docs update

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: red test or characterization before implementation
- Acceptance gate: `W8-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W8-S09; source wave W8; CED-linked design note; tests; docs update
- Review focus covered: records/governance reviewer
- Refactor focus covered: separate pure refactor from behavior change unless tiny
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W8
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W8-S09`
- Source phase: `P12/P13 Snapshots and external boundary`
- Source priority: `P0/P1`
- Source area: `snapshots/dossiers/external`
- Original depends_on: `architecture CED accepted`
- Converted repo dependencies: none
- Source dependency notes still to satisfy: architecture CED accepted
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
