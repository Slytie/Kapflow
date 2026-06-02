---
id: TASK-0491
epic: EPIC-149
title: "Define CAPEX invariant test catalog"
status: TODO
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-149.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W75-SLICE-01` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create executable invariant list covering source occurrence, evidence, approval, closure, pointer, Lab boundaries

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-149.md`
- `codex/context/EPIC-149.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: TDD-G01
- Acceptance gate: `W7_5-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W75-SLICE-01; source wave W7_5; CED-linked design note; tests; docs update
- Review focus covered: Tier 2
- Refactor focus covered: explicit refactor/stabilization checkpoint required before closeout
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W7_5
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W75-SLICE-01`
- Source phase: `P0-P12 TDD and agent lab`
- Source priority: `P0/P1`
- Source area: `tdd/fixtures/agent-lab`
- Original depends_on: `architecture CED accepted`
- Source-only dependency notes: `architecture CED accepted`
- Recommended source branch: `integration/capex-platform`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
