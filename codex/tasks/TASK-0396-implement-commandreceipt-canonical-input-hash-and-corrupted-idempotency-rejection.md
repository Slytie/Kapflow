---
id: TASK-0396
epic: EPIC-141
title: "Implement CommandReceipt canonical input hash and corrupted-idempotency rejection"
status: DONE
completed_at: "2026-06-23T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0233", "TASK-0234", "TASK-0235", "TASK-0236", "TASK-0237", "TASK-0238", "TASK-0239", "TASK-0240"]
risk: high
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W2-S06` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Use canonical JSON/profile with test vectors

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
- Source required tests: red/characterization test or executable acceptance evidence before implementation
- Acceptance gate: `W2-accepted-gates + semantic MR gate`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Implementation artifact(s) implied by W2-S06; source wave W2; CED-linked design note; tests; docs update
- Review focus covered: Tier 3
- Refactor focus covered: explicit refactor/stabilization checkpoint required before closeout
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W2
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W2-S06`
- Source phase: `P4/P5 Corpus and effects`
- Source priority: `P0`
- Source area: `corpus/effects/artifacts/validation`
- Original depends_on: `PR000-PR007`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed as internal runtime foundation evidence: command receipts now store `sha256:` canonical input hashes and the `onetruth.command_receipt_input.canonical_json.sha256.v1` profile, reject non-canonical JSON hash inputs, replay same-scope/same-hash receipts, reject same-scope/different-hash requests as `command_receipt_mismatch`, and reject malformed stored hash/profile rows as `command_receipt_corrupt`.
- Closeout evidence includes `docs/planning/capex_source_ingest/COMMAND_RECEIPT_CANONICAL_INPUT_CONTRACT.yaml`, Alembic/SQLite/model/schema parity for the receipt profile field, and focused receipt tests. No second receipt system, public route, frontend route, CAPEX workflow activation, raw corpus import, event-registry change, official pointer, reviewed-baseline claim, or product activation is introduced.
