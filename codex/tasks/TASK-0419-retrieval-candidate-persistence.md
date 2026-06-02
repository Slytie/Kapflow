---
id: TASK-0419
epic: EPIC-141
title: "Retrieval candidate persistence"
status: TODO
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W3-S009` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
agent/search retrieval provenance

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-141.md`
- `codex/context/EPIC-141.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: retrieval candidate cannot become reviewed evidence directly
- Acceptance gate: `W3-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W3-S009; source wave W3; CED-linked design note; tests; docs update
- Review focus covered: Tier 3
- Refactor focus covered: Separate candidate schema from evidence binding schema
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W3
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W3-S009`
- Source phase: `P6 Extraction and evidence`
- Source priority: `P0/P1`
- Source area: `extraction/search/evidence`
- Original depends_on: `W3-S008`
- Source-only dependency notes: `W3-S008`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
