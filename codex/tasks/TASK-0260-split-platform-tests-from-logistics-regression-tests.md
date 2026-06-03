---
id: TASK-0260
epic: EPIC-139
title: "Split platform tests from logistics regression tests"
status: DONE
completed_at: "2026-06-03T12:00:00+02:00"
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: []
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `CLEAN-004` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Separate platform substrate tests from logistics domain fixtures.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-139.md`
- `codex/context/EPIC-139.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: platform tests pass without logistics fixtures
- Acceptance gate: `CI can run platform subset`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: test directories/tags; CI grouping
- Review focus covered: platform behavior not protected only by logistics examples
- Refactor focus covered: test fixture isolation
- Docs requirement covered: testing guide
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `CLEAN-004`
- Source phase: `P2 Domain boundary`
- Source priority: `P0`
- Source area: `tests`
- Original depends_on: `repo Pass3`
- Source-only dependency notes: `repo Pass3`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed on 2026-06-03 by adding the repo-native `logistics_regression` pytest marker manifest, auto-marking logistics regression tests at collection time, and exposing `platform-substrate-tests` plus `logistics-regression-tests` Make/CI lanes.
- Focused evidence: `tests/contract/test_platform_logistics_test_split.py` proves the manifest covers real tests, logistics fixture roots stay in the logistics lane, and Make/GitHub expose both groups.
- Rollback posture: removing the split should fail the platform/logistics split contract before platform coverage can silently depend on logistics fixture examples again.
