---
id: TASK-0383
epic: EPIC-140
title: "Create CAPEX domain manifest in not-ready/incubation state"
status: DONE
completed_at: "2026-06-05T09:32:46+02:00"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-140.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W1-T003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
domains/capex/domain.yaml with disabled capabilities and readiness prerequisites

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-140.md`
- `codex/context/EPIC-140.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: red/characterization test or executable acceptance evidence before implementation
- Acceptance gate: `W1-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W1-T003; source wave W1; CED-linked design note; tests; docs update
- Review focus covered: architecture reviewer
- Refactor focus covered: none beyond manifest validation
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W1
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W1-T003`
- Source phase: `P3/P4 Foundation`
- Source priority: `P0/P1`
- Source area: `platform/domain/project/storage`
- Original depends_on: `architecture CED accepted`
- Source-only dependency notes: `architecture CED accepted`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed by adding `docs/domains/capex/domain.yaml` as an incubation-state domain manifest with empty workflow, workpage, and side-effect inventories.
- The CAPEX manifest records readiness prerequisites and disabled capabilities for authorization projections, workflow catalog, source-data governance, storage custody, richer workpages, and production/pilot activation.
- Added `docs/domains/capex/README.md` and `DOC_INVENTORY.yaml`; CAPEX runtime activation remains blocked.
- Evidence: `tests/contract/test_capex_domain_manifest.py` and `tests/contract/test_domain_manifest_schema.py`.
