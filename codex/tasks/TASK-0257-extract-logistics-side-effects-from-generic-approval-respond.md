---
id: TASK-0257
epic: EPIC-139
title: "Extract logistics side effects from generic approval.respond"
status: DONE
owners: ["platform"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0236"]
risk: high
context_packs:
  - "codex/context/EPIC-139.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `CLEAN-001` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Generic approval transition emits event only; logistics finalization moves to domain hook registry.

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
- Source required tests: AT-CLEAN-001..004
- Acceptance gate: `CLEAN-APPROVAL`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: approval side-effect registry; tests proving no logistics effect in generic approval
- Review focus covered: approval path purity; domain hooks explicit
- Refactor focus covered: separate generic from logistics behavior; no semantic rename without tests
- Docs requirement covered: backend boundary docs; ADR logistics side-effect extraction
- Rollback/recovery posture recorded: documented if production-facing

## Source row mapping
- Source task ID: `CLEAN-001`
- Source phase: `P2 Domain boundary`
- Source priority: `P0`
- Source area: `backend/platform-domain`
- Original depends_on: `PR003; repo Pass3`
- Source-only dependency notes: `repo Pass3`
- Recommended source branch: `feature/capex-*`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
- Closed on 2026-06-02 by adding the explicit approval-response hook registry, moving weekly publish and dispatch-reporting finalize behavior into logistics hooks, and recording ADR-005.
- Focused evidence: hook registry unit tests, handler import-boundary contract, CAPEX invariant audit contract, approval CLI/API regressions, weekly publish approve/stale regressions, and dispatch-reporting finalize approve/stale regressions passed.
- Rollback posture: removing the hook registry would intentionally fail the CAPEX invariant audit and boundary contract before generic approval domain coupling can silently return.
