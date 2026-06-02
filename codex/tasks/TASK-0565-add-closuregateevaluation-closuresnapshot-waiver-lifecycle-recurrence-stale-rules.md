---
id: TASK-0565
epic: EPIC-142
title: "Add ClosureGateEvaluation, ClosureSnapshot, Waiver, lifecycle recurrence stale rules"
status: TODO
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

## Source files to change
- Repo-native source files required by the source scope and the `EPIC-142` context pack.
- Do not edit generated derivatives before updating their authoritative source.

## Generated / downstream artifacts impacted
Schemas/models; closure vector evaluator; recurrence trigger registry

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
- Converted repo dependencies: TASK-0564
- Source dependency notes still to satisfy: W4 CED-016-019
- Recommended source branch: `capex/closure-waiver-runtime`

## Notes / decisions
- This task is initially imported as TODO even if the CAPEX master package described expected future outputs.
- Raw project corpora remain off-repo; use only sanitized fixtures, manifests, hashes, and aggregate evidence approved by the relevant fixture/governance task.
