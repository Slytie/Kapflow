---
id: TASK-0565
epic: EPIC-142
title: "Add ClosureGateEvaluation, ClosureSnapshot, Waiver, lifecycle recurrence stale rules"
status: DONE
completed_at: 2026-06-08T00:00:00Z
owners: ["platform", "security"]
reviewers: ["architect", "qa"]
depends_on: ["TASK-0564"]
risk: high
context_packs:
  - "codex/context/EPIC-142.md"
patterns: ["capex-v6-planning"]
---

## Why
Imported from CAPEX v6 source task `NU-CB-P0-005` so future work can be executed from repo-native backlog memory without loading the full master package.

## Scope
Implement closure/waiver runtime primitives and recurrence-trigger stale/reopen logic.

## Out of scope
- Runtime or production activation beyond this task's explicit source scope.
- Copying raw K12, K3, or blind-validation project files into the repository.
- Treating generated artifacts, lab reports, or AI outputs as canonical authority.

## Source files to read first
- `docs/planning/CAPEX_MASTER_V6_INTAKE.md`
- `docs/planning/CAPEX_V6_CONVERSION_MAP.csv`
- `docs/planning/epics/EPIC-142.md`
- `codex/context/EPIC-142.md`
- `docs/status/CURRENT_FOCUS.md`
- `docs/architecture/invariants.md`

## Plan
1. Re-read the CAPEX intake record, this task's epic context, and the source row in the conversion map.
2. Start with the required tests or evidence listed below, then make the smallest repo-native change that satisfies the task.
3. Update docs/status/test evidence only where the source scope requires it.
4. Preserve tenant/domain isolation, artifact immutability, canonical approvals, and append-only event truth.

## Verification
- Source required tests: CB2-T008; no-false-closure; lifecycle recurrence tests
- Acceptance gate: `NU-GATE-005`
- Run the smallest relevant repo checks for changed code.
- Run `python3 scripts/validate_repo.py` and `git diff --check` before closing the task.

## Acceptance criteria
- Source output satisfied: Schemas/models; closure vector evaluator; recurrence trigger registry
- Review focus covered: Closure is vector; absence not closure; waiver not pass; recurrence can stale state
- Refactor focus covered: Small modules with explicit policy version
- Docs requirement covered: Update formalism and guardrails
- Rollback/recovery posture recorded: Do not expose closure/promotion UI until gates pass

## Source row mapping
- Source task ID: `NU-CB-P0-005`
- Source phase: `P7 governance/closure`
- Source priority: `P0`
- Source area: `capex/governance/closure`
- Original depends_on: `W4 CED-016-019; NU-CB-P0-004`
- Source-only dependency notes: `W4 CED-016-019`
- Recommended source branch: `capex/closure-waiver-runtime`

## Notes / decisions
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.

## Closeout evidence
- Added ordered migration `20260608_0014_capex_closure_governance_runtime.py`, SQLAlchemy models, SQLite bootstrap DDL, runtime schemas, and repositories for `capex_waivers`, `capex_closure_gate_evaluations`, and `capex_closure_snapshots`.
- Added `onetruth.capex_platform.closure_governance` with explicit closure vectors, waiver-aware but non-pass evaluation results, failed-evaluation snapshot rejection, and a small duplicate-safe recurrence registry that marks current closure snapshots stale when basis refs change.
- Closure now depends on resolved source/evidence truth from the SourceRef resolver; absence of evidence remains a failed vector, and waiver satisfaction is recorded as `satisfied_by_waiver` rather than `pass`.
- Evidence: `PYTHONPATH=src python3.11 -m pytest -q tests/unit/test_capex_closure_governance.py` and `PYTHONPATH=src python3.11 -m pytest -q tests/integration/test_capex_closure_governance_schema_parity.py` passed on 2026-06-08.
