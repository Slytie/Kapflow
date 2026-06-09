---
id: TASK-0662
epic: EPIC-149
title: "Add subject-matter boundary negative tests"
status: TODO
owners: ["qa", "capex-architecture"]
reviewers: ["qa", "backend", "capex-sme"]
depends_on: ["TASK-0568", "TASK-0661"]
risk: high
context_packs: ["codex/context/EPIC-149.md"]
patterns: ["SME-RP acceptance conditions", "semantic negative tests", "no false closure"]
---

# TASK-0662 - Add Subject-Matter Boundary Negative Tests

## Why

Real-project acceptance requires negative tests proving no false project status from PR/PO, supplier statements, work performed, scope closure, defect closure, controlling values, minutes, or settlement.

## Scope

Add a subject-matter negative-test planning row for the generalized SME-RP acceptance suite.

- Use the K12 fixture cases as the first binding suite.
- Preserve `SME-RP-G013` as the gate for boundary negative tests.
- Keep test planning inside the existing CAPEX semantic test posture.

## Out of scope

- Implementing all runtime fixture tests in this planning task.
- Raw fixture corpus import.
- Making the semantic test suite authoritative project truth.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-149 and `SME-RP-G013`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Boundary negative tests are general subject-matter obligations.
- K12 fixture cases are the first test suite, not the only accepted future suite.
- False status from commercial, supplier, work-complete, scope, defect, controlling, minutes, or settlement evidence remains blocked.

## Source row mapping

- Source task ID: `TASK-0639`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G013`
- Fixture refs: `K12-T1;K12-T2;K12-T3;K12-T4;K12-T7;K12-T8;K12-T9;K12-T10`
- Source conditions: `4-A2;4-A3;13-A1;14-D6`
