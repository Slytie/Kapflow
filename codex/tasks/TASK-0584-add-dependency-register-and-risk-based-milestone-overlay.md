---
id: TASK-0584
epic: EPIC-136
title: "Add dependency register and risk-based milestone overlay"
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
Imported from CAPEX v6 source task `SD-TASK-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Create explicit dependency register and risk milestones for stakeholder aligned, architecture proven, system viable, business increment, production ready.

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
- Source required tests: dependencies have owner/needed-by/mitigation
- Acceptance gate: `SD-GATE-003`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: MASTER_Dependency_Register.csv; Risk_Based_Milestone_Model.csv
- Review focus covered: no hidden precedence constraints
- Refactor focus covered: none
- Docs requirement covered: delivery cadence doc
- Rollback/recovery posture recorded: revert register patch

## Closeout evidence
- Added `docs/planning/capex_delivery/MASTER_Dependency_Register.csv` with explicit dependency ids, owners, needed-by milestones, related slices/tasks, mitigations, risk-if-late text, status, and planning-only activation posture.
- Added `docs/planning/capex_delivery/Risk_Based_Milestone_Model.csv` with the exact milestone names `stakeholder aligned`, `architecture proven`, `system viable`, `business increment`, and `production ready`.
- Recorded production-ready as blocked until later restore, capacity, release, storage, raw-corpus, and production-preflight gates close or receive explicit waivers.
- Added contract coverage in `tests/contract/test_capex_semantic_delivery_governance.py` for dependency fields, milestone ordering, valid dependency refs, non-activation posture, and raw-corpus boundary.
- Closeout posture: planning-governance evidence only. No runtime code, migrations, routes, workflow pack activation, raw corpus import, pilot readiness, production readiness, or CAPEX product activation is added.

## Source row mapping
- Source task ID: `SD-TASK-003`
- Source phase: `P0/P1 planning`
- Source priority: `P0`
- Source area: `delivery/dependencies`
- Original depends_on: `SD-TASK-001`
- Recommended source branch: `analysis/master-delivery-safety`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
