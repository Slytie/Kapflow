---
id: TASK-0649
epic: EPIC-140
title: "Define CAPEX scope hierarchy and minimum capex_scope contract"
status: TODO
owners: ["capex-product", "platform"]
reviewers: ["capex-architecture", "backend", "capex-sme"]
depends_on: ["TASK-0261", "TASK-0563"]
risk: high
context_packs: ["codex/context/EPIC-140.md"]
patterns: ["SME-RP acceptance conditions", "scope false-closure prevention"]
---

# TASK-0649 - Define CAPEX Scope Hierarchy And Minimum capex_scope Contract

## Why

Real-project acceptance requires project status to remain separable by scope. K12 motivates the false-closure case, but the contract must be general CAPEX scope truth.

## Scope

Define the minimum `capex_scope` hierarchy and project membership relationship needed before scope-sensitive workflows can activate.

- Specify scope identity, parent/child hierarchy, and project boundary expectations.
- Describe how scope-level status prevents false overall closure.
- Bind the scope contract to `SME-RP-G003`.

## Out of scope

- New database migration or runtime API implementation.
- K12-only scope semantics.
- Project closure or pointer-promotion behavior changes.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-140 and `SME-RP-G003`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Scope hierarchy is described as a general CAPEX real-project contract.
- K12 is referenced only as a motivating fixture case for false-closure coverage.
- No workflow can claim overall closure merely because one scope dimension is closed.

## Source row mapping

- Source task ID: `TASK-0626`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G003`
- Fixture refs: `K12-T1`
- Source conditions: `TOP-02;TOP-03;5-A1;5-A2`
