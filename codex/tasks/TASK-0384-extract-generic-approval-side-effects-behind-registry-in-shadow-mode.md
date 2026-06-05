---
id: TASK-0384
epic: EPIC-140
title: "Extract generic approval side effects behind registry in shadow mode"
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
Imported from CAPEX v6 source task `ARCH-W1-T004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
ApprovalEffectRegistry/SideEffectHandlerRegistry and logistics parity handlers

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
- Source output satisfied: Implementation artifact(s) implied by W1-T004; source wave W1; CED-linked design note; tests; docs update
- Review focus covered: platform + logistics + release reviewer
- Refactor focus covered: pure refactor separate from behavior changes; shadow parity before cutover
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W1
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W1-T004`
- Source phase: `P3/P4 Foundation`
- Source priority: `P0/P1`
- Source area: `platform/domain/project/storage`
- Original depends_on: `architecture CED accepted`
- Source-only dependency notes: `architecture CED accepted`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed by adding `ApprovalEffectRegistry` and `ApprovalEffectPack` behind the existing approval-response hook substrate.
- The default approval-effect registry remains empty and platform-neutral. The logistics compatibility selector now delegates to `LOGISTICS_APPROVAL_RESPONSE_EFFECT_REGISTRY` while preserving existing hook parity for weekly planning and dispatch reporting.
- No approval command payloads, command receipts, API response shapes, routes, migrations, CAPEX approval behavior, or logistics side-effect behavior changed.
- Evidence: `tests/unit/test_approval_effect_registry.py`, `tests/unit/test_approval_response_hooks.py`, `tests/contract/test_handler_import_boundaries.py`, and focused weekly/dispatch approval behavior regressions.
