---
id: TASK-0658
epic: EPIC-142
title: "Extend closure model with partial handover and observation phase"
status: TODO
owners: ["capex-architecture", "capex-product"]
reviewers: ["backend", "maintenance", "production", "capex-sme"]
depends_on: ["TASK-0565"]
risk: high
context_packs: ["codex/context/EPIC-142.md"]
patterns: ["SME-RP acceptance conditions", "no false closure", "closure dimensions"]
---

# TASK-0658 - Extend Closure Model With Partial Handover And Observation Phase

## Why

Handover, production release, commercial settlement, and technical effectiveness are distinct. Real-project acceptance requires closure dimensions that cannot be collapsed by supplier statements or partial handover.

## Scope

Extend closure planning with partial handover, observation phase, commissioning, production release, maintenance, documentation, commercial, and effectiveness dimensions.

- Bind the extension to `SME-RP-G008`.
- Preserve existing closure/waiver/recurrence foundation from `TASK-0565`.
- Treat fixture cases as examples of general closure safety.

## Out of scope

- Runtime closure-command implementation.
- Public closure UI or CAPEX workpage route implementation.
- Treating handover as project closure.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-142 and `SME-RP-G008`.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Partial handover can be represented without closing all project dimensions.
- Defect effectiveness can remain open or enter observation phase after supplier repair.
- Commercial settlement remains separate from technical effectiveness and project closure.

## Source row mapping

- Source task ID: `TASK-0635`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G008`
- Fixture refs: `K12-T2;K12-T3;K12-T9;K12-T10`
- Source conditions: `TOP-06;TOP-07;8-A5;8-A6;10-A2;10-A3;10-A4;14-D4;14-D5`
