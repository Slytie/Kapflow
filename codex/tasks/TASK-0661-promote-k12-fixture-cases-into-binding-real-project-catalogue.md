---
id: TASK-0661
epic: EPIC-146
title: "Promote K12 fixture cases into binding real-project catalogue"
status: TODO
owners: ["capex-fixtures", "qa"]
reviewers: ["qa", "data-governance", "capex-sme"]
depends_on: ["TASK-0597", "TASK-0648"]
risk: high
context_packs: ["codex/context/EPIC-146.md"]
patterns: ["SME-RP acceptance conditions", "real-project validation tiers"]
---

# TASK-0661 - Promote K12 Fixture Cases Into Binding Real-Project Catalogue

## Why

K12 is the first binding real-project fixture slice. The cases must become acceptance obligations without making K12 the product model.

## Scope

Promote `K12-T1` through `K12-T10` into the real-project binding acceptance catalogue and oracle mapping plan.

- Keep the top-level acceptance namespace as `SME-RP`.
- Treat K12 IDs as fixture-case IDs only.
- Bind the work to `SME-RP-G010`.

## Out of scope

- Raw K12 corpus import.
- Fixture file generation or leak-scan implementation.
- K12-only product semantics.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove `K12-T1` through `K12-T10` are fixture cases and not gate IDs.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- K12 fixture cases are represented as binding real-project acceptance cases.
- The repo does not introduce a K12-specific gate namespace.
- No fixture case can produce false official project status.

## Source row mapping

- Source task ID: `TASK-0638`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G010`
- Fixture refs: `K12-T1;K12-T2;K12-T3;K12-T4;K12-T5;K12-T6;K12-T7;K12-T8;K12-T9;K12-T10`
- Source conditions: `TOP-12;12-A1;12-A3`
