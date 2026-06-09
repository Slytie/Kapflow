---
id: TASK-0654
epic: EPIC-143
title: "Add Scope Management workflow specification"
status: TODO
owners: ["capex-product", "capex-architecture"]
reviewers: ["backend", "qa", "capex-sme"]
depends_on: ["TASK-0566", "TASK-0649"]
risk: high
context_packs: ["codex/context/EPIC-143.md"]
patterns: ["SME-RP acceptance conditions", "workflow family definitions"]
---

# TASK-0654 - Add Scope Management Workflow Specification

## Why

Real-project closure can be false if scope dimensions collapse into one status. Scope Management must be a general CAPEX workflow requirement, with K12 only as the first fixture that stresses it.

## Scope

Specify Scope Management as an MVP / early workflow and define its minimum task/workpage routing expectations.

- Bind scope workflow readiness to `capex_scope`.
- Preserve downstream handoff manifest and stale-basis rules.
- Map the workflow to `SME-RP-G003` and `SME-RP-G012`.

## Out of scope

- Runtime workflow activation.
- Frontend implementation.
- K12-only workflow semantics.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-143.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Scope Management is represented as a real-project workflow requirement.
- Scope-specific status can prevent overall closure.
- Downstream workflows cannot consume scope state without canonical handoff basis.

## Source row mapping

- Source task ID: `TASK-0631`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G003;SME-RP-G012`
- Fixture refs: `K12-T1`
- Source conditions: `8-A1;14-D1`
