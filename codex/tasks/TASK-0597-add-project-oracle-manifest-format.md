---
id: TASK-0597
epic: EPIC-146
title: "Add project-oracle manifest format"
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
Imported from CAPEX v6 source task `TP-TASK-009` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Represent expected outputs, negative tests and human oracle approval consistently across K12/K3/blind.

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
- Source output satisfied: Add project-oracle manifest format
- Review focus covered: test data governance; no raw corpus leakage; no project-specific hardcoding
- Refactor focus covered: keep fixture/test utilities reusable across K12, K3, and blind validation
- Docs requirement covered: update three-project testing strategy and runbook
- Rollback/recovery posture recorded: remove fixture release; keep raw data quarantined; record waiver if gate cannot pass

## Source row mapping
- Source task ID: `TP-TASK-009`
- Source phase: `P14A Three-project testing ladder and blind validation readiness`
- Source priority: `P1`
- Source area: `testing/EPIC-146`
- Original depends_on: `TP-TASK-001`
- Recommended source branch: `capex-fixture/* or lab/capex-agent-tasks for agent-only work`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added `docs/planning/capex_three_project_validation/PROJECT_ORACLE_MANIFEST_FORMAT.yaml` as planning evidence for `TP-TASK-009`.
- The format covers K12, K3 mini, K3 shadow, and blind baseline tiers with row families for expected outputs, negative tests, human oracle approval, re-review triggers, pointer officialness, authority lifecycle, raw-leakage guards, and no-overfitting classification.
- Added compatibility refs from the K12 expected-output manifest and K3 mini-fixture expectation catalog to the shared oracle format.
- Added contract coverage in `tests/contract/test_capex_real_project_acceptance.py` for required top-level fields, oracle row fields, row-family coverage, human review posture, gate refs, raw-data boundary, and non-activation posture.
- Closeout posture: planning evidence only. No oracle release, fixture release approval, blind baseline run, raw corpus import, public route, workflow pack activation, CAPEX runtime activation, CAPEX product activation, pilot readiness, or production-preflight approval is added.
