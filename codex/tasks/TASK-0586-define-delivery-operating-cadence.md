---
id: TASK-0586
epic: EPIC-136
title: "Define delivery operating cadence"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0582", "TASK-0584"]
risk: medium
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SD-TASK-005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Define weekly refinement, three-amigos for near-term stories, monthly dependency/risk review, 8-12 week outcome roadmap refresh.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-136.md`
- `codex/context/EPIC-136.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: cadence accepted by engineering PM/SME
- Acceptance gate: `SD-GATE-005`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: MASTER_Delivery_Operating_Cadence.md
- Review focus covered: lean governance, no meeting bloat
- Refactor focus covered: none
- Docs requirement covered: new cadence doc
- Rollback/recovery posture recorded: revert cadence patch

## Closeout evidence
- Added `docs/planning/capex_delivery/MASTER_Delivery_Operating_Cadence.md` as planning-governance evidence for `SD-GATE-005`.
- The cadence records weekly refinement, three-amigos, monthly dependency/risk review, demo/review, and 8-12 week outcome roadmap refresh with owners, inputs, outputs, and decision records.
- The cadence includes lean-governance and no-meeting-bloat guardrails and preserves the one authoritative backlog hierarchy.
- Added contract coverage in `tests/contract/test_capex_semantic_delivery_governance.py` for cadence rhythms, accepted inputs/outputs, decision records, non-activation posture, and raw-corpus boundary.
- Closeout posture: planning-governance evidence only. No runtime code, migrations, routes, workflow pack activation, raw corpus import, pilot readiness, production readiness, or CAPEX product activation is added.

## Source row mapping
- Source task ID: `SD-TASK-005`
- Source phase: `P0/P1 planning`
- Source priority: `P1`
- Source area: `delivery/cadence`
- Original depends_on: `SD-TASK-001;SD-TASK-003`
- Recommended source branch: `analysis/master-delivery-safety`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
