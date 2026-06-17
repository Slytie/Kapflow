---
id: TASK-0585
epic: EPIC-136
title: "Add backlog hierarchy and story decomposition templates"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0582"]
risk: medium
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SD-TASK-004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Add outcome epic, feature, story, and Given-When-Then templates, with rule that near-term stories are vertical and testable.

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
- Source required tests: template review
- Acceptance gate: `SD-GATE-004`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Backlog_Taxonomy_and_Decomposition_Guide.md; templates
- Review focus covered: minimum hierarchy, one authoritative backlog
- Refactor focus covered: none
- Docs requirement covered: new guide
- Rollback/recovery posture recorded: revert guide patch

## Closeout evidence
- Added `docs/planning/capex_delivery/Backlog_Taxonomy_and_Decomposition_Guide.md` with the one authoritative hierarchy: product goal -> outcome epic -> feature -> vertical slice -> story -> Given-When-Then acceptance scenario.
- Added templates under `docs/planning/capex_delivery/templates/` for outcome epics, features, vertical stories, and Given-When-Then acceptance scenarios.
- Templates require metric refs, slice refs, source/evidence refs, acceptance scenarios, non-activation posture, and rollback or recovery notes.
- Added contract coverage in `tests/contract/test_capex_semantic_delivery_governance.py` for singular hierarchy, template requirements, no duplicate backlog systems, no demo-only success criteria, non-activation posture, and raw-corpus boundary.
- Closeout posture: planning-governance evidence only. No runtime code, migrations, routes, workflow pack activation, raw corpus import, pilot readiness, production readiness, or CAPEX product activation is added.

## Source row mapping
- Source task ID: `SD-TASK-004`
- Source phase: `P0/P1 planning`
- Source priority: `P1`
- Source area: `delivery/backlog`
- Original depends_on: `SD-TASK-001`
- Recommended source branch: `analysis/master-delivery-safety`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
