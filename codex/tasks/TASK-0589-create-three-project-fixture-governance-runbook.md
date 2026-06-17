---
id: TASK-0589
epic: EPIC-146
title: "Create three-project fixture governance runbook"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-146.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `TP-TASK-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Define raw/full/sanitized/off-repo handling for K12, K3 and blind validation project.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-146.md`
- `codex/context/EPIC-146.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: fixture-manifest validation; no-raw-data scan; cross-project invariant checks
- Acceptance gate: `TP-G01..TP-G12 as applicable`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Create three-project fixture governance runbook
- Review focus covered: test data governance; no raw corpus leakage; no project-specific hardcoding
- Refactor focus covered: keep fixture/test utilities reusable across K12, K3, and blind validation
- Docs requirement covered: update three-project testing strategy and runbook
- Rollback/recovery posture recorded: remove fixture release; keep raw data quarantined; record waiver if gate cannot pass

## Closeout evidence
- Added `docs/planning/capex_three_project_validation/THREE_PROJECT_FIXTURE_GOVERNANCE_RUNBOOK.md` as planning-governance evidence for `TP-TASK-001`.
- The runbook covers K12, K3, and blind validation fixture tiers; raw/full off-repo handling; sanitized fixtures, manifests, hashes, aggregate evidence, release approval, quarantine, leak-scan, no-overfitting, and no project-specific hardcoding.
- The runbook maps `TP-G01..TP-G12` as governance meanings while explicitly leaving downstream fixture, oracle, blind baseline, scorecard, capacity, and expected-output evidence to later tasks.
- Added contract coverage in `tests/contract/test_capex_real_project_acceptance.py` for fixture tier coverage, raw-data boundary, TP gate references, non-activation posture, and no downstream-gate completion claim.
- Closeout posture: planning-governance evidence only. No fixture release, expected-output manifest, oracle schema, raw corpus import, runtime code, routes, workflow pack activation, pilot readiness, production readiness, or CAPEX product activation is added.

## Source row mapping
- Source task ID: `TP-TASK-001`
- Source phase: `P14A Three-project testing ladder and blind validation readiness`
- Source priority: `P0`
- Source area: `testing/EPIC-146`
- Original depends_on: `P0 blockers; fixture governance; no-raw-data policy`
- Source-only dependency notes: `P0 blockers; fixture governance; no-raw-data policy`
- Recommended source branch: `capex-fixture/* or lab/capex-agent-tasks for agent-only work`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
