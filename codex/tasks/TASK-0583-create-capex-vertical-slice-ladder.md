---
id: TASK-0583
epic: EPIC-136
title: "Create CAPEX vertical-slice ladder"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0582"]
risk: high
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SD-TASK-002` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Classify blocker proof, K12 learning slice, K12 closure slice, procurement escalation MMF, pointer promotion slice, validation holdout.

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
- Source required tests: slice traceability review
- Acceptance gate: `SD-GATE-002`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Vertical_Slice_Ladder.csv; roadmap patch
- Review focus covered: thinness, end-to-end testability, no demo theater
- Refactor focus covered: none
- Docs requirement covered: roadmap update
- Rollback/recovery posture recorded: revert doc/register patch

## Source row mapping
- Source task ID: `SD-TASK-002`
- Source phase: `P0/P1 planning`
- Source priority: `P0`
- Source area: `delivery/backlog`
- Original depends_on: `SD-TASK-001`
- Recommended source branch: `analysis/master-delivery-safety`

## Closeout evidence
- Added `docs/planning/capex_delivery/Vertical_Slice_Ladder.csv` with exact `VS-00` through `VS-05` rows for blocker proof, K12 learning, K12 closure, procurement escalation MMF, pointer promotion, and validation holdout.
- Each slice records entry gates, exit gates, metric refs, repo evidence refs, a planning-only activation posture, and a non-demo-theater guardrail.
- Added semantic contract tests proving slice IDs are exact, metric refs are valid, every slice has entry/exit gates, and the ladder does not claim public runtime/product activation.
- At this task's original closeout, `TASK-0584` was left open for the dependency register and risk-based milestone overlay; `TASK-0584` now has its own closeout evidence and this task remains scoped to the vertical-slice ladder.
- No runtime code, migrations, routes, workflow packs, frontend behavior, raw corpus import, pilot approval, production approval, or CAPEX product activation was introduced.

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
