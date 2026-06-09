---
id: TASK-0659
epic: EPIC-151
title: "Define procurement fields and executive escalation thresholds"
status: TODO
owners: ["capex-product", "controlling"]
reviewers: ["procurement", "plant-management", "capex-sme", "capex-architecture"]
depends_on: ["TASK-0277", "TASK-0290", "TASK-0571"]
risk: high
context_packs: ["codex/context/EPIC-151.md"]
patterns: ["SME-RP acceptance conditions", "executive transparency", "commercial observation boundary"]
---

# TASK-0659 - Define Procurement Fields And Executive Escalation Thresholds

## Why

Executive transparency and commercial-control workflows need mandatory fields and threshold families, but the architecture must not invent numeric business thresholds.

## Scope

Define procurement mandatory fields and executive escalation threshold families for CAPEX transparency.

- Route procurement and commercial data as observed/reconciled evidence.
- Require SME / PM / Controlling sign-off before thresholds activate.
- Bind the work to `SME-RP-G006` and `SME-RP-G007`.

## Out of scope

- Numeric threshold selection.
- ERP replacement or accounting ledger behavior.
- CEO cockpit runtime implementation.
- CAPEX runtime/product activation.

## Verification

- Contract tests prove the SME-RP register maps this task to EPIC-151.
- CAPEX progress data validation after regeneration.
- `python3 scripts/validate_repo.py`
- `git diff --check`

## Acceptance criteria

- Procurement fields are listed as mandatory planning contract inputs.
- Threshold families are configurable after business sign-off; no numeric thresholds are invented by the platform.
- Commercial evidence cannot directly close technical, effectiveness, handover, or assumption dimensions.

## Source row mapping

- Source task ID: `TASK-0636`
- Source namespace: `SME-K12`
- Repo namespace: `SME-RP`
- Gate refs: `SME-RP-G006;SME-RP-G007`
- Fixture refs: `K12-T4;K12-T7;K12-T10`
- Source conditions: `TOP-11;9-A2;9-A3;9-A4;14-D3;14-D10`
