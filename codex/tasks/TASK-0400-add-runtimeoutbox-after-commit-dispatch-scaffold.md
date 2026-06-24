---
id: TASK-0400
epic: EPIC-141
title: "Add RuntimeOutbox after-commit dispatch scaffold"
status: DONE
completed_at: "2026-06-23T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0396", "TASK-0397"]
risk: medium
context_packs:
  - "codex/context/EPIC-141.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `ARCH-W2-S10` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Outbox worker can be simple initially

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
- Source output satisfied: Implementation artifact(s) implied by W2-S10; source wave W2; CED-linked design note; tests; docs update
- Review focus covered: Tier 3
- Refactor focus covered: explicit refactor/stabilization checkpoint required before closeout
- Docs requirement covered: Update relevant CED/ADR, architecture doc, catalog, and master traceability for W2
- Rollback/recovery posture recorded: disable capability or leave runtime state inert; no destructive rollback of governed state

## Source row mapping
- Source task ID: `ARCH-W2-S10`
- Source phase: `P4/P5 Corpus and effects`
- Source priority: `P1`
- Source area: `corpus/effects/artifacts/validation`
- Original depends_on: `W2-S06/S07`
- Source-only dependency notes: `W2-S06/S07`
- Recommended source branch: `foundation/* or capex-runtime-disabled/*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closeout evidence adds `docs/planning/capex_source_ingest/RUNTIME_OUTBOX_AFTER_COMMIT_CONTRACT.yaml` and `onetruth.infrastructure.repositories.runtime_outbox` as an internal relay scaffold over canonical `timeline_events` plus `consumer_cursors`.
- RuntimeOutbox reads committed timeline events after a tenant/domain-scoped consumer cursor, dispatches in deterministic `sequence_no` order, advances the cursor only after successful dispatch or explicit event-type skip, and leaves the cursor before failed events for retry.
- This task adds no second authoritative outbox table, public route, frontend route, worker rewiring, event-registry change, raw corpus import, official pointer, reviewed-baseline claim, or CAPEX runtime/product activation.
