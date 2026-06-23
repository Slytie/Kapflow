---
id: TASK-0286
epic: EPIC-143
title: "Governance / Commitment Chain workflow"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0284"]
risk: high
context_packs:
  - "codex/context/EPIC-143.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `WFLOW-004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Extract approvals, budgets, quotes, orders, revisions, settlements and responsibility shifts.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-143.md`
- `codex/context/EPIC-143.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: order revision; settlement-not-RCA tests
- Acceptance gate: `AT-002; AT-COMMIT-001`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: commitment_chain; expenditure_ledger; flags
- Review focus covered: external/internal officialness; commercial!=technical
- Refactor focus covered: commitment event mappers
- Docs requirement covered: commitment docs
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `WFLOW-004`
- Source phase: `P7 Workflows`
- Source priority: `P0`
- Source area: `workflow/commitments`
- Original depends_on: `WFLOW-002`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Completion evidence
- Added `docs/planning/capex_workflow_catalog/governance_commitment_chain_workflow.yaml` for the `WFLOW-004` Governance / Commitment Chain planning contract.
- Added `onetruth.capex_platform.governance_commitment_chain` to build deterministic commitment-chain, expenditure-ledger, and commitment-flag outputs from sanitized commitment observations and Corpus Baseline refs.
- Added unit and contract coverage for order revisions, settlement-not-RCA boundaries, commercial/responsibility separation, missing basis, invalid event types, duplicate commitment ids, SourceRef scope, and non-activation boundaries.
- This closes planning/internal output-shape evidence only; authored workflow pack activation, approval mutation, public routes, commitment workpages, reviewed baseline truth, official pointers, and CAPEX runtime/product activation remain blocked.
