---
id: TASK-0591
epic: EPIC-146
title: "Build K3 mini-fixture expectation catalog from pass11 artifacts"
status: DONE
completed_at: "2026-06-17T00:00:00Z"
owners: ["qa"]
reviewers: ["platform", "architect"]
depends_on: ["TASK-0589"]
risk: medium
context_packs:
  - "codex/context/EPIC-146.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `TP-TASK-003` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Convert K3 stale/reopen, workpage and schema freeze tables into authority/lifecycle tests.

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
- Source output satisfied: Build K3 mini-fixture expectation catalog from pass11 artifacts
- Review focus covered: test data governance; no raw corpus leakage; no project-specific hardcoding
- Refactor focus covered: keep fixture/test utilities reusable across K12, K3, and blind validation
- Docs requirement covered: update three-project testing strategy and runbook
- Rollback/recovery posture recorded: remove fixture release; keep raw data quarantined; record waiver if gate cannot pass

## Source row mapping
- Source task ID: `TP-TASK-003`
- Source phase: `P14A Three-project testing ladder and blind validation readiness`
- Source priority: `P1`
- Source area: `testing/EPIC-146`
- Original depends_on: `TP-TASK-001`
- Recommended source branch: `capex-fixture/* or lab/capex-agent-tasks for agent-only work`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `docs/planning/capex_three_project_validation/K3_MINI_FIXTURE_EXPECTATION_CATALOG.yaml` as sanitized planning evidence for `TP-TASK-003`.
- The catalog records the observed source synthesis package name and sha256, derived source tables, K3 authority/lifecycle expectation rows, stale/reopen expectations, schema freeze expectations, workpage contract expectations, pointer-policy expectations, approval-validity expectations, rollback/remediation posture, and `TP-G01`, `TP-G04`, `TP-G05`, `TP-G08`, `TP-G11`, and `TP-G12` mappings.
- Added contract coverage in `tests/contract/test_capex_real_project_acceptance.py` for required fields, source package hash, gate refs, expectation rows, freeze families, raw-data boundary, and non-activation posture.
- Closeout posture: planning evidence only. No raw corpus import, fixture release approval, full K3 module activation, public route, workflow pack activation, CAPEX runtime activation, CAPEX product activation, pilot readiness, or production-preflight approval is added.
