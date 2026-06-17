---
id: TASK-0588
epic: EPIC-136
title: "Add Definition of Ready / Done for CAPEX task classes"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: ["TASK-0585"]
risk: medium
context_packs:
  - "codex/context/EPIC-136.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `SD-TASK-007` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
DoR/DoD for architecture, runtime, workpage, agent-lab, fixture, migration/release tasks.

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
- Source required tests: PR template consistency check
- Acceptance gate: `SD-GATE-007`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: MASTER_Definition_of_Ready_Done.md
- Review focus covered: align with TDD/code-review/refactor rules
- Refactor focus covered: none
- Docs requirement covered: DoR/DoD doc and template patch
- Rollback/recovery posture recorded: revert doc/template patch

## Closeout evidence
- Added `docs/planning/capex_delivery/MASTER_Definition_of_Ready_Done.md` as planning-governance evidence for `SD-GATE-007`.
- The DoR/DoD covers architecture, runtime, workpage, fixture, agent-lab, and migration/release task classes.
- Updated `.github/pull_request_template.md` with a CAPEX DoR/DoD consistency checklist for source truth, tests or accepted test-gap, raw-data boundary, activation boundary, rollback/recovery, and generated/progress freshness.
- Added contract coverage in `tests/contract/test_capex_semantic_delivery_governance.py` for task class coverage, TDD/code-review/refactor/source-truth alignment, PR-template consistency, non-activation posture, and raw-corpus boundary.
- Closeout posture: planning-governance evidence only. No runtime code, migrations, routes, workflow pack activation, raw corpus import, pilot readiness, production readiness, or CAPEX product activation is added.

## Source row mapping
- Source task ID: `SD-TASK-007`
- Source phase: `P0/P1 planning`
- Source priority: `P1`
- Source area: `delivery/quality`
- Original depends_on: `SD-TASK-004`
- Recommended source branch: `analysis/master-delivery-safety`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
